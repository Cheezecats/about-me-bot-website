from __future__ import annotations

from backend.generation.intent import QueryIntent


def build_follow_up_questions(intent: QueryIntent | None, status: str) -> list[str]:
    """Return a few useful next questions for the topic just discussed.

    These are deliberately deterministic. The chat should offer helpful paths
    without asking the language model to invent follow-up questions or facts.
    """

    if status != "answered" or intent is None:
        return []

    if intent.kind == "product_meta":
        return [
            "What model powers this chat?",
            "How are sources selected?",
            "Does this chat remember conversations?",
        ]
    if intent.kind == "small_talk":
        return [
            "What are James's hobbies?",
            "What games does James enjoy?",
            "How does this chat work?",
        ]
    if intent.topic == "games":
        if "apex_rank" in intent.entities:
            return ["What season did James reach it in?", "What games does James enjoy?"]
        if "gaming_reason" in intent.entities:
            return ["What games does James enjoy?", "What is James's Apex Legends rank?"]
        return ["What is James's Apex Legends rank?", "Why does James enjoy gaming?"]
    if intent.topic == "photography":
        if "lens" in intent.entities:
            return ["What camera does James use?", "Where has James photographed?"]
        if "camera" in intent.entities:
            return ["What lenses does James use?", "Where has James photographed?"]
        return ["What camera does James use?", "What lenses does James use?"]
    if intent.topic == "music":
        return ["What are James's favorite bands?", "Does James play an instrument?"]
    if intent.topic == "hobbies":
        if "instrument" in intent.entities:
            return ["When did James start playing electric guitar?", "What music does James like?"]
        return ["What sports does James play?", "Does James play an instrument?"]
    if intent.topic == "bio":
        return ["What is James like as a person?", "What are James's hobbies?"]
    if intent.topic == "personality":
        if "aspirations" in intent.entities:
            return ["What projects has James built?", "What Higher Level subjects does James study?"]
        return ["What are James's future academic interests?", "What projects has James built?"]
    if intent.topic == "contact":
        return ["What videos has James made?", "How does JamChat work?"]
    if intent.topic == "videos":
        return ["What camera does James use?", "Where has James travelled?"]
    if intent.topic == "sports":
        return ["Which sport did James start first?", "What position does he play in ice hockey?"]
    if intent.topic == "projects":
        return ["Which projects involve AI?", "What programming languages does he use?"]
    if intent.topic == "writing":
        return ["What is his Extended Essay about?", "What achievements does he have?"]
    if intent.topic == "achievements":
        return ["What essays has James written?", "What projects has he built?"]
    if intent.topic == "travel":
        return ["Where has James photographed?", "What sports does James play?"]
    if intent.topic == "education":
        return ["What programming languages does he use?", "What projects has he built?"]
    if intent.topic in {"food", "season", "favorites"}:
        return ["What are James's hobbies?", "What games does James enjoy?"]

    return [
        "What are James's hobbies?",
        "What projects has he built?",
        "Where has James travelled?",
    ]
