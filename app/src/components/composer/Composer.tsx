import { useRef, useState, KeyboardEvent, ChangeEvent, DragEvent, ClipboardEvent } from 'react';
import { Paperclip, ArrowUp, Square, Globe, ImageIcon, X } from 'lucide-react';
import clsx from 'clsx';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { ModelSelector } from '@/components/models/ModelSelector';
import { FileChip } from '@/components/documents/FileChip';
import { uploadDocument } from '@/services/api';
import type { Attachment } from '@/types';

const ACCEPTED = '.pdf,.txt,.md,.docx,image/*';

export function Composer() {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<Attachment[]>([]);
  const [dragging, setDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sendMessage = useChatStore((s) => s.sendMessage);
  const stopGenerating = useChatStore((s) => s.stopGenerating);
  const streamingId = useChatStore((s) => s.streamingId);

  const selectedModel = useUIStore((s) => s.selectedModel);
  const webSearchEnabled = useUIStore((s) => s.webSearchEnabled);
  const toggleWebSearch = useUIStore((s) => s.toggleWebSearch);
  const imageGenEnabled = useUIStore((s) => s.imageGenEnabled);
  const toggleImageGen = useUIStore((s) => s.toggleImageGen);

  const isStreaming = !!streamingId;

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  };

  // Uploads go through POST /api/documents (see services/api.ts). Each file
  // gets an optimistic "uploading" chip immediately, then is patched in
  // place as progress/status updates arrive.
  const addFiles = (fileList: FileList | File[]) => {
    Array.from(fileList).forEach((file) => {
      const tempId = crypto.randomUUID();
      const placeholder: Attachment = {
        id: tempId,
        name: file.name,
        type: file.type || 'application/octet-stream',
        size: file.size,
        status: 'uploading',
        progress: 0
      };
      setFiles((prev) => [...prev, placeholder]);

      uploadDocument(file, (percent) => {
        setFiles((prev) => prev.map((f) => (f.id === tempId ? { ...f, progress: percent } : f)));
      })
        .then((attachment) => {
          setFiles((prev) => prev.map((f) => (f.id === tempId ? { ...attachment, status: attachment.status ?? 'ready' } : f)));
        })
        .catch((err: Error) => {
          setFiles((prev) => prev.map((f) => (f.id === tempId ? { ...f, status: 'error', error: err.message } : f)));
        });
    });
  };

  const onFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files);
    e.target.value = '';
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const pasted = Array.from(e.clipboardData?.files ?? []);
    if (pasted.length) addFiles(pasted);
  };

  const canSend = (text.trim().length > 0 || files.length > 0) && !isStreaming;

  const handleSend = () => {
    if (!canSend || !selectedModel) return;
    sendMessage(
      text.trim(),
      selectedModel,
      { webSearch: webSearchEnabled, imageGeneration: imageGenEnabled, maxTokens: 1024 },
      files.length ? files : undefined
    );
    setText('');
    setFiles([]);
    requestAnimationFrame(autoResize);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="px-3 sm:px-4 pb-[env(safe-area-inset-bottom)]">
      <div
        className="mx-auto max-w-3xl"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div
          className={clsx(
            'rounded-2xl border bg-white dark:bg-gray-850 shadow-sm transition-colors',
            dragging ? 'border-blue-400 ring-2 ring-blue-400/30' : 'border-gray-200 dark:border-gray-700'
          )}
        >
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2 px-3 pt-3">
              {files.map((f) => (
                <FileChip key={f.id} file={f} onRemove={() => setFiles((x) => x.filter((y) => y.id !== f.id))} />
              ))}
            </div>
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              autoResize();
            }}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            placeholder={
              imageGenEnabled ? 'Describe the image you want to generate…' : 'Message your assistant…'
            }
            rows={1}
            className="w-full resize-none bg-transparent px-4 pt-3 pb-1 outline-none text-[15px] placeholder:text-gray-400 max-h-[200px]"
          />

          <div className="flex items-center justify-between gap-2 px-2.5 py-2">
            <div className="flex items-center gap-1 flex-wrap">
              <input ref={fileInputRef} type="file" multiple accept={ACCEPTED} hidden onChange={onFileInput} />
              <button
                onClick={() => fileInputRef.current?.click()}
                aria-label="Attach files"
                title="Attach a document or image"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300 transition-colors"
              >
                <Paperclip size={17} />
              </button>

              <ToggleChip
                active={webSearchEnabled}
                onClick={toggleWebSearch}
                icon={<Globe size={13} />}
                label="Web Search"
                title="Search the web and ground the answer in results"
              />
              <ToggleChip
                active={imageGenEnabled}
                onClick={toggleImageGen}
                icon={<ImageIcon size={13} />}
                label="Image"
                title="Generate an image instead of a text reply"
              />

              <div className="hidden sm:block">
                <ModelSelector />
              </div>
            </div>

            {isStreaming ? (
              <button
                onClick={stopGenerating}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900"
                aria-label="Stop generating"
              >
                <Square size={14} fill="currentColor" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!canSend}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-30 transition-opacity"
                aria-label="Send message"
              >
                <ArrowUp size={17} />
              </button>
            )}
          </div>

          <div className="sm:hidden px-2.5 pb-2">
            <ModelSelector />
          </div>
        </div>

        <p className="py-2 text-center text-[11px] text-gray-400">
          Responses are generated by AI and may be inaccurate. Verify important information.
        </p>
      </div>
    </div>
  );
}

function ToggleChip({
  active,
  onClick,
  icon,
  label,
  disabled,
  title
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={disabled ? `${label} (unavailable)` : label}
      className={clsx(
        'flex items-center gap-1.5 rounded-full px-2.5 h-8 text-xs font-medium transition-colors border',
        disabled
          ? 'border-transparent text-gray-300 dark:text-gray-600 cursor-not-allowed'
          : active
            ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-950/50 dark:border-blue-800 dark:text-blue-300'
            : 'border-transparent text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
      )}
    >
      {icon}
      <span className="hidden xs:inline sm:inline">{label}</span>
    </button>
  );
}
