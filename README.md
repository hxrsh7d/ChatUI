# ChatUI

A modern, self-hosted AI chat interface powered by a provider-agnostic AI gateway.

ChatUI brings multiple AI providers, local models, document-based conversations, web search, and image generation together behind a unified interface.

## Features

* 🤖 **Multiple AI Providers**

  * Local llama.cpp
  * OpenAI
  * Anthropic
  * Google Gemini
  * Groq
  * Custom OpenAI-compatible APIs

* 💬 **Modern AI Chat Interface**

  * Streaming responses
  * Provider-agnostic architecture
  * Unified chat experience

* 📄 **Document Upload and RAG**

  * PDF support
  * DOCX support
  * TXT and Markdown support
  * Local offline retrieval
  * Optional OpenAI and Google embeddings

* 🌐 **Web Search**

  * Brave Search
  * Tavily
  * SearXNG

* 🎨 **Image Generation**

  * AI-powered image generation through supported providers

* 🔒 **Security Features**

  * Optional access-token protection
  * Rate limiting
  * Environment-based API key configuration

* 🖥️ **Cross-Platform Support**

  * Windows one-click startup
  * macOS and Linux shell scripts
  * Docker deployment support

---

## Architecture

```text
ChatUI
│
├── app/                    # React + Vite frontend
│
├── chatui-backend/         # FastAPI AI gateway
│   ├── providers/          # AI provider integrations
│   ├── documents/          # Document processing and RAG
│   ├── tests/              # Backend tests
│   └── api/                # API endpoints
│
├── START.bat               # Windows launcher
├── STOP.bat                # Windows shutdown script
├── start.sh                # macOS / Linux launcher
├── stop.sh                 # macOS / Linux shutdown script
│
└── docker-compose.yml      # Docker deployment
```

---

# Quick Start

## Windows

The easiest way to start ChatUI on Windows is to double-click:

```text
START.bat
```

The first run automatically:

1. Creates the Python virtual environment
2. Installs backend dependencies
3. Installs frontend dependencies
4. Starts the backend
5. Starts the frontend
6. Opens ChatUI in your browser

To stop ChatUI, run:

```text
STOP.bat
```

---

## macOS / Linux

Make the scripts executable:

```bash
chmod +x start.sh stop.sh
```

Start ChatUI:

```bash
./start.sh
```

Stop ChatUI:

```bash
./stop.sh
```

---

## Accessing ChatUI

After startup, open:

```text
http://127.0.0.1:5173/
```

---

# AI Provider Configuration

Copy the backend environment template:

```text
chatui-backend/.env.example
```

Create:

```text
chatui-backend/.env
```

Then configure the providers you want to use.

| Provider      | Environment Variable |
| ------------- | -------------------- |
| OpenAI        | `OPENAI_API_KEY`     |
| Anthropic     | `ANTHROPIC_API_KEY`  |
| Google Gemini | `GOOGLE_API_KEY`     |
| Groq          | `GROQ_API_KEY`       |

You can also configure:

* Custom OpenAI-compatible APIs
* Local llama.cpp models
* Web search providers
* Image generation providers

> **Important:** Never commit your `.env` file or API keys to GitHub.

---

# Local llama.cpp

ChatUI supports running local AI models through llama.cpp.

The application can use local models while also supporting cloud-based AI providers.

Configure the llama.cpp executable and model directory through your backend environment configuration.

---

# Document RAG

ChatUI supports document-based conversations through a Retrieval-Augmented Generation (RAG) pipeline.

Supported formats include:

* PDF
* DOCX
* TXT
* Markdown

The default retrieval pipeline works locally and offline.

When configured, OpenAI or Google embeddings can be used to improve document retrieval quality.

The retrieval pipeline includes:

```text
Document Upload
      ↓
Text Extraction
      ↓
Chunking
      ↓
Embedding
      ↓
Storage
      ↓
Hybrid Retrieval
      ↓
AI Response
```

---

# Web Search

ChatUI supports multiple web-search providers.

Available options include:

* Brave Search
* Tavily
* SearXNG

Configure the search provider through the backend environment file.

---

# Image Generation

ChatUI supports AI-powered image generation through configured providers.

For OpenAI-based image generation:

```text
IMAGE_PROVIDER=openai
```

An appropriate provider API key must also be configured.

---

# Security

## Access Token Protection

By default, a local ChatUI installation can run without authentication.

If you plan to expose your instance to other users or a network, configure an access token.

Generate a secure token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then add it to:

```text
chatui-backend/.env
```

```text
ACCESS_TOKEN=your-secure-token
```

Restart ChatUI after changing the configuration.

## Rate Limiting

Rate limiting is enabled by default.

The limits can be configured through environment variables, including:

```text
RATE_LIMIT_ENABLED
RATE_LIMIT_CHAT_PER_MINUTE
RATE_LIMIT_UPLOADS_PER_MINUTE
```

---

# Running Tests

Navigate to the backend:

```bash
cd chatui-backend
```

Install the development dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Run the test suite:

```bash
pytest
```

The project includes tests covering important backend functionality such as provider routing, document processing, RAG, authentication, rate limiting, logging, metrics, and API error handling.

---

# Observability

ChatUI provides runtime logging and metrics.

## Logs

Runtime logs can include:

```text
chatui-backend-output.log
chatui-backend-error.log
```

Structured JSON logging can be enabled through the backend configuration.

## Metrics

The backend provides a metrics endpoint:

```text
GET /api/metrics
```

When access-token protection is enabled, this endpoint is protected accordingly.

---

# Docker Deployment

Create the backend environment file:

```bash
cp chatui-backend/.env.example chatui-backend/.env
```

Configure your desired providers and API keys.

Then run:

```bash
docker compose up --build
```

After the containers start, open:

```text
http://localhost:5173
```

> The current Docker configuration is intended for cloud-provider deployments. Local llama.cpp integration may require host-specific configuration outside the container environment.

---

# Project Principles

ChatUI is designed around several principles:

* **Provider independence**
* **Local and cloud AI support**
* **Simple deployment**
* **User-controlled configuration**
* **Privacy-friendly local capabilities**
* **Extensible architecture**

The frontend communicates with a unified backend API rather than directly depending on individual AI providers.

This architecture makes it easier to add or change AI providers without redesigning the entire user interface.

---

# Contributing

Contributions, suggestions, bug reports, and feature requests are welcome.

Before submitting changes:

1. Test your changes locally.
2. Avoid committing API keys or `.env` files.
3. Follow the existing project structure.
4. Run the test suite when modifying backend functionality.

---

# License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.

---

## Author

**Harshad More**

---

### ⚠️ Security Notice

Never upload API keys, access tokens, passwords, or private environment files to a public repository.

Always use `.env.example` files to demonstrate configuration without exposing real credentials.
