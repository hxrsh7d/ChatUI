import { ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  size?: 'sm' | 'md';
}

export const IconButton = forwardRef<HTMLButtonElement, Props>(
  ({ className, active, size = 'md', children, ...rest }, ref) => (
    <button
      ref={ref}
      type="button"
      className={clsx(
        'inline-flex items-center justify-center rounded-lg transition-colors duration-150',
        'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60',
        'disabled:opacity-40 disabled:pointer-events-none',
        size === 'sm' ? 'h-7 w-7' : 'h-9 w-9',
        active && 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white',
        className
      )}
      {...rest}
    >
      {children}
    </button>
  )
);
IconButton.displayName = 'IconButton';
