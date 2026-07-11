from __future__ import annotations

import json

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend import config
from backend.reranker.scoring import rank_scores
from backend.retrieval.bm25 import BM25Index, load_chunks

THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
UNSAFE_COST = 5
FALSE_REFUSAL_COST = 1
UNANSWERABLE_PATH = config.DATA_DIR / "unanswerable_questions.jsonl"
OUTPUT_PATH = config.DATA_DIR / "threshold_calibration.json"


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


def _top_reranker_score(
    model, tokenizer, question, chunks_by_id, bm25, device
) -> float:
    bm25_results = bm25.search(question, k=config.TOP_K)
    candidates = [
        {"chunk_id": cid, "text": chunks_by_id[cid]["text"]}
        for cid, _ in bm25_results
        if cid in chunks_by_id
    ]
    if not candidates:
        return 0.0
    scores = _score_candidates(model, tokenizer, question, candidates, device)
    return max(scores)


def calibrate() -> dict:
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
    if not UNANSWERABLE_PATH.exists():
        raise SystemExit(f"{UNANSWERABLE_PATH} not found.")

    test_rows = _load_jsonl(config.TEST_PATH)
    unanswerable_rows = _load_jsonl(UNANSWERABLE_PATH)
    chunks = load_chunks()
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    bm25 = _load_bm25(chunks)

    device = _device()
    tokenizer = AutoTokenizer.from_pretrained(config.RERANKER_MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(config.RERANKER_MODEL_DIR)
    model.to(device)
    model.eval()

    print(
        f"[calibrate] answerable={len(test_rows)} "
        f"unanswerable={len(unanswerable_rows)} device={device}"
    )

    answerable_scores: list[float] = []
    for r in test_rows:
        s = _top_reranker_score(
            model, tokenizer, r["question"], chunks_by_id, bm25, device
        )
        answerable_scores.append(s)

    unanswerable_scores: list[float] = []
    for r in unanswerable_rows:
        s = _top_reranker_score(
            model, tokenizer, r["question"], chunks_by_id, bm25, device
        )
        unanswerable_scores.append(s)

    n_ans = len(answerable_scores)
    n_unans = len(unanswerable_scores)

    threshold_results: list[dict] = []
    for t in THRESHOLDS:
        false_refusals = sum(1 for s in answerable_scores if s < t)
        unsafe_answers = sum(1 for s in unanswerable_scores if s >= t)
        false_refusal_rate = false_refusals / max(n_ans, 1)
        unsafe_answer_rate = unsafe_answers / max(n_unans, 1)
        cost = UNSAFE_COST * unsafe_answers + FALSE_REFUSAL_COST * false_refusals
        threshold_results.append(
            {
                "threshold": t,
                "false_refusal_rate": false_refusal_rate,
                "unsafe_answer_rate": unsafe_answer_rate,
                "false_refusals": false_refusals,
                "unsafe_answers": unsafe_answers,
                "cost": cost,
            }
        )

    optimal = min(threshold_results, key=lambda r: (r["cost"], -r["threshold"]))

    output = {
        "thresholds": threshold_results,
        "optimal_threshold": optimal["threshold"],
        "optimal": optimal,
        "n_answerable": n_ans,
        "n_unanswerable": n_unans,
        "answerable_top_scores": answerable_scores,
        "unanswerable_top_scores": unanswerable_scores,
        "cost_weights": {"unsafe": UNSAFE_COST, "false_refusal": FALSE_REFUSAL_COST},
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    results = calibrate()
    print("\n[calibrate] threshold sweep:")
    print(
        f"{'threshold':>10} {'false_refusal_rate':>20} "
        f"{'unsafe_answer_rate':>20} {'cost':>8}"
    )
    for r in results["thresholds"]:
        marker = (
            "  <-- optimal"
            if r["threshold"] == results["optimal_threshold"]
            else ""
        )
        print(
            f"{r['threshold']:>10.2f} {r['false_refusal_rate']:>20.4f} "
            f"{r['unsafe_answer_rate']:>20.4f} {r['cost']:>8}{marker}"
        )
    print(
        f"\n[calibrate] optimal threshold = {results['optimal_threshold']} "
        f"(cost={results['optimal']['cost']})"
    )
    print(f"[calibrate] saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
