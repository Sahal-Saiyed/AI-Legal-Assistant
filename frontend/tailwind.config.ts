import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        secondary: "hsl(var(--secondary))",
        "secondary-foreground": "hsl(var(--secondary-foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        border: "hsl(var(--border))",
        ring: "hsl(var(--ring))"
      },
      borderRadius: {
        xl: "calc(var(--radius) - 4px)",
        "2xl": "var(--radius)",
        "3xl": "calc(var(--radius) + 8px)"
      },
      boxShadow: {
        soft: "0 22px 65px -34px rgba(28, 52, 47, 0.28)",
        float: "0 16px 45px -28px rgba(30, 65, 58, 0.34)"
      }
    }
  },
  plugins: []
} satisfies Config;
