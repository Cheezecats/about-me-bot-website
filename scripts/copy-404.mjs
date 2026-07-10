import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const dist = join(__dirname, "..", "dist");
const src = join(dist, "index.html");
const dest = join(dist, "404.html");

if (!existsSync(src)) {
  console.error("[copy-404] dist/index.html not found — did the build run?");
  process.exit(1);
}

copyFileSync(src, dest);
console.log("[copy-404] Copied index.html -> 404.html for GitHub Pages SPA fallback.");
