import { useCallback, useEffect, useState } from 'react';
import clsx from 'clsx';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { useUIStore } from '@/stores/uiStore';
import { fetchModels } from '@/services/api';
import { Sidebar } from '@/components/layout/Sidebar';
import { MobileDrawer } from '@/components/layout/MobileDrawer';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { ChatPage } from '@/pages/ChatPage';

// Note: this app has no authentication system, so there is intentionally no
// call to a `/api/me` endpoint here. The backend does not implement one, and
// per project requirements we don't fabricate a fake endpoint just to quiet
// a console error. `useUIStore().user` simply stays `null`, and every
// component that reads it already falls back to a sensible default
// (e.g. "You").
export default function App() {
  useTheme();

  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setModels = useUIStore((s) => s.setModels);
  const modelsLoading = useUIStore((s) => s.modelsLoading);
  const modelsError = useUIStore((s) => s.modelsError);
  const setModelsLoading = useUIStore((s) => s.setModelsLoading);
  const setModelsError = useUIStore((s) => s.setModelsError);

  const loadModels = useCallback(() => {
    setModelsLoading(true);
    setModelsError(null);

    fetchModels()
      .then((models) => {
        setModels(models);
        if (models.length === 0) {
          setModelsError(
            'No GGUF models were found. Add .gguf files to your configured models directory and refresh.'
          );
        }
      })
      .catch((err) => {
        setModelsError(
          err instanceof Error
            ? err.message
            : 'Failed to reach the backend.'
        );
      })
      .finally(() => setModelsLoading(false));
  }, [setModels, setModelsError, setModelsLoading]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  return (
    <div className="h-full w-full overflow-hidden bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <div className="flex h-full">
        <aside
          className={clsx(
            'hidden md:block shrink-0 overflow-hidden border-r border-gray-100 dark:border-gray-800 transition-width duration-200',
            sidebarOpen ? 'w-[280px]' : 'w-0 border-r-0'
          )}
        >
          <div className="w-[280px] h-full">
            <Sidebar variant="desktop" />
          </div>
        </aside>

        <main className="flex-1 min-w-0 min-h-0 flex flex-col">
          {modelsError && !modelsLoading && (
            <BackendErrorBanner message={modelsError} onRetry={loadModels} />
          )}
          <div className="flex-1 min-h-0">
            <ChatPage />
          </div>
        </main>
      </div>

      <MobileDrawer />
      <SettingsModal />
    </div>
  );
}

function BackendErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  // Local, component-scoped dismiss state (rather than global store state)
  // since it's purely a transient UI concern.
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="flex items-start gap-2.5 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <p className="flex-1 min-w-0">{message}</p>
      <button
        onClick={onRetry}
        className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium hover:bg-amber-100 dark:hover:bg-amber-900/40"
      >
        <RefreshCw size={12} />
        Retry
      </button>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="shrink-0 rounded-md p-1 hover:bg-amber-100 dark:hover:bg-amber-900/40"
      >
        <X size={14} />
      </button>
    </div>
  );
}
