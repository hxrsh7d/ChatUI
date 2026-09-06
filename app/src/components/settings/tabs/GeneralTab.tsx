import { useState } from 'react';
import { SettingsSection, SettingsRow, Toggle, Select } from '../Shared';

export function GeneralTab() {
  const [language, setLanguage] = useState('en');
  const [notifications, setNotifications] = useState(true);
  const [haptics, setHaptics] = useState(true);
  const [saveHistory, setSaveHistory] = useState(true);

  return (
    <div>
      <SettingsSection title="General">
        <SettingsRow label="Language" description="Interface display language">
          <Select
            value={language}
            onChange={setLanguage}
            options={[
              { value: 'en', label: 'English' },
              { value: 'es', label: 'Español' },
              { value: 'fr', label: 'Français' },
              { value: 'de', label: 'Deutsch' },
              { value: 'ja', label: '日本語' }
            ]}
          />
        </SettingsRow>
        <SettingsRow label="Desktop notifications" description="Notify when a response finishes">
          <Toggle checked={notifications} onChange={setNotifications} />
        </SettingsRow>
        <SettingsRow label="Haptic feedback" description="Vibrate on send (mobile only)">
          <Toggle checked={haptics} onChange={setHaptics} />
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="Chats">
        <SettingsRow label="Save chat history" description="Keep conversations stored locally in the browser">
          <Toggle checked={saveHistory} onChange={setSaveHistory} />
        </SettingsRow>
        <SettingsRow label="Export all chats" description="Download your conversation history as JSON">
          <button className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800">
            Export
          </button>
        </SettingsRow>
      </SettingsSection>
    </div>
  );
}
