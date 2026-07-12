from __future__ import annotations

import json

from backend import config
from backend.reranker.inference import Reranker, RerankerUnavailable
from backend.retrieval.bm25 import BM25Index, load_chunks, load_or_build


def _load_jsonl(path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_bm25(chunks: list[dict]) -> BM25Index:
    return load_or_build()


def evaluate() -> dict:
    if not config.TEST_PATH.exists():
        raise SystemExit(
            "data/test.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )

    rows = _load_jsonl(config.TEST_PATH)
    chunks = load_chunks()
    by_id = {c["chunk_id"]: c for c in chunks}
    bm25 = _load_bm25(chunks)

    try:
        reranker = Reranker()
    except RerankerUnavailable as exc:
        raise SystemExit(str(exc)) from exc

    p1_sum = 0.0
    p3_sum = 0.0
    mrr_sum = 0.0
    bm25_p1_sum = 0.0
    bm25_p3_sum = 0.0
    bm25_mrr_sum = 0.0
    bm25_hit = 0
    n = len(rows)

    for r in rows:
        question = r["question"]
        pos_id = r["positive_chunk_id"]
        bm25_results = bm25.search(question, k=10)
        bm25_rank = next(
            (i + 1 for i, (cid, _score) in enumerate(bm25_results) if cid == pos_id),
            0,
        )
        if bm25_rank:
            bm25_hit += 1
            if bm25_rank == 1:
                bm25_p1_sum += 1
            if bm25_rank <= 3:
                bm25_p3_sum += 1
            bm25_mrr_sum += 1.0 / bm25_rank
        candidates = []
        for cid, _score in bm25_results:
            c = by_id.get(cid)
            if c is None:
                continue
            candidates.append({"chunk_id": cid, "text": c["text"]})
        if not candidates:
            continue
        ranked = reranker.rerank(question, candidates)
        rank = 0
        for i, c in enumerate(ranked):
            if c["chunk_id"] == pos_id:
                rank = i + 1
                break
        if rank == 0:
            continue
        if rank == 1:
            p1_sum += 1
        if rank <= 3:
            p3_sum += 1
        mrr_sum += 1.0 / rank

    metrics = {
        "reranker_backend": reranker.backend,
        "precision_at_1": p1_sum / max(n, 1),
        "hit_at_3": p3_sum / max(n, 1),
        "mrr": mrr_sum / max(n, 1),
        "bm25_candidate_recall": bm25_hit / max(n, 1),
        "bm25_precision_at_1": bm25_p1_sum / max(n, 1),
        "bm25_hit_at_3": bm25_p3_sum / max(n, 1),
        "bm25_mrr": bm25_mrr_sum / max(n, 1),
        "n_questions": n,
    }

    config.EVAL_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.EVAL_RESULTS_PATH.write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> None:
    metrics = evaluate()
    print(f"[eval] reranker      = {metrics['reranker_backend']}")
    print(f"[eval] precision@1  = {metrics['precision_at_1']:.4f}")
    print(f"[eval] hit@3        = {metrics['hit_at_3']:.4f}")
    print(f"[eval] mrr          = {metrics['mrr']:.4f}")
    print(f"[eval] bm25_recall  = {metrics['bm25_candidate_recall']:.4f}")
    print(f"[eval] bm25_p@1     = {metrics['bm25_precision_at_1']:.4f}")
    print(f"[eval] bm25_hit@3   = {metrics['bm25_hit_at_3']:.4f}")
    print(f"[eval] bm25_mrr     = {metrics['bm25_mrr']:.4f}")
    print(f"[eval] n_questions  = {metrics['n_questions']}")
    target = config.TARGET_PRECISION_AT_1
    ok = metrics["precision_at_1"] >= target
    print(f"[eval] precision@1 >= {target}? {ok}")


if __name__ == "__main__":
    main()
