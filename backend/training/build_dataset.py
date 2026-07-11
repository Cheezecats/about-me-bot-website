from __future__ import annotations

import json
import random

from backend import config
from backend.retrieval.bm25 import BM25Index


def _load_chunks() -> dict[str, dict]:
    chunks = json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))
    return {c["chunk_id"]: c for c in chunks}


def _load_pairs() -> list[dict]:
    pairs = []
    for line in config.QA_PAIRS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            pairs.append(json.loads(line))
    return pairs


def _sample_random_negatives(
    positive_ids: set[str],
    by_id: dict[str, dict],
    n: int,
    rng: random.Random,
) -> list[str]:
    pool = [cid for cid in by_id if cid not in positive_ids]
    return rng.sample(pool, min(n, len(pool)))


def _sample_negatives(
    question: str,
    positive_ids: set[str],
    by_id: dict[str, dict],
    bm25: BM25Index,
    total: int,
    rng: random.Random,
) -> list[str]:
    n_hard = min(3, max(0, total - 1))
    hard: list[str] = []
    for cid, _score in bm25.search(question, k=10):
        if cid in positive_ids or cid in hard:
            continue
        hard.append(cid)
        if len(hard) >= n_hard:
            break
    excluded = set(hard) | positive_ids
    pool = [cid for cid in by_id if cid not in excluded]
    n_random = total - len(hard)
    random_negs = rng.sample(pool, min(n_random, len(pool)))
    return hard + random_negs


def build() -> None:
    by_id = _load_chunks()
    pairs = _load_pairs()
    if not pairs:
        raise SystemExit("data/qa_pairs.jsonl is empty - author some (question, chunk) pairs first.")

    for p in pairs:
        if p["positive_chunk_id"] not in by_id:
            raise SystemExit(f"positive_chunk_id not found in chunks: {p['positive_chunk_id']}")

    rng = random.Random(42)
    bm25 = BM25Index.build(list(by_id.values()))

    chunk_ids = sorted({p["positive_chunk_id"] for p in pairs})
    rng.shuffle(chunk_ids)
    n = len(chunk_ids)
    n_test = max(1, int(n * config.TRAIN_TEST_SPLIT))
    n_val = max(1, int(n * config.TRAIN_VAL_SPLIT))
    test_chunks = set(chunk_ids[:n_test])
    val_chunks = set(chunk_ids[n_test : n_test + n_val])
    train_chunks = set(chunk_ids[n_test + n_val :])

    chunk_to_questions: dict[str, set[str]] = {}
    question_positives: dict[str, set[str]] = {}
    by_question: dict[str, list[dict]] = {}
    for p in pairs:
        cid = p["positive_chunk_id"]
        q = p["question"]
        chunk_to_questions.setdefault(cid, set()).add(q)
        question_positives.setdefault(q, set()).add(cid)
        by_question.setdefault(q, []).append(p)

    test_qs: set[str] = set()
    val_qs: set[str] = set()
    train_qs: set[str] = set()
    for cid in chunk_ids:
        qs = chunk_to_questions.get(cid, set())
        if cid in test_chunks:
            test_qs |= qs
        elif cid in val_chunks:
            val_qs |= qs
        else:
            train_qs |= qs

    # Deduplicate across splits to prevent train/test leakage when a question
    # is paired with multiple chunks assigned to different splits.
    val_qs -= test_qs
    train_qs -= test_qs
    train_qs -= val_qs

    def make_pair_rows(qs: set[str]) -> list[dict]:
        rows = []
        for q in sorted(qs):
            positives = question_positives[q]
            for p in by_question[q]:
                pos_id = p["positive_chunk_id"]
                rows.append(
                    {"question": q, "chunk_id": pos_id, "text": by_id[pos_id]["text"], "label": 1}
                )
                for neg_id in _sample_negatives(
                    q, positives, by_id, bm25, config.NEGATIVES_PER_POSITIVE, rng
                ):
                    rows.append(
                        {"question": q, "chunk_id": neg_id, "text": by_id[neg_id]["text"], "label": 0}
                    )
        return rows

    def make_test_rows(qs: set[str]) -> list[dict]:
        rows = []
        for q in sorted(qs):
            positives = question_positives[q]
            for p in by_question[q]:
                pos_id = p["positive_chunk_id"]
                neg_ids = _sample_random_negatives(positives, by_id, 9, rng)
                candidates = [{"chunk_id": pos_id, "text": by_id[pos_id]["text"], "label": 1}]
                for nid in neg_ids:
                    candidates.append({"chunk_id": nid, "text": by_id[nid]["text"], "label": 0})
                rng.shuffle(candidates)
                rows.append({"question": q, "positive_chunk_id": pos_id, "candidates": candidates})
        return rows

    train_rows = make_pair_rows(train_qs)
    val_rows = make_pair_rows(val_qs)
    test_rows = make_test_rows(test_qs)

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_jsonl(config.TRAIN_PATH, train_rows)
    _write_jsonl(config.VAL_PATH, val_rows)
    _write_jsonl(config.TEST_PATH, test_rows)

    print(f"[build_dataset] questions: train={len(train_qs)} val={len(val_qs)} test={len(test_qs)}")
    print(f"[build_dataset] rows:      train={len(train_rows)} val={len(val_rows)} test={len(test_rows)}")


def _write_jsonl(path, rows) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    build()
