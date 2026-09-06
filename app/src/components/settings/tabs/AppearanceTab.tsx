import { Sun, Moon, MonitorSmartphone } from 'lucide-react';
import clsx from 'clsx';
import { useUIStore, Theme } from '@/stores/uiStore';
import { SettingsSection } from '../Shared';

const OPTIONS: { id: Theme; label: string; icon: any }[] = [
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'system', label: 'System', icon: MonitorSmartphone }
];

export function AppearanceTab() {
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);

  return (
    <SettingsSection title="Theme">
      <div className="p-4">
        <div className="grid grid-cols-3 gap-3">
          {OPTIONS.map((o) => (
            <button
              key={o.id}
              onClick={() => setTheme(o.id)}
              className={clsx(
                'flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-colors',
                theme === o.id
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/40'
                  : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
              )}
            >
              <o.icon size={20} />
              <span className="text-sm">{o.label}</span>
            </button>
          ))}
        </div>
      </div>
    </SettingsSection>
  );
}
