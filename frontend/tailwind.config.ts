import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./context/**/*.{ts,tsx}", "./types/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "#0f172a",
          surface: "#1e293b",
          surfaceAlt: "#243145",
          primary: "#6366f1",
          secondary: "#06b6d4",
          border: "rgba(148, 163, 184, 0.18)",
          muted: "#94a3b8",
        },
      },
      boxShadow: {
        panel: "0 24px 80px rgba(15, 23, 42, 0.35)",
        glow: "0 18px 60px rgba(99, 102, 241, 0.16)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      backgroundImage: {
        "app-grid": "linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
