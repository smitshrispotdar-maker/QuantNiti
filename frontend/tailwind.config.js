export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#080B11",
        panel: "#0F141D",
        surface: "#141B26",
        raised: "#1A2230",
        line: "#212B3A",
        "line-soft": "#182130",
        up: "#16C784",
        down: "#EA3943",
        ai: "#38BDF8",
        amber: "#F0B90B",
        muted: "#7C8AA0",
        "muted-2": "#556274",
        text: "#D6DEE9",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["10px", "14px"],
        xs: ["11px", "16px"],
        sm: ["12px", "18px"],
        base: ["13px", "20px"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.02) inset, 0 8px 30px rgba(0,0,0,0.25)",
      },
    },
  },
};
