import { resolve } from "path";
import { defineConfig } from "vite";

const __dirname = import.meta.dirname;

export default defineConfig({
  root: ".",
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        login: resolve(__dirname, "login.html"),
        review: resolve(__dirname, "review.html"),
        results: resolve(__dirname, "results.html"),
        history: resolve(__dirname, "history.html"),
        about: resolve(__dirname, "about.html"),
      },
    },
  },
  server: {
    port: 5173,
    open: "/index.html",
    proxy: {
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "^/review(/.*)?$": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => {
          if (
            req.url.endsWith(".html") ||
            req.url.endsWith(".js") ||
            req.url.endsWith(".css") ||
            req.headers.accept?.includes("text/html")
          ) {
            return req.url;
          }
        },
      },
      "/upload": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});


