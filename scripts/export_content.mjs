import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import ts from "typescript";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

// content.ts uses Vite's asset base, which does not exist in Node. Compile the
// pure data module with the installed TypeScript compiler so this also works
// on Node 20, without native TypeScript loading or a running dev server.
const source = readFileSync(join(root, "src", "data", "content.ts"), "utf8")
  .replaceAll("import.meta.env.BASE_URL", JSON.stringify(process.env.VITE_BASE_PATH || "/"));
const javascript = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText;
const content = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString("base64")}`);

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
const outPath = process.argv[2] || join(dataDir, "content_export.json");
writeFileSync(outPath, JSON.stringify(out, null, 2) + "\n", "utf8");

const counts = {};
for (const key of Object.keys(out)) {
  counts[key] = Array.isArray(out[key]) ? out[key].length : typeof out[key];
}
console.log(`[export_content] wrote ${outPath}`);
console.log("[export_content] summary:", counts);
