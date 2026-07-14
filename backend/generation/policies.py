from __future__ import annotations

import re

from backend import config

SENSITIVE_REQUEST_PATTERNS = [
    r"\bpassword\b",
    r"\b(?:phone|telephone)\s+number\b",
    r"\bhome\s+address\b",
    r"\bprivate\s+address\b",
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

PRODUCT_META_PATTERNS = [
    r"\b(?:what|which)\s+(?:is\s+the\s+)?(?:ai\s+)?model\b",
    r"\b(?:who\s+are\s+you|what\s+are\s+you)\b",
    r"\bwhat\s+(?:can|could)\s+(?:you|this\s+(?:chat|bot|assistant))\s+(?:answer|do)\b",
    r"\b(?:architecture|architectural|pipeline|system\s+design|tech(?:nology)?\s+stack)\b",
    r"\b(?:how\s+does\s+(?:this|the)\s+(?:chat|bot|assistant)\s+work|what\s+happens\s+when\s+i\s+ask)\b",
    r"\b(?:rag|retrieval[- ]augmented(?:\s+generation)?|bm25|reranker|query\s+planner)\b",
    r"\b(?:knowledge\s+base|profile\s+facts?|where\s+does\s+(?:the\s+)?(?:data|information)\s+come\s+from)\b",
    r"\bwhere\s+does\s+(?:this|the)\s+(?:chat|bot|assistant)'?s\s+(?:knowledge|data|information)\s+come\s+from\b",
    r"\b(?:source\s+attribution|source\s+labels?|why\s+(?:are|do)\s+(?:there\s+)?sources?)\b",
    r"\b(?:what|where)\s+(?:are|do)\s+(?:the\s+)?(?:sources?|citations?)\b",
    r"\b(?:conversation|chat)\s+(?:memory|history|session|sessions?)\b",
    r"\b(?:does|can|will)\s+(?:this|the)\s+(?:chat|bot|assistant)\s+(?:remember|store|save)\b",
    r"\b(?:is|does)\s+(?:this|the\s+chat|the\s+bot)\s+(?:trained|fine[- ]tuned|fine tuned|use\s+web\s+search|use\s+the\s+internet)\b",
    r"\b(?:fine[- ]tuned|fine tuned)\b",
    r"\b(?:privacy|security|safe|stored|saved)\b.*\b(?:chat|bot|data|information|messages?)\b",
    r"\b(?:why|when)\b.*\b(?:refuse|refuses|cannot\s+answer|can't\s+answer|doesn't\s+answer|does\s+not\s+answer)\b",
    r"\b(?:limitations?|outside\s+(?:the\s+)?profile|general\s+knowledge|web\s+search)\b",
    r"\b(?:github\s+pages|cloudflare|quick\s+tunnel|trycloudflare|deployed|deployment|hosted)\b",
    r"\bwhy\s+(?:use|this|the)\b.*\b(?:model|3b|small|local)\b",
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
    return _matches_any(question, PRODUCT_META_PATTERNS)


def product_meta_answer(question: str) -> str:
    lower = question.lower()
    backend_name = "Ollama" if config.LLM_BACKEND == "ollama" else config.LLM_BACKEND.title()
    wants_model = bool(re.search(r"\b(?:model|qwen|ollama|3b|llm)\b", lower))
    wants_architecture = bool(
        re.search(
            r"\b(?:architecture|architectural|pipeline|system\s+design|tech(?:nology)?\s+stack|how\s+does\s+(?:this|the)\s+(?:chat|bot|assistant)\s+work|rag|retrieval|bm25|reranker|query\s+planner)\b",
            lower,
        )
    )
    wants_knowledge = bool(re.search(r"\b(?:knowledge|knowledge\s+base|profile\s+facts?|data|information)\b", lower))
    wants_sources = bool(re.search(r"\b(?:sources?|citations?)\b", lower))
    wants_memory = bool(re.search(r"\b(?:memory|history|session|sessions?|remember|stored|saved)\b", lower))
    wants_privacy = bool(re.search(r"\b(?:privacy|security|safe|private)\b", lower))
    wants_training = bool(re.search(r"\b(?:trained|training|fine[- ]tuned|fine tuned)\b", lower))
    wants_limits = bool(
        re.search(r"\b(?:limitations?|refuse|refuses|cannot|can't|outside|general\s+knowledge|web\s+search|internet)\b", lower)
    )
    wants_deployment = bool(re.search(r"\b(?:github\s+pages|cloudflare|tunnel|deployed|deployment|hosted)\b", lower))

    model_answer = (
        f"This chat currently uses {config.LLM_MODEL} through {backend_name} on the Mac mini. "
        "The model is prompted with retrieved James-specific context; it is not used as an unrestricted general-purpose assistant."
    )
    architecture_answer = (
        "This is a retrieval-augmented generation (RAG) system with a deterministic interpretation layer:\n\n"
        "1. The React/Vite frontend sends the question to a FastAPI backend.\n"
        "2. A query planner normalizes typos and informal phrasing, then detects the topic and intent.\n"
        "3. BM25 retrieves relevant chunks from James's curated knowledge base. The optional neural reranker is currently disabled.\n"
        "4. Exact fact questions use structured answer templates; broader questions send the retrieved context to the language model.\n"
        "5. Grounding, privacy, and refusal checks run before the answer and supporting sources are returned."
    )
    knowledge_answer = (
        "The chatbot's knowledge comes from curated project files, including `kb_extra/`, `data/profile_facts.json`, "
        "and the indexed `data/chunks.json`. It does not browse the web or silently use outside facts while answering James-specific questions."
    )
    sources_answer = (
        "The Sources section shows the knowledge-base chunks retrieved for that answer. They are evidence from the project's curated files, "
        "not live web citations. Structured answers may show the summary chunk that supplied the relevant fact."
    )
    memory_answer = (
        "Conversation follow-ups use a short in-memory session identified by `session_id`. The backend keeps at most a few recent turns "
        "and expires inactive sessions; there is no database-backed chat history."
    )
    privacy_answer = (
        "The current Ollama setup runs the language model locally on the Mac mini. The backend also blocks common sensitive requests, "
        "filters possible personal data, limits request rates, and refuses to guess when a fact is not in the public profile."
    )
    training_answer = (
        "The current chatbot is not fine-tuned for James. Its knowledge comes from curated files, BM25 retrieval, structured answer logic, "
        "and a grounding prompt. The repository contains experimental training code for a reranker, but that reranker is not in the live path."
    )
    limits_answer = (
        "Ask James is designed for James's public profile—not general web search. It can answer about his hobbies, games, sports, photography, "
        "projects, essays, travel, education, and achievements. It may refuse when the knowledge base lacks evidence, when a request is private, "
        "or when the local model is unavailable."
    )
    deployment_answer = (
        "The frontend is built with Vite and deployed to GitHub Pages. During development and demonstration, the FastAPI/Ollama backend runs on the Mac mini "
        "and is exposed through a temporary Cloudflare Quick Tunnel. That tunnel is suitable for testing but can change or stop when its terminal or backend stops."
    )

    sections: list[str] = []
    if wants_model:
        sections.append(model_answer)
    if wants_architecture:
        sections.append(architecture_answer)
    if wants_knowledge:
        sections.append(knowledge_answer)
    if wants_sources:
        sections.append(sources_answer)
    if wants_memory:
        sections.append(memory_answer)
    if wants_privacy:
        sections.append(privacy_answer)
    if wants_training:
        sections.append(training_answer)
    if wants_limits:
        sections.append(limits_answer)
    if wants_deployment:
        sections.append(deployment_answer)

    if sections:
        return "\n\n".join(sections)
    return (
        "I'm Ask James, a local RAG chatbot for questions about James's photography, videos, essays, hobbies, sports, projects, and favorites. "
        "You can also ask how the architecture, model, sources, memory, or privacy controls work."
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
