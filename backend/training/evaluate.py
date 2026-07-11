from __future__ import annotations

import json

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend import config
from backend.reranker.scoring import rank_scores
from backend.retrieval.bm25 import BM25Index, load_chunks


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


def _score_candidates(model, tokenizer, question: str, candidates: list[dict], device) -> list[float]:
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
    probs = rank_scores(logits)
    return probs


def _load_bm25(chunks: list[dict]) -> BM25Index:
    if config.BM25_INDEX_PATH.exists():
        return BM25Index.load(config.BM25_INDEX_PATH)
    return BM25Index.build(chunks)


def evaluate() -> dict:
    if not config.RERANKER_MODEL_DIR.exists():
        raise SystemExit(
            f"reranker model not found at {config.RERANKER_MODEL_DIR}. "
            "Run `python -m backend.training.train_reranker` first."
        )
    if not config.TEST_PATH.exists():
        raise SystemExit(
            "data/test.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )

    rows = _load_jsonl(config.TEST_PATH)
    chunks = load_chunks()
    by_id = {c["chunk_id"]: c for c in chunks}
    bm25 = _load_bm25(chunks)

    device = _device()
    tokenizer = AutoTokenizer.from_pretrained(config.RERANKER_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(config.RERANKER_MODEL_DIR)
    model.to(device)
    model.eval()

    p1_sum = 0.0
    p3_sum = 0.0
    mrr_sum = 0.0
    bm25_hit = 0
    n = len(rows)

    for r in rows:
        question = r["question"]
        pos_id = r["positive_chunk_id"]
        bm25_results = bm25.search(question, k=10)
        if pos_id in {cid for cid, _ in bm25_results}:
            bm25_hit += 1
        candidates = []
        for cid, _score in bm25_results:
            c = by_id.get(cid)
            if c is None:
                continue
            candidates.append({"chunk_id": cid, "text": c["text"]})
        if not candidates:
            continue
        scores = _score_candidates(model, tokenizer, question, candidates, device)
        ranked = sorted(
            zip(candidates, scores), key=lambda x: x[1], reverse=True
        )
        rank = 0
        for i, (c, _s) in enumerate(ranked):
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
        "precision_at_1": p1_sum / max(n, 1),
        "hit_at_3": p3_sum / max(n, 1),
        "mrr": mrr_sum / max(n, 1),
        "bm25_candidate_recall": bm25_hit / max(n, 1),
        "n_questions": n,
    }

    config.EVAL_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.EVAL_RESULTS_PATH.write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> None:
    metrics = evaluate()
    print(f"[eval] precision@1  = {metrics['precision_at_1']:.4f}")
    print(f"[eval] hit@3        = {metrics['hit_at_3']:.4f}")
    print(f"[eval] mrr          = {metrics['mrr']:.4f}")
    print(f"[eval] bm25_recall  = {metrics['bm25_candidate_recall']:.4f}")
    print(f"[eval] n_questions  = {metrics['n_questions']}")
    target = config.TARGET_PRECISION_AT_1
    ok = metrics["precision_at_1"] >= target
    print(f"[eval] precision@1 >= {target}? {ok}")


if __name__ == "__main__":
    main()
