from __future__ import annotations

import argparse

from backend import config
from backend.generation.answer import answer_or_refuse
from backend.reranker.inference import Reranker, RerankerUnavailable
from backend.retrieval.bm25 import BM25Index, build_and_save, load_chunks, retrieve


def _load_index() -> BM25Index:
    if config.BM25_INDEX_PATH.exists():
        return BM25Index.load(config.BM25_INDEX_PATH)
    return build_and_save()


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
    candidates = retrieve(question, index, chunks, k=config.TOP_K)

    try:
        reranker = Reranker()
    except (SystemExit, RerankerUnavailable) as e:
        raise SystemExit(
            f"{e} Train it first with `python -m backend.training.train_reranker`."
        )

    reranked = reranker.rerank(question, candidates)
    result = answer_or_refuse(question, reranked)

    print(f"Status:     {result['status']}")
    print(f"Answer:     {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Fallback:   {result['fallback_used']}")
    for src in result.get("sources", []):
        print(f"Source:     [{src['category']}] {src['text'][:100]}")


if __name__ == "__main__":
    main()
