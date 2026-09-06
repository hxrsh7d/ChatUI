import { useUIStore } from '@/stores/uiStore';
import { Avatar } from '@/components/common/Avatar';
import { clearAccessToken, getAccessToken } from '@/services/api';
import { SettingsSection, SettingsRow, TextInput } from '../Shared';

export function AccountTab() {
  const user = useUIStore((s) => s.user);
  const hasAccessToken = !!getAccessToken();

  const signOut = () => {
    clearAccessToken();
    window.location.reload();
  };

  return (
    <div>
      <div className="mb-6 flex items-center gap-4">
        <Avatar name={user?.name ?? 'You'} size={56} src={user?.avatarUrl} />
        <div>
          <div className="font-medium">{user?.name ?? 'You'}</div>
          <div className="text-xs text-gray-400">{user?.email ?? 'you@localhost'}</div>
        </div>
      </div>

      <SettingsSection title="Profile">
        <SettingsRow label="Display name">
          <TextInput defaultValue={user?.name} />
        </SettingsRow>
        <SettingsRow label="Email">
          <TextInput defaultValue={user?.email} type="email" />
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="Security">
        <SettingsRow label="Password" description="Change your account password">
          <button className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800">
            Change
          </button>
        </SettingsRow>
        {hasAccessToken && (
          <SettingsRow label="Sign out" description="Forget this device's access code and require it again">
            <button
              onClick={signOut}
              className="rounded-lg bg-red-600 text-white px-3 py-1.5 text-sm hover:bg-red-700"
            >
              Sign out
            </button>
          </SettingsRow>
        )}
      </SettingsSection>
    </div>
  );
}
