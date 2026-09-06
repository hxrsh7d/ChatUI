/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gray: {
          50: '#fafafa',
          100: '#f0f0f0',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#adadad',
          500: '#8a8a8a',
          600: '#666666',
          700: '#454545',
          800: '#2e2e2e',
          850: '#232323',
          900: '#171717',
          925: '#111111',
          950: '#0d0d0d'
        }
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          'Segoe UI',
          'Roboto',
          'Ubuntu',
          'Cantarell',
          'Noto Sans',
          'sans-serif'
        ]
      },
      transitionProperty: {
        width: 'width'
      },
      keyframes: {
        'fade-in': { from: { opacity: 0 }, to: { opacity: 1 } },
        'slide-in': { from: { transform: 'translateX(-100%)' }, to: { transform: 'translateX(0)' } },
        blink: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.2 } }
      },
      animation: {
        'fade-in': 'fade-in 0.15s ease-out',
        'slide-in': 'slide-in 0.2s ease-out',
        blink: 'blink 1.2s ease-in-out infinite'
      }
    }
  },
  plugins: [require('@tailwindcss/typography')]
};
