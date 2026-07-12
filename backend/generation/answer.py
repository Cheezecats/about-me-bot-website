from __future__ import annotations

import re
import signal
import time

import httpx

from backend import config
from backend.retrieval.tokenizer import tokenize, tokenize_query

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CONTEXT_TOP_N = 3
OLLAMA_TIMEOUT = 30.0
MIN_GROUNDING_OVERLAP = 2
SENSITIVE_REQUEST_PATTERNS = [
    r"\bpassword\b",
    r"\b(?:phone|telephone)\s+number\b",
    r"\bhome\s+address\b",
    r"\bexact\s+(?:address|location)\b",
    r"\b(?:bank|account)\s+number\b",
    r"\bsocial\s+security\b",
    r"\b(?:qq|wechat)\b",
    r"\bpassport\s+number\b",
    r"\bip\s+address\b",
    r"\bdate\s+of\s+birth\b",
    r"\bprivate\s+messages?\b",
    r"\bprivate\s+information\b",
    r"\bignore\s+(?:your|the)\s+rules?\b",
    r"\bmedical\s+history\b",
    r"\bparents?\b",
    r"\bfamily(?:'s|)\s+income\b",
    r"\bdorm\s+room\b",
]

SMALL_TALK_PATTERNS = [
    r"^(?:hi|hello|hey|hiya|yo|good morning|good afternoon|good evening|hey there|how are you|how's it going)[!.?,\s]*$",
]
SMALL_TALK_RESPONSE = (
    "Hi! Ask me about James's photography, videos, essays, hobbies, sports, or projects."
)
AMBIGUOUS_REQUEST_PATTERNS = [r"^(?:family|relatives?)[!.?,\s]*$"]
NON_PROFILE_REQUEST_PATTERNS = [
    r"^(?:nice|good|fun|cool|best)\s+games?[!.?,\s]*$",
    r"\b(?:recommend|recommendation|recommendations|suggest|suggestions)\b",
    r"\bfavorite\s+(?:programming\s+)?language\b",
]
REFUSAL_VARIANTS = [
    r"provided context does not contain",
    r"context does not contain",
    r"not enough information",
    r"i do not have that information",
    r"i don't have that information",
]
STRUCTURED_SUMMARY_TITLES = {
    "Achievements & Awards",
    "Education",
    "Electric guitar",
    "Favorite games",
    "Favorite food",
    "Favorite music",
    "Hobbies & Interests",
    "Photography and videography",
    "Projects & Skills",
    "Sports",
    "Travel",
    "Writing & Essays",
    "Favorite season",
}
NUMBER_WORDS = {
    **{word: value for value, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )},
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}
_COMPOUND_SPLIT_PATTERN = re.compile(
    r"\s+(?:and|also|as well as)\s+(?="
    r"(?:what|where|who|when|why|how|does|is|are|has|have|did|can|could|which|tell|favorite|favourite|his|her|their|my|your)\b)",
    flags=re.IGNORECASE,
)


def is_sensitive_request(question: str) -> bool:
    return any(
        re.search(pattern, question, flags=re.IGNORECASE)
        for pattern in SENSITIVE_REQUEST_PATTERNS
    )


def is_small_talk(question: str) -> bool:
    return any(
        re.search(pattern, question.strip(), flags=re.IGNORECASE)
        for pattern in SMALL_TALK_PATTERNS
    )


def _matches_any(question: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, question.strip(), flags=re.IGNORECASE) for pattern in patterns)


def is_ambiguous_request(question: str) -> bool:
    return _matches_any(question, AMBIGUOUS_REQUEST_PATTERNS)


def is_non_profile_request(question: str) -> bool:
    return _matches_any(question, NON_PROFILE_REQUEST_PATTERNS)


def is_product_meta_request(question: str) -> bool:
    return _matches_any(
        question,
        [
            r"\bwhat\s+model\b",
            r"\bwho\s+are\s+you\b",
            r"\bwhat\s+can\s+you\s+answer\b",
            r"\bwhat\s+are\s+you\b",
        ],
    )


def split_compound_question(question: str) -> list[str]:
    """Split only when a conjunction introduces a new question clause."""

    parts = [part.strip(" ,;?") for part in _COMPOUND_SPLIT_PATTERN.split(question.strip())]
    return [part for part in parts if part] or [question.strip()]


def _compound_label(question: str, index: int) -> str:
    lower = question.lower()
    labels = (
        (r"\bpassword\b|\bprivate\b|\baddress\b|\bphone\b", "Privacy"),
        (r"\b(?:favorite|favourite)\s+games?\b|\bgames?\b", "Games"),
        (r"\bprogramming\s+language|\blanguage\b", "Programming language"),
        (r"\bprojects?\b|\bskills?\b", "Projects and skills"),
        (r"\bfood\b|\bramen\b", "Favorite food"),
        (r"\bcamera|lens(?:es)?\b", "Photography and gear"),
        (r"\bseason\b", "Favorite season"),
        (r"\bschool\b|\bstudy\b|\beducation\b", "Education"),
        (r"\bsports?\b|\bskiing\b|\bhockey\b|\btennis\b|\bfloorball\b", "Sports"),
        (r"\btravel(?:ed|led|ing)?\b|\bvisited\b", "Travel"),
        (r"\bessays?|\bpapers?|\bresearch\b", "Writing and essays"),
    )
    for pattern, label in labels:
        if re.search(pattern, lower):
            return label
    return f"Part {index}"


def merge_compound_results(questions: list[str], results: list[dict]) -> dict:
    """Merge independently answered clauses into one readable response."""

    sections = []
    sources: list[dict] = []
    seen_sources: set[str] = set()
    statuses = []
    confidences = []
    fallback_used = False
    total_ms = 0.0

    for index, (question, result) in enumerate(zip(questions, results), start=1):
        result_status = result.get("status", "answered")
        display_answer = result["answer"]
        if result_status == "unavailable":
            display_answer = "I couldn't answer this part right now."
        sections.append(f"{_compound_label(question, index)}:\n{display_answer}")
        statuses.append(result_status)
        confidences.append(float(result.get("confidence", 0.0)))
        fallback_used = fallback_used or bool(result.get("fallback_used", False))
        total_ms += float(result.get("pipeline", {}).get("total_ms", 0.0))
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
        "pipeline": {
            "retrieval_ms": 0,
            "rerank_ms": 0,
            "generation_ms": 0,
            "total_ms": round(total_ms, 1),
        },
    }


def _product_meta_answer(question: str) -> str:
    if re.search(r"\bwhat\s+model\b", question, flags=re.IGNORECASE):
        return f"I'm Ask James, powered locally by {config.LLM_MODEL}. I answer questions about James using this project's knowledge base."
    return "I'm Ask James, a local chatbot for questions about James's photography, videos, essays, hobbies, sports, and projects."


def _numbers_in(text: str) -> set[int]:
    numbers = {int(value) for value in re.findall(r"\b\d+\b", text)}
    words = re.findall(r"[a-z]+", text.lower())
    numbers.update(NUMBER_WORDS[word] for word in words if word in NUMBER_WORDS)
    return numbers


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] {c['text']}")
    return "\n".join(parts)


def _build_messages(
    question: str, context_chunks: list[dict], history: list[dict] | None = None
) -> list[dict]:
    context = _build_context(context_chunks)
    user = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the context above. "
        "Write a concise answer in one to three sentences. "
        "Answer only the topic asked about; ignore unrelated context. "
        "Use normal spelling even if the user made a typo. "
        "Never mention the context or say 'the provided context'. "
        "If the context does not directly answer the question, respond exactly: "
        f"\"{config.REFUSAL_MESSAGE}\""
    )
    messages = [{"role": "system", "content": config.GROUNDING_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user})
    return messages


def _build_sources(chunks: list[dict]) -> list[dict]:
    sources = []
    for c in chunks:
        sources.append(
            {
                "chunk_id": str(c.get("chunk_id", "")),
                "text": c.get("text", ""),
                "category": c.get("metadata", {}).get("category", "unknown"),
            }
        )
    return sources


def _sanitize_context_for_external(chunks: list[dict]) -> list[dict]:
    patterns = [*config.PII_PATTERNS, *config.PRIVATE_KB_PATTERNS]
    return [
        c
        for c in chunks
        if not any(re.search(p, c.get("text", ""), re.IGNORECASE) for p in patterns)
    ]


def _timeout_handler(signum, frame):
    raise TimeoutError("Ollama generation timed out")


def _call_ollama(messages: list[dict], timeout: float = OLLAMA_TIMEOUT) -> str:
    import ollama

    def _invoke() -> str:
        resp = ollama.chat(
            model=config.LLM_MODEL,
            messages=messages,
            options={"temperature": 0.0, "top_p": 0.9},
        )
        return resp["message"]["content"].strip()

    try:
        previous = signal.signal(signal.SIGALRM, _timeout_handler)
    except (ValueError, OSError):
        return _invoke()

    signal.setitimer(signal.ITIMER_REAL, float(timeout))
    try:
        return _invoke()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _call_groq(messages: list[dict]) -> str:
    resp = httpx.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _check_grounding(answer: str, context_chunks: list[dict]) -> bool:
    if answer == config.REFUSAL_MESSAGE:
        return True
    context_text = " ".join(c.get("text", "") for c in context_chunks)
    if not _numbers_in(answer).issubset(_numbers_in(context_text)):
        return False
    answer_words = set(re.findall(r"[a-z]{3,}", answer.lower()))
    context_words: set[str] = set()
    for c in context_chunks:
        context_words.update(re.findall(r"[a-z]{3,}", c.get("text", "").lower()))
    overlap = answer_words & context_words
    return len(overlap) >= MIN_GROUNDING_OVERLAP


def generate_answer(
    question: str, context_chunks: list[dict], history: list[dict] | None = None
) -> tuple[str, bool]:
    if not context_chunks:
        return config.REFUSAL_MESSAGE, False
    fallback_text = context_chunks[0].get("text", config.REFUSAL_MESSAGE)
    try:
        if config.LLM_BACKEND == "ollama":
            messages = _build_messages(question, context_chunks, history)
            return _call_ollama(messages), False
        if config.LLM_BACKEND == "groq":
            safe_chunks = _sanitize_context_for_external(context_chunks)
            messages = _build_messages(question, safe_chunks, history)
            return _call_groq(messages), False
        raise SystemExit(f"Unknown LLM_BACKEND: {config.LLM_BACKEND}")
    except SystemExit:
        raise
    except Exception:
        return fallback_text, True


def apply_pii_filter(text: str) -> str:
    for pattern in config.PII_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return config.REFUSAL_MESSAGE
    return text


def normalize_refusal(text: str) -> str:
    if _matches_any(text, REFUSAL_VARIANTS):
        return config.REFUSAL_MESSAGE
    return text


def _is_structured_summary(chunk: dict) -> bool:
    return chunk.get("metadata", {}).get("title", "") in STRUCTURED_SUMMARY_TITLES


def _extractive_answer(chunk: dict) -> str:
    title = chunk.get("metadata", {}).get("title", "")
    text = chunk.get("text", "").strip()
    for prefix in (f"## {title} ", f"# {title} "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if title == "Favorite games":
        return f"James's favorite games: {text}"
    return text


def _is_compound_request(question: str) -> bool:
    return bool(re.search(r"\b(?:and|also|as well as)\b", question, flags=re.IGNORECASE))


def _format_structured_answer(question: str, chunks: list[dict]) -> str | None:
    if not chunks or _is_compound_request(question):
        return None
    chunk = chunks[0]
    title = chunk.get("metadata", {}).get("title", "")
    if title not in STRUCTURED_SUMMARY_TITLES:
        return None

    body = _extractive_answer(chunk)
    if title == "Favorite games":
        match = re.search(
            r"Competitive top 3:\s*(.*?)(?:\.\s*|$)Non-competitive top 3:\s*(.*?)(?:\.$|$)",
            body,
            flags=re.IGNORECASE,
        )
        if match:
            return (
                "James's favorite games are:\n\n"
                f"- Competitive: {match.group(1).strip()}\n"
                f"- Non-competitive: {match.group(2).strip()}"
            )
    if title == "Electric guitar":
        return "Yes—James plays electric guitar. He started in 2025, is self-taught, and focuses on J-pop and rock."
    if title == "Photography and videography":
        if re.search(r"\blens(?:es)?\b", question, flags=re.IGNORECASE):
            return "James uses a NIKKOR 24-120mm F4 S lens and a NIKKOR 85mm F1.8 lens."
        if re.search(r"\bcamera(?:s)?\b", question, flags=re.IGNORECASE):
            return "James's primary camera is a Nikon Z8. He also uses a DJI Action 4 and an iPhone 13 Pro."
    if title == "Travel":
        return (
            "James has travelled to Japan, Greece, Italy, and Xinjiang. "
            "He also travelled or trained abroad in the United States and Russia through ice hockey."
        )
    if title == "Favorite season":
        return "James's favorite season is winter, especially with snow."
    if title == "Favorite food":
        return "James's favorite food is Japanese ramen. He also enjoys ice cream and apple-flavored foods."
    if title == "Achievements & Awards":
        return (
            "James's achievements include:\n\n"
            "- 2025 Physics Bowl National Silver Award\n"
            "- National top 5% placement in China Thinks Big\n"
            "- Research publication in the Curieux Academic Journal\n"
            "- Participation in the Lumiere Research Program\n"
            "- Participation in the 丘成桐中学科学奖 (Qiu Competition)"
        )
    if title == "Sports" and re.search(
        r"\b(?:which|what)\b.*\b(?:first|earliest)\b|\bstarted\s+first\b",
        question,
        flags=re.IGNORECASE,
    ):
        years = {
            sport: int(year)
            for sport, year in re.findall(
                r"\b(skiing|ice hockey|tennis|floorball)\s+in\s+(20\d{2})\b",
                body,
                flags=re.IGNORECASE,
            )
        }
        if years:
            first_sport, first_year = min(years.items(), key=lambda item: item[1])
            return f"James started {first_sport} first, in {first_year}."
    return body


def _select_context_chunks(question: str, reranked_chunks: list[dict]) -> list[dict]:
    if len(reranked_chunks) <= 1:
        return reranked_chunks
    if _is_structured_summary(reranked_chunks[0]):
        return reranked_chunks[:1]
    top_score = float(reranked_chunks[0].get("score", 0.0))
    second_score = float(reranked_chunks[1].get("score", 0.0))
    # A clear BM25 winner is usually a focused fact. Sending only that chunk
    # prevents a small model from blending in nearby but unrelated facts.
    if top_score - second_score >= 1.5:
        return reranked_chunks[:1]
    return reranked_chunks[:CONTEXT_TOP_N]


def answer_or_refuse(
    question: str,
    reranked_chunks: list[dict],
    history: list[dict] | None = None,
    enforce_confidence_threshold: bool = True,
) -> dict:
    t_start = time.perf_counter()

    if is_small_talk(question):
        return {
            "status": "answered",
            "answer": SMALL_TALK_RESPONSE,
            "confidence": 1.0,
            "sources": [],
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }

    if is_product_meta_request(question):
        return {
            "status": "answered",
            "answer": _product_meta_answer(question),
            "confidence": 1.0,
            "sources": [],
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }

    if is_ambiguous_request(question) or is_non_profile_request(question):
        return {
            "status": "refused",
            "answer": config.REFUSAL_MESSAGE,
            "confidence": 0.0,
            "sources": [],
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }

    if not reranked_chunks:
        return {
            "status": "refused",
            "answer": config.REFUSAL_MESSAGE,
            "confidence": 0.0,
            "sources": [],
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }
    if is_sensitive_request(question):
        return {
            "status": "refused",
            "answer": config.REFUSAL_MESSAGE,
            "confidence": 0.0,
            "sources": [],
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }
    top_score = float(reranked_chunks[0].get("score", 0.0))
    top_n = _select_context_chunks(question, reranked_chunks)
    sources = _build_sources(top_n)
    if enforce_confidence_threshold and top_score < config.CONFIDENCE_THRESHOLD:
        return {
            "status": "refused",
            "answer": config.REFUSAL_MESSAGE,
            "confidence": top_score,
            "sources": sources,
            "fallback_used": False,
            "pipeline": {"retrieval_ms": 0, "rerank_ms": 0, "generation_ms": 0, "total_ms": 0},
        }

    structured_answer = _format_structured_answer(question, top_n)
    if structured_answer is not None:
        total_ms = round((time.perf_counter() - t_start) * 1000, 1)
        return {
            "status": "answered",
            "answer": structured_answer,
            "confidence": top_score,
            "sources": sources,
            "fallback_used": False,
            "pipeline": {
                "retrieval_ms": 0,
                "rerank_ms": 0,
                "generation_ms": 0,
                "total_ms": total_ms,
            },
        }

    t_gen_start = time.perf_counter()
    answer_text, fallback_used = generate_answer(question, top_n, history)
    generation_ms = round((time.perf_counter() - t_gen_start) * 1000, 1)

    filtered = normalize_refusal(apply_pii_filter(answer_text))

    if top_n and _is_structured_summary(top_n[0]) and (
        filtered == config.REFUSAL_MESSAGE
        or re.search(r"\bfull\s+name\s+project\b", filtered, flags=re.IGNORECASE)
        or not _check_grounding(filtered, top_n)
    ):
        # A structured KB summary is safer than a refusal or an invented
        # interpretation when the small model is uncertain.
        filtered = _extractive_answer(top_n[0])

    if filtered == config.REFUSAL_MESSAGE:
        status = "refused"
    elif fallback_used:
        status = "unavailable"
    elif not _check_grounding(filtered, top_n):
        status = "refused"
        filtered = config.REFUSAL_MESSAGE
    else:
        status = "answered"

    total_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return {
        "status": status,
        "answer": filtered,
        "confidence": top_score,
        "sources": sources,
        "fallback_used": fallback_used,
        "pipeline": {
            "retrieval_ms": 0,
            "rerank_ms": 0,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        },
    }
