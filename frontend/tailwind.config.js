/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#fffdf8',
          100: '#fbf3e0',
          200: '#f5e6c6',
        },
        maroon: {
          50: '#f7e9ea',
          100: '#e7c1c6',
          400: '#8a2432',
          500: '#6b1a24',
          600: '#5a151d',
          700: '#3f0f15',
          900: '#2a0a0e',
        },
        gold: {
          300: '#e8cd7a',
          400: '#d4af37',
          500: '#b8912a',
          600: '#96741e',
        },
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
