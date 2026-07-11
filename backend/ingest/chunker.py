from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from backend import config

OVERLAP_SENTENCES = 1


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _chunk_text(text: str, max_words: int = config.MAX_CHUNK_WORDS) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for sent in sentences:
        sent_words = len(sent.split())
        if sent_words > max_words:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_words = 0
            words = sent.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))
            continue
        if current and current_words + sent_words > max_words:
            chunks.append(" ".join(current))
            current = [sent]
            current_words = sent_words
        else:
            current.append(sent)
            current_words += sent_words
    if current:
        chunks.append(" ".join(current))
    return chunks


def _add_overlap(chunks: list[str]) -> list[str]:
    if len(chunks) <= 1 or OVERLAP_SENTENCES <= 0:
        return chunks
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_sents = _split_sentences(chunks[i - 1])
        overlap = prev_sents[-OVERLAP_SENTENCES:] if prev_sents else []
        if overlap:
            result.append(" ".join(overlap) + " " + chunks[i])
        else:
            result.append(chunks[i])
    return result


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower()).strip()
    slug = re.sub(r"\s+", "_", slug)
    return slug[:40] if slug else "section"


def _structural_id(category: str, heading: str, ordinal: int) -> str:
    slug = _slugify(heading)
    return f"{category}_{slug}_{ordinal:03d}"


def _content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _make_chunks_from_section(
    text: str, source: str, category: str, heading: str, ordinal: int
) -> list[dict]:
    out: list[dict] = []
    pieces = _chunk_text(text)
    pieces = _add_overlap(pieces)
    for i, piece in enumerate(pieces):
        cid = _structural_id(category, heading, ordinal + i)
        out.append(
            {
                "chunk_id": cid,
                "text": piece,
                "content_hash": _content_hash(piece),
                "metadata": {
                    "source": source,
                    "category": category,
                    "title": heading,
                    "heading_path": heading,
                    "section_index": ordinal + i,
                },
            }
        )
    return out


def _parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    lines = text.split("\n")
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in lines:
        if line.startswith("#"):
            if current_heading or current_body:
                sections.append((current_heading, "\n".join(current_body).strip()))
            current_heading = line.lstrip("#").strip()
            current_body = []
        else:
            current_body.append(line)
    if current_heading or current_body:
        sections.append((current_heading, "\n".join(current_body).strip()))
    return sections


def _from_bio(bio: dict) -> list[dict]:
    chunks: list[dict] = []
    summary = (
        f"{bio.get('name', 'James')} is a {bio.get('age', '')}-year-old "
        f"{bio.get('role', '')} living in {bio.get('location', '')}. "
        f"Tagline: {bio.get('tagline', '')}."
    )
    chunks += _make_chunks_from_section(summary, "site", "bio", "Bio summary", 0)
    ordinal = 1
    for p in bio.get("paragraphs", []):
        chunks += _make_chunks_from_section(p, "site", "bio", "Bio", ordinal)
        ordinal += 1
    return chunks


def _from_socials(socials: list[dict]) -> list[dict]:
    parts = []
    for s in socials:
        label = s.get("label", "")
        href = s.get("href", "")
        if label.lower() == "email":
            parts.append(f"James can be contacted by email at {href.replace('mailto:', '')}.")
        elif "youtube" in href.lower():
            handle = href.rstrip("/").split("/")[-1]
            parts.append(f"James's YouTube channel is {handle} ({href}).")
        else:
            parts.append(f"{label}: {href}.")
    return _make_chunks_from_section(" ".join(parts), "site", "contact", "Contact and socials", 0)


def _from_sports(sports: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for i, s in enumerate(sports):
        name = s.get("name", "")
        since = s.get("since", "")
        desc = s.get("description", "")
        text = f"James plays {name}, which he started in {since}. {desc}"
        chunks += _make_chunks_from_section(text, "site", "sport", name, i)
    return chunks


def _from_hobbies(hobbies: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for i, h in enumerate(hobbies):
        name = h.get("name", "")
        desc = h.get("description", "")
        chunks += _make_chunks_from_section(f"{name}: {desc}", "site", "hobby", name, i)
    return chunks


def _from_videos(videos: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for i, v in enumerate(videos):
        title = v.get("title", "")
        quality = v.get("quality", "")
        year = v.get("year", "")
        desc = v.get("description", "")
        text = f"James filmed a video titled '{title}' ({quality}, {year}). {desc}"
        chunks += _make_chunks_from_section(text, "site", "video", title, i)
    return chunks


def _from_essays(essays: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for i, e in enumerate(essays):
        title = e.get("title", "")
        abstract = e.get("abstract", "")
        chunks += _make_chunks_from_section(
            f"James wrote an essay titled '{title}'. {abstract}", "site", "essay", title, i
        )
    return chunks


def _from_photos(photos: list[dict], hero_caption: str | None) -> list[dict]:
    chunks: list[dict] = []
    ordinal = 0
    for p in photos:
        caption = p.get("caption")
        if caption:
            chunks += _make_chunks_from_section(
                f"Photography by James: {caption}", "site", "photo", "Photography", ordinal
            )
            ordinal += 1
    if hero_caption:
        chunks += _make_chunks_from_section(
            f"Photography by James: {hero_caption}", "site", "photo", "Photography", ordinal
        )
    return chunks


def _from_kb_extra(extra_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    if not extra_dir.exists():
        return chunks
    for md in sorted(extra_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8").strip()
        category = md.stem
        sections = _parse_markdown_sections(text)
        ordinal = 0
        for heading, body in sections:
            section_text = f"## {heading}\n{body}" if heading else body
            if not body.strip():
                continue
            made = _make_chunks_from_section(section_text, "extra", category, heading or category, ordinal)
            chunks += made
            ordinal += len(made)
    return chunks


def build_chunks(content_path: Path, extra_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    if content_path.exists():
        content = json.loads(content_path.read_text(encoding="utf-8"))
        if "bio" in content:
            chunks += _from_bio(content["bio"])
        if "socials" in content:
            chunks += _from_socials(content["socials"])
        if "sports" in content:
            chunks += _from_sports(content["sports"])
        if "otherHobbies" in content:
            chunks += _from_hobbies(content["otherHobbies"])
        if "videos" in content:
            chunks += _from_videos(content["videos"])
        if "essays" in content:
            chunks += _from_essays(content["essays"])
        if "photos" in content or "heroCaption" in content:
            chunks += _from_photos(content.get("photos", []), content.get("heroCaption"))
    chunks += _from_kb_extra(extra_dir)
    chunks.sort(key=lambda c: c["chunk_id"])
    return chunks


def main() -> None:
    chunks = build_chunks(config.CONTENT_EXPORT_PATH, config.KB_EXTRA_DIR)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CHUNKS_PATH.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    categories: dict[str, int] = {}
    for c in chunks:
        cat = c["metadata"]["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print(f"[chunker] wrote {len(chunks)} chunks to {config.CHUNKS_PATH}")
    print(f"[chunker] categories: {categories}")


if __name__ == "__main__":
    main()
