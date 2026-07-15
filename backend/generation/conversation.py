from __future__ import annotations

import re
import time

from backend import config

_FOLLOWUP_TOKENS = frozenset(
    {
        "he", "his", "him", "she", "her", "it", "they", "them", "about", "that", "this", "those", "these",
        "anything", "else", "also", "more", "other", "another", "and", "start", "started", "one", "first", "second", "third",
    }
)
_EXPLICIT_TOPIC_TOKENS = frozenset(
    {
        "camera", "cameras", "lens", "lenses", "photography", "videography",
        "sports", "sport", "skiing", "hockey", "tennis", "floorball", "soccer",
        "games", "game", "music", "song", "guitar", "instrument", "hobbies",
        "hobby", "essays", "essay", "projects", "project", "travel", "travelled",
        "food", "season", "school", "education", "rank", "programming", "language", "languages",
        "awards", "award", "achievements", "achievement", "anime", "movie", "book",
    }
)
_STOPWORDS = frozenset(
    "the a an and or but is are was were be been being to of in on at for with about "
    "this that it he his him she her they them what when where why how james".split()
)
_VAGUE_FOLLOWUP_PATTERN = re.compile(
    r"^(?:what about|tell me more|anything else|what else|anything more|something else|anything to add|go on|continue|keep going|is that all|and|what about it|what about that|what about this)[!.?,\s]*$",
    re.IGNORECASE,
)

_TOPIC_CONTEXT_TERMS = {
    "photography": ("photography", "camera", "lens"),
    "games": ("games",),
    "music": ("music", "songs"),
    "hobbies": ("hobbies",),
    "sports": ("sports",),
    "travel": ("travel",),
    "writing": ("writing", "essays"),
    "achievements": ("achievements",),
    "projects": ("projects",),
    "education": ("education",),
    "food": ("food",),
    "season": ("season",),
}
_ENTITY_CONTEXT_TERMS = {
    "apex_rank": ("Apex Legends", "rank"),
    "camera": ("photography", "camera"),
    "lens": ("photography", "lens"),
    "song": ("music", "songs"),
    "band": ("music", "bands"),
    "artist": ("music", "artist"),
}


def _is_followup(question: str) -> bool:
    tokens = set(re.findall(r"[a-z]+", question.lower()))
    return bool(tokens & _FOLLOWUP_TOKENS) or bool(_VAGUE_FOLLOWUP_PATTERN.fullmatch(question.strip()))


def _keywords(text: str, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    caps = re.findall(r"\b([A-Z][a-zA-Z]{2,})\b", text)
    for w in caps:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= limit:
            return out
    words = re.findall(r"[A-Za-z]{4,}", text)
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= limit:
            break
    return out


class ConversationState:
    def __init__(self, max_turns: int = config.MAX_HISTORY_TURNS) -> None:
        self.max_turns = max_turns
        self.history: list[tuple[str, str, str]] = []
        self.last_topic: str | None = None
        self.last_entities: tuple[str, ...] = ()
        self.last_answer: str = ""

    def record(
        self,
        question: str,
        answer: str,
        topic: str,
        entities: tuple[str, ...] = (),
    ) -> None:
        self.history.append((question, answer, topic))
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]
        self.last_topic = topic
        self.last_entities = tuple(entities)
        self.last_answer = answer

    def _context_prefix(self) -> str:
        terms: list[str] = []
        for entity in self.last_entities:
            terms.extend(_ENTITY_CONTEXT_TERMS.get(entity, ()))
        if self.last_topic:
            terms.extend(_TOPIC_CONTEXT_TERMS.get(self.last_topic, ()))
        # A second-hop “which one?” needs the concrete item from the previous
        # answer, not merely the broad topic. This is deliberately limited to
        # list-like topics so it cannot leak arbitrary answer text into search.
        if self.last_topic in {"sports", "games", "projects"}:
            terms.extend(_keywords(self.last_answer, limit=3))

        deduplicated: list[str] = []
        seen: set[str] = set()
        for term in terms:
            normalized = term.lower()
            if normalized not in seen:
                seen.add(normalized)
                deduplicated.append(term)
        return " ".join(deduplicated)

    def augment_query(self, question: str) -> str:
        if not self.history or not _is_followup(question):
            return question
        lower = question.lower()
        # “Season” is ambiguous in this profile: it can mean James's favorite
        # season or the Apex Legends season attached to his rank. Preserve the
        # previous Apex entity when the follow-up uses a pronoun.
        if (
            "apex_rank" in self.last_entities
            and re.search(r"\bseason\b", lower)
            and re.search(r"\b(?:he|it|reach|reached)\b", lower)
        ):
            return "Apex Legends rank " + question

        question_tokens = set(re.findall(r"[a-z]+", question.lower()))
        # An explicit topic is more reliable than keywords extracted from the
        # previous answer. This prevents a follow-up about lenses from being
        # contaminated by an earlier answer about food or seasons.
        if question_tokens & _EXPLICIT_TOPIC_TOKENS:
            return question
        prefix = self._context_prefix()
        if not prefix:
            return question
        return prefix + " " + question

    def build_history_messages(self) -> list[dict]:
        messages: list[dict] = []
        for q, a, _topic in self.history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})
        return messages


class ConversationStore:
    """Bounded, expiring in-memory session store for the local API."""

    def __init__(
        self,
        *,
        max_conversations: int = config.MAX_CONVERSATIONS,
        ttl_seconds: int = config.SESSION_TTL_SECONDS,
    ) -> None:
        self.max_conversations = max_conversations
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, ConversationState]] = {}

    def _evict(self, now: float) -> None:
        expired = [
            session_id
            for session_id, (last_access, _state) in self._items.items()
            if now - last_access > self.ttl_seconds
        ]
        for session_id in expired:
            self._items.pop(session_id, None)
        while len(self._items) > self.max_conversations:
            oldest = min(self._items, key=lambda key: self._items[key][0])
            self._items.pop(oldest, None)

    def get(self, session_id: str) -> ConversationState:
        now = time.monotonic()
        self._evict(now)
        item = self._items.get(session_id)
        if item is None:
            state = ConversationState()
        else:
            state = item[1]
        self._items[session_id] = (now, state)
        return state

    def touch(self, session_id: str) -> None:
        if session_id in self._items:
            self._items[session_id] = (time.monotonic(), self._items[session_id][1])

    def __len__(self) -> int:
        self._evict(time.monotonic())
        return len(self._items)
