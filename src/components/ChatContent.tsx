import { memo, type ReactNode } from "react";
import { parseChatBlocks } from "../lib/chat-format";
import { trimLinkPunctuation } from "../lib/chat";

function inline(text: string): ReactNode[] {
  return text.split(/(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s)]+|\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer">{link[1]}<span className="sr-only"> (opens a new tab)</span></a>;
    if (/^https?:\/\//.test(part)) {
      const [url, punctuation] = trimLinkPunctuation(part);
      return <span key={i}><a href={url} target="_blank" rel="noopener noreferrer">{url}<span className="sr-only"> (opens a new tab)</span></a>{punctuation}</span>;
    }
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}

export default memo(function ChatContent({ content }: { content: string }) {
  return <div className="chat-prose">{parseChatBlocks(content).map((block, i) => {
    if (block.kind === "list") {
      const items = block.items.map((text, n) => <li key={n}>{inline(text)}</li>);
      return block.ordered ? <ol key={i} start={block.start}>{items}</ol> : <ul key={i}>{items}</ul>;
    }
    if (block.kind === "table") return <div className="chat-table" key={i} role="region" aria-label="Answer table" tabIndex={0}><table><thead><tr>{block.headers.map((h, n) => <th key={n} scope="col">{inline(h)}</th>)}</tr></thead><tbody>{block.rows.map((row, n) => <tr key={n}>{block.headers.map((_, c) => <td key={c}>{inline(row[c] || "")}</td>)}</tr>)}</tbody></table></div>;
    if (block.kind === "code") return <pre key={i} tabIndex={0} aria-label="Code excerpt"><code>{block.text}</code></pre>;
    if (block.kind === "heading") return <h4 key={i}>{inline(block.text)}</h4>;
    if (block.kind === "quote") return <blockquote key={i}>{inline(block.text)}</blockquote>;
    return <p key={i}>{inline(block.text)}</p>;
  })}</div>;
});
