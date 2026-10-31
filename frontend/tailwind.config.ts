import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 900: "var(--navy-900)", 700: "var(--navy-700)" },
        sky: { 500: "var(--sky-500)", 100: "var(--sky-100)" },
        bg: "var(--bg)",
        card: "var(--card)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        line: "var(--line)",
        ok: { DEFAULT: "var(--ok)", bg: "var(--ok-bg)" },
        warn: { DEFAULT: "var(--warn)", bg: "var(--warn-bg)" },
        risk: { DEFAULT: "var(--risk)", bg: "var(--risk-bg)" },
        money: "var(--money)",
      },
      fontFamily: { sans: ["Inter", "Noto Sans Devanagari", "system-ui", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgba(15,23,42,.06), 0 4px 16px rgba(15,23,42,.06)" },
      borderRadius: { card: "16px", btn: "12px", phone: "36px" },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        pulsering: { "0%,100%": { boxShadow: "0 0 0 6px rgba(0,180,230,.18)" }, "50%": { boxShadow: "0 0 0 16px rgba(0,180,230,.08)" } },
        floatup: { from: { opacity: "1", transform: "translateY(0)" }, to: { opacity: "0", transform: "translateY(-18px)" } },
        slidedown: { from: { transform: "translateY(-100%)" }, to: { transform: "none" } },
      },
      animation: {
        rise: "rise .15s ease-out both",
        pulsering: "pulsering 1.2s ease-in-out infinite",
        floatup: "floatup 1.2s ease-out forwards",
        slidedown: "slidedown .25s ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;
