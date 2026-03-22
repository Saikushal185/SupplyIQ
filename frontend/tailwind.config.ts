import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#07131a",
        panel: "#0d1e27",
        accent: "#19a7b0",
        accentWarm: "#f4a261",
      },
      boxShadow: {
        glow: "0 24px 64px rgba(25, 167, 176, 0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
