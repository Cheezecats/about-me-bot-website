import pytest

from backend.retrieval import bm25
from backend.retrieval.tokenizer import tokenize


MINI_CORPUS = [
    {"chunk_id": "a", "text": "James plays Apex Legends and reached Diamond rank.", "metadata": {}},
    {"chunk_id": "b", "text": "James started ice hockey in 2015 and tennis in 2018.", "metadata": {}},
    {"chunk_id": "c", "text": "Photography of Japan winter landscapes in Hokkaido.", "metadata": {}},
]


def test_tokenizer_strips_stopwords_and_case():
    assert tokenize("What is he in Apex Legends?") == ["apex", "legends"]
    assert tokenize("") == []
    assert tokenize("   ") == []


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


def test_real_kb_apex_query_top3():
    if not bm25.config.CHUNKS_PATH.exists():
        pytest.skip("data/chunks.json not built")
    idx = bm25.BM25Index.load(bm25.config.BM25_INDEX_PATH) if bm25.config.BM25_INDEX_PATH.exists() else bm25.BM25Index.build(bm25.load_chunks())
    chunks = bm25.load_chunks()
    results = bm25.retrieve("apex rank", idx, chunks, k=3)
    assert any("diamond" in r["text"].lower() for r in results)
    assert results[0]["metadata"]["category"] == "apex_rank"
