from __future__ import annotations

import json
import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend import config
from backend.reranker.scoring import rank_scores
from backend.retrieval.bm25 import BM25Index, load_chunks

CROSS_ENCODER_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
OUTPUT_PATH = config.DATA_DIR / "ablation_results.json"


def _load_jsonl(path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _load_bm25(chunks: list[dict]) -> BM25Index:
    if config.BM25_INDEX_PATH.exists():
        return BM25Index.load(config.BM25_INDEX_PATH)
    return BM25Index.build(chunks)


def _bm25_candidates(bm25, question, chunks_by_id, k) -> list[dict]:
    results = bm25.search(question, k=k)
    return [
        {"chunk_id": cid, "text": chunks_by_id[cid]["text"]}
        for cid, _ in results
        if cid in chunks_by_id
    ]


def _score_candidates(model, tokenizer, question, candidates, device) -> list[float]:
    texts = [c["text"] for c in candidates]
    enc = tokenizer(
        [question] * len(texts),
        texts,
        truncation=True,
        padding=True,
        max_length=256,
        return_tensors="pt",
    )
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits
    return rank_scores(logits)


def _rank_metrics(ranked_ids, pos_id) -> tuple[float, float, float]:
    rank = 0
    for i, cid in enumerate(ranked_ids):
        if cid == pos_id:
            rank = i + 1
            break
    p1 = 1.0 if rank == 1 else 0.0
    hit3 = 1.0 if 1 <= rank <= 3 else 0.0
    mrr = 1.0 / rank if rank > 0 else 0.0
    return p1, hit3, mrr


def _summarize(name, p1_list, hit3_list, mrr_list, latency_list) -> dict:
    n = len(p1_list)
    return {
        "approach": name,
        "precision_at_1": sum(p1_list) / max(n, 1),
        "hit_at_3": sum(hit3_list) / max(n, 1),
        "mrr": sum(mrr_list) / max(n, 1),
        "avg_latency_ms": (sum(latency_list) / max(n, 1)) * 1000.0,
        "n_questions": n,
    }


def _run_bm25_only(bm25, rows) -> dict:
    p1_list: list[float] = []
    hit3_list: list[float] = []
    mrr_list: list[float] = []
    lat: list[float] = []
    for r in rows:
        t0 = time.perf_counter()
        results = bm25.search(r["question"], k=10)
        lat.append(time.perf_counter() - t0)
        ranked_ids = [cid for cid, _ in results]
        a, b, c = _rank_metrics(ranked_ids, r["positive_chunk_id"])
        p1_list.append(a)
        hit3_list.append(b)
        mrr_list.append(c)
    return _summarize("bm25_only", p1_list, hit3_list, mrr_list, lat)


def _run_finetuned(model, tokenizer, bm25, rows, chunks_by_id, device) -> dict:
    if rows:
        warm = _bm25_candidates(bm25, rows[0]["question"], chunks_by_id, 10)
        if warm:
            _score_candidates(model, tokenizer, rows[0]["question"], warm, device)
    p1_list: list[float] = []
    hit3_list: list[float] = []
    mrr_list: list[float] = []
    lat: list[float] = []
    for r in rows:
        t0 = time.perf_counter()
        candidates = _bm25_candidates(bm25, r["question"], chunks_by_id, 10)
        if not candidates:
            lat.append(time.perf_counter() - t0)
            p1_list.append(0.0)
            hit3_list.append(0.0)
            mrr_list.append(0.0)
            continue
        scores = _score_candidates(
            model, tokenizer, r["question"], candidates, device
        )
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        lat.append(time.perf_counter() - t0)
        ranked_ids = [c["chunk_id"] for c, _ in ranked]
        a, b, c = _rank_metrics(ranked_ids, r["positive_chunk_id"])
        p1_list.append(a)
        hit3_list.append(b)
        mrr_list.append(c)
    return _summarize(
        "bm25_plus_finetuned_distilbert", p1_list, hit3_list, mrr_list, lat
    )


def _run_zeroshot(bm25, rows, chunks_by_id) -> dict:
    from sentence_transformers import CrossEncoder

    ce = CrossEncoder(CROSS_ENCODER_NAME)
    if rows:
        warm = _bm25_candidates(bm25, rows[0]["question"], chunks_by_id, 10)
        if warm:
            ce.predict([[rows[0]["question"], warm[0]["text"]]])
    p1_list: list[float] = []
    hit3_list: list[float] = []
    mrr_list: list[float] = []
    lat: list[float] = []
    for r in rows:
        t0 = time.perf_counter()
        candidates = _bm25_candidates(bm25, r["question"], chunks_by_id, 10)
        if not candidates:
            lat.append(time.perf_counter() - t0)
            p1_list.append(0.0)
            hit3_list.append(0.0)
            mrr_list.append(0.0)
            continue
        pairs = [[r["question"], c["text"]] for c in candidates]
        scores = ce.predict(pairs).tolist()
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        lat.append(time.perf_counter() - t0)
        ranked_ids = [c["chunk_id"] for c, _ in ranked]
        a, b, c = _rank_metrics(ranked_ids, r["positive_chunk_id"])
        p1_list.append(a)
        hit3_list.append(b)
        mrr_list.append(c)
    return _summarize(
        "bm25_plus_zeroshot_cross_encoder", p1_list, hit3_list, mrr_list, lat
    )


def run_ablation() -> dict:
    if not config.TEST_PATH.exists():
        raise SystemExit(
            "data/test.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )
    if not config.RERANKER_MODEL_DIR.exists():
        raise SystemExit(
            f"reranker model not found at {config.RERANKER_MODEL_DIR}. "
            "Run `python -m backend.training.train_reranker` first."
        )

    rows = _load_jsonl(config.TEST_PATH)
    chunks = load_chunks()
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    bm25 = _load_bm25(chunks)

    print(f"[ablation] n_questions={len(rows)} chunks={len(chunks)}")

    print("[ablation] running bm25_only ...")
    bm25_metrics = _run_bm25_only(bm25, rows)
    print(f"[ablation] bm25_only p@1={bm25_metrics['precision_at_1']:.4f}")

    print("[ablation] running bm25 + zero-shot cross-encoder ...")
    zeroshot_metrics = _run_zeroshot(bm25, rows, chunks_by_id)
    print(f"[ablation] zeroshot p@1={zeroshot_metrics['precision_at_1']:.4f}")

    device = _device()
    tokenizer = AutoTokenizer.from_pretrained(config.RERANKER_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(config.RERANKER_MODEL_DIR)
    model.to(device)
    model.eval()
    print("[ablation] running bm25 + fine-tuned DistilBERT reranker ...")
    finetuned_metrics = _run_finetuned(
        model, tokenizer, bm25, rows, chunks_by_id, device
    )
    print(f"[ablation] finetuned p@1={finetuned_metrics['precision_at_1']:.4f}")

    results = {
        "n_questions": len(rows),
        "approaches": [bm25_metrics, zeroshot_metrics, finetuned_metrics],
    }
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> None:
    results = run_ablation()
    print("\n[ablation] summary:")
    print(
        f"{'approach':<40} {'p@1':>8} {'hit@3':>8} "
        f"{'mrr':>8} {'latency_ms':>12}"
    )
    for a in results["approaches"]:
        print(
            f"{a['approach']:<40} {a['precision_at_1']:>8.4f} "
            f"{a['hit_at_3']:>8.4f} {a['mrr']:>8.4f} "
            f"{a['avg_latency_ms']:>12.2f}"
        )
    print(f"[ablation] saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
