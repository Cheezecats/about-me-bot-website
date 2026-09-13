"""Named public subjects and their evidence, shared by planning and memory.

These rules select documents, not new facts. A missing document is never
replaced by a different document from the same broad category.
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Any

from backend import config
from backend.generation.contracts import SemanticContract

# entity, query pattern, topic, evidence title, category
FOCUSED_SUBJECTS = (
    ("hallucination_evaluator", r"\bhallucination\s+(?:evaluator|evaluation)\b", "projects", "Hallucination Evaluation", "projects_skills"),
    ("histology_benchmark", r"\bhistology\s+(?:classifier|benchmark)\b", "projects", "Foundation Model Histology Benchmark", "projects_skills"),
    ("histology_paper", r"\bhistology\b.*\b(?:paper|research|essay|classif)|\b(?:paper|research|essay)\b.*\bhistology\b", "writing", "Histology classification research paper", "writing"),
    ("llm_paper", r"\b(?:llm|hallucination|language models?)\b.*\b(?:paper|research|essay)|\b(?:paper|research|essay)\b.*\b(?:llm|hallucination)\b", "writing", "LLM Hallucination research paper", "writing"),
    ("physics_ia", r"\bphysics\s+(?:ia|internal assessment)\b", "writing", "IB Physics IA", "writing"),
    ("math_ia", r"\b(?:math|mathematics)\s+(?:ia|internal assessment)\b", "writing", "Math IA", "writing"),
    ("extended_essay", r"\bextended essay\b", "writing", "Extended Essay (EE)", "writing"),
    ("tok_exhibition", r"\b(?:tok|theory of knowledge)\b", "writing", "TOK Exhibition", "writing"),
    ("pc_build", r"\bpc\s+(?:build|building|experience)|\b(?:build|built|building)\b.*\b(?:pc|computer)\b", "projects", "PC build project", "projects_skills"),
    ("econ_grapher", r"\b(?:econ(?:omics)?[- ]graph(?:er|ing)|economics graphing tool)\b", "projects", "Econ Grapher", "projects_skills"),
    ("sat_app", r"\bsat\s+vocab(?:ulary)?\b", "projects", "SAT Vocabulary Review App", "projects_skills"),
    ("physics_reason", r"\b(?:why|reason)\b.*\bphysics\b", "education", "Physics teacher", "education"),
    ("previous_curriculum", r"\b(?:before|prior|previous)\b.*\b(?:ibdp|ib|curriculum)\b", "education", "Previous curriculum", "education"),
    ("japan_trip", r"\b(?:how long|duration|21[- ]day|tokyo|kyoto|itinerary)\b.*\bjapan\b|\bjapan\b.*\b(?:trip|duration|itinerary)\b", "travel", "Japan (21-day trip)", "travel"),
    ("hockey_lessons", r"\b(?:learn|learned|lessons?|taught)\b.*\bhockey\b|\bhockey\b.*\b(?:learn|learned|lessons?|taught)\b", "sports", "Life lessons", "sports"),
)

# These subjects need prose synthesis, not an overview template. Selecting a
# precise document still lets the model handle varied wording in the question.
GENERATIVE_SUBJECTS = (
    ("failure_view", r"\bfail(?:ure|ures|ing)\b", "personality", "Sees failure as data", "personality"),
    ("engineering_motivation", r"\b(?:why|motivat\w*|enjoy\w*|interest\w*|appeal\w*|skill\w*|creative|logic|design)\b.*\bengineering\b|\bengineering\b.*\b(?:motivat\w*|enjoy\w*|appeal\w*|skill\w*|creative|logic|design)\b", "personality", "Views engineering as duality", "personality"),
    ("hardware_interest", r"\b(?:interests?|enjoy|like|curious)\b.*\b(?:hardware|chip design)\b", "education", "Favorite engineering topics", "education"),
    ("tennis_experience", r"\b(?:reward\w*|challeng\w*|enjoy\w*|why)\b.*\btennis\b|\btennis\b.*\b(?:reward\w*|challeng\w*|enjoy\w*)\b", "sports", "Tennis", "sports"),
    ("ai_learning", r"\b(?:ai|llm)\b.*\b(?:learn\w*|study\w*)\b", "hobbies", "AI/LLM usage", "hobbies"),
    ("school_challenge", r"\b(?:challeng\w*|hardest|difficult\w*|struggl\w*)\b.*\b(?:school|ib|student)\b|\b(?:school|ib|student)\b.*\b(?:challeng\w*|hardest|difficult\w*|struggl\w*)\b", "education", "Personal challenge", "bio"),
    ("democratizing_technology", r"\b(?:democratiz\w*|accessib\w*)\b.*\btechnology\b|\btechnology\b.*\b(?:democratiz\w*|accessib\w*)\b", "personality", "Values democratizing technology", "personality"),
    ("teamwork_view", r"\b(?:views?|think|believe|feel|value|why|prefer\w*)\b.*\bteamwork\b|\bteamwork\b.*\b(?:views?|think|believe|feel|value|prefer\w*)\b", "personality", "Values teamwork", "personality"),
)
GENERATIVE_ENTITIES = frozenset(item[0] for item in GENERATIVE_SUBJECTS)
FOCUSED_SUBJECTS = (*FOCUSED_SUBJECTS, *GENERATIVE_SUBJECTS)

CONTRACT_FOCUSED_TITLES: dict[str, frozenset[str]] = {
    "fft_tuner": frozenset({"Tune-app (FFT Guitar Tuner)"}),
    "medical_platform": frozenset({"智愈APP (Zhiyu App) — Flutter medical platform"}),
    "cs_inspiration": frozenset({"Person who sparked CS interest"}),
    "qiu_competition": frozenset({"丘成桐中学科学奖 (Qiu Competition)"}),
    "uniswap_project": frozenset({"Uniswap V3 EE experiment"}),
    "camera_xinjiang": frozenset({"Xinjiang, China"}),
    "video_greece": frozenset({"Greece"}),
    "video_japan": frozenset({"Japan Winter"}),
    "video_xinjiang": frozenset({"Xinjiang, China"}),
    "travel_greece": frozenset({"Greece (Athens, Ionian Sea)"}),
    "travel_italy": frozenset({"Italy (Tuscany)"}),
    "travel_japan": frozenset({"Japan (Hokkaido)", "Japan (21-day trip)"}),
    "travel_xinjiang": frozenset({"Xinjiang, China"}),
    "travel_russia": frozenset({"Russia"}),
    "travel_united_states": frozenset({"United States (Los Angeles)"}),
    "apex_rank": frozenset({"apex_rank"}),
    "aspirations": frozenset({"Future aspirations"}),
    "higher_level_subjects": frozenset({"Education", "HL subjects"}),
    "previous_curriculum": frozenset({"Previous curriculum"}),
    "hardware_interest": frozenset({"Favorite engineering topics"}),
    "engineering_motivation": frozenset({"Views engineering as duality"}),
    "failure_view": frozenset({"Sees failure as data"}),
    "tennis_experience": frozenset({"Tennis"}),
    "ai_learning": frozenset({"AI/LLM usage"}),
    "school_challenge": frozenset({"Personal challenge"}),
    "democratizing_technology": frozenset({"Values democratizing technology"}),
    "teamwork_view": frozenset({"Values teamwork"}),
    "graduation": frozenset({"Expected graduation"}),
    "publication": frozenset({"Curieux Academic Journal publication"}),
    "drawing": frozenset({"Digital drawing"}),
    "gaming_reason": frozenset({"Gaming as relaxation", "Gaming connects with peers"}),
    "additional_hobbies": frozenset({"Fun fact: cosplay", "3D printer interest", "Founding clubs", "Tactile Book Project"}),
}


@dataclass(frozen=True)
class EvidenceCapability:
    """A positive authorization for a relation/object pair."""

    key: str
    domain: str
    relation: str
    object_types: frozenset[str]
    titles: frozenset[str] = frozenset()
    categories: frozenset[str] = frozenset()
    evidence_kind: str = "exact_fact"


def _capability(contract: SemanticContract, intent: Any) -> EvidenceCapability | None:
    relation = contract.relation
    object_type = contract.object_type
    domain = contract.domain or "unresolved"
    entities = set(getattr(intent, "entities", ()))

    # These are intentionally absent: related facts must not authorize a
    # missing favorite athlete, price, or unsupported paper limitation.
    if relation == "limitations":
        return None
    if domain == "sports" and object_type == "athlete" and relation in {"favorite", "likes"}:
        return None
    focused_keys = {item[0] for item in FOCUSED_SUBJECTS}
    if entities and any(entity in focused_keys or entity in CONTRACT_FOCUSED_TITLES for entity in entities):
        return EvidenceCapability("focused", domain, relation, frozenset({object_type}), evidence_kind="explanatory_evidence")
    if domain == "photography" and relation == "favorite" and object_type == "photograph":
        return EvidenceCapability(
            "curated_photo_selection", domain, relation, frozenset({"photograph"}),
            evidence_kind="documented_selection",
        )

    if domain == "photography" and relation == "uses" and object_type in {"camera", "lens"}:
        return EvidenceCapability("photography_equipment", domain, relation, frozenset({object_type}), frozenset({"Photography and videography"}), frozenset({"hobbies"}))
    if domain == "photography" and relation == "photographed_in" and object_type == "place":
        return EvidenceCapability("photographed_locations", domain, relation, frozenset({"place"}), categories=frozenset({"travel", "hobbies"}))
    if domain == "sports" and relation in {"supports", "favorite"} and object_type == "team":
        return EvidenceCapability("football_team_preference", domain, relation, frozenset({"team"}), frozenset({"Favorite football team"}), frozenset({"favorites"}))
    if domain == "sports" and relation == "playing_position" and object_type == "position":
        return EvidenceCapability("sports_positions", domain, relation, frozenset({"position"}), frozenset({"Sports positions"}), frozenset({"favorites", "sport"}))
    if domain == "sports" and relation in {"started", "current_participation", "lists", "count"}:
        return EvidenceCapability("sports_profile", domain, relation, frozenset({"sport", "position", "unresolved"}), frozenset({"Sports"}), frozenset({"sport", "sports"}))

    if domain == "games" and relation == "rank" and "apex_rank" in entities:
        return EvidenceCapability("apex_rank", domain, relation, frozenset({"rank"}), frozenset({"apex_rank"}), frozenset({"apex_rank"}))
    if domain == "games" and relation == "reason" and object_type == "explanation":
        return EvidenceCapability("gaming_reason", domain, relation, frozenset({"explanation"}), frozenset({"Gaming as relaxation", "Gaming connects with peers"}), frozenset({"gaming", "hobby", "personality"}), evidence_kind="explanatory_evidence")

    if domain == "music" and relation in {"favorite", "likes", "listens_to", "lists"} and object_type in {"song", "artist", "band", "unresolved"}:
        return EvidenceCapability("favorite_music", domain, relation, frozenset({object_type}), frozenset({"Favorite music"}), frozenset({"favorites"}))
    if domain == "games" and relation in {"favorite", "likes", "lists", "count"}:
        return EvidenceCapability("favorite_games", domain, relation, frozenset({"game", "unresolved"}), frozenset({"Favorite games"}), frozenset({"favorites", "gaming"}))

    if domain == "projects" and relation == "learned_by" and object_type == "method":
        return EvidenceCapability("coding_learning", domain, relation, frozenset({"method"}), frozenset({"Self-taught programming"}), frozenset({"education", "projects_skills"}))
    if domain == "projects" and "programming_languages" in entities:
        return EvidenceCapability("programming_languages", domain, relation, frozenset({object_type}), frozenset({"Programming languages"}), frozenset({"projects_skills"}))
    if domain == "hobbies" and object_type == "instrument" and relation in {"lists", "current_participation", "started", "learned_by", "method"}:
        return EvidenceCapability("instrument", domain, relation, frozenset({object_type}), frozenset({"Electric guitar"}), frozenset({"hobbies", "hobby"}))
    if domain == "hobbies" and object_type == "unresolved" and relation in {"lists", "count"}:
        return EvidenceCapability("hobbies_overview", domain, relation, frozenset({"unresolved"}), categories=frozenset({"hobbies", "hobby"}))
    if domain == "projects" and relation == "created" and object_type == "project":
        return EvidenceCapability("projects", domain, relation, frozenset({"project"}), frozenset({"Projects & Skills"}), frozenset({"projects_skills"}))
    if domain == "projects" and relation in {"lists", "count"}:
        return EvidenceCapability("projects", domain, relation, frozenset({"project", "unresolved"}), frozenset({"Projects & Skills"}), frozenset({"projects_skills"}))

    if domain == "favorites":
        favorite_titles = {
            "anime": "Favorite anime",
            "movie": "Favorite movie",
            "book": "Favorite book series",
            "place": "Favorite place",
            "school_subject": "Favorite school subject",
        }
        title = favorite_titles.get(object_type)
        if title and relation == "favorite":
            return EvidenceCapability(f"favorite_{object_type}", domain, relation, frozenset({object_type}), frozenset({title}), frozenset({"favorites"}))
        if "favorites_overview" in entities:
            return EvidenceCapability("favorites_overview", domain, relation, frozenset({object_type}), categories=frozenset({"favorites"}))
        if relation == "lists" and object_type == "unresolved":
            return EvidenceCapability("favorites_overview", domain, relation, frozenset({"unresolved"}), categories=frozenset({"favorites"}))

    if domain == "videos" and relation in {"lists", "created"}:
        return EvidenceCapability("videos_overview", domain, relation, frozenset({"video", "unresolved"}), categories=frozenset({"video"}))

    if domain == "education" and relation == "studies" and object_type == "school_subject":
        return EvidenceCapability("education_subjects", domain, relation, frozenset({"school_subject"}), frozenset({"Education", "HL subjects"}), frozenset({"education"}))
    if domain == "education" and relation == "favorite" and object_type == "school_subject":
        return EvidenceCapability("favorite_school_subject", domain, relation, frozenset({"school_subject"}), frozenset({"Favorite school subject"}), frozenset({"favorites"}))
    if domain == "education" and relation == "reason" and object_type == "explanation":
        return EvidenceCapability("subject_preference_reason", domain, relation, frozenset({"explanation"}), frozenset({"Physics teacher"}), frozenset({"education"}))

    if domain == "travel" and relation == "visited" and object_type == "place":
        return EvidenceCapability("travel_history", domain, relation, frozenset({"place"}), frozenset({"Travel"}), frozenset({"travel"}))
    if domain == "travel" and relation == "favorite" and object_type == "place":
        return EvidenceCapability("favorite_place", domain, relation, frozenset({"place"}), frozenset({"Favorite place"}), frozenset({"travel", "favorites"}))

    if domain == "writing" and relation == "method" and object_type == "paper" and "histology_paper" in entities:
        return EvidenceCapability("histology_paper_method", domain, relation, frozenset({"paper"}), frozenset({"Histology classification research paper"}), frozenset({"writing"}))
    if domain == "writing" and relation in {"lists", "count"}:
        return EvidenceCapability("writing_overview", domain, relation, frozenset({"paper", "unresolved"}), frozenset({"Writing & Essays"}), frozenset({"writing"}))

    focused_keys = {item[0] for item in FOCUSED_SUBJECTS}
    if entities and any(entity in focused_keys for entity in entities):
        return EvidenceCapability("focused", domain, relation, frozenset({object_type}), evidence_kind="explanatory_evidence")

    # Preserve positive access to the remaining curated overview domains.
    overview_titles = {
        "bio": ("bio", "Personal Bio"),
        "personality": ("personality", "Personality & Values"),
        "videos": ("video", "Videos"),
        "hobbies": ("hobbies", "Hobbies & Interests"),
        "achievements": ("achievements", "Achievements & Awards"),
        "contact": ("contact", "Contact & Links"),
    }
    if relation in {"lists", "count", "describes", "likes"} and domain in overview_titles:
        category, title = overview_titles[domain]
        titles = frozenset({title}) if domain not in {"bio", "personality", "contact", "videos"} else frozenset()
        return EvidenceCapability(f"{domain}_overview", domain, relation, frozenset({object_type}), titles, frozenset({category}))
    if relation in {"lists", "count"} and domain == "education":
        return EvidenceCapability("education_overview", domain, relation, frozenset({object_type, "unresolved"}), frozenset({"Education"}), frozenset({"education"}))
    return None


def _curated_photo_chunk() -> dict:
    try:
        photos = json.loads(config.CONTENT_EXPORT_PATH.read_text(encoding="utf-8")).get("photos", [])
        count = sum(bool(photo.get("featured")) for photo in photos)
    except (OSError, ValueError, TypeError):
        count = 0
    return {
        "chunk_id": "content_curated_photo_picks",
        "text": f"Curated photography picks: {count} featured photo picks, rather than one documented favorite photograph.",
        "metadata": {"category": "photo_selection", "title": "Curated photography picks", "source": "src/data/content.ts"},
    }


def eligible_evidence(contract: SemanticContract, intent: Any, chunks: list[dict]) -> list[dict]:
    """Filter retrieved candidates by capability before a formatter sees them."""

    capability = _capability(contract, intent)
    if capability is None:
        return []
    if capability.key == "curated_photo_selection":
        chunk = _curated_photo_chunk()
        chunk["score"] = 1.0
        return [chunk]
    focused = focused_chunks(tuple(getattr(intent, "entities", ())), chunks)
    if capability.key == "focused":
        titles = set().union(*(CONTRACT_FOCUSED_TITLES.get(entity, frozenset()) for entity in getattr(intent, "entities", ())))
        if titles:
            return [chunk for chunk in chunks if chunk.get("metadata", {}).get("title") in titles]
        return focused or []
    if focused and capability.titles.intersection({c.get("metadata", {}).get("title", "") for c in focused}):
        chunks = focused
    filtered = [
        chunk for chunk in chunks
        if (not capability.titles or chunk.get("metadata", {}).get("title") in capability.titles)
        and (not capability.categories or chunk.get("metadata", {}).get("category") in capability.categories)
    ]
    if not filtered and capability.categories and all(
        not chunk.get("metadata", {}).get("title") for chunk in chunks
    ):
        # Low-level callers may provide a deliberately small fixture with a
        # category but no generated heading. A known category is still a
        # positive eligibility signal; public corpus chunks retain the title
        # check above.
        filtered = [
            chunk for chunk in chunks
            if chunk.get("metadata", {}).get("category") in capability.categories
        ]
    return filtered


def capability_for(contract: SemanticContract, intent: Any) -> EvidenceCapability | None:
    """Expose the reviewed capability for diagnostics and answer gating."""

    return _capability(contract, intent)


def focused_subjects(question: str) -> tuple[str, ...]:
    return tuple(entity for entity, pattern, *_ in FOCUSED_SUBJECTS if re.search(pattern, question, re.IGNORECASE))


def focused_topic(question: str) -> str | None:
    return next((topic for _, pattern, topic, *_ in FOCUSED_SUBJECTS if re.search(pattern, question, re.IGNORECASE)), None)


def focused_chunks(entities: tuple[str, ...], chunks: list[dict]) -> list[dict] | None:
    for entity, _, _, title, category in FOCUSED_SUBJECTS:
        if entity in entities:
            titles = {title, "Ice hockey description"} if entity == "hockey_lessons" else {title}
            return [chunk for chunk in chunks if chunk.get("metadata", {}).get("title") in titles
                    and chunk.get("metadata", {}).get("category") == category]
    return None


def focused_retrieval_query(entities: tuple[str, ...]) -> str | None:
    return next((title for entity, _, _, title, _ in FOCUSED_SUBJECTS if entity in entities), None)


def subject_name(entity: str) -> str | None:
    return next((title for key, _, _, title, _ in FOCUSED_SUBJECTS if key == entity), None)
