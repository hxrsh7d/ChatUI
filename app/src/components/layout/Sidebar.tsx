import { useMemo, useState } from 'react';
import {
  MessageSquarePlus,
  Search,
  PanelLeftClose,
  Settings,
  Pin,
  PinOff,
  Pencil,
  Trash2,
  MoreHorizontal,
  Sparkles,
  X
} from 'lucide-react';
import clsx from 'clsx';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { groupLabelForTimestamp, groupOrderIndex } from '@/utils/date';
import { IconButton } from '@/components/common/IconButton';
import { DropdownMenu, DropdownItem } from '@/components/common/DropdownMenu';
import { Avatar } from '@/components/common/Avatar';
import type { Conversation } from '@/types';

export function Sidebar({ variant }: { variant: 'desktop' | 'mobile' }) {
  const conversations = useChatStore((s) => s.conversations);
  const activeId = useChatStore((s) => s.activeId);
  const selectConversation = useChatStore((s) => s.selectConversation);
  const deleteConversation = useChatStore((s) => s.deleteConversation);
  const renameConversation = useChatStore((s) => s.renameConversation);
  const togglePin = useChatStore((s) => s.togglePin);
  const newConversation = useChatStore((s) => s.newConversation);

  const selectedModel = useUIStore((s) => s.selectedModel);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const openSettings = useUIStore((s) => s.openSettings);
  const user = useUIStore((s) => s.user);

  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const closeIfMobile = () => variant === 'mobile' && setMobileSidebarOpen(false);

  const filtered = useMemo(
    () => conversations.filter((c) => c.title.toLowerCase().includes(query.trim().toLowerCase())),
    [conversations, query]
  );

  const pinned = filtered.filter((c) => c.pinned);
  const unpinned = filtered.filter((c) => !c.pinned);

  const groups = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    for (const c of unpinned) {
      const label = groupLabelForTimestamp(c.updatedAt);
      if (!map.has(label)) map.set(label, []);
      map.get(label)!.push(c);
    }
    return [...map.entries()]
      .sort((a, b) => groupOrderIndex(a[0]) - groupOrderIndex(b[0]))
      .map(([label, items]) => [label, items.sort((a, b) => b.updatedAt - a.updatedAt)] as const);
  }, [unpinned]);

  const startEdit = (c: Conversation) => {
    setEditingId(c.id);
    setEditValue(c.title);
  };
  const commitEdit = () => {
    if (editingId && editValue.trim()) renameConversation(editingId, editValue.trim());
    setEditingId(null);
  };

  return (
    <div className="flex h-full w-full flex-col bg-gray-50 dark:bg-gray-925 text-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-3 pt-3 pb-1">
        <div className="flex items-center gap-2 px-1 font-semibold text-gray-900 dark:text-white">
          <Sparkles size={18} className="text-blue-600" />
          <span>ChatUI</span>
        </div>
        {variant === 'desktop' ? (
          <IconButton size="sm" onClick={toggleSidebar} aria-label="Collapse sidebar">
            <PanelLeftClose size={17} />
          </IconButton>
        ) : (
          <IconButton size="sm" onClick={() => setMobileSidebarOpen(false)} aria-label="Close sidebar">
            <X size={18} />
          </IconButton>
        )}
      </div>

      {/* New chat */}
      <div className="px-3 pt-2">
        <button
          onClick={() => {
            newConversation(selectedModel);
            closeIfMobile();
          }}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors font-medium"
        >
          <MessageSquarePlus size={18} />
          New Chat
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pt-1 pb-2">
        <div className="flex items-center gap-2 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 px-3 py-2">
          <Search size={15} className="text-gray-400 shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search chats"
            className="w-full bg-transparent outline-none placeholder:text-gray-400 text-sm"
          />
        </div>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 && (
          <p className="px-3 py-6 text-center text-gray-400 text-xs">No conversations yet</p>
        )}

        {pinned.length > 0 && (
          <ChatGroup
            label="Pinned"
            items={pinned}
            activeId={activeId}
            editingId={editingId}
            editValue={editValue}
            setEditValue={setEditValue}
            onSelect={(id) => {
              selectConversation(id);
              closeIfMobile();
            }}
            onEditStart={startEdit}
            onEditCommit={commitEdit}
            onDelete={deleteConversation}
            onTogglePin={togglePin}
          />
        )}

        {groups.map(([label, items]) => (
          <ChatGroup
            key={label}
            label={label}
            items={items}
            activeId={activeId}
            editingId={editingId}
            editValue={editValue}
            setEditValue={setEditValue}
            onSelect={(id) => {
              selectConversation(id);
              closeIfMobile();
            }}
            onEditStart={startEdit}
            onEditCommit={commitEdit}
            onDelete={deleteConversation}
            onTogglePin={togglePin}
          />
        ))}
      </div>

      {/* Footer: settings + user */}
      <div className="border-t border-gray-200 dark:border-gray-800 p-2">
        <button
          onClick={() => openSettings('general')}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <Settings size={17} />
          Settings
        </button>
        <button
          onClick={() => openSettings('account')}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 mt-0.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <Avatar name={user?.name ?? 'You'} size={26} src={user?.avatarUrl} />
          <div className="flex flex-col items-start leading-tight">
            <span className="font-medium text-gray-900 dark:text-gray-100">{user?.name ?? 'You'}</span>
            <span className="text-[11px] text-gray-400">{user?.role === 'admin' ? 'Administrator' : 'User'}</span>
          </div>
        </button>
      </div>
    </div>
  );
}

function ChatGroup({
  label,
  items,
  activeId,
  editingId,
  editValue,
  setEditValue,
  onSelect,
  onEditStart,
  onEditCommit,
  onDelete,
  onTogglePin
}: {
  label: string;
  items: Conversation[];
  activeId: string | null;
  editingId: string | null;
  editValue: string;
  setEditValue: (v: string) => void;
  onSelect: (id: string) => void;
  onEditStart: (c: Conversation) => void;
  onEditCommit: () => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
}) {
  return (
    <div className="mb-2">
      <div className="px-3 pt-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">{label}</div>
      <div className="flex flex-col gap-0.5">
        {items.map((c) => (
          <div
            key={c.id}
            id="sidebar-chat-item"
            className={clsx(
              'group relative flex items-center rounded-xl px-3 py-2 cursor-pointer transition-colors',
              activeId === c.id
                ? 'bg-gray-200/70 dark:bg-gray-800'
                : 'hover:bg-gray-100 dark:hover:bg-gray-800/60'
            )}
            onClick={() => editingId !== c.id && onSelect(c.id)}
          >
            {editingId === c.id ? (
              <input
                autoFocus
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={onEditCommit}
                onKeyDown={(e) => e.key === 'Enter' && onEditCommit()}
                onClick={(e) => e.stopPropagation()}
                className="w-full bg-transparent outline-none border-b border-gray-400 text-sm"
              />
            ) : (
              <div dir="auto" className="flex-1 truncate text-[13.5px] text-gray-700 dark:text-gray-200">
                {c.title}
              </div>
            )}

            {editingId !== c.id && (
              <DropdownMenu
                trigger={({ toggle }) => (
                  <IconButton
                    size="sm"
                    className="opacity-0 group-hover:opacity-100 shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle();
                    }}
                    aria-label="Chat options"
                  >
                    <MoreHorizontal size={15} />
                  </IconButton>
                )}
              >
                <DropdownItem icon={c.pinned ? <PinOff size={14} /> : <Pin size={14} />} onClick={() => onTogglePin(c.id)}>
                  {c.pinned ? 'Unpin' : 'Pin'}
                </DropdownItem>
                <DropdownItem icon={<Pencil size={14} />} onClick={() => onEditStart(c)}>
                  Rename
                </DropdownItem>
                <DropdownItem icon={<Trash2 size={14} />} danger onClick={() => onDelete(c.id)}>
                  Delete
                </DropdownItem>
              </DropdownMenu>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
