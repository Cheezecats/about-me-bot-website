from __future__ import annotations

import json
import math
import random

from backend import config
from backend.reranker.inference import Reranker, RerankerUnavailable
from backend.retrieval.bm25 import BM25Index, load_chunks, load_or_build

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


def _load_bm25(chunks: list[dict]) -> BM25Index:
    return load_or_build()


def _top_reranker_score(
    reranker: Reranker, question, chunks_by_id, bm25
) -> float:
    bm25_results = bm25.search(question, k=config.TOP_K)
    candidates = [
        {"chunk_id": cid, "text": chunks_by_id[cid]["text"]}
        for cid, _ in bm25_results
        if cid in chunks_by_id
    ]
    if not candidates:
        return 0.0
    ranked = reranker.rerank(question, candidates)
    return float(ranked[0]["score"]) if ranked else 0.0


def _validation_questions(rows: list[dict]) -> list[str]:
    """Extract one answerable question per validation group from flat pair rows."""

    questions = {row["question"] for row in rows if row.get("label") == 1}
    if not questions:
        raise ValueError("No positive validation rows found for threshold calibration.")
    return sorted(questions)


def _split_unanswerable_questions(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep a small, deterministic unanswerable holdout set for final reporting."""

    if len(rows) < 2:
        raise ValueError("Need at least two unanswerable questions for calibration and holdout.")
    shuffled = list(rows)
    random.Random(config.RANDOM_SEED).shuffle(shuffled)
    n_calibration = round(len(shuffled) * config.UNANSWERABLE_CALIBRATION_SPLIT)
    n_calibration = min(max(n_calibration, 1), len(shuffled) - 1)
    return shuffled[:n_calibration], shuffled[n_calibration:]


def _candidate_thresholds(answerable_scores: list[float], unanswerable_scores: list[float]) -> list[float]:
    """Return exact score boundaries for every distinct answer/refuse outcome."""

    values = sorted(set(answerable_scores + unanswerable_scores))
    thresholds = [0.0]
    thresholds.extend(math.nextafter(value, math.inf) for value in values)
    return sorted(set(thresholds))


def build_threshold_results(
    answerable_scores: list[float], unanswerable_scores: list[float]
) -> list[dict]:
    results: list[dict] = []
    for threshold in _candidate_thresholds(answerable_scores, unanswerable_scores):
        false_refusals = sum(score < threshold for score in answerable_scores)
        unsafe_answers = sum(score >= threshold for score in unanswerable_scores)
        false_refusal_rate = false_refusals / max(len(answerable_scores), 1)
        unsafe_answer_rate = unsafe_answers / max(len(unanswerable_scores), 1)
        results.append(
            {
                "threshold": threshold,
                "false_refusal_rate": false_refusal_rate,
                "unsafe_answer_rate": unsafe_answer_rate,
                "false_refusals": false_refusals,
                "unsafe_answers": unsafe_answers,
                "cost": UNSAFE_COST * unsafe_answers + FALSE_REFUSAL_COST * false_refusals,
            }
        )
    return results


def select_deployment_threshold(threshold_results: list[dict]) -> tuple[dict | None, str]:
    """Select only a threshold that meets both stated operating constraints."""

    eligible = [
        result
        for result in threshold_results
        if meets_operating_constraints(result)
    ]
    if not eligible:
        return None, "no_threshold_meets_operating_constraints"
    selected = min(
        eligible,
        key=lambda result: (
            result["cost"],
            result["false_refusal_rate"],
            result["unsafe_answer_rate"],
            result["threshold"],
        ),
    )
    return selected, "validated_on_validation_split"


def meets_operating_constraints(metrics: dict | None) -> bool:
    return bool(
        metrics is not None
        and metrics["false_refusal_rate"] <= config.MAX_FALSE_REFUSAL_RATE
        and metrics["unsafe_answer_rate"] <= config.MAX_UNSAFE_ANSWER_RATE
    )


def _metrics_at_threshold(
    threshold: float, answerable_scores: list[float], unanswerable_scores: list[float]
) -> dict:
    false_refusals = sum(score < threshold for score in answerable_scores)
    unsafe_answers = sum(score >= threshold for score in unanswerable_scores)
    return {
        "threshold": threshold,
        "false_refusals": false_refusals,
        "unsafe_answers": unsafe_answers,
        "false_refusal_rate": false_refusals / max(len(answerable_scores), 1),
        "unsafe_answer_rate": unsafe_answers / max(len(unanswerable_scores), 1),
        "n_answerable": len(answerable_scores),
        "n_unanswerable": len(unanswerable_scores),
    }


def calibrate() -> dict:
    if not config.VAL_PATH.exists() or not config.TEST_PATH.exists():
        raise SystemExit(
            "data/val.jsonl or data/test.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )
    if not UNANSWERABLE_PATH.exists():
        raise SystemExit(f"{UNANSWERABLE_PATH} not found.")

    validation_questions = _validation_questions(_load_jsonl(config.VAL_PATH))
    test_questions = [row["question"] for row in _load_jsonl(config.TEST_PATH)]
    unanswerable_calibration, unanswerable_holdout = _split_unanswerable_questions(
        _load_jsonl(UNANSWERABLE_PATH)
    )
    chunks = load_chunks()
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    bm25 = _load_bm25(chunks)

    try:
        reranker = Reranker()
    except RerankerUnavailable as exc:
        raise SystemExit(str(exc)) from exc

    print(
        f"[calibrate] validation_answerable={len(validation_questions)} "
        f"calibration_unanswerable={len(unanswerable_calibration)} "
        f"holdout_answerable={len(test_questions)} "
        f"holdout_unanswerable={len(unanswerable_holdout)} backend={reranker.backend} "
        f"device={reranker.device}"
    )

    validation_answerable_scores = [
        _top_reranker_score(reranker, question, chunks_by_id, bm25)
        for question in validation_questions
    ]
    calibration_unanswerable_scores = [
        _top_reranker_score(reranker, row["question"], chunks_by_id, bm25)
        for row in unanswerable_calibration
    ]
    threshold_results = build_threshold_results(
        validation_answerable_scores, calibration_unanswerable_scores
    )
    selected, selection_status = select_deployment_threshold(threshold_results)

    holdout_answerable_scores = [
        _top_reranker_score(reranker, question, chunks_by_id, bm25)
        for question in test_questions
    ]
    holdout_unanswerable_scores = [
        _top_reranker_score(reranker, row["question"], chunks_by_id, bm25)
        for row in unanswerable_holdout
    ]
    holdout = (
        _metrics_at_threshold(
            selected["threshold"], holdout_answerable_scores, holdout_unanswerable_scores
        )
        if selected is not None
        else None
    )
    holdout_passes = meets_operating_constraints(holdout)
    if selected is not None and not holdout_passes:
        selection_status = "holdout_did_not_meet_operating_constraints"

    output = {
        "selection_status": selection_status,
        "reranker_backend": reranker.backend,
        "recommended_for_deployment": bool(selected is not None and holdout_passes),
        "recommended_threshold": selected["threshold"] if holdout_passes else None,
        "selected_validation_metrics": selected,
        "operating_constraints": {
            "max_false_refusal_rate": config.MAX_FALSE_REFUSAL_RATE,
            "max_unsafe_answer_rate": config.MAX_UNSAFE_ANSWER_RATE,
        },
        "cost_weights": {"unsafe": UNSAFE_COST, "false_refusal": FALSE_REFUSAL_COST},
        "validation_thresholds": threshold_results,
        "holdout_metrics": holdout,
        "n_validation_answerable": len(validation_answerable_scores),
        "n_calibration_unanswerable": len(calibration_unanswerable_scores),
        "n_holdout_answerable": len(holdout_answerable_scores),
        "n_holdout_unanswerable": len(holdout_unanswerable_scores),
        "validation_answerable_top_scores": validation_answerable_scores,
        "calibration_unanswerable_top_scores": calibration_unanswerable_scores,
        "holdout_answerable_top_scores": holdout_answerable_scores,
        "holdout_unanswerable_top_scores": holdout_unanswerable_scores,
    }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    results = calibrate()
    print("\n[calibrate] validation threshold sweep:")
    print(
        f"{'threshold':>10} {'false_refusal_rate':>20} "
        f"{'unsafe_answer_rate':>20} {'cost':>8}"
    )
    selected = results["selected_validation_metrics"]
    for result in results["validation_thresholds"]:
        marker = "  <-- selected" if selected == result else ""
        print(
            f"{result['threshold']:>10.4f} {result['false_refusal_rate']:>20.4f} "
            f"{result['unsafe_answer_rate']:>20.4f} {result['cost']:>8}{marker}"
        )
    print(f"\n[calibrate] selection_status = {results['selection_status']}")
    if not results["recommended_for_deployment"]:
        print("[calibrate] no threshold is recommended for deployment")
    else:
        print(f"[calibrate] recommended threshold = {selected['threshold']:.4f}")
        print(f"[calibrate] independent holdout = {results['holdout_metrics']}")
    print(f"[calibrate] saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
