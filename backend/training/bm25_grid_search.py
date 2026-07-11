from __future__ import annotations

import json

from backend import config
from backend.retrieval.bm25 import BM25Index, load_chunks

K1_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5]
B_VALUES = [0.25, 0.50, 0.75, 1.0]
SELECTION_METRIC = "recall_at_10"
OUTPUT_PATH = config.DATA_DIR / "bm25_grid_search.json"


def _load_jsonl(path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _recall_at_k(bm25, questions, pos_ids, k) -> float:
    hits = 0
    for q, pos_id in zip(questions, pos_ids):
        results = bm25.search(q, k=k)
        if pos_id in {cid for cid, _ in results}:
            hits += 1
    return hits / max(len(questions), 1)


def grid_search() -> dict:
    if not config.CHUNKS_PATH.exists():
        raise SystemExit(
            "data/chunks.json not found. Run the ingest/chunker pipeline first."
        )
    if not config.QA_PAIRS_PATH.exists():
        raise SystemExit(
            "data/qa_pairs.jsonl not found. Author some (question, chunk) pairs first."
        )

    chunks = load_chunks()
    pairs = _load_jsonl(config.QA_PAIRS_PATH)
    questions = [p["question"] for p in pairs]
    pos_ids = [p["positive_chunk_id"] for p in pairs]

    base = BM25Index.build(chunks)

    results: list[dict] = []
    for k1 in K1_VALUES:
        for b in B_VALUES:
            bm25 = BM25Index(
                base.inverted_index,
                base.doc_len,
                base.avgdl,
                base.n_docs,
                k1=k1,
                b=b,
            )
            r1 = _recall_at_k(bm25, questions, pos_ids, 1)
            r3 = _recall_at_k(bm25, questions, pos_ids, 3)
            r10 = _recall_at_k(bm25, questions, pos_ids, 10)
            results.append(
                {
                    "k1": k1,
                    "b": b,
                    "recall_at_1": r1,
                    "recall_at_3": r3,
                    "recall_at_10": r10,
                }
            )

    best = max(
        results,
        key=lambda r: (r["recall_at_10"], r["recall_at_3"], r["recall_at_1"]),
    )

    output = {
        "selection_metric": SELECTION_METRIC,
        "k1_values": K1_VALUES,
        "b_values": B_VALUES,
        "results": results,
        "best": best,
        "n_questions": len(questions),
        "n_chunks": len(chunks),
    }
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    results = grid_search()
    print("\n[bm25_grid] results (sorted by k1, b):")
    print(f"{'k1':>5} {'b':>5} {'recall@1':>10} {'recall@3':>10} {'recall@10':>10}")
    for r in sorted(results["results"], key=lambda x: (x["k1"], x["b"])):
        is_best = (
            r["k1"] == results["best"]["k1"] and r["b"] == results["best"]["b"]
        )
        marker = "  <-- best" if is_best else ""
        print(
            f"{r['k1']:>5.2f} {r['b']:>5.2f} {r['recall_at_1']:>10.4f} "
            f"{r['recall_at_3']:>10.4f} {r['recall_at_10']:>10.4f}{marker}"
        )
    print(
        f"\n[bm25_grid] best k1={results['best']['k1']} b={results['best']['b']} "
        f"recall@10={results['best']['recall_at_10']:.4f}"
    )
    print(f"[bm25_grid] saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
