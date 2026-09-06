import { FileText, X, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import type { Attachment } from '@/types';
import { formatBytes } from '@/utils/date';

export function FileChip({ file, onRemove }: { file: Attachment; onRemove?: () => void }) {
  return (
    <div
      className={clsx(
        'flex items-center gap-2 rounded-xl border px-2.5 py-2 text-xs max-w-[220px]',
        file.status === 'error'
          ? 'border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40'
          : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800'
      )}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
        {file.status === 'uploading' || file.status === 'processing' ? (
          <Loader2 size={14} className="animate-spin text-gray-400" />
        ) : file.status === 'error' ? (
          <AlertCircle size={14} className="text-red-500" />
        ) : (
          <FileText size={14} className="text-gray-500" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium text-gray-700 dark:text-gray-200">{file.name}</div>
        <div className="text-[10px] text-gray-400">
          {file.status === 'uploading'
            ? `Uploading… ${file.progress ?? 0}%`
            : file.status === 'processing'
              ? 'Processing…'
              : file.status === 'error'
                ? file.error ?? 'Upload failed'
                : formatBytes(file.size)}
        </div>
      </div>
      {onRemove && (
        <button onClick={onRemove} className="shrink-0 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
          <X size={14} />
        </button>
      )}
    </div>
  );
}
