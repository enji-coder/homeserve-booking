export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12241c",
        forest: "#1c4f3e",
        moss: "#3e6154",
        leaf: "#e7f3ec",
        cream: "#f3eee4",
        paper: "#fbf8f2",
        clay: "#c24d2c",
        gold: "#a57932",
        line: "#e4daca",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 24px 50px -28px rgba(18,36,28,0.45)",
      },
    },
  },
  plugins: [],
};
