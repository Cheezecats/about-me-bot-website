import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function chatApiOrigin(apiUrl: string): string {
  if (!apiUrl || apiUrl.startsWith("/")) return "";

  try {
    const origin = new URL(apiUrl).origin;
    return origin === "http://localhost:8000" ? "" : ` ${origin}`;
  } catch {
    return "";
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const repositoryName = process.env.GITHUB_REPOSITORY?.split("/").pop();
  const base =
    env.VITE_BASE_PATH ||
    (process.env.GITHUB_ACTIONS === "true" && repositoryName
      ? `/${repositoryName}/`
      : "/");
  const apiOrigin = chatApiOrigin(env.VITE_CHAT_API_URL || "");

  return {
    base,
    plugins: [
      react(),
      tailwindcss(),
      {
        name: "inject-chat-api-origin-into-csp",
        transformIndexHtml(html: string) {
          return html.replace("%CHAT_API_ORIGIN%", apiOrigin);
        },
      },
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
      cssMinify: true,
      chunkSizeWarningLimit: 1200,
    },
    optimizeDeps: {
      include: ["p5"],
    },
    server: {
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
