from __future__ import annotations

import re

from backend.generation.intent import detect_intent

_COMPOUND_SPLIT_PATTERN = re.compile(
    r"\s+(?:and|also|as well as)\s+(?="
    r"(?:what|where|who|when|why|how|does|is|are|has|have|did|can|could|which|tell|favorite|favourite|his|her|their|my|your)\b)",
    flags=re.IGNORECASE,
)


def split_compound_question(question: str) -> list[str]:
    """Split conjunctions only when they introduce a new question clause."""

    parts = [part.strip(" ,;?") for part in _COMPOUND_SPLIT_PATTERN.split(question.strip())]
    return [part for part in parts if part] or [question.strip()]


def compound_label(question: str, index: int) -> str:
    intent = detect_intent(question)
    labels = {
        "privacy": "Privacy",
        "games": "Games",
        "projects": "Projects and skills",
        "food": "Favorite food",
        "photography": "Photography and gear",
        "season": "Favorite season",
        "education": "Education",
        "sports": "Sports",
        "travel": "Travel",
        "writing": "Writing and essays",
        "achievements": "Achievements",
        "music": "Music",
        "hobbies": "Hobbies",
        "favorites": "Favorites",
    }
    return labels.get(intent.topic or intent.kind, "Additional detail")


def merge_compound_results(questions: list[str], results: list[dict]) -> dict:
    sections: list[str] = []
    sources: list[dict] = []
    seen_sources: set[str] = set()
    statuses: list[str] = []
    confidences: list[float] = []
    fallback_used = False
    total_ms = 0.0

    for index, (question, result) in enumerate(zip(questions, results), start=1):
        result_status = result.get("status", "answered")
        display_answer = result.get("answer", "")
        if result_status == "unavailable":
            display_answer = "I couldn't answer this part right now."
        sections.append(f"{compound_label(question, index)}:\n{display_answer}")
        statuses.append(result_status)
        confidences.append(float(result.get("confidence", 0.0)))
        fallback_used = fallback_used or bool(result.get("fallback_used", False))
        total_ms += float(result.get("pipeline", {}).get("total_ms", 0.0))
        if result_status != "answered":
            continue
        for source in result.get("sources", []):
            chunk_id = str(source.get("chunk_id", ""))
            if chunk_id and chunk_id not in seen_sources:
                seen_sources.add(chunk_id)
                sources.append(source)

    if any(status == "answered" for status in statuses):
        status = "answered"
    elif any(status == "unavailable" for status in statuses):
        status = "unavailable"
    else:
        status = "refused"

    return {
        "status": status,
        "answer": "\n\n".join(sections),
        "confidence": min(confidences, default=0.0),
        "sources": sources,
        "fallback_used": fallback_used,
        "reason": "compound",
        "pipeline": {
            "retrieval_ms": 0,
            "rerank_ms": 0,
            "generation_ms": 0,
            "total_ms": round(total_ms, 1),
        },
    }
