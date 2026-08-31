/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#005eb8",
          600: "#004a94",
          700: "#003a73",
          900: "#001e3d",
        },
      },
    },
  },
  plugins: [],
};
