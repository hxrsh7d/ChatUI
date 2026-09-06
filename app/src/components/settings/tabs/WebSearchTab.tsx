import { useState } from 'react';
import { SettingsSection, SettingsRow, Toggle, Select } from '../Shared';

export function WebSearchTab() {
  const [enabled, setEnabled] = useState(true);
  const [engine, setEngine] = useState('backend-default');
  const [maxResults, setMaxResults] = useState('5');

  return (
    <div>
      <p className="mb-4 text-xs text-gray-400">
        Web search runs through your backend's configured provider (Brave, Tavily, or SearXNG — see
        <code className="font-mono"> SEARCH_PROVIDER</code> in your .env). Check the Providers tab to see whether
        one is currently configured.
      </p>
      <SettingsSection title="Web search">
        <SettingsRow label="Enable web search" description="Allow the composer's Web Search toggle to be used">
          <Toggle checked={enabled} onChange={setEnabled} />
        </SettingsRow>
        <SettingsRow label="Search engine" description="Configured on your backend via SEARCH_PROVIDER (Brave, Tavily, or SearXNG)">
          <Select
            value={engine}
            onChange={setEngine}
            options={[{ value: 'backend-default', label: 'Backend default' }]}
          />
        </SettingsRow>
        <SettingsRow label="Results per query" description="Number of pages retrieved and shown as citations">
          <Select
            value={maxResults}
            onChange={setMaxResults}
            options={[
              { value: '3', label: '3' },
              { value: '5', label: '5' },
              { value: '8', label: '8' }
            ]}
          />
        </SettingsRow>
      </SettingsSection>
    </div>
  );
}
