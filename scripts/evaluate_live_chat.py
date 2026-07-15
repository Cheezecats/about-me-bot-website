from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CASES = ROOT / "data" / "live_evaluation_questions.jsonl"
DEFAULT_OUTPUT = ROOT / "data" / "eval_results.json"


def load_cases(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def evaluate(
    endpoint: str,
    cases: list[dict],
    *,
    repeats: int = 1,
    timeout: float = 45.0,
) -> dict:
    results: list[dict] = []
    latencies: list[float] = []
    with httpx.Client(timeout=timeout) as client:
        for case_index, case in enumerate(cases):
            for repeat in range(repeats):
                started = time.perf_counter()
                try:
                    response = client.post(
                        endpoint,
                        json={
                            "question": case["question"],
                            "session_id": f"live-eval-{case_index}-{repeat}",
                        },
                    )
                    latency_ms = round((time.perf_counter() - started) * 1000, 1)
                    latencies.append(latency_ms)
                    payload = response.json()
                    answer = str(payload.get("answer", ""))
                    status_ok = payload.get("status") == case["expected_status"]
                    terms_ok = all(term.lower() in answer.lower() for term in case.get("terms", []))
                    results.append(
                        {
                            "question": case["question"],
                            "status_code": response.status_code,
                            "status": payload.get("status"),
                            "expected_status": case["expected_status"],
                            "terms": case.get("terms", []),
                            "passed": response.status_code == 200 and status_ok and terms_ok,
                            "latency_ms": latency_ms,
                            "reason": payload.get("reason", ""),
                            "answer": answer,
                        }
                    )
                except Exception as exc:
                    latency_ms = round((time.perf_counter() - started) * 1000, 1)
                    latencies.append(latency_ms)
                    results.append(
                        {
                            "question": case["question"],
                            "status_code": None,
                            "status": "unavailable",
                            "expected_status": case["expected_status"],
                            "terms": case.get("terms", []),
                            "passed": False,
                            "latency_ms": latency_ms,
                            "reason": "request_error",
                            "error": str(exc),
                        }
                    )

    passed = sum(1 for result in results if result["passed"])
    false_refusals = sum(
        1
        for result in results
        if result["expected_status"] == "answered" and result["status"] in {"refused", "clarification"}
    )
    unsafe_answers = sum(
        1
        for result in results
        if result["expected_status"] == "refused" and result["status"] == "answered"
    )
    return {
        "endpoint": endpoint,
        "cases": len(cases),
        "repeats": repeats,
        "requests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "accuracy": round(passed / len(results), 4) if results else 0.0,
        "false_refusals": false_refusals,
        "unexpected_answers": unsafe_answers,
        "latency_ms": {
            "median": round(statistics.median(latencies), 1) if latencies else 0.0,
            "p95_approx": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1) if latencies else 0.0,
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the live JamChat API through HTTP.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/chat")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = evaluate(args.endpoint, load_cases(args.cases), repeats=max(1, args.repeats), timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
