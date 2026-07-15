from __future__ import annotations

import re
import signal
import time

import httpx

from backend import config
from backend.generation.compound import merge_compound_results, split_compound_question
from backend.generation.formatting import (
    build_context,
    build_sources,
    check_grounding,
    numbers_in,
)
from backend.generation.intent import QueryIntent, detect_intent
from backend.generation.policies import (
    SMALL_TALK_RESPONSE,
    apply_pii_filter,
    is_ambiguous_request,
    is_non_profile_request,
    is_product_meta_request,
    is_sensitive_request,
    is_small_talk,
    normalize_refusal,
    product_meta_answer,
)
from backend.generation.query_plan import build_query_plan
from backend.generation.structured_answers import (
    STRUCTURED_SUMMARY_TITLES,
    extractive_answer,
    format_structured_answer,
    is_structured_summary,
)

# These aliases keep the existing test and internal-call surface stable while
# the implementation lives in focused modules.
_check_grounding = check_grounding
_numbers_in = numbers_in
_build_sources = build_sources
_extractive_answer = extractive_answer
_is_structured_summary = is_structured_summary

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CONTEXT_TOP_N = 3
OLLAMA_TIMEOUT = 30.0


def _result(
    status: str,
    answer: str,
    *,
    confidence: float = 0.0,
    sources: list[dict] | None = None,
    fallback_used: bool = False,
    total_ms: float = 0.0,
    generation_ms: float = 0.0,
    reason: str = "",
) -> dict:
    return {
        "status": status,
        "answer": answer,
        "confidence": confidence,
        "sources": sources or [],
        "fallback_used": fallback_used,
        "reason": reason,
        "pipeline": {
            "retrieval_ms": 0,
            "rerank_ms": 0,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        },
    }


def _build_messages(
    question: str, context_chunks: list[dict], history: list[dict] | None = None
) -> list[dict]:
    context = build_context(context_chunks)
    user = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the context above. "
        "Use one to three concise sentences, or a short bullet list when the question asks for multiple items. "
        "Answer only the topic asked about; ignore unrelated context. "
        "Use normal spelling even if the user made a typo. "
        "Never mention the context or say 'the provided context'. "
        "Do not infer ages from years, favorites from general usage, or relationships between separate facts. "
        "If the context does not directly answer the question, respond exactly: "
        f"\"{config.REFUSAL_MESSAGE}\""
    )
    messages = [{"role": "system", "content": config.GROUNDING_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user})
    return messages


def _sanitize_context_for_external(chunks: list[dict]) -> list[dict]:
    patterns = [*config.PII_PATTERNS, *config.PRIVATE_KB_PATTERNS]
    return [
        chunk
        for chunk in chunks
        if not any(re.search(pattern, chunk.get("text", ""), re.IGNORECASE) for pattern in patterns)
    ]


def _timeout_handler(signum, frame):
    raise TimeoutError("Ollama generation timed out")


def _call_ollama(messages: list[dict], timeout: float = OLLAMA_TIMEOUT) -> str:
    import ollama

    def _invoke() -> str:
        response = ollama.chat(
            model=config.LLM_MODEL,
            messages=messages,
            options={"temperature": 0.0, "top_p": 0.9},
        )
        return response["message"]["content"].strip()

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
    response = httpx.post(
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
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def generate_answer(
    question: str, context_chunks: list[dict], history: list[dict] | None = None
) -> tuple[str, bool]:
    if not context_chunks:
        return config.REFUSAL_MESSAGE, False
    fallback_text = context_chunks[0].get("text", config.REFUSAL_MESSAGE)
    try:
        messages = _build_messages(question, context_chunks, history)
        if config.LLM_BACKEND == "ollama":
            return _call_ollama(messages), False
        if config.LLM_BACKEND == "groq":
            safe_chunks = _sanitize_context_for_external(context_chunks)
            if not safe_chunks:
                return config.REFUSAL_MESSAGE, False
            return _call_groq(_build_messages(question, safe_chunks, history)), False
        raise SystemExit(f"Unknown LLM_BACKEND: {config.LLM_BACKEND}")
    except SystemExit:
        raise
    except Exception:
        return fallback_text, True


def _is_compound_request(question: str) -> bool:
    return len(split_compound_question(question)) > 1


def _select_context_chunks(
    question: str, reranked_chunks: list[dict], intent: QueryIntent | None = None
) -> list[dict]:
    if len(reranked_chunks) <= 1:
        return reranked_chunks
    if intent is not None and "additional_hobbies" in intent.entities:
        return reranked_chunks[:4]
    if _is_structured_summary(reranked_chunks[0]):
        return reranked_chunks[:1]
    top_score = float(reranked_chunks[0].get("score", 0.0))
    second_score = float(reranked_chunks[1].get("score", 0.0))
    if top_score - second_score >= 1.5:
        return reranked_chunks[:1]
    return reranked_chunks[:CONTEXT_TOP_N]


def answer_or_refuse(
    question: str,
    reranked_chunks: list[dict],
    history: list[dict] | None = None,
    enforce_confidence_threshold: bool = True,
    intent_question: str | None = None,
) -> dict:
    started = time.perf_counter()
    semantic_question = intent_question.strip() if intent_question else question
    if intent_question is None:
        # Keep direct callers (CLI/tests) compatible with the API path by
        # applying the same deterministic normalization when no plan was
        # supplied by the request orchestrator.
        semantic_question = build_query_plan(question).normalized_question
    intent: QueryIntent = detect_intent(question)
    if intent_question or semantic_question != question:
        resolved_intent = detect_intent(semantic_question)
        if resolved_intent.kind != "unknown":
            # The planner's normalized query is the authoritative semantic
            # interpretation, while policy checks below still inspect the raw
            # user message for privacy and unsupported requests.
            intent = resolved_intent

    if intent.kind == "small_talk" or is_small_talk(question):
        return _result("answered", SMALL_TALK_RESPONSE, confidence=1.0, reason="small_talk")

    if intent.kind == "product_meta" or is_product_meta_request(question):
        return _result("answered", product_meta_answer(question), confidence=1.0, reason="product_meta")

    if intent.kind == "unknown" and intent.followup:
        return _result("clarification", config.CLARIFICATION_MESSAGE, reason="ambiguous_followup")

    if intent.kind in {"privacy", "ambiguous", "unsupported"} or is_ambiguous_request(question) or is_non_profile_request(question):
        reason = {
            "privacy": "privacy",
            "unsupported": "unsupported",
            "ambiguous": "ambiguous_request",
        }.get(intent.kind, "unsupported")
        return _result("refused", config.REFUSAL_MESSAGE, reason=reason)

    if not reranked_chunks or is_sensitive_request(question):
        return _result(
            "refused",
            config.REFUSAL_MESSAGE,
            reason="privacy" if is_sensitive_request(question) else "no_retrieval",
        )

    top_score = float(reranked_chunks[0].get("score", 0.0))
    top_chunks = _select_context_chunks(semantic_question, reranked_chunks, intent)
    sources = _build_sources(top_chunks)
    if enforce_confidence_threshold and top_score < config.CONFIDENCE_THRESHOLD:
        return _result(
            "refused",
            config.REFUSAL_MESSAGE,
            confidence=top_score,
            sources=sources,
            reason="low_retrieval_confidence",
        )

    structured = format_structured_answer(semantic_question, top_chunks, intent)
    if structured is not None and not _is_compound_request(question):
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return _result(
            "answered",
            structured,
            confidence=top_score,
            sources=sources,
            total_ms=elapsed,
            reason="structured_fact",
        )

    generation_started = time.perf_counter()
    answer_text, fallback_used = generate_answer(question, top_chunks, history)
    generation_ms = round((time.perf_counter() - generation_started) * 1000, 1)
    filtered = normalize_refusal(apply_pii_filter(answer_text))

    if top_chunks and _is_structured_summary(top_chunks[0]) and (
        filtered == config.REFUSAL_MESSAGE
        or re.search(r"\bfull\s+name\s+project\b", filtered, flags=re.IGNORECASE)
        or not _check_grounding(filtered, top_chunks)
    ):
        structured_fallback = format_structured_answer(semantic_question, top_chunks, intent)
        if structured_fallback is not None:
            filtered = structured_fallback

    if filtered == config.REFUSAL_MESSAGE:
        status = "refused"
        reason = "model_refusal"
    elif fallback_used:
        status = "unavailable"
        filtered = config.UNAVAILABLE_MESSAGE
        reason = "llm_unavailable"
    elif not _check_grounding(filtered, top_chunks):
        status = "refused"
        filtered = config.REFUSAL_MESSAGE
        reason = "grounding_failed"
    else:
        status = "answered"
        reason = "generated"

    elapsed = round((time.perf_counter() - started) * 1000, 1)
    return _result(
        status,
        filtered,
        confidence=top_score,
        sources=sources,
        fallback_used=fallback_used,
        total_ms=elapsed,
        generation_ms=generation_ms,
        reason=reason,
    )
