import json
import os

import pytest

from backend.retrieval import bm25
from backend.retrieval.tokenizer import tokenize, tokenize_query


MINI_CORPUS = [
    {"chunk_id": "a", "text": "James plays Apex Legends and reached Diamond rank.", "metadata": {}},
    {"chunk_id": "b", "text": "James started ice hockey in 2015 and tennis in 2018.", "metadata": {}},
    {"chunk_id": "c", "text": "Photography of Japan winter landscapes in Hokkaido.", "metadata": {}},
]


def test_tokenizer_strips_stopwords_and_case():
    assert tokenize("What is he in Apex Legends?") == ["apex", "legends"]
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_query_tokenizer_handles_common_variations():
    assert "games" in tokenize_query("favorite game")
    assert "favorite" in tokenize_query("favoriate game")
    assert "interests" in tokenize_query("what are your hobbies")
    assert "photography" in tokenize_query("photographt")
    assert "papers" in tokenize_query("what essays has James written")
    assert "traveled" in tokenize_query("Where has James travelled")
    assert "guitar" in tokenize_query("Does James play an instrument")
    assert "favorite" in tokenize_query("What games does James enjoy")
    assert "education" in tokenize_query("What school does James attend")
    assert "achievements" in tokenize_query("What awards has James won")


def test_bm25_build_sets_stats():
    idx = bm25.BM25Index.build(MINI_CORPUS)
    assert idx.n_docs == 3
    assert idx.avgdl > 0
    assert "apex" in idx.inverted_index
    assert idx.inverted_index["apex"] == {"a": 1}


def test_bm25_scores_deterministic():
    idx = bm25.BM25Index.build(MINI_CORPUS)
    s1 = idx.score("apex rank", "a")
    s2 = idx.score("apex rank", "a")
    assert s1 == s2


def test_bm25_ranking_order():
    idx = bm25.BM25Index.build(MINI_CORPUS)
    results = idx.search("apex legends diamond", k=3)
    assert results[0][0] == "a"
    assert results[0][1] > 0
    results_sport = idx.search("ice hockey 2015", k=3)
    assert results_sport[0][0] == "b"


def test_bm25_empty_query():
    idx = bm25.BM25Index.build(MINI_CORPUS)
    assert idx.search("", k=3) == []
    assert idx.search("   ", k=3) == []


def test_bm25_unknown_terms_return_empty():
    idx = bm25.BM25Index.build(MINI_CORPUS)
    assert idx.search("zzzznonexistent", k=3) == []


def test_bm25_save_load_roundtrip(tmp_path):
    idx = bm25.BM25Index.build(MINI_CORPUS)
    p = tmp_path / "idx.json"
    idx.save(p)
    loaded = bm25.BM25Index.load(p)
    assert loaded.n_docs == idx.n_docs
    assert loaded.inverted_index == idx.inverted_index
    assert loaded.search("apex", k=1)[0][0] == "a"


def test_load_or_build_rebuilds_when_chunks_are_newer(tmp_path, monkeypatch):
    chunks_path = tmp_path / "chunks.json"
    index_path = tmp_path / "bm25_index.json"
    chunks_path.write_text(json.dumps(MINI_CORPUS), encoding="utf-8")
    bm25.BM25Index.build([MINI_CORPUS[0]]).save(index_path)

    monkeypatch.setattr(bm25.config, "CHUNKS_PATH", chunks_path)
    monkeypatch.setattr(bm25.config, "BM25_INDEX_PATH", index_path)
    stale_time = index_path.stat().st_mtime_ns
    os.utime(chunks_path, ns=(stale_time + 1_000_000_000, stale_time + 1_000_000_000))

    refreshed = bm25.load_or_build()

    assert refreshed.n_docs == len(MINI_CORPUS)
    assert refreshed.search("photography", k=1)[0][0] == "c"


def test_real_kb_apex_query_top3():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.load(bm25.config.BM25_INDEX_PATH) if bm25.config.BM25_INDEX_PATH.exists() else bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    results = bm25.retrieve("apex rank", idx, chunks, k=3)
    assert any("diamond" in r["text"].lower() for r in results)
    assert results[0]["metadata"]["category"] == "apex_rank"


def test_real_kb_favorite_game_query_finds_favorite_games():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    results = bm25.retrieve("favoriate game", idx, chunks, k=3)
    assert results[0]["chunk_id"] == "favorites_favorite_games_002"


def test_real_kb_broad_topic_queries_find_summary_chunks():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    assert bm25.retrieve("sports", idx, chunks, k=1)[0]["chunk_id"] == "sports_sports_000"
    assert bm25.retrieve("what essays has James written", idx, chunks, k=1)[0]["chunk_id"] == "writing_writing_essays_000"


def test_real_kb_synonyms_find_their_topic_chunks():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    assert bm25.retrieve("Where has James travelled", idx, chunks, k=1)[0]["chunk_id"] == "travel_travel_000"
    assert bm25.retrieve("Does James play an instrument", idx, chunks, k=1)[0]["chunk_id"] == "hobbies_electric_guitar_000"
    assert bm25.retrieve("What projects has James built", idx, chunks, k=1)[0]["chunk_id"] == "projects_skills_projects_skills_000"


def test_real_kb_awards_query_finds_achievements_summary():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    assert bm25.retrieve("What awards has James won", idx, chunks, k=1)[0]["chunk_id"] == "achievements_achievements_awards_000"
    assert bm25.retrieve("awards", idx, chunks, k=1)[0]["chunk_id"] == "achievements_achievements_awards_000"
