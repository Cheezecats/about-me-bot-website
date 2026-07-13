from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "data" / "profile_facts.json"

REQUIRED_SECTIONS = {
    "favorite_games",
    "favorite_food",
    "favorite_season",
    "favorite_music",
    "hobbies",
    "guitar",
    "photography",
    "sports",
    "travel",
    "education",
    "projects",
    "programming_languages",
    "writing",
    "writing_details",
    "achievements",
    "apex_rank",
}


def _load() -> dict:
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


def validate_facts(facts: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_SECTIONS - facts.keys()
    errors.extend(f"missing section: {section}" for section in sorted(missing))
    sources = facts.get("_sources", {})
    for section in REQUIRED_SECTIONS:
        for source in sources.get(section, []):
            if not (ROOT / source).is_file():
                errors.append(f"{section}: missing evidence source {source}")

    serialized = json.dumps(facts, ensure_ascii=False).lower()
    for forbidden in ("password", "home address", "social security"):
        if forbidden in serialized:
            errors.append(f"forbidden private field present: {forbidden}")
    if "@" in serialized:
        errors.append("email-like content must not be stored in profile facts")

    for section in REQUIRED_SECTIONS:
        if not facts.get(section):
            errors.append(f"empty section: {section}")
    return errors


def main() -> None:
    errors = validate_facts(_load())
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Profile facts valid: {FACTS_PATH}")


if __name__ == "__main__":
    main()
