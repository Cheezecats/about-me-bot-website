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
    # “One of his interests” is an indefinite expression, not a claimed count.
    words = re.findall(r"[a-z]+", re.sub(r"\bone of\b", "of", text.lower()))
    numbers.update(NUMBER_WORDS[word] for word in words if word in NUMBER_WORDS)
    return numbers


def build_context(chunks: list[dict]) -> str:
    return "\n".join(f"[{index}] {chunk['text']}" for index, chunk in enumerate(chunks, 1))


def attribute_profile_quote(answer: str, chunks: list[dict]) -> str:
    """Attribute a verbatim first-person quote instead of impersonating James."""
    quote = answer.strip().strip('"“”')
    if re.match(r"^(?:I\b|My\b)", quote) and any(quote in c.get("text", "") for c in chunks):
        return f'James says: “{quote}”'
    return answer


def _grounding_terms(text: str) -> set[str]:
    """Extract factual terms from Latin and CJK/Japanese text."""

    latin = {
        word
        for word in re.findall(r"[a-z]{4,}", text.lower())
        if word not in _GROUNDING_STOPWORDS
    }
    return latin | {term.lower() for term in _NON_LATIN_RUN.findall(text)}


def check_grounding(answer: str, context_chunks: list[dict]) -> bool:
    if not answer.strip() or re.search(r"\bflappy\s*bird\b", answer, re.IGNORECASE):
        return False
    if answer == config.REFUSAL_MESSAGE:
        return True
    context_text = " ".join(c.get("text", "") for c in context_chunks)
    if not numbers_in(answer).issubset(numbers_in(context_text)):
        return False
    answer_words = _grounding_terms(answer)
    context_words = _grounding_terms(context_text)
    if not answer_words:
        return False
    overlap = len(answer_words & context_words)
    # Structured answers are handled separately. For model output, require a
    # meaningful share of its factual vocabulary to come from the retrieved
    # evidence, not merely two generic words.
    minimum_overlap = 1 if any(_NON_LATIN_RUN.fullmatch(term) for term in answer_words) else MIN_GROUNDING_OVERLAP
    if overlap < minimum_overlap or overlap / len(answer_words) < 0.55:
        return False
    # An accurate first sentence must not hide an unrelated second claim.
    # Keep decimal points and abbreviations inside sentences intact.
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z\u3040-\u9fff])|\n+", answer):
        terms = _grounding_terms(sentence)
        if terms and len(terms & context_words) / len(terms) < 0.55:
            return False
    return True


def check_contract_relevance(answer: str, contract, context_chunks: list[dict]) -> bool:
    """Require generated text to address the contract, not only cite evidence."""

    if not answer.strip() or answer == config.REFUSAL_MESSAGE:
        return True
    relation = getattr(contract, "relation", "unresolved")
    object_type = getattr(contract, "object_type", "unresolved")
    lower = answer.lower()
    context = " ".join(chunk.get("text", "") for chunk in context_chunks).lower()
    aliases = {
        "camera": ("camera", "nikon", "dji", "iphone"),
        "lens": ("lens", "nikkor"),
        "team": ("real madrid",),
        "position": ("defender", "forward"),
        "song": ("君の神様になりたい", "こはならむ"),
        "artist": ("deco*27", "hatsune miku"),
        "band": ("yorushika", "hitorie"),
        "project": ("project", "website", "tuner", "platform", "grapher", "vocabulary", "evaluator", "classifier", "uniswap", "robotics"),
        "school_subject": ("computer science", "mathematics", "physics"),
        "place": ("japan", "greece", "italy", "xinjiang", "tuscany", "athens", "hokkaido"),
        "paper": ("paper", "attention pooling", "knn", "mlp", "method", "architecture"),
        "method": ("self-taught", "independently", "tutorial", "method", "attention pooling", "architecture"),
    }
    required = aliases.get(object_type)
    if required and not any(term in lower for term in required if term in context or term in {"camera", "lens", "defender", "forward", "project", "paper", "method"}):
        return False
    if relation == "supports" and object_type == "team":
        return "real madrid" in lower
    if relation == "playing_position" and object_type == "position":
        return any(term in lower for term in ("defender", "forward"))
    if relation == "photographed_in" and object_type == "place":
        return any(term in lower for term in ("japan", "greece", "italy", "xinjiang", "tuscany", "athens", "hokkaido"))
    if relation == "created" and object_type == "project" and getattr(contract, "constraints", {}).get("technology") == "python":
        return "python" in lower or any(term in lower for term in aliases["project"] if term in context)
    # Explanatory relations need a single cited sentence that actually carries
    # the requested relationship.  Whole-chunk lexical overlap is insufficient:
    # it allowed a model to turn a nearby biographical sentence (for example,
    # an AI-writing contest) into the cause of a separate documented activity.
    relation_cues = {
        "reason": (
            "because", "since", "purpose", "reason", "for ", "helps", "enjoy", "interest", "motivat",
            "appeal", "aim", "result", "best part", "challeng", "reward", "hardest", "difficult", "struggl",
        ),
        "result": ("result", "lead", "outcome", "therefore", "so "),
        "method": ("using", "through", "via", "self-taught", "tutorial", "method", "approach", "architecture"),
        "uses": ("uses", "using", "use ", "for ", "through", "via"),
    }
    cues = relation_cues.get(relation)
    if cues:
        answer_terms = _grounding_terms(answer)
        if not answer_terms:
            return False
        # A bare restatement such as “computer hardware” is not an explanation
        # of why that topic matters.  Longer source-grounded outcome language
        # remains valid even when it does not use an explicit “because” clause.
        if relation == "reason" and len(answer_terms) < 3 and not any(cue in lower for cue in cues):
            return False
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
            sentence_lower = sentence.lower()
            sentence_terms = _grounding_terms(sentence)
            overlap = len(answer_terms & sentence_terms)
            if (
                any(cue in sentence_lower for cue in cues)
                and overlap >= 1
                and overlap / len(answer_terms) >= 0.55
            ):
                return True
        return False
    return True


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
