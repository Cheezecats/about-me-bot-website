from __future__ import annotations

import json

from backend import config


def main() -> None:
    if not config.CHUNKS_PATH.exists():
        raise SystemExit("data/chunks.json not built. Run `python -m backend.ingest.chunker` first.")
    chunks = json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))
    print(f"# {len(chunks)} chunks  (use these chunk_ids in data/qa_pairs.jsonl)\n")
    for c in chunks:
        cat = c["metadata"]["category"]
        title = c["metadata"]["title"]
        text = c["text"].replace("\n", " ")
        if len(text) > 90:
            text = text[:87] + "..."
        print(f"{c['chunk_id']}  [{cat}/{title}]  {text}")


if __name__ == "__main__":
    main()
