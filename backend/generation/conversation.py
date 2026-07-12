from __future__ import annotations

import re

from backend import config

_FOLLOWUP_TOKENS = frozenset(
    {"he", "his", "him", "she", "her", "it", "they", "them", "about", "that", "this", "those", "these"}
)
_EXPLICIT_TOPIC_TOKENS = frozenset(
    {
        "camera", "cameras", "lens", "lenses", "photography", "videography",
        "sports", "sport", "skiing", "hockey", "tennis", "floorball", "soccer",
        "games", "game", "music", "song", "guitar", "instrument", "hobbies",
        "hobby", "essays", "essay", "projects", "project", "travel", "travelled",
        "food", "season", "school", "education", "rank", "programming",
    }
)
_STOPWORDS = frozenset(
    "the a an and or but is are was were be been being to of in on at for with about "
    "this that it he his him she her they them what when where why how james".split()
)


def _is_followup(question: str) -> bool:
    tokens = set(re.findall(r"[a-z]+", question.lower()))
    return bool(tokens & _FOLLOWUP_TOKENS)


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

    def record(self, question: str, answer: str, topic: str) -> None:
        self.history.append((question, answer, topic))
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns :]

    def augment_query(self, question: str) -> str:
        if not self.history or not _is_followup(question):
            return question
        question_tokens = set(re.findall(r"[a-z]+", question.lower()))
        # An explicit topic is more reliable than keywords extracted from the
        # previous answer. This prevents a follow-up about lenses from being
        # contaminated by an earlier answer about food or seasons.
        if question_tokens & _EXPLICIT_TOPIC_TOKENS:
            return question
        _last_q, last_answer, last_topic = self.history[-1]
        kws = _keywords(last_answer) or _keywords(last_topic)
        if not kws:
            return question
        return " ".join(kws) + " " + question

    def build_history_messages(self) -> list[dict]:
        messages: list[dict] = []
        for q, a, _topic in self.history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})
        return messages
