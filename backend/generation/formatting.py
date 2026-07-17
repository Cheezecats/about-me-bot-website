from __future__ import annotations

import re

from backend import config

MIN_GROUNDING_OVERLAP = 2
_NON_LATIN_RUN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]{2,}")
_GROUNDING_STOPWORDS = frozenset(
    "about answer also and are as asked based been but context detail does for from have he her his "
    "include includes information is it james not of on or profile provided that the their there this to was "
    "what with you your".split()
)
NUMBER_WORDS = {
    **{
        word: value
        for value, word in enumerate(
            "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
        )
    },
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


def numbers_in(text: str) -> set[int]:
    numbers = {int(value) for value in re.findall(r"\b\d+\b", text)}
    words = re.findall(r"[a-z]+", text.lower())
    numbers.update(NUMBER_WORDS[word] for word in words if word in NUMBER_WORDS)
    return numbers


def build_context(chunks: list[dict]) -> str:
    return "\n".join(f"[{index}] {chunk['text']}" for index, chunk in enumerate(chunks, 1))


def _grounding_terms(text: str) -> set[str]:
    """Extract factual terms from Latin and CJK/Japanese text."""

    latin = {
        word
        for word in re.findall(r"[a-z]{4,}", text.lower())
        if word not in _GROUNDING_STOPWORDS
    }
    return latin | {term.lower() for term in _NON_LATIN_RUN.findall(text)}


def check_grounding(answer: str, context_chunks: list[dict]) -> bool:
    if answer == config.REFUSAL_MESSAGE:
        return True
    context_text = " ".join(c.get("text", "") for c in context_chunks)
    if not numbers_in(answer).issubset(numbers_in(context_text)):
        return False
    answer_words = _grounding_terms(answer)
    context_words = _grounding_terms(context_text)
    if not answer_words:
        return True
    overlap = len(answer_words & context_words)
    # Structured answers are handled separately. For model output, require a
    # meaningful share of its factual vocabulary to come from the retrieved
    # evidence, not merely two generic words.
    minimum_overlap = 1 if any(_NON_LATIN_RUN.fullmatch(term) for term in answer_words) else MIN_GROUNDING_OVERLAP
    return overlap >= minimum_overlap and overlap / len(answer_words) >= 0.55


def build_sources(chunks: list[dict]) -> list[dict]:
    sources = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "")
        category = metadata.get("category", "unknown")
        sources.append(
            {
                "chunk_id": str(chunk.get("chunk_id", "")),
                "text": chunk.get("text", ""),
                "category": category,
                "title": title,
                "label": title or category.replace("_", " ").title(),
                "source": metadata.get("source", "knowledge base"),
            }
        )
    return sources
