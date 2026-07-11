import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const content = await import(join(root, "src", "data", "content.ts"));

const exportKeys = [
  "bio",
  "socials",
  "sports",
  "otherHobbies",
  "videos",
  "essays",
  "navLinks",
  "photos",
  "heroCaption",
];

const out = {};
for (const key of exportKeys) {
  if (key in content) {
    out[key] = content[key];
  } else {
    console.warn(`[export_content] key not found: ${key}`);
  }
}

const dataDir = join(root, "data");
mkdirSync(dataDir, { recursive: true });
const outPath = join(dataDir, "content_export.json");
writeFileSync(outPath, JSON.stringify(out, null, 2) + "\n", "utf8");

const counts = {};
for (const key of Object.keys(out)) {
  counts[key] = Array.isArray(out[key]) ? out[key].length : typeof out[key];
}
console.log(`[export_content] wrote ${outPath}`);
console.log("[export_content] summary:", counts);
