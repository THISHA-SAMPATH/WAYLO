/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        page: "#F4F2EC",
        card: "#FFFFFF",
        ink: "#14201B",
        muted: "#5B6B63",
        primary: "#17352B",
        highlight: "#E3F26D",
        accent: "#F26B3A",
        success: "#1F7A4D",
        danger: "#C2410C",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        '24': '24px',
        '32': '32px',
      },
      boxShadow: {
        'soft': '0 8px 30px rgba(20, 32, 27, 0.05)',
        'soft-lg': '0 20px 45px rgba(20, 32, 27, 0.08)',
        'card': '0 4px 24px rgba(20, 32, 27, 0.04)',
      }
    },
  },
  plugins: [],
}
