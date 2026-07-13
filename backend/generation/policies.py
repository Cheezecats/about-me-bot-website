from __future__ import annotations

import re

from backend import config

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
    r"\b(?:favorite|favourite)\s+(?:restaurant|photographer|university|college|movie|film|book|anime|series|actor|actress|brand)\b",
    r"\bleast\s+favorite\s+(?:games?|songs?|artists?|bands?|restaurants?|movies?|films?|books?)\b",
    r"\bfuture\s+(?:university|college)\b",
]
REFUSAL_VARIANTS = [
    r"provided context does not contain",
    r"context does not contain",
    r"not enough information",
    r"i do not have that information",
    r"i don't have that information",
]


def _matches_any(question: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, question.strip(), flags=re.IGNORECASE) for pattern in patterns)


def is_sensitive_request(question: str) -> bool:
    return _matches_any(question, SENSITIVE_REQUEST_PATTERNS)


def is_small_talk(question: str) -> bool:
    return _matches_any(question, SMALL_TALK_PATTERNS)


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


def product_meta_answer(question: str) -> str:
    if re.search(r"\bwhat\s+model\b", question, flags=re.IGNORECASE):
        return (
            f"I'm Ask James, powered locally by {config.LLM_MODEL}. "
            "I answer questions about James using this project's knowledge base."
        )
    return (
        "I'm Ask James, a local chatbot for questions about James's photography, videos, "
        "essays, hobbies, sports, and projects."
    )


def apply_pii_filter(text: str) -> str:
    for pattern in config.PII_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return config.REFUSAL_MESSAGE
    return text


def normalize_refusal(text: str) -> str:
    if _matches_any(text, REFUSAL_VARIANTS):
        return config.REFUSAL_MESSAGE
    return text
