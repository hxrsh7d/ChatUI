
import type {
  Attachment,
  ChatSendOptions,
  Citation,
  GeneratedImage,
  Message,
  ModelInfo,
  User
} from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

// ---------------------------------------------------------------------------
// Low-level fetch helpers
// ---------------------------------------------------------------------------

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_token');

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
}

// ---------------------------------------------------------------------------
// Access token (only relevant when the backend has ACCESS_TOKEN configured)
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  return localStorage.getItem('auth_token');
}

export function setAccessToken(token: string): void {
  localStorage.setItem('auth_token', token);
}

export function clearAccessToken(): void {
  localStorage.removeItem('auth_token');
}

export type AccessCheckResult = 'ok' | 'unauthorized' | 'unreachable';

// Lightweight, dedicated check used by the access gate on load (and after
// the user submits a token). Deliberately separate from fetchHealth() so a
// 401 can be distinguished cleanly from "backend is down", which the rest
// of the app already handles on its own via the existing model-load error
// banner.
export async function verifyAccess(): Promise<AccessCheckResult> {
  const baseUrl = API_BASE.replace(/\/api\/?$/, '');
  try {
    const res = await fetch(`${baseUrl}/health`, {
      headers: { ...authHeaders() }
    });
    if (res.status === 401) return 'unauthorized';
    if (res.ok) return 'ok';
    return 'unreachable';
  } catch {
    return 'unreachable';
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init?.headers ?? {})
    }
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');

    throw new Error(
      `${res.status} ${res.statusText}: ${text}`
    );
  }

  const contentType =
    res.headers.get('content-type') ?? '';

  if (contentType.includes('application/json')) {
    return res.json();
  }

  return undefined as unknown as T;
}

// ---------------------------------------------------------------------------
// Models
//
// GET /v1/models
//
// Models come ONLY from the real backend.
// There is intentionally NO fake/mock model fallback.
// ---------------------------------------------------------------------------

export async function fetchModels(): Promise<ModelInfo[]> {
  const baseUrl = API_BASE.replace(/\/api\/?$/, '');

  const res = await fetch(
    `${baseUrl}/v1/models`,
    {
      headers: {
        ...authHeaders()
      }
    }
  );

  if (!res.ok) {
    throw new Error(
      `Failed to fetch models (${res.status} ${res.statusText})`
    );
  }

  const data = await res.json();

  const list = Array.isArray(data)
    ? data
    : Array.isArray(data?.data)
      ? data.data
      : [];

  return list
    .filter((m: any) => m?.id)
    .map((m: any): ModelInfo => ({
      id: String(m.id),

      name: String(
        m.name ??
        String(m.id)
          .replace(/\.[^.]+$/, '')
          .replace(/[-_]+/g, ' ')
      ),

      provider:
        m.provider ??
        m.owned_by ??
        'local',

      group:
        m.group ??
        'llama.cpp',

      description:
        m.description,

      contextLength:
        m.context_length
    }));
}

// ---------------------------------------------------------------------------
// Model loading
//
// POST /api/models/load
//
// Body:
// {
//   "model": "qwen2.5-3b-instruct-q4_k_m.gguf"
// }
// ---------------------------------------------------------------------------

export interface LoadModelResponse {
  success: boolean;
  model: string;
  message: string;
}

export async function loadModel(
  model: string
): Promise<LoadModelResponse> {
  if (!model) {
    throw new Error('No model selected.');
  }

  const res = await fetch(
    `${API_BASE}/models/load`,
    {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },

      body: JSON.stringify({
        model
      })
    }
  );

  let data: any = null;

  try {
    data = await res.json();
  } catch {
    // Backend may return a non-JSON response.
  }

  if (!res.ok || !data?.success) {
    throw new Error(
      data?.detail ??
      data?.message ??
      `Failed to load model (${res.status} ${res.statusText})`
    );
  }

  return {
    success: Boolean(data.success),
    model: String(data.model ?? model),
    message: String(
      data.message ??
      `Loaded ${model}`
    )
  };
}

// ---------------------------------------------------------------------------
// Backend health
// ---------------------------------------------------------------------------

export interface BackendHealth {
  status: string;
  llama_server: boolean;
  loaded_model: string | null;
  models_directory?: string;
  models_available?: number;
}

export async function fetchHealth(): Promise<BackendHealth> {
  const baseUrl = API_BASE.replace(/\/api\/?$/, '');

  const res = await fetch(
    `${baseUrl}/health`,
    {
      headers: {
        ...authHeaders()
      }
    }
  );

  if (!res.ok) {
    throw new Error(
      `Backend health check failed (${res.status})`
    );
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export async function fetchConversations(): Promise<any[]> {
  return request<any[]>('/conversations');
}

// ---------------------------------------------------------------------------
// Current user
// ---------------------------------------------------------------------------

export async function fetchCurrentUser(): Promise<User> {
  return request<User>('/me');
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

export interface ProviderStatus {
  id: string;
  name: string;
  configured: boolean;
  kind: string;
}

export interface ProvidersResponse {
  ai_providers: ProviderStatus[];
  web_search: { configured: boolean; provider: string | null };
  image_generation: { configured: boolean; provider: string | null };
}

export async function fetchProviders(): Promise<ProvidersResponse> {
  return request<ProvidersResponse>('/providers');
}

export interface CustomProvider {
  id: string;
  name: string;
  base_url: string;
  model: string;
  source: 'env' | 'user';
}

export interface AddCustomProviderInput {
  name: string;
  base_url: string;
  api_key: string;
  model: string;
}

export async function fetchCustomProviders(): Promise<CustomProvider[]> {
  const res = await request<{ providers: CustomProvider[] }>('/providers/custom');
  return res.providers;
}

export async function addCustomProvider(input: AddCustomProviderInput): Promise<CustomProvider> {
  return request<CustomProvider>('/providers/custom', {
    method: 'POST',
    body: JSON.stringify(input)
  });
}

export async function deleteCustomProvider(id: string): Promise<void> {
  await request<void>(`/providers/custom/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Documents / attachments
// ---------------------------------------------------------------------------

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void
): Promise<Attachment> {
  const token =
    localStorage.getItem('auth_token');

  const formData = new FormData();

  formData.append('file', file);

  const xhr = new XMLHttpRequest();

  return new Promise((resolve, reject) => {
    xhr.open(
      'POST',
      `${API_BASE}/documents`
    );

    if (token) {
      xhr.setRequestHeader(
        'Authorization',
        `Bearer ${token}`
      );
    }

    // Upload progress
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }

      const percent = Math.round(
        (event.loaded / event.total) * 100
      );

      onProgress?.(percent);
    };

    xhr.onload = () => {
      if (
        xhr.status >= 200 &&
        xhr.status < 300
      ) {
        try {
          const data = JSON.parse(
            xhr.responseText
          );

          resolve(data);
        } catch {
          reject(
            new Error(
              'Invalid response from document upload.'
            )
          );
        }

        return;
      }

      reject(
        new Error(
          `${xhr.status} ${xhr.statusText}: ${xhr.responseText}`
        )
      );
    };

    xhr.onerror = () => {
      reject(
        new Error(
          'Document upload failed.'
        )
      );
    };

    xhr.onabort = () => {
      reject(
        new Error(
          'Document upload was cancelled.'
        )
      );
    };

    xhr.send(formData);
  });
}

// ---------------------------------------------------------------------------
// Chat streaming
//
// POST /api/chat
//
// Request:
//
// {
//   "model": "...",
//   "messages": [...],
//   "webSearch": false,
//   "imageGeneration": false,
//   "attachmentIds": []
// }
//
// SSE response:
//
// data: {"type":"token","content":"Hello"}
//
// data: {"type":"done"}
// ---------------------------------------------------------------------------

export interface StreamChatRequest {
  model: string;

  messages: Pick<
    Message,
    'role' | 'content'
  >[];

  options?: ChatSendOptions;
}

export interface StreamChatCallbacks {
  onToken?: (
    content: string
  ) => void;

  onSearchStatus?: (
    status: string
  ) => void;

  onCitations?: (
    citations: Citation[]
  ) => void;

  onImage?: (
    image: GeneratedImage
  ) => void;

  onDone?: () => void;

  onError?: (
    error: Error
  ) => void;
}

export function streamChat(
  request: StreamChatRequest,
  callbacks: StreamChatCallbacks,
  signal?: AbortSignal
): void {
  fetch(
    `${API_BASE}/chat`,
    {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },

      body: JSON.stringify({
        model: request.model,
        messages: request.messages,
        ...(request.options ?? {})
      }),

      signal
    }
  )
    .then(async (res) => {
      if (!res.ok) {
        const text =
          await res.text().catch(() => '');

        throw new Error(
          `${res.status} ${res.statusText}: ${text}`
        );
      }

      if (!res.body) {
        throw new Error(
          'Chat response has no body.'
        );
      }

      const reader =
        res.body.getReader();

      const decoder =
        new TextDecoder();

      let buffer = '';

      let doneReceived = false;

      while (true) {
        const {
          value,
          done
        } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(
          value,
          {
            stream: true
          }
        );

        const events =
          buffer.split('\n\n');

        buffer =
          events.pop() ?? '';

        for (const event of events) {
          const line = event
            .split('\n')
            .find((line) =>
              line.startsWith('data:')
            );

          if (!line) {
            continue;
          }

          const raw =
            line
              .slice(5)
              .trim();

          if (!raw) {
            continue;
          }

          try {
            const data =
              JSON.parse(raw);

            switch (data.type) {
              case 'token': {
                if (
                  typeof data.content ===
                  'string'
                ) {
                  callbacks.onToken?.(
                    data.content
                  );
                }

                break;
              }

              case 'search_status': {
                if (
                  typeof data.status ===
                  'string'
                ) {
                  callbacks.onSearchStatus?.(
                    data.status
                  );
                }

                break;
              }

              case 'citations': {
                if (
                  Array.isArray(
                    data.citations
                  )
                ) {
                  callbacks.onCitations?.(
                    data.citations as Citation[]
                  );
                }

                break;
              }

              case 'image': {
                if (data.image) {
                  callbacks.onImage?.(
                    data.image as GeneratedImage
                  );
                }

                break;
              }

              case 'done': {
                if (!doneReceived) {
                  doneReceived = true;
                  callbacks.onDone?.();
                }

                break;
              }

              case 'error': {
                callbacks.onError?.(
                  new Error(
                    typeof data.message ===
                    'string'
                      ? data.message
                      : 'Unknown backend error.'
                  )
                );

                break;
              }
            }
          } catch {
            // Ignore malformed SSE events.
          }
        }
      }

      // If the backend closes the connection
      // without sending {type:"done"}, finish
      // the message gracefully.
      if (!doneReceived) {
        callbacks.onDone?.();
      }
    })
    .catch((error) => {
      if (
        error?.name ===
        'AbortError'
      ) {
        return;
      }

      callbacks.onError?.(
        error instanceof Error
          ? error
          : new Error(
              String(error)
            )
      );
    });
}

// ---------------------------------------------------------------------------
// Optional conversation deletion helper
// ---------------------------------------------------------------------------

export async function deleteConversation(
  id: string
): Promise<void> {
  await request<void>(
    `/conversations/${encodeURIComponent(id)}`,
    {
      method: 'DELETE'
    }
  );
}

