# ChatUI

A modern, self-hosted AI chat interface backed by a provider-agnostic AI gateway.

ChatUI gives you one unified chat interface for **local llama.cpp models, OpenAI, Anthropic, Google Gemini, Groq, and custom OpenAI-compatible endpoints**, while also supporting streaming responses, document upload and RAG, web search, image generation, authentication, model selection, conversations, and Docker deployment.

The project is designed to let you run AI locally when possible, connect cloud AI providers when needed, or combine both through a single frontend.

---

## Features

* Modern self-hosted chat interface
* Local AI inference with **llama.cpp**
* OpenAI support
* Anthropic support
* Google Gemini support
* Groq support
* Custom OpenAI-compatible providers
* Streaming AI responses
* Document upload
* RAG / document retrieval
* Web search integrations
* Image generation
* Optional access-token authentication
* Model selection
* Conversations
* Built-in rate limiting
* Request and provider metrics
* Structured logging
* Docker deployment
* Windows one-click startup/shutdown
* Linux/macOS startup/shutdown scripts

---

## Project structure

```text
ChatUI/
├── app/                         React + Vite frontend
├── chatui-backend/              FastAPI backend / AI gateway
├── START.bat                    Windows one-click launcher
├── STOP.bat                     Windows shutdown script
├── start.sh                     macOS / Linux launcher
├── stop.sh                      macOS / Linux shutdown script
├── docker-compose.yml           Docker deployment
├── LICENSE
└── README.md
```

---

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/hxrsh7d/ChatUI.git
cd ChatUI
```

### 2. Configure the frontend

Create:

```text
app/.env.local
```

The repository includes a blank template. Add your own backend API URL:

```env
VITE_API_BASE=http://127.0.0.1:8000/api
```

For the default local setup:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
API:      http://127.0.0.1:8000/api
```

If your backend runs on a different host or port, replace the value of `VITE_API_BASE` with your own backend API URL.

> **Important:** `app/.env.local` is environment-specific. Each user should configure it for their own backend installation.

Do not put provider API keys, passwords, or other secrets in the frontend environment file. Provider credentials belong in:

```text
chatui-backend/.env
```

### 3. Configure the backend

Create the backend environment file from the provided example.

From the repository root:

```bash
cd chatui-backend
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Then edit:

```text
chatui-backend/.env
```

You only need to configure the providers and features you want to use.

All provider API keys are optional.

### 4. Start ChatUI

#### Windows

Double-click:

```text
START.bat
```

To stop ChatUI:

```text
STOP.bat
```

The launcher automatically handles the local backend environment, backend dependencies, frontend dependencies, and startup process.

#### macOS / Linux

First time only:

```bash
chmod +x start.sh stop.sh
```

Start:

```bash
./start.sh
```

Stop:

```bash
./stop.sh
```

The startup scripts prepare the required dependencies on the first run and start both the backend and frontend.

Once running, open:

```text
http://127.0.0.1:5173/
```

---

## Local llama.cpp

ChatUI can use local GGUF models through **llama.cpp**.

For the local provider:

1. Install or build llama.cpp.
2. Make sure `llama-server` is available to the backend.
3. Place your GGUF models in the configured models directory.
4. Start ChatUI.
5. Select the available local model from the model selector.

The backend automatically manages the local llama.cpp server process.

### Models directory

The models directory is configured through:

```env
MODELS_DIR=
```

For example:

```env
MODELS_DIR=C:\llama.cpp\models
```

The exact path depends on your local llama.cpp installation.

> **Important:** GGUF model files are not included in this repository. Users must download and configure their own models.

Local models can be large, so make sure your system has sufficient RAM, storage, and CPU resources for the model you choose.

---

## Configuring AI providers

Copy:

```text
chatui-backend/.env.example
```

to:

```text
chatui-backend/.env
```

Then configure whichever providers you want to use.

You do not need to configure every provider.

| Provider / feature           | Configuration                                                                                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| OpenAI                       | `OPENAI_API_KEY`                                                                                               |
| Anthropic                    | `ANTHROPIC_API_KEY`                                                                                            |
| Google Gemini                | `GOOGLE_API_KEY`                                                                                               |
| Groq                         | `GROQ_API_KEY`                                                                                                 |
| Custom OpenAI-compatible API | Configure from **Settings -> Providers -> Add a custom provider**, or use `CUSTOM_OPENAI_COMPATIBLE_PROVIDERS` |
| Web search                   | `SEARCH_PROVIDER` plus the corresponding API key or URL                                                        |
| Image generation             | `IMAGE_PROVIDER=openai` with `OPENAI_API_KEY`                                                                  |

After changing:

```text
chatui-backend/.env
```

restart ChatUI:

Windows:

```text
STOP.bat
START.bat
```

macOS / Linux:

```bash
./stop.sh
./start.sh
```

---

## Provider-independent model routing

The backend exposes a unified API to the frontend.

Models can be identified using either:

```text
<model>
```

or:

```text
<provider>:<model>
```

For example:

```text
openai:gpt-4o-mini
```

This allows the frontend to remain independent of the underlying AI provider.

A local llama.cpp model can continue to use its model filename for backward compatibility.

---

## Document upload and RAG

ChatUI includes a local document retrieval pipeline.

Supported document formats include:

```text
PDF
DOCX
TXT
MD
```

The general pipeline is:

```text
Document upload
      |
      v
Text extraction
      |
      v
Document chunking
      |
      v
Embedding
      |
      v
SQLite storage
      |
      v
Hybrid retrieval
      |
      v
Relevant context
      |
      v
AI response
```

RAG works without a cloud embedding provider by using a local offline fallback.

If OpenAI or Google API credentials are configured, ChatUI can use their embedding capabilities to improve retrieval quality.

The retrieval system combines:

* Embedding similarity
* BM25 lexical search
* Reciprocal Rank Fusion

This allows semantic and keyword-based retrieval to work together.

---

## Web search

ChatUI can integrate web search through supported search providers.

Configure:

```env
SEARCH_PROVIDER=
```

Supported options include:

```text
brave
tavily
searxng
```

Configure the corresponding API key or URL in:

```text
chatui-backend/.env
```

Web search is optional.

---

## Image generation

ChatUI can expose image generation through a supported provider.

For OpenAI image generation:

```env
IMAGE_PROVIDER=openai
```

and configure:

```env
OPENAI_API_KEY=your_key_here
```

Image generation is optional and depends on the configured provider.

---

## Authentication

By default, the backend does **not** require authentication.

This is convenient when running ChatUI privately on your own machine.

However, if you expose the backend to other people or to a network, authentication should be enabled.

### Enable access-token authentication

Generate a secure token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add it to:

```text
chatui-backend/.env
```

For example:

```env
ACCESS_TOKEN=your_generated_token
```

Restart the backend.

Users will be prompted for the access code when they first access ChatUI.

Users can sign out and remove the stored token from:

```text
Settings -> Account
```

> **Security note:** Do not expose an unauthenticated ChatUI backend to an untrusted network.

---

## Rate limiting

Rate limiting is enabled by default.

The default limits are:

```text
20 chat requests / minute / client IP
10 uploads / minute / client IP
```

Configuration is available in:

```text
chatui-backend/.env
```

Relevant settings include:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CHAT_PER_MINUTE=20
RATE_LIMIT_UPLOADS_PER_MINUTE=10
```

To disable rate limiting:

```env
RATE_LIMIT_ENABLED=false
```

Rate limiting is in-memory and per-process. It resets when the backend restarts.

This is intended for the project's single-backend deployment model.

---

## Running the tests

From the repository root:

```bash
cd chatui-backend
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The test suite covers areas including:

* Provider routing
* Custom provider management
* Provider persistence across restart
* Document parsing
* PDF/DOCX fixtures
* Document chunking
* Hybrid RAG retrieval
* Embeddings
* BM25 retrieval
* Upload API behavior
* Access-token enforcement
* Rate limiting
* Structured logging
* Metrics
* Chat endpoint error handling

The tests do not make real network calls to cloud providers.

The test configuration explicitly prevents real provider credentials from being used during the test run.

---

## Observability

### Logs

The launcher scripts produce backend logs next to the launcher files:

```text
chatui-backend-output.log
chatui-backend-error.log
```

For machine-readable JSON logs:

```env
LOG_FORMAT=json
```

The default format is human-readable.

### Metrics

ChatUI exposes:

```text
GET /api/metrics
```

When authentication is enabled, the metrics endpoint is protected by the access token.

Metrics include request counts, errors, latency, and provider-level information.

Metrics are stored in memory and reset when the backend restarts.

---

## Docker deployment

Docker can be used to deploy ChatUI with cloud-based AI providers.

> **Local llama.cpp is not included in the Docker deployment.**

Start the deployment with:

```bash
cp chatui-backend/.env.example chatui-backend/.env
```

Configure your provider credentials and then run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5173
```

### Docker limitations

The local llama.cpp integration is currently a Windows-oriented process-managed integration.

It launches and manages:

```text
llama-server.exe
```

using Windows process/network management commands.

Therefore, local llama.cpp inference is not included in the container image.

Without local models, the Docker deployment can still use the configured cloud providers.

The frontend container serves the production build through nginx.

nginx proxies:

```text
/api
/v1
/health
```

to the backend container so the browser communicates through a single origin.

> **Docker testing note:** The Docker deployment has been configured and reviewed, but it has not been validated end-to-end in an environment with a Docker daemon. Treat the first `docker compose up --build` as the real deployment test and inspect `docker compose logs` if a service does not start correctly.

---

## Architecture

ChatUI is organized around a provider-agnostic backend.

```text
                    +----------------------+
                    |      ChatUI UI       |
                    |   React + Vite       |
                    +----------+-----------+
                               |
                               | HTTP / SSE
                               v
                    +----------------------+
                    |   FastAPI Backend    |
                    |     AI Gateway       |
                    +----------+-----------+
                               |
             +-----------------+-----------------+
             |                 |                 |
             v                 v                 v
      +-------------+   +-------------+   +-------------+
      | llama.cpp   |   | Cloud APIs  |   | Custom API  |
      |   Local     |   | OpenAI etc. |   | Compatible  |
      +------+------+   +-------------+   +-------------+
             |
             v
      +--------------------+
      | Local GGUF Models  |
      +--------------------+
```

### Provider routing

Model IDs are routed through the provider registry.

A bare model filename routes to local llama.cpp for backward compatibility.

Provider-qualified models use:

```text
<provider>:<model>
```

For example:

```text
openai:gpt-4o-mini
```

Implementation:

```text
chatui-backend/providers/registry.py
```

### RAG architecture

The document pipeline is implemented under:

```text
chatui-backend/documents/
```

It performs:

```text
Upload
  |
  v
Extraction
  |
  v
Chunking
  |
  v
Embedding
  |
  v
SQLite
  |
  v
Hybrid retrieval
  |
  v
Context injection
```

Retrieval combines embedding similarity and BM25 lexical scoring and fuses the rankings using Reciprocal Rank Fusion.

### Streaming architecture

Provider adapters expose a common streaming contract.

The backend emits a consistent set of SSE event types, including:

```text
token
search_status
citations
image
error
done
```

This allows the React frontend to remain provider-agnostic while supporting different AI backends.

Implementation:

```text
chatui-backend/providers/base.py
```

---

## Development

### Frontend

The frontend is built with:

```text
React
TypeScript
Vite
```

To work on the frontend:

```bash
cd app
npm install
npm run dev
```

The development server runs on:

```text
http://localhost:5173
```

The Vite development server proxies API requests to the local backend.

### Backend

The backend is built with:

```text
Python
FastAPI
```

Backend development dependencies can be installed with:

```bash
cd chatui-backend
pip install -r requirements.txt -r requirements-dev.txt
```

Run the tests with:

```bash
pytest
```

---

## Environment files

ChatUI uses separate environment configuration for the frontend and backend.

```text
app/.env.local
chatui-backend/.env
```

### Frontend

```env
VITE_API_BASE=http://127.0.0.1:8000/api
```

### Backend

Copy:

```text
chatui-backend/.env.example
```

to:

```text
chatui-backend/.env
```

and configure the providers you want to use.

Never publish real API keys or credentials.

---

## Troubleshooting

### ChatUI opens but cannot connect to the backend

Check:

```text
app/.env.local
```

and verify:

```env
VITE_API_BASE=http://127.0.0.1:8000/api
```

Then make sure the backend is running.

Check:

```text
http://127.0.0.1:8000/health
```

### Backend does not start

Check the backend logs:

```text
chatui-backend-error.log
chatui-backend-output.log
```

Also verify that Python and the required backend dependencies are installed.

### Local model does not appear

Check:

```env
MODELS_DIR=
```

Make sure the configured directory exists and contains compatible GGUF model files.

Remember that ChatUI does not distribute GGUF models.

### Cloud provider does not appear

Verify that the corresponding API key is configured in:

```text
chatui-backend/.env
```

For example:

```env
OPENAI_API_KEY=your_key_here
```

Then restart ChatUI.

### Frontend dependencies are missing

From:

```text
app/
```

run:

```bash
npm install
```

Then restart the frontend.

---

## Privacy and deployment model

ChatUI can be used as a completely local interface when configured with llama.cpp and local models.

In that configuration:

```text
User
  |
  v
ChatUI
  |
  v
FastAPI backend
  |
  v
llama.cpp
  |
  v
Local GGUF model
```

No cloud AI provider is required for local inference.

When cloud providers are configured, requests intended for those providers are sent to the corresponding external service according to that provider's API behavior and your configuration.

Users should review the privacy and data-handling policies of any external provider they enable.

---

## Project goals

ChatUI is designed around a simple idea:

> **One interface, multiple AI backends.**

Instead of building a separate interface for every AI provider, ChatUI provides a common frontend and a provider-agnostic gateway.

This makes it possible to:

* Run models locally
* Switch between AI providers
* Add custom OpenAI-compatible endpoints
* Use cloud AI when local inference is not practical
* Search the web
* Work with uploaded documents
* Generate images
* Keep the frontend independent from individual provider APIs

---

## License

See [`LICENSE`](LICENSE) for the project's license.

---

## Repository

GitHub:

https://github.com/hxrsh7d/ChatUI

---

## Status

ChatUI is an actively developed self-hosted AI interface.

The local development workflow has been verified from a fresh GitHub clone, including frontend installation, backend startup, local llama.cpp integration, model loading, and AI chat functionality.

Docker deployment is provided as an additional deployment option and should be tested in the target Docker environment before production use.
