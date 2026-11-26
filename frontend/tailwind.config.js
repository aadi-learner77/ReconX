/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sand: {
          50: "var(--sand-50)",
          100: "var(--sand-100)",
          200: "var(--sand-200)",
          300: "var(--sand-300)",
          400: "var(--sand-400)",
        },
        ink: {
          500: "var(--ink-500)",
          700: "var(--ink-700)",
          900: "var(--ink-900)",
        },
        paper: "var(--paper)",
        canvas: "var(--canvas-bg)",
        "on-ink": "var(--text-on-ink)",
        status: {
          "success-fg": "var(--status-success-fg)",
          "success-bg": "var(--status-success-bg)",
          "warning-fg": "var(--status-warning-fg)",
          "warning-bg": "var(--status-warning-bg)",
          "danger-fg": "var(--status-danger-fg)",
          "danger-bg": "var(--status-danger-bg)",
          "info-fg": "var(--status-info-fg)",
          "info-bg": "var(--status-info-bg)",
          "neutral-fg": "var(--status-neutral-fg)",
          "neutral-bg": "var(--status-neutral-bg)",
        },
      },
      fontFamily: {
        display: ['"Outfit"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        hero: "24px",
        card: "16px",
        control: "10px",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
      },
    },
  },
  plugins: [],
};
