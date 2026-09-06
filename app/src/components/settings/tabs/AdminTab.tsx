import { useState } from 'react';
import { SettingsSection, SettingsRow, Toggle } from '../Shared';

export function AdminTab() {
  const [signupsEnabled, setSignupsEnabled] = useState(true);
  const [defaultRole, setDefaultRole] = useState<'user' | 'admin'>('user');

  return (
    <div>
      <SettingsSection title="Users">
        <SettingsRow label="Allow new sign-ups" description="Let new users create accounts on this instance">
          <Toggle checked={signupsEnabled} onChange={setSignupsEnabled} />
        </SettingsRow>
        <SettingsRow label="Default role for new users">
          <select
            value={defaultRole}
            onChange={(e) => setDefaultRole(e.target.value as 'user' | 'admin')}
            className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2.5 py-1.5 text-sm"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </SettingsRow>
        <SettingsRow label="Manage users" description="View, edit roles, or remove accounts">
          <button className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800">
            Open user list
          </button>
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="System">
        <SettingsRow label="Backend status" description="Connection to your FastAPI backend">
          <span className="text-xs text-gray-400">Checked automatically</span>
        </SettingsRow>
        <SettingsRow label="Usage analytics" description="Aggregate, non-content request metrics">
          <Toggle checked={true} onChange={() => {}} />
        </SettingsRow>
      </SettingsSection>
    </div>
  );
}
