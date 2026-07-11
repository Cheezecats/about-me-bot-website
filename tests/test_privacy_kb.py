import json
import re

import pytest

from backend import config


def _load_chunks():
    if not config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built; run `python -m backend.ingest.chunker`")
    return json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))


# Whitelist: known public info or false positives that match regex patterns
# but are intentionally public (Bilibili UID) or harmless (dates, game names, ages)
_WHITELIST = [
    "1614032286",  # Bilibili UID - public info
    "55 contributions",  # GitHub stats - public, false positive on address pattern
    "Life at 18",  # age reference - false positive on address pattern
    "18 looks",  # continuation of "Life at 18"
    "Mario Kart",  # game name - false positive on address pattern
    "2024, 2025, and 2026",  # years - false positive on address pattern
    "2023 vs post",  # "post-2023" weapon mechanic - false positive on address pattern
    "pre-2023",  # weapon mechanic - false positive on address pattern
    "suihe0812@gmail.com",  # Public email - intentionally public contact info
]


def test_no_private_data_in_kb():
    chunks = _load_chunks()
    violations = []
    for c in chunks:
        for pattern in config.PRIVATE_KB_PATTERNS:
            matches = re.findall(pattern, c["text"], flags=re.IGNORECASE)
            for m in matches:
                if not any(wl.lower() in m.lower() or m.lower() in wl.lower() for wl in _WHITELIST):
                    violations.append((c["chunk_id"], pattern, m, c["text"]))
    assert not violations, f"private data found in KB chunks: {violations}"


def test_chunks_have_required_fields():
    chunks = _load_chunks()
    for c in chunks:
        assert "chunk_id" in c
        assert "text" in c
        assert "metadata" in c
        assert {"source", "category", "title"} <= set(c["metadata"])


def test_chunk_ids_unique():
    chunks = _load_chunks()
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_word_limit():
    chunks = _load_chunks()
    for c in chunks:
        assert len(c["text"].split()) <= config.MAX_CHUNK_WORDS, c["text"]
