from __future__ import annotations

import json
import re
import time
import threading
import logging
from dataclasses import dataclass, replace

import httpx

from backend import config
from backend.generation.compound import merge_compound_results, split_compound_question
from backend.generation.contracts import SemanticContract, unavailable_profile_detail
from backend.generation.evidence import capability_for, eligible_evidence, focused_chunks
from backend.generation.formatting import (
    build_context,
    build_sources,
    check_grounding,
    check_contract_relevance,
    numbers_in,
    attribute_profile_quote,
)
from backend.generation.intent import QueryIntent
from backend.generation.policies import (
    apply_pii_filter,
    is_ambiguous_request,
    is_non_profile_request,
    is_product_meta_request,
    is_sensitive_request,
    is_small_talk,
    normalize_refusal,
    product_meta_answer,
)
from backend.generation.query_plan import _merge_contract_intent, build_query_plan
from backend.generation.structured_answers import (
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
_generation_slots = threading.BoundedSemaphore(config.MAX_LLM_CONCURRENCY)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedDraft:
    """Internal model-output envelope checked before a public answer is returned."""

    answer: str
    answered_relation: str
    evidence_ids: tuple[str, ...]

    def cited_chunks(self, context_chunks: list[dict]) -> list[dict]:
        """Resolve cited IDs in draft order after validation has checked them."""

        by_id = {str(chunk.get("chunk_id", "")): chunk for chunk in context_chunks}
        return [by_id[evidence_id] for evidence_id in self.evidence_ids if evidence_id in by_id]

    def validate(self, contract: SemanticContract | None, context_chunks: list[dict]) -> bool:
        # The model cannot approve its own evidence.
        # Every cited ID and relation must match the reviewed request and current context.
        if contract is None or not self.answer.strip():
            # A blank answer or missing contract cannot be checked safely.
            return False
        # Build the set from the current retrieval result, not from model output.
        available_ids = {str(chunk.get("chunk_id", "")) for chunk in context_chunks}
        # Reject missing or repeated citations before checking the answer text.
        if (
            not self.evidence_ids
            or len(set(self.evidence_ids)) != len(self.evidence_ids)
            or not set(self.evidence_ids).issubset(available_ids)
        ):
            return False
        # Only IDs from the current context can become public source labels.
        # The relation field describes the draft, but it is not proof of correctness.
        # The answer must still be grounded in the cited text and contract.
        if self.answered_relation != contract.relation:
            # A citation is not enough if the draft answers a different question from the one the visitor asked.
            return False
        # Resolve approved IDs into actual passages before checking their content.
        cited_chunks = self.cited_chunks(context_chunks)
        # Separate checks prevent a correct citation from hiding a wrong answer.
        return check_grounding(self.answer, cited_chunks) and check_contract_relevance(
            self.answer, contract, cited_chunks
        )


def _parse_generated_draft(raw: str) -> GeneratedDraft | None:
    """Accept only the compact, schema-shaped draft requested from the model."""

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"answer", "answered_relation", "evidence_ids"}:
        return None
    answer = payload.get("answer")
    relation = payload.get("answered_relation")
    evidence_ids = payload.get("evidence_ids")
    if (
        not isinstance(answer, str)
        or not answer.strip()
        or not isinstance(relation, str)
        or not relation.strip()
        or not isinstance(evidence_ids, list)
        or not all(isinstance(evidence_id, str) and evidence_id.strip() for evidence_id in evidence_ids)
    ):
        return None
    return GeneratedDraft(answer=answer.strip(), answered_relation=relation.strip(), evidence_ids=tuple(evidence_ids))


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
    question: str,
    context_chunks: list[dict],
    history: list[dict] | None = None,
    contract: SemanticContract | None = None,
) -> list[dict]:
    valid_evidence_ids = [str(chunk.get("chunk_id", "")) for chunk in context_chunks]
    context = "\n\n".join(
        f"SOURCE ID: {chunk.get('chunk_id', '')}\nSOURCE TEXT: {chunk.get('text', '')}"
        for chunk in context_chunks
    )
    contract_text = ""
    if contract is not None:
        relation_guidance = {
            "reason": "explain the documented reason or purpose, not merely a related example",
            "result": "state the documented result or outcome directly",
            "likes": "answer the preference or comparison and preserve the evidence's stated criterion",
            "uses": "state what James uses it for",
            "method": "state the documented method or approach",
        }.get(contract.relation, "answer the requested relationship directly")
        contract_text = (
            "\n\nResolved contract (follow this request; do not broaden it): "
            f"subject={contract.subject}; domain={contract.domain}; relation={contract.relation}; "
            f"object_type={contract.object_type}; constraints={contract.constraints}; "
            f"response_mode={contract.response_mode}. Answer focus: {relation_guidance}."
        )
    user = (
        f"Context:\n{context}\n\n"
        f"Question: {question}{contract_text}\n\n"
        "Answer the question using only the context above. "
        "Prefer one concise sentence, or a short bullet list when the question asks for multiple items. "
        "Do not add a concluding sentence that repeats the question or the answer. "
        "Answer only the topic asked about; include the relevant specifics and ignore unrelated context. "
        "Write one complete, standalone answer sentence; never respond with only a heading, a topic name, or a quote fragment. "
        "For a reason, include the documented reason, purpose, or outcome. For a comparison, name the preferred side and its documented criterion. "
        "When one cited sentence names multiple distinct mechanisms that answer the question, include each of them. "
        "Speak about James in the third person, including when the evidence quotes him saying I or my. "
        "Use normal spelling even if the user made a typo. "
        "Never mention the context or say 'the provided context'. "
        "Do not infer ages from years, favorites from general usage, or relationships between separate facts. "
        "Return exactly one JSON object and no Markdown or surrounding text. It must have exactly these fields: "
        "{\"answer\": string, \"answered_relation\": string, \"evidence_ids\": [string]}. "
        "For a supported answer, answered_relation must exactly equal the resolved relation and evidence_ids must list only the IDs "
        "of sentences that directly support the answer. Do not cite a nearby but unrelated fact. "
        f"The only valid evidence_ids are: {json.dumps(valid_evidence_ids)}. Copy an ID exactly from that list; "
        "never put a source sentence, label, quotation, or bracketed context in evidence_ids. "
        "If the context does not directly answer the question, set answer exactly to "
        f"\"{config.REFUSAL_MESSAGE}\" and use an empty evidence_ids list."
    )
    messages = [{"role": "system", "content": config.GROUNDING_SYSTEM_PROMPT}]
    # The current question has already been resolved against session memory.
    # Prior user statements and assistant answers are not new evidence.
    messages.append({"role": "user", "content": user})
    return messages


def _sanitize_context_for_external(chunks: list[dict]) -> list[dict]:
    patterns = [*config.PII_PATTERNS, *config.PRIVATE_KB_PATTERNS]
    return [
        chunk
        for chunk in chunks
        if not any(re.search(pattern, chunk.get("text", ""), re.IGNORECASE) for pattern in patterns)
    ]


def _call_ollama(messages: list[dict], timeout: float = OLLAMA_TIMEOUT) -> str:
    """Call Ollama with a real HTTP timeout that also works in worker threads."""

    response = httpx.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": config.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.0, "top_p": 0.9, "num_predict": config.LLM_MAX_OUTPUT_TOKENS, "num_ctx": 4096},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    content = data["message"]["content"]
    if not isinstance(content, str) or not content.strip() or data.get("done_reason") == "length":
        raise ValueError("Ollama returned an empty or truncated answer")
    return content.strip()


def _call_groq(messages: list[dict], timeout: float = OLLAMA_TIMEOUT) -> str:
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
            "max_tokens": config.LLM_MAX_OUTPUT_TOKENS,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def generate_answer(
    question: str, context_chunks: list[dict], history: list[dict] | None = None,
    *, contract: SemanticContract | None = None, timeout: float = OLLAMA_TIMEOUT,
) -> tuple[str, bool]:
    if not context_chunks:
        return config.REFUSAL_MESSAGE, False
    if timeout <= 0 or not _generation_slots.acquire(blocking=False):
        return config.UNAVAILABLE_MESSAGE, True
    try:
        # The public path passes its already resolved contract.  Direct callers
        # retain the three-argument surface and derive one only when needed.
        resolved_contract = contract
        if resolved_contract is None and config.SEMANTIC_CONTRACT_ENABLED:
            resolved_contract = build_query_plan(question).intent.contract
        messages = _build_messages(question, context_chunks, history, resolved_contract)
        if config.LLM_BACKEND == "ollama":
            return _call_ollama(messages, timeout=timeout), False
        if config.LLM_BACKEND == "groq":
            safe_chunks = _sanitize_context_for_external(context_chunks)
            if not safe_chunks:
                return config.REFUSAL_MESSAGE, False
            return _call_groq(_build_messages(question, safe_chunks, contract=resolved_contract), timeout=timeout), False
        raise ValueError(f"Unknown LLM_BACKEND: {config.LLM_BACKEND}")
    except Exception as exc:
        logger.warning("Answer generation unavailable (%s)", type(exc).__name__)
        return config.UNAVAILABLE_MESSAGE, True
    finally:
        _generation_slots.release()


def _is_compound_request(question: str) -> bool:
    return len(split_compound_question(question)) > 1


def _select_context_chunks(
    question: str, reranked_chunks: list[dict], intent: QueryIntent | None = None
) -> list[dict]:
    if not reranked_chunks:
        return reranked_chunks
    focused = focused_chunks(intent.entities, reranked_chunks) if intent is not None else None
    if focused is not None:
        return focused
    if intent is not None and "additional_hobbies" in intent.entities:
        return reranked_chunks[:4]
    if intent is not None and "favorites_overview" in intent.entities:
        favorite_chunks: list[dict] = []
        seen_titles: set[str] = set()
        for chunk in reranked_chunks:
            metadata = chunk.get("metadata", {})
            if metadata.get("category") not in {"favorites", "gaming", "food", "season", "travel"}:
                continue
            title = str(metadata.get("title") or chunk.get("chunk_id") or "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            favorite_chunks.append(chunk)
        return favorite_chunks[:7] if favorite_chunks else reranked_chunks[:3]
    if intent is not None and intent.topic == "videos" and not any(
        entity in intent.entities for entity in {"video_greece", "video_japan", "video_xinjiang"}
    ):
        return reranked_chunks[:3]
    if intent is not None and intent.topic == "contact":
        target_titles = {
            "youtube": "YouTube channel",
            "github": "GitHub profile",
            "website": "Personal website",
        }
        for entity, title in target_titles.items():
            if entity in intent.entities:
                target = next(
                    (chunk for chunk in reranked_chunks if chunk.get("metadata", {}).get("title") == title),
                    None,
                )
                return [target] if target is not None else reranked_chunks[:1]
        return reranked_chunks[:5]
    if intent is not None:
        target_titles = {
            "fft_tuner": "Tune-app (FFT Guitar Tuner)",
            "medical_platform": "智愈APP (Zhiyu App) — Flutter medical platform",
            "cs_inspiration": "Person who sparked CS interest",
            "qiu_competition": "丘成桐中学科学奖 (Qiu Competition)",
            "uniswap_project": "Uniswap V3 EE experiment",
            "video_greece": "Greece",
            "video_japan": "Japan Winter",
            "video_xinjiang": "Xinjiang, China",
            "camera_xinjiang": "Xinjiang, China",
            "sport_skiing": "Sports",
            "sport_ice_hockey": "Sports",
            "sport_tennis": "Sports",
            "sport_floorball": "Sports",
            "sport_soccer": "Sports",
            "camera": "Photography and videography",
            "lens": "Photography and videography",
            "instrument": "Electric guitar",
            "aspirations": "Future aspirations",
            "research_overview": "Writing & Essays",
            "graduation": "Expected graduation",
            "higher_level_subjects": "Education",
            "travel_italy": "Italy (Tuscany)",
            "travel_greece": "Greece (Athens, Ionian Sea)",
            "travel_japan": "Japan (Hokkaido)",
            "travel_xinjiang": "Xinjiang, China",
            "travel_russia": "Russia",
            "travel_united_states": "United States (Los Angeles)",
        }
        for entity, title in target_titles.items():
            if entity.startswith("sport_") and intent.topic != "sports":
                continue
            if entity in intent.entities:
                target = next(
                    (
                        chunk
                        for chunk in reranked_chunks
                        if chunk.get("metadata", {}).get("title") == title
                        and (
                            entity != "graduation"
                            or chunk.get("metadata", {}).get("category") == "education"
                        )
                    ),
                    None,
                )
                return [target] if target is not None else reranked_chunks[:1]
        if "photographed_places" in intent.entities:
            destination_titles = {
                "Japan (Hokkaido)",
                "Italy (Tuscany)",
                "Greece (Athens, Ionian Sea)",
            }
            matches = [
                chunk
                for chunk in reranked_chunks
                if chunk.get("metadata", {}).get("title") in destination_titles
            ]
            return matches[:3] if matches else reranked_chunks[:3]
    if len(reranked_chunks) <= 1:
        return reranked_chunks
    if _is_structured_summary(reranked_chunks[0]):
        return reranked_chunks[:1]
    top_score = float(reranked_chunks[0].get("score", 0.0))
    second_score = float(reranked_chunks[1].get("score", 0.0))
    if top_score - second_score >= 1.5:
        return reranked_chunks[:1]
    return reranked_chunks[:CONTEXT_TOP_N]


def _format_single_source_explanation(
    contract: SemanticContract | None,
    capability: object | None,
    context_chunks: list[dict],
) -> str | None:
    """Return one complete reviewed explanation without model compression.

    This path is deliberately limited to a single capability-authorized source
    and explanatory relationships. It preserves coordinated evidence (such as
    two documented accessibility mechanisms) that a small local model can
    otherwise compress into an incomplete answer.
    """

    if (
        contract is None
        or getattr(capability, "evidence_kind", None) != "explanatory_evidence"
        or contract.relation not in {"describes", "reason", "result", "method", "uses", "likes"}
        or len(context_chunks) != 1
    ):
        return None
    source_text = extractive_answer(context_chunks[0]).strip()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", source_text):
        candidate = sentence.strip()
        if not candidate or not check_grounding(candidate, context_chunks) or not check_contract_relevance(
            candidate, contract, context_chunks
        ):
            continue
        # Preserve an extractive answer while making source fragments readable
        # as a standalone third-person sentence.
        if re.match(r"^(?:enjoys|regularly uses|describes|reflects|started)\b", candidate, re.IGNORECASE):
            candidate = f"James {candidate[:1].lower()}{candidate[1:]}"
        return attribute_profile_quote(candidate, context_chunks)
    return None


def answer_or_refuse(
    question: str,
    reranked_chunks: list[dict],
    history: list[dict] | None = None,
    enforce_confidence_threshold: bool = True,
    intent_question: str | None = None,
    intent_override: QueryIntent | None = None,
    generation_timeout: float | None = None,
) -> dict:
    started = time.perf_counter()
    semantic_question = intent_question.strip() if intent_question else question
    # Keep the visitor's wording separate so the answer addresses the actual question, not only the search phrase.
    if intent_question is None:
        # Direct callers use the same normalisation as the API when no plan is supplied.
        semantic_question = build_query_plan(question).normalized_question
    # Use the planner's merged intent rather than only the canonical wording.
    # Canonicalisation can remove entities that the final answer still needs.
    planned_intent = build_query_plan(question).intent
    if not config.SEMANTIC_CONTRACT_ENABLED:
        planned_intent = replace(planned_intent, contract=None)
    if intent_override is not None:
        intent = intent_override
    elif intent_question and semantic_question != question:
        # A state-resolved caller may supply a subject without the merged planner intent.
        # Merge both so inherited subjects and the original operator remain available.
        resolved_intent = build_query_plan(semantic_question).intent
        intent = _merge_contract_intent(resolved_intent, planned_intent)
    else:
        intent = planned_intent

    # Handle deterministic outcomes first so safe replies do not need model generation.
    # Early returns also make refusal and error behaviour easier to test.
    # Private or sensitive questions are refused before retrieval or generation.
    if intent.kind == "privacy" or is_sensitive_request(question):
        return _result("refused", config.REFUSAL_MESSAGE, reason="privacy")

    # Greetings and other small-talk replies do not need a knowledge search.
    if intent.kind == "small_talk" or is_small_talk(question):
        from backend.generation.policies import small_talk_answer
        return _result("answered", small_talk_answer(question), confidence=1.0, reason="small_talk")

    # Questions about the website itself can use a fixed, immediate response.
    if intent.kind == "product_meta" or is_product_meta_request(question):
        return _result("answered", product_meta_answer(question), confidence=1.0, reason="product_meta")

    # An unresolved follow-up receives clarification instead of an invented topic.
    if intent.kind == "unknown" and intent.followup:
        return _result("clarification", config.CLARIFICATION_MESSAGE, reason="ambiguous_followup")

    # Stop unsupported or ambiguous details before a model can answer with a related but wrong passage.
    if intent.kind in {"privacy", "ambiguous", "unsupported"} or is_ambiguous_request(question) or is_non_profile_request(question) or unavailable_profile_detail(semantic_question, intent) or unavailable_profile_detail(question, intent):
        reason = {
            "privacy": "privacy",
            "unsupported": "unsupported",
            "ambiguous": "ambiguous_request",
        }.get(intent.kind, "unsupported")
        return _result("refused", config.REFUSAL_MESSAGE, reason=reason)

    # Retrieval may be broad, but only evidence approved for the contract may reach a formatter or model.
    # An unsupported relationship must stop here instead of becoming a substitute answer.
    capability = None
    if config.SEMANTIC_CONTRACT_ENABLED and intent.contract is not None:
        capability = capability_for(intent.contract, intent)
        if capability is None:
            return _result("refused", config.REFUSAL_MESSAGE, reason="unsupported")
        # A related topic is not enough; the selected passage must satisfy the requested fact.
        eligible = eligible_evidence(intent.contract, intent, reranked_chunks)
        if not eligible and reranked_chunks and all(not chunk.get("metadata") for chunk in reranked_chunks):
            # Low-level callers may provide preselected fixtures without metadata.
            # The public API always passes metadata-bearing corpus chunks.
            eligible = reranked_chunks
        if not eligible:
            # A missing approved passage is a reason to refuse, not to guess.
            return _result("refused", config.REFUSAL_MESSAGE, reason="missing_evidence")
        reranked_chunks = eligible

    if not reranked_chunks or is_sensitive_request(question):
        # Without approved evidence, refusal is safer than guessing.
        return _result(
            "refused",
            config.REFUSAL_MESSAGE,
            reason="privacy" if is_sensitive_request(question) else "no_retrieval",
        )

    top_score = float(reranked_chunks[0].get("score", 0.0))
    top_chunks = _select_context_chunks(semantic_question, reranked_chunks, intent)
    if not top_chunks:
        return _result("refused", config.REFUSAL_MESSAGE, reason="missing_evidence")
    sources = _build_sources(top_chunks)
    if enforce_confidence_threshold and top_score < config.CONFIDENCE_THRESHOLD:
        return _result(
            "refused",
            config.REFUSAL_MESSAGE,
            confidence=top_score,
            sources=[],
            reason="low_retrieval_confidence",
        )

    # Use a deterministic formatter when approved evidence already contains the requested fact.
    # Model generation is the final fallback.
    structured = format_structured_answer(semantic_question, top_chunks, intent)
    if structured == config.REFUSAL_MESSAGE:
        return _result("refused", config.REFUSAL_MESSAGE, reason="unsupported_detail")
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

    explanatory = _format_single_source_explanation(intent.contract, capability, top_chunks)
    if explanatory is not None and not _is_compound_request(question):
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return _result(
            "answered",
            explanatory,
            confidence=top_score,
            sources=sources,
            total_ms=elapsed,
            reason="structured_evidence",
        )

    # Keep the resolved request unchanged so inherited subjects and constraints are not lost.
    # Only remaining explanatory cases reach the model after deterministic checks fail.
    model_contract = (
        intent.contract or build_query_plan(semantic_question).intent.contract
        if config.SEMANTIC_CONTRACT_ENABLED
        else None
    )
    generation_started = time.perf_counter()
    generation_options = {"timeout": generation_timeout} if generation_timeout is not None else {}
    answer_text, fallback_used = generate_answer(
        semantic_question,
        top_chunks,
        history,
        contract=model_contract,
        **generation_options,
    )
    generation_ms = round((time.perf_counter() - generation_started) * 1000, 1)
    draft: GeneratedDraft | None = None
    filtered = config.REFUSAL_MESSAGE

    if fallback_used:
        status = "unavailable"
        filtered = config.UNAVAILABLE_MESSAGE
        reason = "llm_unavailable"
    else:
        # The rollback flag deliberately preserves the established plain-text
        # generation path.  The evidence-scoped draft protocol is active only
        # with the semantic-contract boundary enabled.
        raw_refusal = normalize_refusal(apply_pii_filter(answer_text))
        if raw_refusal == config.REFUSAL_MESSAGE:
            status = "refused"
            reason = "model_refusal"
        elif not config.SEMANTIC_CONTRACT_ENABLED:
            filtered = raw_refusal
            status = "answered"
            reason = "generated"
        else:
            # A plain refusal remains backward-compatible with older local
            # models; every non-refusal response must be a structured draft.
            draft = _parse_generated_draft(answer_text)
            if draft is None:
                status = "refused"
                reason = "invalid_draft"
            else:
                filtered = normalize_refusal(apply_pii_filter(attribute_profile_quote(draft.answer, top_chunks)))
                draft = replace(draft, answer=filtered)
                if filtered == config.REFUSAL_MESSAGE:
                    status = "refused"
                    reason = "model_refusal"
                elif not draft.validate(model_contract, top_chunks):
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
        sources=(
            _build_sources(draft.cited_chunks(top_chunks))
            if status == "answered" and draft is not None
            else sources if status == "answered" and not config.SEMANTIC_CONTRACT_ENABLED else []
        ),
        fallback_used=fallback_used,
        total_ms=elapsed,
        generation_ms=generation_ms,
        reason=reason,
    )
