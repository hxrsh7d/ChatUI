import { FormEvent, useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import {
  fetchProviders,
  fetchCustomProviders,
  addCustomProvider,
  deleteCustomProvider,
  type ProvidersResponse,
  type CustomProvider
} from '@/services/api';
import { SettingsSection, SettingsRow, TextInput } from '../Shared';

// Providers are configured server-side via environment variables (API keys
// never reach the browser -- see chatui-backend/.env.example). This tab
// reflects the REAL configuration state reported by GET /api/providers; it
// never shows a fake "Connected" badge for something the backend can't
// actually reach.
export function ProvidersTab() {
  const models = useUIStore((s) => s.models);
  const isLocalConnected = models.some((m) => m.provider === 'local');

  const [data, setData] = useState<ProvidersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchProviders()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <p className="mb-4 text-xs text-gray-400">
        Provider API keys are configured on the backend (via environment variables) and never sent to the browser.
        Statuses below come live from your backend at <code className="font-mono">GET /api/providers</code>.
      </p>

      <SettingsSection title="AI providers">
        <SettingsRow
          label="llama.cpp (local)"
          description={
            isLocalConnected
              ? `Serving ${models.filter((m) => m.provider === 'local').length} local GGUF model(s) via your backend`
              : 'No local models detected — check your backend health'
          }
        >
          <StatusBadge configured={isLocalConnected} />
        </SettingsRow>

        {loading && (
          <div className="flex items-center gap-2 px-4 py-3 text-xs text-gray-400">
            <Loader2 size={13} className="animate-spin" /> Checking provider status…
          </div>
        )}

        {error && <p className="px-4 py-3 text-xs text-red-500">Couldn't reach the backend: {error}</p>}

        {data?.ai_providers
          .filter((p) => p.id !== 'local' && !p.id.startsWith('custom:'))
          .map((p) => (
            <SettingsRow key={p.id} label={p.name} description={p.configured ? 'Configured on the backend' : 'Not configured — set the API key in your .env'}>
              <StatusBadge configured={p.configured} />
            </SettingsRow>
          ))}
      </SettingsSection>

      <CustomProvidersSection />

      {data && (
        <SettingsSection title="Other capabilities">
          <SettingsRow
            label="Web search"
            description={data.web_search.configured ? `Using ${data.web_search.provider}` : 'Not configured — set SEARCH_PROVIDER in your .env'}
          >
            <StatusBadge configured={data.web_search.configured} />
          </SettingsRow>
          <SettingsRow
            label="Image generation"
            description={data.image_generation.configured ? `Using ${data.image_generation.provider}` : 'Not configured — set IMAGE_PROVIDER in your .env'}
          >
            <StatusBadge configured={data.image_generation.configured} />
          </SettingsRow>
        </SettingsSection>
      )}

      <SettingsSection title="API endpoint">
        <SettingsRow label="Backend base URL" description="Where this frontend sends all chat and model requests">
          <code className="rounded bg-gray-100 dark:bg-gray-800 px-2 py-1 text-xs">/api</code>
        </SettingsRow>
      </SettingsSection>
    </div>
  );
}

function StatusBadge({ configured }: { configured: boolean }) {
  return (
    <span
      className={
        configured
          ? 'flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400'
          : 'flex items-center gap-1.5 text-xs text-gray-400'
      }
    >
      {configured ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
      {configured ? 'Connected' : 'Not configured'}
    </span>
  );
}

// Extracts a clean "detail" message out of the raw "<status> <statusText>:
// <json body>" error the shared request() helper throws, falling back to
// the raw message if it isn't JSON. Local to this form only -- doesn't
// change how errors are surfaced anywhere else in the app.
function friendlyErrorMessage(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  const jsonStart = message.indexOf('{');
  if (jsonStart !== -1) {
    try {
      const parsed = JSON.parse(message.slice(jsonStart));
      if (typeof parsed?.detail === 'string') return parsed.detail;
    } catch {
      // not JSON, fall through to the raw message
    }
  }
  return message;
}

function CustomProvidersSection() {
  const [providers, setProviders] = useState<CustomProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetchCustomProviders()
      .then(setProviders)
      .catch(() => {
        /* the main GET /api/providers call above already surfaces a connectivity error */
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const onAdd = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await addCustomProvider({ name: name.trim(), base_url: baseUrl.trim(), api_key: apiKey.trim(), model: model.trim() });
      setName('');
      setBaseUrl('');
      setApiKey('');
      setModel('');
      setShowForm(false);
      load();
    } catch (err) {
      setFormError(friendlyErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (id: string) => {
    setRemovingId(id);
    try {
      await deleteCustomProvider(id);
      load();
    } catch {
      // best-effort; the row stays and the user can retry
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <SettingsSection title="Custom OpenAI-compatible providers">
      <div className="px-4 pt-3 text-xs text-gray-400">
        Point at vLLM, a self-hosted server, or any other OpenAI-compatible endpoint.
      </div>

      {loading && (
        <div className="flex items-center gap-2 px-4 py-3 text-xs text-gray-400">
          <Loader2 size={13} className="animate-spin" /> Loading…
        </div>
      )}

      {!loading && providers.length === 0 && <div className="px-4 py-3 text-xs text-gray-400">None added yet.</div>}

      {providers.map((p) => (
        <SettingsRow key={p.id} label={p.name} description={[p.base_url, p.model].filter(Boolean).join(' · ')}>
          {p.source === 'user' ? (
            <button
              onClick={() => onDelete(p.id)}
              disabled={removingId === p.id}
              className="text-xs text-red-500 hover:text-red-600 disabled:opacity-40"
            >
              {removingId === p.id ? 'Removing…' : 'Remove'}
            </button>
          ) : (
            <span className="text-xs text-gray-400">Set via .env</span>
          )}
        </SettingsRow>
      ))}

      {showForm ? (
        <form onSubmit={onAdd} className="flex flex-col gap-3 px-4 py-4">
          <FormField label="Name">
            <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="My vLLM box" required />
          </FormField>
          <FormField label="Base URL">
            <TextInput
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:8000/v1"
              required
            />
          </FormField>
          <FormField label="API key (optional)">
            <TextInput
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Leave blank if none"
            />
          </FormField>
          <FormField label="Model">
            <TextInput value={model} onChange={(e) => setModel(e.target.value)} placeholder="llama-3-70b" />
          </FormField>

          {formError && <p className="text-xs text-red-500">{formError}</p>}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-3 py-1.5 text-sm font-medium disabled:opacity-40"
            >
              {submitting && <Loader2 size={13} className="animate-spin" />}
              Add provider
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setFormError(null);
              }}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="px-4 py-3">
          <button
            onClick={() => setShowForm(true)}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
          >
            + Add a custom provider
          </button>
        </div>
      )}
    </SettingsSection>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      {children}
    </label>
  );
}
