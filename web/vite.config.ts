import { defineConfig } from "vite";

export default defineConfig({
  base: "/dashboard/",
  server: {
    proxy: {
      "/": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
