import { useState } from 'react';
import clsx from 'clsx';
import {
  Settings as SettingsIcon,
  Palette,
  Cpu,
  Plug,
  FileText,
  Globe,
  ImageIcon,
  UserCircle,
  ShieldCheck
} from 'lucide-react';
import { Modal } from '@/components/common/Modal';
import { useUIStore } from '@/stores/uiStore';
import { GeneralTab } from './tabs/GeneralTab';
import { AppearanceTab } from './tabs/AppearanceTab';
import { ModelsTab } from './tabs/ModelsTab';
import { ProvidersTab } from './tabs/ProvidersTab';
import { DocumentsTab } from './tabs/DocumentsTab';
import { WebSearchTab } from './tabs/WebSearchTab';
import { ImageGenTab } from './tabs/ImageGenTab';
import { AccountTab } from './tabs/AccountTab';
import { AdminTab } from './tabs/AdminTab';

const TABS = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'models', label: 'Models', icon: Cpu },
  { id: 'providers', label: 'Providers', icon: Plug },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'websearch', label: 'Web Search', icon: Globe },
  { id: 'imagegen', label: 'Image Generation', icon: ImageIcon },
  { id: 'account', label: 'Account', icon: UserCircle },
  { id: 'admin', label: 'Admin', icon: ShieldCheck, adminOnly: true }
] as const;

export function SettingsModal() {
  const open = useUIStore((s) => s.settingsOpen);
  const closeSettings = useUIStore((s) => s.closeSettings);
  const settingsTab = useUIStore((s) => s.settingsTab);
  const openSettings = useUIStore((s) => s.openSettings);
  const user = useUIStore((s) => s.user);
  const isAdmin = user?.role === 'admin';

  const visibleTabs = TABS.filter((t) => !('adminOnly' in t && t.adminOnly) || isAdmin);

  return (
    <Modal open={open} onClose={closeSettings} title="Settings" size="xl">
      <div className="flex h-[70vh] min-h-[420px] min-w-0 flex-col sm:flex-row">
        <div className="w-full shrink-0 overflow-x-auto border-b border-gray-100 p-2 dark:border-gray-800 sm:w-48 sm:border-b-0 sm:border-r">
          {visibleTabs.map((t) => (
            <button
              key={t.id}
              onClick={() => openSettings(t.id)}
              className={clsx(
                'flex w-max min-w-full items-center sm:w-full gap-2.5 rounded-lg px-3 py-2 text-sm text-left transition-colors',
                settingsTab === t.id
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white font-medium'
                  : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800/60'
              )}
            >
              <t.icon size={15} />
              {t.label}
            </button>
          ))}
        </div>
        <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-4 sm:p-6">
          {settingsTab === 'general' && <GeneralTab />}
          {settingsTab === 'appearance' && <AppearanceTab />}
          {settingsTab === 'models' && <ModelsTab />}
          {settingsTab === 'providers' && <ProvidersTab />}
          {settingsTab === 'documents' && <DocumentsTab />}
          {settingsTab === 'websearch' && <WebSearchTab />}
          {settingsTab === 'imagegen' && <ImageGenTab />}
          {settingsTab === 'account' && <AccountTab />}
          {settingsTab === 'admin' && isAdmin && <AdminTab />}
        </div>
      </div>
    </Modal>
  );
}
