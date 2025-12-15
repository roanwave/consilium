import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        war: {
          bg: "#0a0a0b",
          surface: "#141416",
          border: "#27272a",
          muted: "#3f3f46",
          text: "#e4e4e7",
          accent: "#d97706",
          accentMuted: "#92400e",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
