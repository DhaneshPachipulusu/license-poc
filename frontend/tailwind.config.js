/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        'bg-primary': '#0a0a0f',
        'bg-secondary': '#12121a',
        'bg-tertiary': '#1a1a24',
        'bg-elevated': '#22222e',
        'border-subtle': '#2a2a3a',
        'border-medium': '#3a3a4a',
        'text-primary': '#f0f0f5',
        'text-secondary': '#a0a0b0',
        'text-muted': '#606070',
      },
    },
  },
  plugins: [],
};