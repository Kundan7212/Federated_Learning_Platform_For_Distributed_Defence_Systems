/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#030712',
          900: '#0a0f1e',
          800: '#0f172a',
          700: '#1e293b',
          600: '#334155',
        },
        cyber: {
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
      animation: {
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow':        'glow 2s ease-in-out infinite alternate',
        'scan':        'scan 3s linear infinite',
        'fade-in':     'fadeIn 0.5s ease-in',
        'slide-in':    'slideIn 0.3s ease-out',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 5px #22d3ee, 0 0 10px #22d3ee' },
          to:   { boxShadow: '0 0 10px #22d3ee, 0 0 30px #22d3ee, 0 0 60px #22d3ee' },
        },
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideIn: {
          from: { transform: 'translateX(-20px)', opacity: '0' },
          to:   { transform: 'translateX(0)',     opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
