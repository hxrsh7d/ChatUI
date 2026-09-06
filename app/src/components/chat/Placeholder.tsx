import { Sparkles } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';

const SUGGESTIONS = [
  'Explain quantum computing in simple terms',
  'Write a Python function to reverse a linked list',
  'Draft a polite email declining a meeting',
  'Summarize the key ideas of stoicism'
];

export function Placeholder({ onPick }: { onPick: (text: string) => void }) {
  const user = useUIStore((s) => s.user);

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white mb-4">
        <Sparkles size={26} />
      </div>
      <h1 className="text-2xl font-medium text-gray-800 dark:text-gray-100">
        {greeting()}, {user?.name?.split(' ')[0] ?? 'there'}
      </h1>
      <p className="mt-1 text-gray-400">How can I help you today?</p>

      <div className="mt-8 grid w-full max-w-lg grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-3 text-left text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}
