/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        primary: 'var(--color-primary)',
        muted: 'var(--color-muted)',
        positive: 'var(--color-positive)',
        negative: 'var(--color-negative)',
        neutral: 'var(--color-neutral)',
        warning: 'var(--color-warning)',
        border: 'var(--color-border)',
        accent: 'var(--color-accent)',
      },
      fontFamily: {
        sans: ['Inter', 'DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'Roboto Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}