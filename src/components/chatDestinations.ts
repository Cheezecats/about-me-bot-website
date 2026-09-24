import entries from "../../data/chat_destinations.json";

export interface ChatDestination {
  id: string;
  label: string;
  kind: "internal" | "external";
  href: string;
  subject: string;
  preview?: { title: string; subtitle: string; image: string; alt: string };
}

const internalPaths = new Set([
  "/photography", "/photography#authors-choice", "/videos", "/essays", "/hobbies", "/hobbies#sports",
]);

const externalHosts = new Set([
  "www.youtube.com", "open.spotify.com", "www.realmadrid.com", "www.ea.com",
  "www.counter-strike.net", "playvalorant.com", "www.cyberpunk.net",
  "www.rockstargames.com", "overwatch.blizzard.com", "civilization.2k.com", "www.nintendo.com",
]);

function isApprovedDestination(entry: ChatDestination): boolean {
  if (!entry?.id || !entry.label || !entry.subject || typeof entry.href !== "string") return false;
  if (entry.kind === "internal") return internalPaths.has(entry.href);
  if (entry.kind !== "external") return false;
  try {
    const url = new URL(entry.href);
    return url.protocol === "https:" && externalHosts.has(url.hostname) && !url.username && !url.password && !url.port;
  } catch {
    return false;
  }
}

const catalog = new Map(
  (entries as ChatDestination[]).filter(isApprovedDestination).map(entry => [entry.id, entry]),
);

export function resolveChatActions(ids: unknown): ChatDestination[] {
  if (!Array.isArray(ids)) return [];
  const seen = new Set<string>();
  const actions: ChatDestination[] = [];
  for (const id of ids) {
    if (typeof id !== "string" || seen.has(id)) continue;
    seen.add(id);
    const entry = catalog.get(id);
    if (entry) actions.push(entry);
  }
  return actions;
}

export function favoriteSongPreview(): ChatDestination["preview"] {
  const preview = catalog.get("song-youtube")?.preview;
  if (!preview || !preview.title || !preview.subtitle || !preview.alt) return undefined;
  try {
    const url = new URL(preview.image);
    return url.protocol === "https:" && url.hostname === "i.ytimg.com" && /^\/vi\/[\w-]{11}\/hqdefault\.jpg$/.test(url.pathname)
      ? preview : undefined;
  } catch {
    return undefined;
  }
}
