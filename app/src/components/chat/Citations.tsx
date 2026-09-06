import { useState } from 'react';
import { ChevronDown, Globe } from 'lucide-react';
import clsx from 'clsx';
import type { Citation } from '@/types';

export function Citations({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  if (!citations.length) return null;

  return (
    <div className="mb-2 mt-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-800 px-2.5 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
      >
        <Globe size={13} />
        {citations.length} source{citations.length > 1 ? 's' : ''}
        <ChevronDown size={13} className={clsx('transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {citations.map((c, i) => (
            <a
              key={c.id}
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-xl border border-gray-200 dark:border-gray-800 p-2.5 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
            >
              <div className="flex items-center gap-1.5 text-[11px] text-gray-400 mb-1">
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800 text-[10px]">
                  {i + 1}
                </span>
                <span className="truncate">{new URL(c.url).hostname}</span>
              </div>
              <div className="text-xs font-medium text-gray-800 dark:text-gray-100 line-clamp-1">{c.title}</div>
              {c.snippet && (
                <div className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">{c.snippet}</div>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
