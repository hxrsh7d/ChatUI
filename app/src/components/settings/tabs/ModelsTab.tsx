import { Cpu, Cloud, RefreshCw } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { fetchModels } from '@/services/api';
import { SettingsSection, SettingsRow } from '../Shared';

export function ModelsTab() {
  const models = useUIStore((s) => s.models);
  const setModels = useUIStore((s) => s.setModels);
  const selectedModel = useUIStore((s) => s.selectedModel);
  const setSelectedModel = useUIStore((s) => s.setSelectedModel);

  const refresh = async () => {
    const list = await fetchModels();
    setModels(list);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Models are fetched live from your backend at <code className="font-mono">GET /v1/models</code>.
        </p>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 px-2.5 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <SettingsSection title="Available models">
        {models.map((m) => (
          <SettingsRow
            key={m.id}
            label={m.name}
            description={`${m.group ?? m.provider} · ${m.id}`}
          >
            <div className="flex items-center gap-2">
              {m.provider === 'local' ? (
                <Cpu size={14} className="text-emerald-600" />
              ) : (
                <Cloud size={14} className="text-blue-500" />
              )}
              <input
                type="radio"
                name="default-model"
                checked={selectedModel === m.id}
                onChange={() => setSelectedModel(m.id)}
                className="!size-4 !rounded-full"
              />
            </div>
          </SettingsRow>
        ))}
        {models.length === 0 && <p className="p-4 text-sm text-gray-400">No models found.</p>}
      </SettingsSection>
    </div>
  );
}
