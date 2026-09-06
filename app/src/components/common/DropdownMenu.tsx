import { ReactNode, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import clsx from 'clsx';

interface Props {
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode;
  children: ReactNode;
  align?: 'left' | 'right';
  className?: string;
}

interface Position {
  top: number;
  left: number;
}

const VIEWPORT_GAP = 8;
const MENU_GAP = 6;

export function DropdownMenu({ trigger, children, align = 'left', className }: Props) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<Position>({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const updatePosition = () => {
    const trigger = triggerRef.current;
    const menu = menuRef.current;
    if (!trigger || !menu) return;

    const triggerRect = trigger.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = align === 'right' ? triggerRect.right - menuRect.width : triggerRect.left;
    let top = triggerRect.bottom + MENU_GAP;

    // Keep the menu inside the viewport. This is especially important for
    // dropdowns inside the sidebar, where an absolute menu would otherwise
    // be clipped by the sidebar's fixed width.
    if (left + menuRect.width > viewportWidth - VIEWPORT_GAP) {
      left = viewportWidth - menuRect.width - VIEWPORT_GAP;
    }
    if (left < VIEWPORT_GAP) {
      left = VIEWPORT_GAP;
    }

    if (top + menuRect.height > viewportHeight - VIEWPORT_GAP) {
      top = triggerRect.top - menuRect.height - MENU_GAP;
    }
    if (top < VIEWPORT_GAP) {
      top = VIEWPORT_GAP;
    }

    setPosition({ top, left });
  };

  useEffect(() => {
    if (!open) return;

    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    const onViewportChange = () => updatePosition();

    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', onViewportChange);
    window.addEventListener('scroll', onViewportChange, true);

    requestAnimationFrame(updatePosition);

    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', onViewportChange);
      window.removeEventListener('scroll', onViewportChange, true);
    };
  }, [open, align]);

  return (
    <div className="relative inline-flex min-w-0" ref={triggerRef}>
      {trigger({ open, toggle: () => setOpen((o) => !o) })}
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className={clsx(
              'fixed z-[100] min-w-[180px] rounded-xl border border-gray-100 dark:border-gray-800',
              'bg-white dark:bg-gray-900 shadow-lg py-1.5 animate-fade-in',
              'max-w-[calc(100vw-16px)] overflow-y-auto',
              className
            )}
            style={{ top: position.top, left: position.left }}
            onClick={() => setOpen(false)}
          >
            {children}
          </div>,
          document.body
        )}
    </div>
  );
}

export function DropdownItem({
  children,
  onClick,
  danger,
  icon
}: {
  children: ReactNode;
  onClick?: () => void;
  danger?: boolean;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'flex w-full items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors',
        danger
          ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40'
          : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
      )}
    >
      {icon}
      {children}
    </button>
  );
}
