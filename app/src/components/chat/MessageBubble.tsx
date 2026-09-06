import { useState } from 'react';
import { Copy, Check, Pencil, RotateCcw, ThumbsUp, ThumbsDown, User, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import type { Message } from '@/types';
import { Markdown } from './Markdown';
import { Citations } from './Citations';
import { FileChip } from '@/components/documents/FileChip';
import { IconButton } from '@/components/common/IconButton';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { formatTime } from '@/utils/date';

export function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const editMessage = useChatStore((s) => s.editMessage);
  const regenerate = useChatStore((s) => s.regenerate);
  const selectedModel = useUIStore((s) => s.selectedModel);

  const isUser = message.role === 'user';

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const commitEdit = () => {
    setEditing(false);
    if (draft.trim() && draft !== message.content) {
      editMessage(message.id, draft.trim(), message.model ?? selectedModel);
    }
  };

  return (
    <div className={clsx('group flex gap-3 px-1', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div
        className={clsx(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full mt-0.5',
          isUser ? 'bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900' : 'bg-blue-600 text-white'
        )}
      >
        {isUser ? <User size={14} /> : <Sparkles size={14} />}
      </div>

      <div className={clsx('flex max-w-[85%] sm:max-w-[75%] flex-col', isUser ? 'items-end' : 'items-start')}>
        {message.attachments && message.attachments.length > 0 && (
          <div className="mb-1.5 flex flex-wrap gap-1.5 justify-end">
            {message.attachments.map((a) => (
              <FileChip key={a.id} file={a} />
            ))}
          </div>
        )}

        {message.searchStatus && (
          <div className="mb-1.5 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
            {message.searchStatus}
          </div>
        )}

        {!isUser && message.citations && message.citations.length > 0 && <Citations citations={message.citations} />}

        <div
          className={clsx(
            'rounded-2xl px-4 py-2.5',
            isUser
              ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
              : 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-gray-100'
          )}
        >
          {editing ? (
            <div className="min-w-[240px]">
              <textarea
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={Math.min(10, Math.max(2, draft.split('\n').length))}
                className="w-full resize-none bg-transparent outline-none text-sm"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  onClick={() => {
                    setEditing(false);
                    setDraft(message.content);
                  }}
                  className="rounded-lg px-3 py-1 text-xs bg-white/10 hover:bg-white/20"
                >
                  Cancel
                </button>
                <button onClick={commitEdit} className="rounded-lg px-3 py-1 text-xs bg-blue-600 text-white hover:bg-blue-500">
                  Send
                </button>
              </div>
            </div>
          ) : isUser ? (
            <p className="whitespace-pre-wrap break-words text-[0.9375rem] leading-relaxed">{message.content}</p>
          ) : (
            <>
              <Markdown content={message.content || (message.isStreaming ? '' : '')} />
              {message.isStreaming && message.content === '' && <TypingDots />}
            </>
          )}
        </div>

        {message.images && message.images.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message.images.map((img) => (
              <img
                key={img.id}
                src={img.url}
                alt={img.prompt ?? 'Generated image'}
                className="max-w-[260px] rounded-xl border border-gray-200 dark:border-gray-800"
              />
            ))}
          </div>
        )}

        {message.error && (
          <p className="mt-1 text-xs text-red-500">Something went wrong: {message.error}</p>
        )}

        {/* Actions row */}
        {!editing && (message.content || message.images?.length) && (
          <div
            className={clsx(
              'mt-1 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity',
              isUser && 'flex-row-reverse'
            )}
          >
            <IconButton size="sm" onClick={copy} aria-label="Copy">
              {copied ? <Check size={13} /> : <Copy size={13} />}
            </IconButton>
            {isUser ? (
              <IconButton size="sm" onClick={() => setEditing(true)} aria-label="Edit">
                <Pencil size={13} />
              </IconButton>
            ) : (
              <>
                <IconButton
                  size="sm"
                  onClick={() => regenerate(message.id, message.model ?? selectedModel)}
                  aria-label="Regenerate"
                >
                  <RotateCcw size={13} />
                </IconButton>
                <IconButton
                  size="sm"
                  active={feedback === 'up'}
                  onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                  aria-label="Good response"
                >
                  <ThumbsUp size={13} />
                </IconButton>
                <IconButton
                  size="sm"
                  active={feedback === 'down'}
                  onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                  aria-label="Bad response"
                >
                  <ThumbsDown size={13} />
                </IconButton>
              </>
            )}
            <span className="ml-1 text-[10px] text-gray-400">{formatTime(message.createdAt)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-gray-400 typing-dot"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
