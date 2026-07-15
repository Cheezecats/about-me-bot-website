from __future__ import annotations

import re
from difflib import get_close_matches
from dataclasses import dataclass

from backend.generation.intent import QueryIntent, detect_intent, is_additional_detail_request


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
    "favouriate": "favorite",
    "faverite": "favorite",
    "favorate": "favorite",
    "photografy": "photography",
    "photograhpy": "photography",
    "hobies": "hobbies",
    "hobbie": "hobby",
    "achievment": "achievement",
    "accomplishements": "achievements",
    "lense": "lens",
    "lensis": "lenses",
    "sngs": "songs",
    "musc": "music",
}

# Keep fuzzy correction limited to James's known public topics. This catches
# minor new typos without autocorrecting names or inventing facts.
_DOMAIN_WORDS = (
    "achievements", "achievement", "photography", "hobbies", "hobby",
    "favorite", "favourite", "instrument", "camera", "cameras", "lenses",
    "lens", "music", "songs", "song", "bands", "band", "artists", "artist",
    "projects", "project", "essays", "essay", "sports", "sport", "travel",
    "traveled", "visited", "rank", "games", "game", "guitar", "education",
    "school", "season", "food", "dislikes", "dislike",
)
_NEVER_FUZZY_CORRECT = {"james", "what", "does", "do", "like", "likes", "he", "his"}
_DOMAIN_WORD_SET = frozenset(_DOMAIN_WORDS)


def _clean(text: str) -> str:
    text = _WHITESPACE.sub(" ", text.strip())
    for wrong, right in _TYPO_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Za-z][A-Za-z'-]*\b", _correct_domain_typo, text)
    return text.strip(" ,;?")


def _correct_domain_typo(match: re.Match[str]) -> str:
    token = match.group(0)
    lowered = token.lower()
    if lowered in _DOMAIN_WORD_SET or lowered in _NEVER_FUZZY_CORRECT or len(lowered) < 5:
        return token
    match_result = get_close_matches(lowered, _DOMAIN_WORDS, n=1, cutoff=0.84)
    if not match_result:
        return token
    corrected = match_result[0]
    return corrected if token.islower() else corrected.capitalize()


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

    if re.search(r"\b(?:hobbies?|interests?|pastimes?|free\s+time)\b", lower):
        if is_additional_detail_request(cleaned):
            return "What else does James do for fun?"
        return "What are James's hobbies?"

    if re.search(r"\b(?:anything|what)\s+(?:else|more)\b", lower) and re.search(r"\b(?:fun|hobby|hobbies|interest|interests?)\b", lower):
        return "What else does James do for fun?"

    if re.search(r"\b(?:what\s+(?:did|has)|tell\s+me\s+what)\s+(?:james|he)\s+(?:write|wrote|written)\b", lower):
        return "What essays has James written?"

    if re.search(r"\b(?:what\s+does|what\s+do)\s+(?:james|he)\b", lower) and re.search(
        r"\b(?:for\s+fun|in\s+(?:his|their)\s+free\s+time)\b", lower
    ):
        return "What are James's hobbies?"

    if re.search(r"\b(?:apex(?:\s+legends)?)\b", lower) and re.search(r"\bseason\b", lower) and re.search(
        r"\b(?:reach|reached|reach(?:ed)?|it)\b", lower
    ):
        return "What season did James reach it in Apex Legends?"

    if re.search(r"\b(?:apex(?:\s+legends)?)\b", lower) and re.search(
        r"\b(?:rank|ranked|ranking|how\s+good|highest|peak)\b", lower
    ):
        return "What is James's highest rank in Apex Legends?"

    if re.search(r"\b(?:games?|gaming)\b", lower) and not re.search(
        r"\b(?:why|because|relax|relaxation|unwind|decompress|social|connect|friends|peers|matter)\b", lower
    ) and re.search(
        r"\b(?:play|plays|played|enjoy|enjoys|like|likes|favorite|favourite)\b", lower
    ):
        return "What are James's favorite games?"

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

    retrieval_query = normalized
    if "coding_origin" in intent.entities:
        retrieval_query = "Self-taught Python during middle school programming"
    elif "gaming_reason" in intent.entities:
        retrieval_query = "gaming unwind decompress after school friends peers social connection"
    elif "additional_hobbies" in intent.entities:
        retrieval_query = "cosplay 3D printer founding clubs tactile picture books"

    rewritten = normalized != original or retrieval_query != normalized
    confidence = 0.96 if rewritten else (0.82 if intent.kind != "unknown" else 0.20)
    return QueryPlan(
        original_question=original,
        normalized_question=normalized,
        retrieval_query=retrieval_query,
        intent=intent,
        confidence=confidence,
        rewritten=rewritten,
    )
