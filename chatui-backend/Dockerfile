# ChatUI backend -- FastAPI AI gateway.
#
# Local llama.cpp is a Windows-oriented process-managed integration (see
# providers/llama_cpp.py) and is intentionally NOT part of this image --
# running it would need a GGUF model volume and a Linux llama-server binary
# neither of which this Dockerfile assumes. In a container, this backend
# runs happily as a pure cloud-provider gateway (OpenAI/Anthropic/Google/
# Groq/custom OpenAI-compatible/web search/image generation); "no local
# models found" is a normal, harmless state (see providers/llama_cpp.py's
# autostart(), which logs and continues rather than failing).

FROM python:3.12-slim

WORKDIR /app

# System deps for pypdf/python-docx are pure-Python; nothing extra needed
# beyond a C toolchain-free slim image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persisted uploads/sqlite DB -- mount a volume here in production so
# documents survive container restarts/redeploys.
RUN mkdir -p /app/data/uploads
VOLUME ["/app/data"]

EXPOSE 8000

# No .env file is copied into the image on purpose -- provider API keys and
# ACCESS_TOKEN must be supplied as real container environment variables
# (see docker-compose.yml), never baked into the image.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
