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
    "movis": "movies",
    "anme": "anime",
    "bookes": "books",
}

# Keep fuzzy correction limited to James's known public topics. This catches
# minor new typos without autocorrecting names or inventing facts.
_DOMAIN_WORDS = (
    "achievements", "achievement", "photography", "hobbies", "hobby",
    "favorite", "favorites", "favourite", "instrument", "camera", "cameras", "lenses",
    "lens", "music", "songs", "song", "bands", "band", "artists", "artist",
    "projects", "project", "essays", "essay", "sports", "sport", "travel",
    "traveled", "visited", "rank", "games", "game", "gaming", "videogame", "videogames",
    "photographed", "photographing", "photos", "pictures", "guitar", "education",
    "school", "season", "food", "dislikes", "dislike", "anime", "movie",
    "movies", "film", "films", "book", "books", "series", "place", "subject",
    "subjects", "ide", "editor", "editors", "vscode", "zed", "workbuddy", "trae",
    "biography", "personality", "contact", "youtube", "github", "bilibili", "videos",
    "graduation", "graduate", "drawing", "published", "publication", "aspirations",
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

    if re.search(r"\b(?:ide|ides|editor|editors|vscode|vs\s+code|zed|workbuddy|trae)\b", lower):
        return "What IDE/editor tools does James use?"

    if re.search(r"\b(?:tell\s+me\s+about\s+james|who\s+is\s+james|james'?s?\s+bio|about\s+james)\b", lower):
        return "Who is James?"
    if re.search(r"\b(?:what\s+is\s+james\s+like|james'?s?\s+personality|what\s+kind\s+of\s+person)\b", lower):
        return "What is James like as a person?"
    if re.search(r"\b(?:how\s+can\s+i\s+contact|contact\s+james|james'?s?\s+contact)\b", lower):
        return "How can I contact James?"
    if re.search(r"\b(?:youtube\s+(?:channel|account)|his\s+youtube|james'?s?\s+youtube)\b", lower):
        return "What is James's YouTube channel?"
    if re.search(r"\b(?:github\s+(?:profile|account)|his\s+github|james'?s?\s+github)\b", lower):
        return "What is James's GitHub profile?"
    if re.search(r"\b(?:what\s+videos?|which\s+videos?|videos?\s+(?:has|did)|tell\s+me\s+about.*videos?)\b", lower):
        return "What videos has James made?"
    if re.search(r"\b(?:when\s+(?:will|does).*graduate|graduation|graduate)\b", lower):
        return "When will James graduate?"
    if re.search(r"\b(?:what\s+subjects?.*(?:study|take)|(?:hl|higher\s+level)\s+subjects?)\b", lower):
        return "What Higher Level subjects does James study?"
    if re.search(
        r"\b(?:what\s+does\s+james\s+want\s+to\s+study|future\s+(?:academic\s+)?(?:plans?|interests?)|academic\s+interests?|aspirations?)\b",
        lower,
    ):
        return "What are James's future academic interests?"
    if re.search(r"\b(?:does\s+(?:james|he)\s+draw|digital\s+drawing|drawing\s+hobby)\b", lower):
        return "Does James do digital drawing?"
    if re.search(r"\b(?:what\s+(?:did|has)\s+(?:james|he)\s+publish(?:ed)?|publication|curieux)\b", lower):
        return "What has James published?"
    if re.search(r"\banime\b", lower) and re.search(r"\b(?:influence|influenced|impact|style)\b", lower):
        return "How has anime influenced James's visual style?"
    if re.search(r"\b(?:best|strongest|better)\s+sport\b", lower):
        return "What sport is James best at?"

    if re.search(
        r"\b(?:where|what\s+(?:places?|locations?)|which\s+(?:places?|countries?))\b", lower
    ) and re.search(
        r"\b(?:photograph(?:y|ed|s)?|photo(?:s)?|picture(?:s)?|filmed|shot)\b", lower
    ):
        return "Where has James photographed?"

    destination_rules = (
        (r"\b(?:italy|tuscany)\b", "What did James do in Italy?"),
        (r"\b(?:greece|athens)\b", "What did James do in Greece?"),
        (r"\b(?:japan|hokkaido)\b", "What did James do in Japan?"),
        (r"\bxinjiang\b", "What did James do in Xinjiang?"),
        (r"\brussia\b", "What did James do in Russia?"),
        (r"\b(?:united\s+states|los\s+angeles)\b", "What did James do in the United States?"),
    )
    if (
        not re.search(r"\b(?:film|filmed|filming|video|videos)\b", lower)
        and (re.search(r"\b(?:what about|tell me about|what did|what happened|where|how)\b", lower) or len(lower.split()) <= 3)
    ):
        for pattern, canonical in destination_rules:
            if re.search(pattern, lower):
                return canonical

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

    if re.search(r"\b(?:what\s+did|what\s+has|did|has)\s+(?:james|he)\s+film(?:ed|ing)?\b", lower):
        return cleaned

    # Bare topic chips and informal questions should converge on the same
    # curated summary. Otherwise "anime" can retrieve a secondary paragraph
    # and bypass the deterministic formatter used for the favorite fact.
    favorite_topic_rules = (
        (r"\b(?:game|games|gaming|videogame|videogames)\b", "What are James's favorite games?"),
        (r"\banime\b", "What is James's favorite anime?"),
        (r"\b(?:movie|movies|film|films)\b", "What is James's favorite movie?"),
        (r"\b(?:book|books|book\s+series|series)\b", "What is James's favorite book series?"),
        (r"\b(?:favorite|favourite)\s+place\b", "What is James's favorite place?"),
        (r"\b(?:favorite|favourite)\s+(?:school\s+)?subjects?\b", "What is James's favorite school subject?"),
    )
    for pattern, canonical in favorite_topic_rules:
        if re.fullmatch(rf"(?:james'?s?\s+)?(?:favorite|favourite)?\s*{pattern}", lower) or (
            re.search(pattern, lower)
            and re.search(r"\b(?:like|likes|favorite|favourite|enjoy|enjoys|love|loves|watch|watched|read|reads|reading)\b", lower)
            and not re.search(r"\b(?:influence|influenced|impact|style)\b", lower)
            and not (
                re.search(r"\b(?:game|games|gaming|videogame|videogames)\b", lower)
                and re.search(r"\b(?:why|because|relax|relaxation|unwind|decompress|social|connect|friends|peers|matter)\b", lower)
            )
        ):
            return canonical

    if re.search(r"\b(?:anything|what)\s+(?:else|more)\b", lower) and re.search(r"\b(?:fun|hobby|hobbies|interest|interests?)\b", lower):
        return "What else does James do for fun?"

    if re.search(r"\b(?:what\s+(?:did|has)|tell\s+me\s+what)\s+(?:james|he)\s+(?:write|wrote|written)\b", lower):
        return "What essays has James written?"

    if re.search(r"\b(?:what\s+does|what\s+do)\s+(?:james|he)\b", lower) and re.search(
        r"\b(?:for\s+fun|in\s+(?:his|their)\s+free\s+time)\b", lower
    ):
        return "What are James's hobbies?"

    if re.search(r"\blens(?:es)?\b", lower) and re.search(r"\bcameras?\b", lower) and re.search(
        r"\b(?:what|which|his|james|use|uses|does)\b", lower
    ):
        return "What camera and lenses does James use?"

    if re.search(r"\blens(?:es)?\b", lower) and re.search(
        r"\b(?:what|which|his|james|use|uses|does)\b", lower
    ):
        return "What lenses does James use?"

    if not re.search(r"\blens(?:es)?\b", lower) and re.search(r"\bcameras?\b", lower) and re.search(
        r"\b(?:what|which|his|james|use|uses|does)\b", lower
    ):
        return "What camera gear does James use?"

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
    topic_queries = {
        "bio": "James Sui 17 student Shanghai technologist",
        "personality": "personality nice outgoing self learner engineering values",
        "contact": "contact YouTube GitHub Bilibili website public email",
        "videos": "videos filmed video vlog Nikon Z8",
    }
    retrieval_query = topic_queries.get(intent.topic or "", retrieval_query)
    if "graduation" in intent.entities:
        retrieval_query = "expected graduation 2027 education"
    elif "higher_level_subjects" in intent.entities:
        retrieval_query = "Education Higher Level Computer Science Mathematics Physics"
    elif "aspirations" in intent.entities:
        retrieval_query = "future aspirations engineering semiconductors aerospace quantum computing"
    elif "drawing" in intent.entities:
        retrieval_query = "digital drawing creative outlet hobbies"
    elif "publication" in intent.entities:
        retrieval_query = "Curieux Academic Journal publication research paper"
    elif "anime_influence" in intent.entities:
        retrieval_query = "Anime influence visual styles Japanese fashion"
    elif "photographed_places" in intent.entities:
        retrieval_query = "photographed Japan Hokkaido Italy Tuscany Greece Athens"
    destination_queries = {
        "travel_italy": "Italy Tuscany sunset photography",
        "travel_greece": "Greece Athens Ionian Sea photography video",
        "travel_japan": "Japan Hokkaido winter photography video 21 day Tokyo Kyoto",
        "travel_xinjiang": "Xinjiang video Nikon Z8 iPhone 13 Pro Bilibili",
        "travel_russia": "Russia ice hockey international matches",
        "travel_united_states": "United States Los Angeles ice hockey training",
    }
    for entity, query in destination_queries.items():
        if entity in intent.entities and intent.topic == "travel":
            retrieval_query = query
            break
    if "lens" in intent.entities:
        retrieval_query = "photography camera lenses NIKKOR 24-120mm 85mm"
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
