/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: '#C8FF57',
      },
      keyframes: {
        blob: {
          '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' },
          '33%':       { transform: 'translate(30px, -40px) scale(1.08)' },
          '66%':       { transform: 'translate(-20px, 20px) scale(0.95)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-up-slow': {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%':   { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'spin': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'blob-1':       'blob 7s ease-in-out infinite',
        'blob-2':       'blob 9s ease-in-out infinite 2s',
        'blob-3':       'blob 11s ease-in-out infinite 4s',
        'fade-in':      'fade-in 0.8s ease-out both',
        'fade-up':      'fade-up 0.5s ease-out both',
        'fade-up-slow': 'fade-up-slow 1.2s ease-out both',
        'slide-up':     'slide-up 0.4s ease-out both',
        'spin':         'spin 1s linear infinite',
      },
    },
  },
  plugins: [],
}
