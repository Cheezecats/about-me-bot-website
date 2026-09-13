from __future__ import annotations

import argparse

from backend import config
from backend.generation.answer import answer_or_refuse
from backend.generation.query_plan import build_query_plan
from backend.retrieval.bm25 import BM25Index, load_or_build, load_chunks, retrieve


def _load_index() -> BM25Index:
    return load_or_build()


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{config.CHATBOT_NAME} - standalone CLI chatbot")
    parser.add_argument("question", nargs="?", help="Question to send to JamChat")
    args = parser.parse_args()

    question = args.question
    if not question or not question.strip():
        raise SystemExit("Please provide a non-empty question.")
    question = question.strip()
    if len(question) > config.MAX_QUERY_LEN:
        raise SystemExit(f"Question too long (max {config.MAX_QUERY_LEN} characters).")

    index = _load_index()
    chunks = load_chunks()
    plan = build_query_plan(question)
    query = plan.retrieval_query if config.QUERY_PLANNER_ENABLED else question
    candidates = retrieve(query, index, chunks, k=config.TOP_K)
    reranker = None
    if config.RERANKER_ENABLED:
        try:
            from backend.reranker.inference import Reranker
            reranker = Reranker()
        except (ImportError, RuntimeError, OSError):
            print("Optional reranker unavailable; using BM25.")
    reranked = reranker.rerank(query, candidates) if reranker else candidates
    result = answer_or_refuse(
        question, reranked, enforce_confidence_threshold=reranker is not None,
        intent_question=plan.normalized_question, intent_override=plan.intent,
        generation_timeout=config.CHAT_TIMEOUT_SECONDS,
    )

    print(f"Status:     {result['status']}")
    print(f"Answer:     {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Fallback:   {result['fallback_used']}")
    for src in result.get("sources", []):
        print(f"Source:     [{src['category']}] {src['text'][:100]}")


if __name__ == "__main__":
    main()
