from __future__ import annotations

import re
from dataclasses import dataclass

from backend.generation.intent import QueryIntent, detect_intent


@dataclass(frozen=True)
class QueryPlan:
    """Validated, explainable interpretation passed into retrieval."""

    original_question: str
    normalized_question: str
    retrieval_query: str
    intent: QueryIntent
    confidence: float
    rewritten: bool
    method: str = "deterministic"


_WHITESPACE = re.compile(r"\s+")
_TYPO_REPLACEMENTS = {
    "favoriate": "favorite",
    "favrite": "favorite",
    "favouite": "favorite",
    "photographt": "photography",
    "photografy": "photography",
    "hobbys": "hobbies",
    "ank": "rank",
    "acheivements": "achievements",
    "acheivement": "achievement",
    "achievments": "achievements",
    "musci": "music",
    "insturment": "instrument",
    "instruement": "instrument",
}


def _clean(text: str) -> str:
    text = _WHITESPACE.sub(" ", text.strip())
    for wrong, right in _TYPO_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    return text.strip(" ,;?")


def _canonical_question(question: str) -> str:
    cleaned = _clean(question)
    lower = cleaned.lower()

    # Minimal deterministic CJK routing for the public topics the widget
    # already supports. This avoids adding a translation dependency while
    # still allowing common Chinese-only questions to reach the same curated
    # answer paths as their English equivalents.
    if re.search(r"(?:最喜欢|喜欢).*(?:游戏|电竞)", lower):
        return "What are James's favorite games?"
    if re.search(r"(?:最喜欢|喜欢).*(?:音乐|歌曲|歌曲|歌)", lower):
        return "What songs does James like?"
    if re.search(r"(?:会弹|弹什么|演奏|乐器)", lower):
        return "Does James play an instrument?"
    if re.search(r"(?:爱好|兴趣)", lower):
        return "What are James's hobbies?"

    if re.search(r"\bapex\s+legends\b", lower) and re.search(r"\bseason\b", lower) and re.search(
        r"\b(?:reach|reached|reach(?:ed)?|it)\b", lower
    ):
        return "What season did James reach it in Apex Legends?"

    if re.search(r"\bapex\s+legends\b", lower) and re.search(r"\brank\b", lower):
        return "What is James's highest rank in Apex Legends?"

    if (
        re.search(r"\b(?:songs?|tracks?)\b", lower)
        or (
            re.search(r"\bmusic\b", lower)
            and re.search(r"\b(?:like|likes|liked|enjoy|enjoys)\b", lower)
        )
    ) and re.search(
        r"\b(?:like|likes|liked|enjoy|enjoys|favorite|favourite)\b", lower
    ):
        return "What songs does James like?"

    if re.search(r"\bbands?\b", lower) and not re.search(r"\bartists?\b", lower) and re.search(
        r"\b(?:like|likes|liked|enjoy|enjoys|favorite|favourite)\b", lower
    ):
        return "What are James's favorite bands?"

    if re.search(r"\bartists?\b", lower) and not re.search(r"\bbands?\b", lower) and re.search(
        r"\b(?:like|likes|liked|enjoy|enjoys|favorite|favourite)\b", lower
    ):
        return "What is James's favorite artist?"

    if re.search(r"\b(?:bands?|artists?)\b", lower) and re.search(
        r"\b(?:like|likes|liked|enjoy|enjoys|favorite|favourite)\b", lower
    ):
        return "What are James's favorite bands and artists?"

    if re.search(r"\b(?:dislike|dislikes|disliked|least favorite|hate|hates)\b", lower) or re.search(
        r"\b(?:do|does)\s+not\s+like\b|\bdon't\s+like\b|\bdoesn't\s+like\b", lower
    ):
        return "What has James explicitly said he dislikes?"

    if re.fullmatch(r"(?:james'?s?\s+)?(?:hobbies|interests?)", lower):
        return "What are James's hobbies?"

    return cleaned


def build_query_plan(question: str) -> QueryPlan:
    original = question.strip()
    normalized = _canonical_question(original)
    intent = detect_intent(normalized)

    # The Apex rank entity is intentionally explicit because "rank" is a
    # fact-level entity rather than a broad topic like games or hobbies.
    if re.search(r"\bapex\s+legends\b", normalized, re.IGNORECASE) and re.search(
        r"\brank\b", normalized, re.IGNORECASE
    ):
        intent = QueryIntent(
            kind="profile",
            topic="games",
            entities=tuple(dict.fromkeys((*intent.entities, "apex_rank"))),
            comparison=intent.comparison,
            ordinal=intent.ordinal,
            before_year=intent.before_year,
            followup=intent.followup,
        )

    rewritten = normalized != original
    confidence = 0.96 if rewritten else (0.82 if intent.kind != "unknown" else 0.20)
    return QueryPlan(
        original_question=original,
        normalized_question=normalized,
        retrieval_query=normalized,
        intent=intent,
        confidence=confidence,
        rewritten=rewritten,
    )
