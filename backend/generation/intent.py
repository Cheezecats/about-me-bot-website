from __future__ import annotations

import re
from dataclasses import dataclass

from backend.generation import policies


@dataclass(frozen=True)
class QueryIntent:
    """Small, explainable intent representation used before retrieval."""

    kind: str
    topic: str | None = None
    entities: tuple[str, ...] = ()
    followup: bool = False
    comparison: bool = False
    before_year: int | None = None
    ordinal: int | None = None


_TOPIC_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:camera|cameras|lens|lenses|photograph|photography|photographs?|photo|photos?|picture|pictures?|videograph|video|gear)\b", "photography"),
    (r"\b(?:favorite|favourite)\s+(?:game|games)\b|\b(?:game|games|gaming|apex|valorant|csgo|cyberpunk)\b", "games"),
    (r"\b(?:food|eat|eating|ramen|ice cream)\b", "food"),
    (r"\b(?:season|winter|summer|spring|autumn|fall)\b", "season"),
    (r"\b(?:music|song|songs|track|tracks|artist|band|bands|listen|singer|playlist)\b", "music"),
    (r"\b(?:hobbies|hobby|interests?|instrument|guitar|drawing|pc building|pastime|free time|fun)\b", "hobbies"),
    (r"\b(?:sports?|skiing|hockey|tennis|floorball|soccer)\b", "sports"),
    (r"\b(?:travel(?:ed|led|ing)?|visited|visit|been|went|countries|country|trip|abroad)\b", "travel"),
    (r"\b(?:essay|essays|paper|papers|research|writing|written|wrote|write|ia|internal assessment)\b", "writing"),
    (r"\b(?:award|awards|achievement|achievements|accomplishment|accomplishments|won|victory|medal)\b", "achievements"),
    (r"\b(?:school|study|studies|education|curriculum|grade|ibdp|igcse|subjects?)\b", "education"),
    (r"\b(?:project|projects|built|created|developed|skills?|programming|code|coding|language|python|typescript|solidity)\b", "projects"),
    (r"\b(?:anime|movie|film|book|series)\b", "favorites"),
)

_FOLLOWUP_PATTERN = re.compile(
    r"\b(?:what about|tell me more|when did (?:he|james) start|where was that|which one|the first|the second|the third|continue|go on|keep going|is that all)\b"
    r"|\b(?:anything else|what else|anything more|something else|anything to add|and|also|his|her|their|that|this|those|these)\b",
    re.IGNORECASE,
)


def is_additional_detail_request(question: str) -> bool:
    """Detect natural-language requests for more items in the current topic."""

    lower = question.strip().lower().strip(" ,;?!")
    if re.search(r"\b(?:anything|what|something)\s+(?:else|more)\b", lower):
        return True
    if re.search(
        r"\b(?:tell me more|more about|other|additional|another|besides|anything to add|what about the rest|is that all|go on|keep going)\b",
        lower,
    ):
        return True
    if re.search(r"\b(?:more|some more)\s+(?:hobbies?|interests?|activities?|things)\b", lower):
        return True
    if lower in {"and", "also", "more", "other", "another", "continue", "go on", "keep going", "is that all"} or re.search(
        r"\b(?:and|also|more|continue)\s*$", lower
    ):
        return True
    if re.match(r"^(?:and|also)\b", lower) and not re.search(
        r"\b(?:what|which|list|name)\b.*\b(?:hobbies?|interests?)\b", lower
    ):
        return True
    return False


def _ordinal(question: str) -> int | None:
    match = re.search(r"\b(first|second|third|1st|2nd|3rd)\b", question, re.IGNORECASE)
    if not match:
        return None
    return {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}[match.group(1).lower()]


def _topic(question: str) -> str | None:
    for pattern, topic in _TOPIC_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return topic
    return None


def detect_intent(question: str) -> QueryIntent:
    question = question.strip()
    lower = question.lower()

    if policies.is_sensitive_request(question):
        return QueryIntent("privacy")
    if policies.is_small_talk(question):
        return QueryIntent("small_talk")
    if policies.is_product_meta_request(question):
        return QueryIntent("product_meta")
    if policies.is_ambiguous_request(question):
        return QueryIntent("ambiguous")
    if policies.is_non_profile_request(question):
        return QueryIntent("unsupported")

    if re.search(r"\bfavorite\s+(?:programming\s+)?language\b", lower):
        return QueryIntent("unsupported", topic="projects")

    if re.search(r"\b(?:dislike|dislikes|disliked|least favorite|hate|hates)\b", lower):
        topic = "preferences"
    elif re.search(r"\b(?:train|training|competed|competition)\b", lower) and re.search(r"\bhockey\b", lower):
        topic = "travel"
    else:
        topic = _topic(question)
    comparison = bool(
        re.search(r"\b(?:compare|versus|vs\.?|which|before|earliest|first|latest|most|different)\b", lower)
    )
    before_match = re.search(r"\bbefore\s+(20\d{2})\b", lower)
    followup = bool(_FOLLOWUP_PATTERN.search(question))
    additional_hobby_request = bool(
        is_additional_detail_request(question)
        and re.search(r"\b(?:fun|hobbies?|interests?|pastimes?)\b", lower)
    )
    entities = tuple(
        entity
        for entity in (
            "camera" if re.search(r"\bcameras?\b", lower) else None,
            "lens" if re.search(r"\blens(?:es)?\b", lower) else None,
            "competitive" if "competitive" in lower else None,
            "non-competitive" if "non-competitive" in lower or "noncompetitive" in lower else None,
            "ai" if re.search(r"\b(?:ai|llm|machine learning|computer vision)\b", lower) else None,
            "programming_languages" if re.search(r"\bprogramming\s+languages?\b|\blanguages?\s+does", lower) else None,
            "visited" if re.search(r"\b(?:visit|visited|travel(?:ed|led)?)\b", lower) else None,
            "training" if re.search(r"\b(?:train|training|competed|competition)\b", lower) else None,
            "song" if re.search(r"\b(?:song|songs|track|tracks)\b", lower) else None,
            "band" if re.search(r"\bbands?\b", lower) else None,
            "artist" if re.search(r"\bartists?\b", lower) else None,
            "dislikes" if re.search(r"\b(?:dislike|dislikes|disliked|least favorite|hate|hates)\b", lower) else None,
            "additional_hobbies" if additional_hobby_request else None,
            "gaming_reason" if re.search(r"\b(?:why|because|relax|relaxation|unwind|decompress|social|connect|friends|peers|matter)\b", lower) and re.search(r"\b(?:game|games|gaming|apex|valorant|csgo)\b", lower) else None,
            "coding_origin" if re.search(r"\b(?:learn|learned|self-taught|taught|started)\b", lower) and re.search(r"\b(?:code|coding|programming|python|software)\b", lower) else None,
            "apex_rank" if re.search(r"\bapex\s+legends\b", lower) and re.search(r"\brank\b", lower) else None,
        )
        if entity
    )

    return QueryIntent(
        kind="profile" if topic else "unknown",
        topic=topic,
        entities=entities,
        followup=followup,
        comparison=comparison,
        before_year=int(before_match.group(1)) if before_match else None,
        ordinal=_ordinal(question),
    )
