"""
Core of the AI gateway: turns one normalized chat request into a stream of
SSE-ready event dicts, regardless of which provider ends up serving it.

This is where item 20 ("Chat Request Model") and item 15 ("Web Search
Flow") / item 13 ("Document Chat") come together: the frontend always POSTs
the same shape to /api/chat, and this module decides -- based on the
resolved model's capabilities and the request flags -- whether to run
RAG retrieval, web search grounding, image generation, or a plain chat
call, then normalizes whatever the chosen provider returns back into the
same event vocabulary the existing frontend SSE parser already handles.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from documents import store as doc_store
from documents.rag import build_context_block as build_doc_context, retrieve as retrieve_chunks
from images.registry import get_active_provider as get_active_image_provider
from logging_config import get_logger
from metrics import metrics
from providers.base import ProviderError
from providers.registry import registry
from search.registry import build_context_block as build_search_context, get_active_provider as get_active_search_provider

logger = get_logger("chat")


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content")
            return content if isinstance(content, str) else ""
    return ""


async def _collect_attachment_context(attachment_ids: list[str], query: str) -> tuple[str, list[dict[str, Any]]]:
    """Returns (text_context_from_documents, image_attachments_for_vision)."""
    if not attachment_ids:
        return "", []

    docs = {d["id"]: d for d in doc_store.get_documents(attachment_ids)}
    text_doc_ids = [doc_id for doc_id, d in docs.items() if d.get("kind", "text") == "text"]
    image_doc_ids = [doc_id for doc_id, d in docs.items() if d.get("kind") == "image"]

    text_context = ""
    if text_doc_ids:
        chunks = await retrieve_chunks(query, text_doc_ids)
        text_context = build_doc_context(chunks)

    images: list[dict[str, Any]] = []
    if image_doc_ids:
        for blob in doc_store.get_image_blobs(image_doc_ids):
            images.append({"mime_type": blob["mime_type"], "data_base64": blob["data_base64"]})

    return text_context, images


async def stream_chat_response(request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    model_id = request.get("model")
    messages = request.get("messages", [])
    web_search_requested = bool(request.get("webSearch"))
    image_generation_requested = bool(request.get("imageGeneration"))
    attachment_ids = request.get("attachmentIds") or []
    max_tokens = int(request.get("maxTokens") or 1024)

    if not isinstance(messages, list) or not messages:
        yield {"type": "error", "message": "No messages provided."}
        return

    query = _last_user_text(messages)

    try:
        provider, provider_model_id = registry.resolve(model_id)
    except ProviderError as exc:
        yield {"type": "error", "message": exc.message}
        return

    # ------------------------------------------------------------------
    # Image generation is a distinct concept from chat (item 17/18): if
    # requested, we don't run a text completion at all -- the user's
    # message IS the image prompt.
    # ------------------------------------------------------------------
    if image_generation_requested:
        image_provider = await get_active_image_provider()
        if image_provider is None:
            yield {
                "type": "error",
                "message": "Image generation is not configured on this backend. Set IMAGE_PROVIDER and the matching API key.",
            }
            return

        yield {"type": "search_status", "status": "Generating image…"}
        start = time.perf_counter()
        try:
            image = await image_provider.generate(query or "An image")
        except Exception as exc:  # noqa: BLE001
            metrics.record_provider_call(f"image:{image_provider.id}", time.perf_counter() - start, is_error=True)
            logger.warning(f"image generation failed via {image_provider.id}: {exc}")
            yield {"type": "error", "message": f"Image generation failed: {exc}"}
            return
        metrics.record_provider_call(f"image:{image_provider.id}", time.perf_counter() - start, is_error=False)

        yield {"type": "image", "image": {"id": provider_model_id or "image", "url": image.url, "prompt": image.prompt}}
        yield {"type": "done"}
        return

    # ------------------------------------------------------------------
    # Normal chat: gather RAG context, web search context, and vision
    # attachments before calling the resolved provider.
    # ------------------------------------------------------------------
    system_parts: list[str] = []

    doc_context, image_attachments = await _collect_attachment_context(attachment_ids, query)
    if doc_context:
        system_parts.append(doc_context)

    if image_attachments:
        models = await provider.list_models()
        matched = next((m for m in models if m.id == model_id), None)
        supports_vision = bool(matched and matched.capabilities.vision)
        if not supports_vision:
            yield {
                "type": "error",
                "message": "The selected model doesn't support image input. Choose a vision-capable model to use image attachments.",
            }
            return

    if web_search_requested:
        search_provider = await get_active_search_provider()
        if search_provider is None:
            yield {
                "type": "error",
                "message": "Web search is not configured on this backend. Set SEARCH_PROVIDER and the matching API key.",
            }
            return

        yield {"type": "search_status", "status": f"Searching the web for \u201c{query[:80]}\u201d…"}
        try:
            results = await search_provider.search(query, max_results=5)
        except Exception as exc:  # noqa: BLE001
            yield {"type": "error", "message": f"Web search failed: {exc}"}
            return

        if results:
            citations = [{"id": str(i), "title": r.title, "url": r.url, "snippet": r.snippet} for i, r in enumerate(results, start=1)]
            yield {"type": "citations", "citations": citations}
            system_parts.append(build_search_context(results))
        yield {"type": "search_status", "status": ""}

    system_prompt = "\n\n---\n\n".join(system_parts) if system_parts else None

    start = time.perf_counter()
    try:
        async for event in provider.stream_chat(
            provider_model_id,
            messages,
            max_tokens=max_tokens,
            system=system_prompt,
            images=image_attachments or None,
        ):
            yield event
    except ProviderError as exc:
        metrics.record_provider_call(provider.id, time.perf_counter() - start, is_error=True)
        logger.warning(f"provider call failed via {provider.id}: {exc.message}")
        yield {"type": "error", "message": exc.message}
        return
    except Exception as exc:  # noqa: BLE001
        metrics.record_provider_call(provider.id, time.perf_counter() - start, is_error=True)
        logger.error(f"unexpected error calling {provider.id}: {exc}")
        yield {"type": "error", "message": f"Unexpected error: {exc}"}
        return

    metrics.record_provider_call(provider.id, time.perf_counter() - start, is_error=False)
    yield {"type": "done"}
