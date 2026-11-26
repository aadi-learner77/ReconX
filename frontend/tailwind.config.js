/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
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
        display: ['"Manrope"', "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ['"Fraunces"', "Georgia", "serif"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        control: "var(--radius-control)",
        card: "var(--radius-card)",
        hero: "var(--radius-hero)",
      },
      boxShadow: {
        hairline: "var(--shadow-hairline)",
        card: "var(--shadow-card)",
        floating: "var(--shadow-floating)",
        soft: "var(--shadow-soft)",
      },
      transitionDuration: {
        fast: "var(--motion-fast)",
        base: "var(--motion-base)",
        slow: "var(--motion-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
      },
    },
  },
  plugins: [],
};
