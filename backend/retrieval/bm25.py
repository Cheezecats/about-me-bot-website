from __future__ import annotations

import json
import math
from pathlib import Path

from backend import config
from backend.retrieval.tokenizer import tokenize


class BM25Index:
    def __init__(
        self,
        inverted_index: dict[str, dict[str, int]],
        doc_len: dict[str, int],
        avgdl: float,
        n_docs: int,
        k1: float = config.BM25_K1,
        b: float = config.BM25_B,
    ) -> None:
        self.inverted_index = inverted_index
        self.doc_len = doc_len
        self.avgdl = avgdl
        self.n_docs = n_docs
        self.k1 = k1
        self.b = b

    @classmethod
    def build(cls, chunks: list[dict]) -> "BM25Index":
        inverted: dict[str, dict[str, int]] = {}
        doc_len: dict[str, int] = {}
        total_len = 0
        for c in chunks:
            cid = c["chunk_id"]
            tokens = tokenize(c["text"])
            doc_len[cid] = len(tokens)
            total_len += len(tokens)
            tf: dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            for tok, freq in tf.items():
                inverted.setdefault(tok, {})[cid] = freq
        avgdl = (total_len / n_docs) if (n_docs := len(chunks)) else 0.0
        return cls(inverted, doc_len, avgdl, n_docs)

    def _idf(self, term: str) -> float:
        n_t = len(self.inverted_index.get(term, {}))
        if n_t == 0:
            return 0.0
        return math.log(1 + (self.n_docs - n_t + 0.5) / (n_t + 0.5))

    def score(self, query: str, chunk_id: str) -> float:
        s = 0.0
        dl = self.doc_len.get(chunk_id, 0)
        denom_norm = self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0))
        for term in tokenize(query):
            postings = self.inverted_index.get(term)
            if not postings:
                continue
            f = postings.get(chunk_id)
            if not f:
                continue
            idf = self._idf(term)
            s += idf * (f * (self.k1 + 1)) / (f + denom_norm)
        return s

    def search(self, query: str, k: int = config.TOP_K) -> list[tuple[str, float]]:
        q_terms = tokenize(query)
        if not q_terms:
            return []
        candidates: set[str] = set()
        for term in q_terms:
            postings = self.inverted_index.get(term)
            if postings:
                candidates.update(postings.keys())
        scored = [(cid, self.score(query, cid)) for cid in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def to_dict(self) -> dict:
        return {
            "inverted_index": self.inverted_index,
            "doc_len": self.doc_len,
            "avgdl": self.avgdl,
            "n_docs": self.n_docs,
            "k1": self.k1,
            "b": self.b,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BM25Index":
        return cls(
            inverted_index=data["inverted_index"],
            doc_len=data["doc_len"],
            avgdl=data["avgdl"],
            n_docs=data["n_docs"],
            k1=data.get("k1", config.BM25_K1),
            b=data.get("b", config.BM25_B),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict()) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "BM25Index":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_chunks(path: Path = config.CHUNKS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def retrieve(
    query: str, index: BM25Index, chunks: list[dict], k: int = config.TOP_K
) -> list[dict]:
    by_id = {c["chunk_id"]: c for c in chunks}
    results = []
    for cid, score in index.search(query, k):
        c = by_id.get(cid)
        if c is None:
            continue
        results.append({**c, "score": round(score, 4)})
    return results


def build_and_save() -> BM25Index:
    chunks = load_chunks()
    index = BM25Index.build(chunks)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    index.save(config.BM25_INDEX_PATH)
    print(f"[bm25] indexed {index.n_docs} chunks, avgdl={index.avgdl:.2f}, vocab={len(index.inverted_index)}")
    return index


if __name__ == "__main__":
    build_and_save()
