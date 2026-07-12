from __future__ import annotations

import re
import signal
import time

import httpx

from backend import config

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
    r"\bmedical\s+history\b",
    r"\bparents?\b",
    r"\bfamily(?:'s|)\s+income\b",
    r"\bdorm\s+room\b",
]


def is_sensitive_request(question: str) -> bool:
    return any(
        re.search(pattern, question, flags=re.IGNORECASE)
        for pattern in SENSITIVE_REQUEST_PATTERNS
    )


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
        "Answer the question using only the context above."
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
        resp = ollama.chat(model=config.LLM_MODEL, messages=messages)
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


def answer_or_refuse(
    question: str,
    reranked_chunks: list[dict],
    history: list[dict] | None = None,
    enforce_confidence_threshold: bool = True,
) -> dict:
    t_start = time.perf_counter()

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
    top_n = reranked_chunks[:CONTEXT_TOP_N]
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

    t_gen_start = time.perf_counter()
    answer_text, fallback_used = generate_answer(question, top_n, history)
    generation_ms = round((time.perf_counter() - t_gen_start) * 1000, 1)

    filtered = apply_pii_filter(answer_text)

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
