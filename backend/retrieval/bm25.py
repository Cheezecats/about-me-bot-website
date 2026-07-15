from __future__ import annotations

import json
import math
from pathlib import Path

from backend import config
from backend.retrieval.tokenizer import tokenize, tokenize_query


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
        for term in tokenize_query(query):
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
        q_terms = tokenize_query(query)
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


def load_chunks(path: Path | None = None) -> list[dict]:
    path = path or config.CHUNKS_PATH
    chunks = json.loads(path.read_text(encoding="utf-8"))
    public_chunks: list[dict] = []
    for chunk in chunks:
        if chunk.get("chunk_id") in config.HIDDEN_CHAT_CHUNK_IDS:
            continue
        # The public project summary is a curated list, so remove details
        # James has excluded from JamChat even when an older generated corpus
        # is still present on disk.
        if chunk.get("chunk_id") == "projects_skills_projects_skills_000":
            chunk = {**chunk, "text": chunk["text"].replace(", and a Flappy Bird game.", ".")}
        public_chunks.append(chunk)
    return public_chunks


def retrieve(
    query: str, index: BM25Index, chunks: list[dict], k: int = config.TOP_K
) -> list[dict]:
    by_id = {c["chunk_id"]: c for c in chunks}
    results = []
    query_terms = set(tokenize_query(query))
    project_query = bool(query_terms & {"project", "projects", "built", "created", "developed"})
    achievement_query = bool(query_terms & {"award", "awards", "achievement", "achievements", "won"})
    travel_query = bool(query_terms & {"travel", "traveled", "travelled", "visited", "visit", "country", "countries", "training", "train", "abroad"})
    favorite_query = bool(query_terms & {"favorite", "favourite", "anime", "movie", "movies", "film", "films", "book", "books", "series", "place", "subject", "subjects", "ide", "editor", "editors"})
    specific_achievement_terms = query_terms & {
        "physics", "bowl", "curieux", "lumiere", "qiu", "china", "thinks", "big"
    }
    # Rank a sufficiently broad candidate pool before applying heading and
    # topic-summary bonuses; otherwise a summary ranked just below k can
    # never recover even when its title directly matches the query.
    candidate_k = max(k, config.TOP_K)
    for cid, score in index.search(query, candidate_k):
        c = by_id.get(cid)
        if c is None:
            continue
        category = c.get("metadata", {}).get("category", "")
        if project_query and category in {"bio", "contact"}:
            continue
        title_terms = set(tokenize(c.get("metadata", {}).get("title", "")))
        expanded_query_terms = set(tokenize_query(query))
        title_match = bool(title_terms & expanded_query_terms)
        # Prefer a chunk whose heading directly names the requested topic.
        # This resolves queries such as "favorite game" without changing the
        # BM25 index or enabling the unvalidated reranker.
        heading_bonus = 5.0 if title_match else 0.0
        summary_bonus = (
            12.0
            if achievement_query
            and not specific_achievement_terms
            and c.get("metadata", {}).get("title") == "Achievements & Awards"
            else 0.0
        )
        if travel_query and c.get("metadata", {}).get("title") == "Travel":
            summary_bonus += 12.0
        if project_query and c.get("metadata", {}).get("title") in {"Projects & Skills", "Programming languages"}:
            summary_bonus += 8.0
        if favorite_query and c.get("metadata", {}).get("title") in {
            "Favorite anime", "Favorite movie", "Favorite book series", "Favorite place",
            "Favorite school subject", "Favorite games", "Favorite music", "Favorite food",
            "Favorite season", "IDE/editor usage",
        }:
            summary_bonus += 10.0
        results.append({**c, "score": round(score + heading_bonus + summary_bonus, 4)})
    results.sort(key=lambda c: c["score"], reverse=True)
    return results[:k]


def build_and_save() -> BM25Index:
    chunks = load_chunks()
    index = BM25Index.build(chunks)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    index.save(config.BM25_INDEX_PATH)
    print(f"[bm25] indexed {index.n_docs} chunks, avgdl={index.avgdl:.2f}, vocab={len(index.inverted_index)}")
    return index


def load_or_build() -> BM25Index:
    """Load a current index, rebuilding it when the chunk source changed."""

    if (
        config.BM25_INDEX_PATH.exists()
        and config.CHUNKS_PATH.exists()
        and config.BM25_INDEX_PATH.stat().st_mtime_ns >= config.CHUNKS_PATH.stat().st_mtime_ns
    ):
        return BM25Index.load(config.BM25_INDEX_PATH)
    return build_and_save()


if __name__ == "__main__":
    build_and_save()
