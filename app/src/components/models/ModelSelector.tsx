
import { useMemo, useState } from 'react';
import { ChevronDown, Cpu, Cloud, Check, Loader2 } from 'lucide-react';
import clsx from 'clsx';

import { useUIStore } from '@/stores/uiStore';
import { DropdownMenu } from '@/components/common/DropdownMenu';
import { loadModel } from '@/services/api';
import type { ModelInfo } from '@/types';

// This build only ever receives "local" models from the backend (GGUF files
// served by llama.cpp), but we keep a couple of readable fallback labels in
// case a future backend reports something else — without inventing fake
// cloud-provider names for models that were never actually reachable.
const PROVIDER_LABEL: Record<string, string> = {
  local: 'Local (llama.cpp)'
};

export function ModelSelector() {
  const models = useUIStore((s) => s.models);
  const selectedModel = useUIStore((s) => s.selectedModel);
  const setSelectedModel = useUIStore((s) => s.setSelectedModel);

  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const map = new Map<string, ModelInfo[]>();

    for (const model of models) {
      const key = model.provider;

      if (!map.has(key)) {
        map.set(key, []);
      }

      map.get(key)!.push(model);
    }

    return map;
  }, [models]);

  const current = models.find((model) => model.id === selectedModel);

  const handleModelSelect = async (model: ModelInfo) => {
    if (loadingModel || model.id === selectedModel) {
      return;
    }

    setError(null);
    setLoadingModel(model.id);

    try {
      const result = await loadModel(model.id);

      if (!result.success) {
        throw new Error(result.message || 'Failed to load model.');
      }

      // Only update the frontend selection after the backend
      // confirms that the model was loaded successfully.
      setSelectedModel(result.model);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Failed to load model.';

      setError(message);
    } finally {
      setLoadingModel(null);
    }
  };

  return (
    <DropdownMenu
      align="left"
      trigger={({ toggle, open }) => (
        <button
          onClick={toggle}
          disabled={loadingModel !== null}
          className={clsx(
            'flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors',
            'hover:bg-gray-100 dark:hover:bg-gray-800',
            open && 'bg-gray-100 dark:bg-gray-800',
            loadingModel && 'cursor-wait opacity-80'
          )}
        >
          {loadingModel ? (
            <Loader2
              size={14}
              className="animate-spin text-blue-600"
            />
          ) : current?.provider === 'local' ? (
            <Cpu
              size={14}
              className="text-emerald-600"
            />
          ) : (
            <Cloud
              size={14}
              className="text-blue-500"
            />
          )}

          <span className="max-w-[160px] truncate">
            {loadingModel
              ? 'Loading model...'
              : current?.name ?? 'Select a model'}
          </span>

          <ChevronDown
            size={14}
            className="text-gray-400"
          />
        </button>
      )}
      className="w-72 max-h-[60vh] overflow-y-auto"
    >
      {error && (
        <div className="mx-2 mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
          {error}
        </div>
      )}

      {[...grouped.entries()].map(([provider, list]) => (
        <div key={provider} className="py-1">
          <div className="flex items-center gap-1.5 px-3 pb-1 pt-2 text-[11px] font-medium uppercase tracking-wide text-gray-400">
            {provider === 'local' ? (
              <Cpu size={12} />
            ) : (
              <Cloud size={12} />
            )}

            {PROVIDER_LABEL[provider] ?? provider ?? 'Local'}
          </div>

          {list.map((model) => {
            const isSelected = model.id === selectedModel;
            const isLoading = model.id === loadingModel;

            return (
              <button
                key={model.id}
                onClick={() => handleModelSelect(model)}
                disabled={loadingModel !== null}
                className={clsx(
                  'flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm',
                  'hover:bg-gray-100 dark:hover:bg-gray-800',
                  'disabled:cursor-not-allowed disabled:opacity-60',
                  isSelected &&
                    'bg-gray-50 dark:bg-gray-800/60'
                )}
              >
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-gray-800 dark:text-gray-100">
                    {model.name}
                  </span>

                  {model.group && (
                    <span className="text-[11px] text-gray-400">
                      {model.group}
                    </span>
                  )}

                  {isLoading && (
                    <span className="mt-0.5 text-[10px] text-blue-600 dark:text-blue-400">
                      Loading...
                    </span>
                  )}
                </div>

                {isLoading ? (
                  <Loader2
                    size={15}
                    className="shrink-0 animate-spin text-blue-600"
                  />
                ) : (
                  isSelected && (
                    <Check
                      size={15}
                      className="shrink-0 text-blue-600"
                    />
                  )
                )}
              </button>
            );
          })}
        </div>
      ))}

      {models.length === 0 && (
        <div className="px-3 py-4 text-sm text-gray-400">
          No models available
        </div>
      )}
    </DropdownMenu>
  );
}
