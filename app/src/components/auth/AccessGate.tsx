import { FormEvent, useEffect, useState } from 'react';
import { Lock, Loader2 } from 'lucide-react';
import { setAccessToken, verifyAccess } from '@/services/api';

// Gates the app behind a single shared access token, but ONLY when the
// backend actually has one configured (ACCESS_TOKEN in chatui-backend/.env).
// When it isn't configured, verifyAccess() resolves 'ok' immediately and
// this component just renders its children -- zero friction for solo use.
// Connectivity problems (backend down, etc.) are deliberately NOT handled
// here; they fall through to the app's existing "failed to reach backend"
// banner so we don't duplicate that error handling.
export function AccessGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<'checking' | 'ok' | 'locked'>('checking');
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = () => {
    verifyAccess().then((result) => {
      setStatus(result === 'unauthorized' ? 'locked' : 'ok');
    });
  };

  useEffect(() => {
    check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setSubmitting(true);
    setError(null);
    setAccessToken(input.trim());

    verifyAccess().then((result) => {
      setSubmitting(false);
      if (result === 'ok') {
        setStatus('ok');
      } else {
        setError('That access code was not accepted. Check with whoever shared it with you and try again.');
      }
    });
  };

  if (status === 'checking') {
    return (
      <div className="flex h-full w-full items-center justify-center bg-white dark:bg-gray-900">
        <Loader2 size={22} className="animate-spin text-gray-300 dark:text-gray-600" />
      </div>
    );
  }

  if (status === 'ok') {
    return <>{children}</>;
  }

  return (
    <div className="flex h-full w-full items-center justify-center bg-white dark:bg-gray-900 px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-2xl border border-gray-100 dark:border-gray-800 p-6 shadow-sm"
      >
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
          <Lock size={17} className="text-gray-500 dark:text-gray-300" />
        </div>
        <h1 className="mb-1 text-base font-semibold text-gray-900 dark:text-gray-100">Access code required</h1>
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          This ChatUI instance is shared. Enter the access code you were given to continue.
        </p>
        <input
          type="password"
          autoFocus
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Access code"
          className="mb-3 w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500/40"
        />
        {error && <p className="mb-3 text-xs text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={submitting || !input.trim()}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-3 py-2 text-sm font-medium disabled:opacity-40 transition-opacity"
        >
          {submitting ? <Loader2 size={14} className="animate-spin" /> : null}
          Continue
        </button>
      </form>
    </div>
  );
}
