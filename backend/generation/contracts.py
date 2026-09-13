"""Shared semantic contract and conservative profile boundaries.

The contract is deliberately small and serialisation-friendly.  It describes
what a visitor asked for; retrieval may broaden a query, but it must not
change these fields.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticContract:
    """The one interpretation consumed by retrieval, answering and actions."""

    original_text: str
    subject: str | None = None
    domain: str | None = None
    relation: str = "unresolved"
    object_type: str = "unresolved"
    constraints: dict[str, Any] = field(default_factory=dict)
    response_mode: str = "information"
    context_resolution: str = "unresolved"
    antecedent_id: str | None = None
    supporting_spans: tuple[str, ...] = ()
    provenance: str = "deterministic"
    confidence: float = 0.0

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.original_text.strip():
            errors.append("original_text is required")
        if self.response_mode not in {"information", "navigation", "both"}:
            errors.append("response_mode is invalid")
        if self.context_resolution not in {"explicit", "inherited", "ambiguous", "unresolved"}:
            errors.append("context_resolution is invalid")
        if not self.relation:
            errors.append("relation is required")
        if not self.object_type:
            errors.append("object_type is required")
        if self.context_resolution == "inherited" and not self.antecedent_id:
            errors.append("inherited context needs an antecedent_id")
        if self.provenance not in {"deterministic", "memory", "clarification", "unresolved"}:
            errors.append("provenance is invalid")
        return tuple(errors)


def unresolved_contract(question: str, *, kind: str = "unresolved") -> SemanticContract:
    """Create a safe contract for policy turns without inventing a subject."""

    return SemanticContract(
        original_text=question,
        relation=kind,
        object_type="unresolved",
        context_resolution="unresolved",
        provenance="unresolved",
    )


def unavailable_profile_detail(question: str, intent: Any) -> bool:
    lower = question.lower()
    if re.search(r"\bflappy\s*bird\b", lower):
        return True
    # Never silently replace another named person with James.
    subject = re.search(r"\b(?:does|did|has)\s+([a-z]+)\s+(?:have|like|do|play|use|study|live|build|write|enjoy)\b", lower)
    if subject and subject.group(1) not in {
        "james", "he", "she", "it", "jamchat", "this", "that", "ai", "llm", "technology"
    }:
        return True
    if intent.topic in {"photography", "hobbies"} and re.search(
        r"\b(?:cost|costs|price|paid|buy|bought|purchase|settings?|brand|serial|aperture|shutter|iso)\b", lower
    ):
        return True
    if intent.topic == "photography" and re.search(r"\b(?:why|before|previous|prior|canon)\b", lower):
        return True
    if "instrument" in intent.entities and "fft_tuner" not in intent.entities and re.search(
        r"\b(?:why|piano|violin|drums|brand|model|teacher)\b", lower
    ):
        return True
    if intent.topic == "food" and re.search(r"\b(?:why|how much|how often|where|when)\b", lower):
        return True
    if intent.topic == "sports" and intent.negated and intent.question_operator != "yes_no":
        return True
    if intent.topic == "travel" and re.search(r"\b(?:who|with whom|hotel|flight|cost)\b", lower):
        return True
    if intent.topic == "travel" and intent.question_operator == "when" and "travel_italy" in intent.entities:
        return True
    if re.search(r"\b(?:grades|gpa|exam scores?|university.*(?:attend|going))\b", lower):
        return True
    return False


def summary_can_answer(question: str, intent: Any) -> bool:
    """A topic match alone cannot authorize an answer to a narrower question.

Focused document answers run separately. These are the operators supported
by the broad curated summaries; other questions continue to grounded generation.
"""
    contract = getattr(intent, "contract", None)
    if contract is not None and contract.relation in {"learned_by", "method", "reason", "result", "started", "current_participation", "photographed_in"}:
        return True
    if intent.question_operator == "why":
        return "gaming_reason" in intent.entities or intent.topic == "season"
    if intent.question_operator == "how":
        return bool({"coding_origin", "instrument", "apex_rank", "public_contact", "anime_influence"}.intersection(intent.entities)) or intent.topic == "bio"
    if intent.question_operator == "when":
        return bool({"instrument", "graduation", "coding_origin", "apex_rank"}.intersection(intent.entities)) or intent.topic == "sports"
    if intent.question_operator == "who":
        return intent.topic in {"bio", "music", "contact"} or "cs_inspiration" in intent.entities
    if intent.temporal_relation in {"before", "after"}:
        return intent.topic == "sports"
    # Specific details that a topic overview cannot provide.
    return not bool(re.search(
        r"\b(?:how often|how long|settings?|cost|price|brand|professional|latest|these days|"
        r"learn(?:ed)? from|research results?|conclusions?|limitations?)\b", question, re.IGNORECASE
    ))
