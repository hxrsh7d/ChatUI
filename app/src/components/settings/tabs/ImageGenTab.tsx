import { useState } from 'react';
import { SettingsSection, SettingsRow, Toggle, Select } from '../Shared';

export function ImageGenTab() {
  const [enabled, setEnabled] = useState(true);
  const [size, setSize] = useState('1024x1024');

  return (
    <div>
      <p className="mb-4 text-xs text-gray-400">
        Image generation runs through your backend's configured provider (currently OpenAI's image API — see
        <code className="font-mono"> IMAGE_PROVIDER</code> in your .env). Check the Providers tab to see whether
        one is currently configured.
      </p>
      <SettingsSection title="Image generation">
      <SettingsRow label="Enable image generation" description="Allow the composer's Image toggle to be used">
        <Toggle checked={enabled} onChange={setEnabled} />
      </SettingsRow>
      <SettingsRow label="Default size" description="Sent as a hint to your backend's image provider">
        <Select
          value={size}
          onChange={setSize}
          options={[
            { value: '512x512', label: '512×512' },
            { value: '1024x1024', label: '1024×1024' },
            { value: '1024x1792', label: '1024×1792' }
          ]}
        />
      </SettingsRow>
      </SettingsSection>
    </div>
  );
}
