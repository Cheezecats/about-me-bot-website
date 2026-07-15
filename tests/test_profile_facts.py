from __future__ import annotations

import json

from backend import config
from scripts.validate_profile_facts import validate_facts


def _facts() -> dict:
    return json.loads((config.DATA_DIR / "profile_facts.json").read_text(encoding="utf-8"))


def test_profile_facts_has_required_public_sections():
    facts = _facts()
    required = {
        "favorite_games",
        "favorite_food",
        "favorite_season",
        "favorite_music",
        "favorite_anime",
        "favorite_movie",
        "favorite_book_series",
        "favorite_place",
        "favorite_school_subject",
        "ide_editors",
        "hobbies",
        "guitar",
        "photography",
        "sports",
        "travel",
        "education",
        "projects",
        "programming_languages",
        "writing",
        "achievements",
    }
    assert required <= facts.keys()
    assert facts["sports"]
    assert facts["projects"]
    assert facts["achievements"]
    assert all("flappy" not in project["name"].lower() for project in facts["projects"])


def test_profile_facts_do_not_contain_private_field_names_or_pii():
    text = json.dumps(_facts(), ensure_ascii=False).lower()
    assert "password" not in text
    assert "home address" not in text
    assert "social security" not in text
    assert "@" not in text


def test_profile_facts_validation_pipeline_passes():
    assert validate_facts(_facts()) == []
