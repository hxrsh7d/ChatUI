import { ReactNode } from 'react';
import clsx from 'clsx';

export function SettingsSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-7">
      <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      <div className="flex flex-col divide-y divide-gray-100 dark:divide-gray-800 rounded-xl border border-gray-100 dark:border-gray-800">
        {children}
      </div>
    </div>
  );
}

export function SettingsRow({
  label,
  description,
  children
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 px-4 py-3.5">
      <div className="min-w-0">
        <div className="text-sm text-gray-800 dark:text-gray-100">{label}</div>
        {description && <div className="text-xs text-gray-400 mt-0.5">{description}</div>}
      </div>
      <div className="shrink-0 max-w-full">{children}</div>
    </div>
  );
}

export function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={clsx(
        'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50',
        checked ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
      )}
    >
      <span
        className={clsx(
          'pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-150 ease-out',
          checked ? 'translate-x-5' : 'translate-x-0'
        )}
      />
    </button>
  );
}

export function Select({
  value,
  onChange,
  options
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2.5 py-1.5 text-sm outline-none"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        'rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm outline-none w-56',
        'focus:ring-2 focus:ring-blue-500/40',
        props.className
      )}
    />
  );
}
