"""
Local llama.cpp provider.

This is a straight refactor of the original single-file backend's
llama-server process management (discovery, start/stop/switch, health,
streaming) into the new provider interface. The behavior is preserved
exactly -- same env vars, same Windows process handling, same
verification-before-declaring-success semantics -- it is just reachable
through `AIProvider` now instead of being hard-coded into main.py.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

import config
from logging_config import get_logger
from providers.base import AIProvider, Capabilities, ModelInfo, ProviderError

logger = get_logger("llama_cpp")


class LlamaCppProvider(AIProvider):
    id = "local"
    display_name = "llama.cpp (local)"

    def __init__(self) -> None:
        self.llama_cpp_exe = Path(config.LLAMA_CPP_EXE)
        self.models_dir = Path(config.MODELS_DIR)
        self.host = config.LLAMA_HOST
        self.port = config.LLAMA_PORT
        self.url = f"http://{self.host}:{self.port}"
        self.default_model = config.LLAMA_DEFAULT_MODEL

        self.process: Optional[subprocess.Popen] = None
        self.loaded_model: Optional[str] = None
        self._switch_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_model_files(self) -> list[Path]:
        if not self.models_dir.exists():
            return []
        return sorted(
            (p for p in self.models_dir.iterdir() if p.is_file() and p.suffix.lower() == ".gguf"),
            key=lambda p: p.name.lower(),
        )

    async def is_configured(self) -> bool:
        return bool(self.discover_model_files())

    async def list_models(self) -> list[ModelInfo]:
        models = []
        for path in self.discover_model_files():
            try:
                size_gb = path.stat().st_size / (1024**3)
            except OSError:
                size_gb = 0
            models.append(
                ModelInfo(
                    id=path.name,  # unprefixed, for backward compatibility
                    name=path.stem.replace("-", " ").replace("_", " "),
                    provider="local",
                    group="llama.cpp",
                    description=f"Local GGUF model ({size_gb:.2f} GB)",
                    capabilities=Capabilities(
                        chat=True,
                        streaming=True,
                        vision=False,
                        documents=True,
                        tools=False,
                        web_search=False,
                        image_generation=False,
                    ),
                )
            )
        return models

    # ------------------------------------------------------------------
    # Process / port management (unchanged behavior from the original
    # single-file backend)
    # ------------------------------------------------------------------

    @staticmethod
    def _port_is_open(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def _get_windows_pids_on_port(self, port: int) -> list[int]:
        if os.name != "nt":
            return []
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return []

        pids: set[int] = set()
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            protocol, local_address, _, state, pid_text = parts[0], parts[1].lower(), parts[2], parts[3].upper(), parts[4]
            if protocol.upper() != "TCP" or state != "LISTENING":
                continue
            if not local_address.endswith(f":{port}"):
                continue
            if not (
                local_address.startswith(f"{self.host.lower()}:")
                or local_address.startswith("0.0.0.0:")
                or local_address.startswith("[::]:")
            ):
                continue
            try:
                pids.add(int(pid_text))
            except ValueError:
                continue
        return sorted(pids)

    def _get_process_command_line(self, pid: int) -> str:
        if os.name != "nt":
            return ""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f'(Get-CimInstance Win32_Process -Filter "ProcessId = {pid}").CommandLine',
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _is_llama_server_pid(self, pid: int) -> bool:
        command_line = self._get_process_command_line(pid).lower()
        if not command_line:
            return False
        return "llama-server.exe" in command_line or "llama-server" in command_line

    def _kill_process(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.returncode == 0
        except Exception:
            return False

    def _stop_backend_process(self) -> None:
        if self.process is None:
            return
        try:
            if self.process.poll() is None:
                if os.name == "nt":
                    self._kill_process(self.process.pid)
                else:
                    self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                    try:
                        self.process.wait(timeout=3)
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            self.process = None

    def stop_server_on_configured_port(self) -> None:
        self._stop_backend_process()
        if os.name != "nt":
            return
        for pid in self._get_windows_pids_on_port(self.port):
            if pid == os.getpid():
                continue
            if self._is_llama_server_pid(pid):
                self._kill_process(pid)
        deadline = time.time() + 10
        while time.time() < deadline:
            if not self._port_is_open(self.host, self.port):
                break
            time.sleep(0.25)

    # ------------------------------------------------------------------
    # llama-server HTTP helpers
    # ------------------------------------------------------------------

    async def server_ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.url}/v1/models")
                return response.status_code == 200
        except Exception:
            return False

    async def get_loaded_model_from_server(self) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.url}/v1/models")
                if response.status_code != 200:
                    return None
                data = response.json()
                models = data.get("data", [])
                if not isinstance(models, list) or not models:
                    return None
                model_id = models[0].get("id", "")
                if not model_id:
                    return None
                return Path(str(model_id)).name
        except Exception:
            return None

    async def _wait_for_server(self, timeout: int = 90) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if await self.server_ready():
                return True
            await asyncio.sleep(0.5)
        return False

    async def _wait_until_port_free(self, timeout: int = 10) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if not self._port_is_open(self.host, self.port):
                return True
            await asyncio.sleep(0.25)
        return False

    # ------------------------------------------------------------------
    # Load / switch model
    # ------------------------------------------------------------------

    async def load_model(self, model_name: str) -> dict[str, Any]:
        async with self._switch_lock:
            if not isinstance(model_name, str) or not model_name.strip():
                return {"success": False, "error": "No model specified."}
            model_name = model_name.strip()

            requested_path = Path(model_name)
            if requested_path.name != model_name:
                return {"success": False, "error": "Invalid model filename."}

            model_path = self.models_dir / model_name
            if not model_path.exists():
                return {"success": False, "error": f"Model not found: {model_name}"}
            if not model_path.is_file():
                return {"success": False, "error": f"Model is not a file: {model_name}"}
            if model_path.suffix.lower() != ".gguf":
                return {"success": False, "error": "Only GGUF models are supported."}
            if not self.llama_cpp_exe.exists():
                return {"success": False, "error": f"llama-server.exe not found at: {self.llama_cpp_exe}"}

            current_server_model = None
            if await self.server_ready():
                current_server_model = await self.get_loaded_model_from_server()

            if current_server_model and current_server_model.lower() == model_name.lower():
                self.loaded_model = current_server_model
                return {"success": True, "model": current_server_model, "message": "Model already loaded."}

            self.loaded_model = None
            self.stop_server_on_configured_port()

            if not await self._wait_until_port_free(timeout=10):
                return {
                    "success": False,
                    "error": f"Port {self.port} is still occupied. Unable to safely switch llama-server.",
                }

            command = [str(self.llama_cpp_exe), "-m", str(model_path), "--host", self.host, "--port", str(self.port)]

            try:
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                self.process = subprocess.Popen(
                    command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags
                )
            except Exception as exc:
                self.process = None
                self.loaded_model = None
                return {"success": False, "error": f"Failed to start llama-server: {exc}"}

            if not await self._wait_for_server(timeout=90):
                self._stop_backend_process()
                self.loaded_model = None
                return {"success": False, "error": "llama-server started but did not become ready within 90 seconds."}

            actual_model = await self.get_loaded_model_from_server()
            if not actual_model:
                self._stop_backend_process()
                self.loaded_model = None
                return {"success": False, "error": "llama-server became ready, but the loaded model could not be determined."}

            if actual_model.lower() != model_name.lower():
                self._stop_backend_process()
                self.loaded_model = None
                return {
                    "success": False,
                    "error": f"Model switch verification failed. Requested '{model_name}', but llama-server reports '{actual_model}'.",
                    "requested_model": model_name,
                    "actual_model": actual_model,
                }

            self.loaded_model = actual_model
            return {"success": True, "model": actual_model, "message": f"Loaded {actual_model}"}

    async def health(self) -> dict[str, Any]:
        server_running = await self.server_ready()
        actual_model = None
        if server_running:
            actual_model = await self.get_loaded_model_from_server()
            self.loaded_model = actual_model
        else:
            self.loaded_model = None
        return {
            "status": "ok",
            "llama_server": server_running,
            "loaded_model": self.loaded_model,
            "models_directory": str(self.models_dir),
            "models_available": len(self.discover_model_files()),
        }

    async def autostart(self) -> None:
        models = self.discover_model_files()
        if not models:
            logger.info(f"No GGUF models found in {self.models_dir}")
            return

        default_model = self.default_model or models[0].name
        available_names = {m.name.lower() for m in models}

        if default_model.lower() not in available_names:
            logger.warning(f"Configured default model '{default_model}' was not found.")
            logger.info("Available models: " + ", ".join(m.name for m in models))
            default_model = models[0].name
            logger.info(f"Falling back to '{default_model}'.")

        logger.info(f"Starting llama-server with '{default_model}'...")
        result = await self.load_model(default_model)
        if result.get("success"):
            logger.info(f"llama-server ready. Loaded model: {result.get('model')}")
        else:
            logger.error(f"Failed to start llama-server: {result.get('error', 'Unknown error')}")

    async def shutdown(self) -> None:
        self.stop_server_on_configured_port()
        self.loaded_model = None

    # ------------------------------------------------------------------
    # Chat streaming
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
        images: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if not await self.server_ready():
            raise ProviderError("llama-server is not running. Load a model first.", kind="provider_unavailable")

        actual_model = await self.get_loaded_model_from_server()
        if not actual_model:
            raise ProviderError("llama-server is running, but no loaded model could be detected.", kind="model_unavailable")

        self.loaded_model = actual_model

        full_messages = list(messages)
        if system:
            full_messages = [{"role": "system", "content": system}, *full_messages]

        payload = {
            "model": actual_model,
            "messages": full_messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.url}/v1/chat/completions", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise ProviderError(error_text.decode(errors="replace"), kind="provider_unavailable", status_code=response.status_code)

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield {"type": "token", "content": content}
