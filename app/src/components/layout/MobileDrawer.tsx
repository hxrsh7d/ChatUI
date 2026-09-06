import { useUIStore } from '@/stores/uiStore';
import { Sidebar } from './Sidebar';

export function MobileDrawer() {
  const open = useUIStore((s) => s.mobileSidebarOpen);
  const setOpen = useUIStore((s) => s.setMobileSidebarOpen);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/40 animate-fade-in" onClick={() => setOpen(false)} />
      <div className="absolute left-0 top-0 h-full w-[85vw] max-w-[320px] shadow-2xl animate-slide-in">
        <Sidebar variant="mobile" />
      </div>
    </div>
  );
}
