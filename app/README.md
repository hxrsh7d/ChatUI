# ChatUI Frontend

An independent, self-hosted chatbot frontend built to closely match the **Open WebUI**
user experience (layout, spacing, typography, interaction patterns), but implemented
from scratch as a clean React + TypeScript app with **no Open WebUI backend
dependencies**. It talks only to your own Python/FastAPI backend.

```
Browser → This Frontend → Python/FastAPI → llama.cpp / OpenAI / Groq / RAG / Web Search / Image Gen
```

All provider API keys and credentials stay on your backend. The frontend never sees
or stores them.

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS (custom neutral palette matched to Open WebUI's grayscale + Inter font)
- Zustand (state, persisted to `localStorage`)
- react-markdown + rehype-highlight (streaming-safe markdown + code highlighting)
- lucide-react (icons)

## Getting started

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api -> http://localhost:8000
npm run build       # production build to dist/
npm run preview     # preview the production build
```

Copy `.env.example` to `.env` and adjust `VITE_API_BASE` if your backend isn't on
`localhost:8000` or not proxied through `/api`.

**No backend yet?** The app still runs. `src/services/api.ts` automatically falls
back to a local mock (simulated streaming, uploads, search citations, and image
generation) whenever a real request fails, so you can develop and demo the UI before
the backend exists. Once your FastAPI server responds, the mock is never triggered.

## Project structure

```
src/
├── components/
│   ├── chat/        MessageList, MessageBubble, Markdown, Citations, Placeholder
│   ├── composer/     Composer (attach, web search / image toggles, send/stop)
│   ├── documents/    FileChip (upload progress / status)
│   ├── layout/       Sidebar, Navbar, MobileDrawer
│   ├── models/       ModelSelector (grouped by provider)
│   ├── settings/     SettingsModal + 9 tabs (General, Appearance, Models, …)
│   └── common/       Button, IconButton, Modal, DropdownMenu, Avatar
├── pages/            ChatPage
├── hooks/            useTheme, useMediaQuery
├── services/         api.ts — the only place that talks to the backend
├── stores/           chatStore (conversations/streaming), uiStore (theme, models, …)
├── types/            shared TS types
└── utils/            date/grouping/formatting helpers
```

## Backend API contract

Implement these endpoints on your FastAPI backend. Paths are relative to
`VITE_API_BASE` (default `/api`), except `GET /v1/models` which is fetched from
the site root to match the OpenAI-style convention requested in the brief.

### `GET /v1/models`
Returns the available models (no hard-coded list in the frontend).

```json
{
  "data": [
    { "id": "qwen2.5-14b-instruct", "name": "Qwen 2.5 14B Instruct", "provider": "local", "group": "llama.cpp" },
    { "id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "group": "OpenAI" }
  ]
}
```
`provider` should be one of `local | openai | groq | other` — used to group the
model selector and choose an icon.

### `POST /api/chat`
Streams a chat completion. Send `Content-Type: application/json`:

```json
{
  "model": "qwen2.5-14b-instruct",
  "messages": [{ "role": "user", "content": "Hello" }],
  "stream": true,
  "web_search": false,
  "image_generation": false,
  "attachment_ids": []
}
```

Response: a streamed body of newline-delimited JSON events (SSE-style `data:` lines
are also accepted). Recognized event types:

```
{"type":"token","content":"Hel"}
{"type":"token","content":"lo"}
{"type":"search_status","status":"Searching the web…"}
{"type":"citations","citations":[{"id":"1","title":"…","url":"https://…","snippet":"…"}]}
{"type":"image","image":{"id":"1","url":"https://…","prompt":"…"}}
{"type":"error","message":"…"}
{"type":"done"}
```
Only `token` events are required for a minimal implementation.

### `POST /api/documents`
`multipart/form-data` file upload (field name `file`). Return:
```json
{ "id": "doc_123", "name": "notes.pdf", "url": "https://…" }
```
Upload progress is tracked client-side via `XMLHttpRequest`.

### `GET /api/auth/me`
```json
{ "id": "u1", "name": "Ada", "email": "ada@example.com", "role": "admin" }
```
`role` gates the Admin tab in Settings.

### `GET /api/conversations`, `DELETE /api/conversations/{id}`
Optional — conversations are persisted client-side by default. Implement these if
you want server-side history/sync; wire them up in `src/services/api.ts` and
`src/stores/chatStore.ts`.

## Notes

- Auth: if your backend requires a bearer token, store it in
  `localStorage.setItem('auth_token', ...)` — `services/api.ts` attaches it
  automatically to every request.
- Theming: light/dark/system, toggled from the navbar or Settings → Appearance.
- Responsive: sidebar becomes a slide-in drawer under the `md` breakpoint (768px);
  composer, message bubbles, and code blocks were tested down to 320px.
