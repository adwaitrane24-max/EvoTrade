/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0A0A0B',
          surface: '#111114',
          elevated: '#16161A',
          border: '#1F1F25',
        },
        text: {
          primary: '#E8E8EC',
          secondary: '#9A9AA3',
          muted: '#5A5A63',
        },
        signal: {
          buy: '#10B981',
          sell: '#EF4444',
          hold: '#6B7280',
        },
        accent: {
          primary: '#3B82F6',
          secondary: '#8B5CF6',
        },
        regime: {
          bull: '#10B981',
          bear: '#EF4444',
          sideways: '#F59E0B',
          crash: '#DC2626',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { transform: 'translateY(12px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        pulse3: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse3 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
