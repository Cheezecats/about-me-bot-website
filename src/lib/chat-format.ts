/** Small, safe subset of Markdown used by JamChat. No HTML is interpreted. */
export type ChatBlock =
  | { kind: "paragraph" | "heading" | "quote" | "code"; text: string }
  | { kind: "list"; items: string[]; ordered: boolean; start: number }
  | { kind: "table"; headers: string[]; rows: string[][] };

export function parseChatBlocks(content: string): ChatBlock[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ChatBlock[] = [];
  const cells = (line: string) => line.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
  for (let i = 0; i < lines.length;) {
    const line = lines[i].trim();
    if (!line) { i++; continue; }
    if (line.startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
      if (i < lines.length) i++;
      blocks.push({ kind: "code", text: code.join("\n") });
      continue;
    }
    if (line.includes("|") && i + 1 < lines.length && cells(lines[i + 1]).length > 1 && cells(lines[i + 1]).every(c => /^:?-{3,}:?$/.test(c))) {
      const headers = cells(line), rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(cells(lines[i++]));
      blocks.push({ kind: "table", headers, rows });
      continue;
    }
    const item = line.match(/^([-*•]|\d+[.)])\s+(.+)$/);
    if (item) {
      const ordered = /^\d/.test(item[1]);
      const items = [item[2]];
      const start = ordered ? parseInt(item[1], 10) : 1;
      i++;
      while (i < lines.length) {
        const next = lines[i].trim().match(/^([-*•]|\d+[.)])\s+(.+)$/);
        if (!next || /^\d/.test(next[1]) !== ordered) break;
        items.push(next[2]); i++;
      }
      blocks.push({ kind: "list", ordered, start, items });
      continue;
    }
    if (/^#{1,6}\s/.test(line)) blocks.push({ kind: "heading", text: line.replace(/^#{1,6}\s+/, "") });
    else if (/^>\s?/.test(line)) blocks.push({ kind: "quote", text: line.replace(/^>\s?/, "") });
    else blocks.push({ kind: "paragraph", text: line });
    i++;
  }
  return blocks;
}

export function isNearBottom(scrollTop: number, scrollHeight: number, clientHeight: number): boolean {
  return scrollHeight - scrollTop - clientHeight < 64;
}
