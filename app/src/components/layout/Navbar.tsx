import { Menu, PanelLeftOpen, MessageSquarePlus, Sun, Moon } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useChatStore } from '@/stores/chatStore';
import { IconButton } from '@/components/common/IconButton';

export function Navbar({ title }: { title: string }) {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setMobileSidebarOpen = useUIStore((s) => s.setMobileSidebarOpen);
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);
  const selectedModel = useUIStore((s) => s.selectedModel);
  const newConversation = useChatStore((s) => s.newConversation);

  return (
    <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-gray-100 dark:border-gray-800 px-3">
      <div className="flex items-center gap-1 min-w-0">
        <IconButton className="md:hidden" onClick={() => setMobileSidebarOpen(true)} aria-label="Open menu">
          <Menu size={19} />
        </IconButton>
        {!sidebarOpen && (
          <IconButton className="hidden md:inline-flex" onClick={toggleSidebar} aria-label="Open sidebar">
            <PanelLeftOpen size={19} />
          </IconButton>
        )}
        <h1 className="truncate px-1 text-sm font-medium text-gray-700 dark:text-gray-200">{title}</h1>
      </div>

      <div className="flex items-center gap-1">
        <IconButton
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </IconButton>
        <IconButton onClick={() => newConversation(selectedModel)} aria-label="New chat">
          <MessageSquarePlus size={19} />
        </IconButton>
      </div>
    </div>
  );
}
