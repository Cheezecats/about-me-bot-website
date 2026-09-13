from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from backend import config
from backend.generation.intent import QueryIntent, detect_intent
from backend.generation.contracts import summary_can_answer
from backend.generation.evidence import focused_chunks, GENERATIVE_ENTITIES

STRUCTURED_SUMMARY_TITLES = frozenset(
    {
        "Achievements & Awards",
        "Education",
        "Electric guitar",
        "Favorite games",
        "Favorite anime",
        "Anime (top favorites)",
        "Favorite movie",
        "Favorite book series",
        "Favorite place",
        "Favorite school subject",
        "IDE/editor usage",
        "Favorite food",
        "Favorite music",
        "Favorite season",
        "Hobbies & Interests",
        "Photography and videography",
        "Projects & Skills",
        "Programming languages",
        "Sports",
        "Travel",
        "Writing & Essays",
    }
)
FACTS_PATH = config.DATA_DIR / "profile_facts.json"

_SUMMARY_TOPICS: dict[str, frozenset[str]] = {
    "Achievements & Awards": frozenset({"achievements"}),
    "Education": frozenset({"education"}),
    "Electric guitar": frozenset({"hobbies"}),
    "Favorite games": frozenset({"games"}),
    "Favorite anime": frozenset({"favorites"}),
    "Anime (top favorites)": frozenset({"favorites"}),
    "Favorite movie": frozenset({"favorites"}),
    "Favorite book series": frozenset({"favorites"}),
    "Favorite place": frozenset({"favorites", "travel"}),
    "Favorite school subject": frozenset({"favorites", "education"}),
    "IDE/editor usage": frozenset({"favorites"}),
    "Favorite food": frozenset({"food"}),
    "Favorite music": frozenset({"music"}),
    "Favorite season": frozenset({"season"}),
    "Hobbies & Interests": frozenset({"hobbies"}),
    "Photography and videography": frozenset({"photography"}),
    "Projects & Skills": frozenset({"projects"}),
    "Programming languages": frozenset({"projects", "education"}),
    "Sports": frozenset({"sports"}),
    "Travel": frozenset({"travel"}),
    "Writing & Essays": frozenset({"writing"}),
}


@lru_cache(maxsize=1)
def load_profile_facts(path: Path = FACTS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_structured_summary(chunk: dict) -> bool:
    return chunk.get("metadata", {}).get("title", "") in STRUCTURED_SUMMARY_TITLES


def _summary_matches_intent(title: str, intent: QueryIntent) -> bool:
    """Prevent a retrieved summary from answering a different topic."""

    contract = intent.contract
    topic = intent.topic or (contract.domain if contract is not None else None)

    if title == "Favorite season" and topic == "preferences" and "dislikes" in intent.entities:
        return True
    required_entity = {
        "Favorite anime": "anime",
        "Anime (top favorites)": "anime",
        "Favorite movie": "movie",
        "Favorite book series": "book",
        "Favorite place": "place",
        "Favorite school subject": "school_subject",
        "IDE/editor usage": "ide",
    }.get(title)
    if required_entity and required_entity not in intent.entities and not (
        intent.contract is not None and intent.contract.object_type == required_entity
    ):
        return False
    return topic in _SUMMARY_TOPICS.get(title, frozenset())


def extractive_answer(chunk: dict) -> str:
    title = chunk.get("metadata", {}).get("title", "")
    text = chunk.get("text", "").strip()
    for prefix in (f"## {title} ", f"# {title} "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    if title == "Favorite games":
        return f"James's favorite games: {text}"
    return text


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _format_games(facts: dict, intent: QueryIntent, question: str) -> str:
    games = facts["favorite_games"]
    if re.search(r"\b(?:except|other than|excluding)\b.*\bapex\b", question, re.IGNORECASE):
        remaining = [game for game in games["competitive"] + games["non_competitive"] if game != "Apex Legends"]
        return "Other documented favorites include:\n\n" + _bullets(remaining)
    if intent.negated and "apex_game" in intent.entities:
        return "No — Apex Legends is one of James's competitive favorite games."
    competitive_only = "competitive" in intent.entities or "competitive" in intent.qualifiers
    noncompetitive_only = "non-competitive" in intent.entities or "non-competitive" in intent.qualifiers
    if intent.question_operator == "count":
        selected = games["non_competitive"] if noncompetitive_only else games["competitive"] if competitive_only else games["competitive"] + games["non_competitive"]
        return f"His profile lists {len(selected)} favorite games: " + ", ".join(selected) + "."
    if competitive_only and not noncompetitive_only:
        if intent.quantity == "one":
            return f"One of James's competitive favorites is {games['competitive'][0]}."
        return "James's competitive favorites are:\n\n" + _bullets(games["competitive"])
    if noncompetitive_only and not competitive_only:
        if intent.quantity == "one":
            return f"One of James's non-competitive favorites is {games['non_competitive'][0]}."
        return "James's non-competitive favorites are:\n\n" + _bullets(games["non_competitive"])
    if intent.quantity == "singular" and "favorite" in intent.qualifiers:
        return (
            "James's favorite games are:\n\n"
            "- The profile does not rank one single favorite game.\n"
            + "- Competitive: " + ", ".join(games["competitive"])
            + "\n- Non-competitive: " + ", ".join(games["non_competitive"])
        )
    return (
        "James's favorite games are:\n\n"
        + "- Competitive: "
        + ", ".join(games["competitive"])
        + "\n- Non-competitive: "
        + ", ".join(games["non_competitive"])
    )


def _format_music(facts: dict, intent: QueryIntent) -> str:
    music = facts["favorite_music"]
    contract = intent.contract
    contract_object = contract.object_type if contract is not None else None
    if "music_overview" in intent.entities:
        return (
            f"James's current favorite song is \"{music['song']}\" by {music['song_artist']}. "
            f"His favorite artist is {music['artist']}; favorite bands include {', '.join(music['bands'])}."
        )
    if "band" in intent.entities and "artist" in intent.entities:
        return (
            f"James's favorite artist is {music['artist']}; his favorite bands are "
            f"{', '.join(music['bands'])}."
        )
    if contract_object == "artist" or ("artist" in intent.entities and "song" not in intent.entities and "band" not in intent.entities):
        return f"James's favorite artist is {music['artist']}."
    if contract_object == "band" or ("band" in intent.entities and "song" not in intent.entities):
        return f"James's favorite bands are {', '.join(music['bands'])}."
    if "band" in intent.entities and "song" not in intent.entities:
        if intent.quantity == "singular" and "favorite" in intent.qualifiers:
            return (
                f"James's favorite bands are {', '.join(music['bands'])}; the profile does not rank one above the other."
            )
        return f"James's favorite bands are {', '.join(music['bands'])}."
    if contract_object == "song" or ("song" in intent.entities and "band" not in intent.entities and "artist" not in intent.entities):
        return f"James's current favorite song is \"{music['song']}\" by {music['song_artist']}."
    if "artist" in intent.entities and "song" not in intent.entities and "band" not in intent.entities:
        return f"James's favorite artist is {music['artist']}."
    return (
        f"James's current favorite song is \"{music['song']}\" by {music['song_artist']}. "
        f"His favorite artist is {music['artist']}; favorite bands include {', '.join(music['bands'])}."
    )


def _format_favorite_anime(facts: dict) -> str:
    anime = facts["favorite_anime"]
    answer = "James's favorite anime include:\n\n" + _bullets(anime["top"])
    if anime.get("also_loves"):
        answer += "\n\nHe also loves " + ", ".join(anime["also_loves"]) + "."
    return answer


def _format_favorite_movie(facts: dict) -> str:
    movie = facts["favorite_movie"]
    return (
        "James's favorite movies are:\n\n"
        f"- Hollywood: {movie['hollywood']}\n"
        f"- Non-Hollywood: {movie['non_hollywood']}"
    )


def _format_favorite_book(facts: dict) -> str:
    book = facts["favorite_book_series"]
    return f"James's favorite book series is {book['title']} by {book['author']}. {book['detail']}"


def _format_favorite_place(facts: dict) -> str:
    return f"James's favorite place is {facts['favorite_place']}."


def _format_favorite_school_subject(facts: dict) -> str:
    return f"James's favorite school subject is {facts['favorite_school_subject']}."


def _format_ide_usage(facts: dict) -> str:
    return "James uses several IDEs and editors:\n\n" + _bullets(facts["ide_editors"])


def _format_favorites_overview(facts: dict) -> str:
    games = facts["favorite_games"]
    music = facts["favorite_music"]
    anime = facts["favorite_anime"]
    return (
        "James's documented favorites include:\n\n"
        f"- Games: {', '.join(games['competitive'][:3])}\n"
        f"- Anime: {', '.join(anime['top'][:3])}\n"
        f"- Song: {music['song']}\n"
        f"- Artist: {music['artist']}\n"
        f"- Food: {facts['favorite_food']['primary']}\n"
        f"- Season: {facts['favorite_season']['primary']}\n"
        f"- Place: {facts['favorite_place']}"
    )


def _format_photography_overview(facts: dict) -> str:
    photography = facts["photography"]
    return (
        f"James is an active photographer and videographer. His primary camera is a {photography['primary_camera']}; "
        f"he also uses a {photography['additional_cameras'][0]} and an {photography['additional_cameras'][1]}. "
        "He has photographed in Hokkaido, Tuscany and Athens."
    )


def _format_sports(facts: dict, intent: QueryIntent, question: str) -> str:
    sports = facts["sports"]
    started = [sport for sport in sports if "started" in sport]
    if intent.question_operator == "count":
        return f"James plays {len(sports)} sports: skiing, ice hockey, tennis, floorball, and soccer."
    sport_entities = {
        "sport_skiing": "skiing",
        "sport_ice_hockey": "ice hockey",
        "sport_tennis": "tennis",
        "sport_floorball": "floorball",
        "sport_soccer": "soccer",
    }
    named = [sport for sport in sports if any(entity in intent.entities and sport["name"] == name for entity, name in sport_entities.items())]
    if len(named) >= 2 and intent.temporal_relation in {"before", "after"}:
        ordered = sorted(named, key=lambda sport: question.lower().find(sport["name"].replace("ice ", "")))
        if any("started" not in sport for sport in ordered):
            return config.REFUSAL_MESSAGE
        first, second = ordered[:2]
        matches = first["started"] < second["started"] if intent.temporal_relation == "before" else first["started"] > second["started"]
        return f"{'Yes' if matches else 'No'} — James started {first['name']} in {first['started']} and {second['name']} in {second['started']}."
    after = re.search(r"\bafter\s+(20\d{2})\b", question, re.IGNORECASE)
    if after:
        year = int(after.group(1))
        selected = [sport for sport in started if sport["started"] > year]
        return (f"Sports with documented start dates after {year}:\n\n" + _bullets([f"{sport['name'].title()} ({sport['started']})" for sport in selected])
                if selected else f"His profile doesn't list a sport with a start date after {year}.")
    if intent.relation == "started" and named and intent.temporal_relation not in {"before", "after"} and re.search(r"\b(?:start|started|begin|began|take\s+up)\b", question, re.IGNORECASE):
        for entity, name in sport_entities.items():
            if entity in intent.entities:
                sport = next((item for item in started if item["name"] == name), None)
                if sport is None:
                    return config.REFUSAL_MESSAGE
                activity = "skiing" if name == "skiing" else f"playing {name}"
                return f"James started {activity} in {sport['started']}."
    if "best_sport" in intent.entities:
        return (
            "James plays skiing, ice hockey, tennis, floorball, and soccer, but his public profile "
            "does not identify one as his best sport."
        )
    if intent.before_year is not None:
        selected = [sport for sport in started if sport["started"] < intent.before_year]
        if not selected:
            return f"James did not list a sport that he started before {intent.before_year}."
        return (
            f"Sports James started before {intent.before_year}:\n\n"
            + _bullets([f"{sport['name'].title()} ({sport['started']})" for sport in selected])
        )
    if intent.temporal_relation == "before" and len(named) == 1:
        target = named[0]
        earlier = [sport for sport in started if sport["started"] < target["started"]]
        if earlier:
            return f"James started {earlier[0]['name']} before {target['name']}."
        return config.REFUSAL_MESSAGE
    if intent.comparison and re.search(r"\b(?:first|earliest|started first)\b", question, re.IGNORECASE):
        first = min(started, key=lambda sport: sport["started"])
        return f"James started {first['name']} first, in {first['started']}."
    if re.search(r"\bposition", question, re.IGNORECASE):
        selected = named or [sport for sport in sports if "position" in sport]
        if any("position" not in sport for sport in selected):
            return config.REFUSAL_MESSAGE
        return "James plays " + " and ".join(f"{sport['name']} as a {sport['position']}" for sport in selected) + "."
    if named:
        return " ".join(
            f"James {'started skiing' if sport['name'] == 'skiing' else 'started playing ' + sport['name']} in {sport['started']}"
            + (f" and plays as a {sport['position']}" if "position" in sport else "") + "."
            if "started" in sport else f"James plays {sport['name']} as a {sport['position']}."
            for sport in named
        )
    return "James's sports include:\n\n" + _bullets(
        [f"{sport['name'].title()}" + (f" (started {sport['started']})" if "started" in sport else "") for sport in sports]
    )


def _format_projects(facts: dict, intent: QueryIntent, question: str) -> str:
    if "programming_languages" in intent.entities:
        return "James works with:\n\n" + _bullets(facts["programming_languages"])
    if "ai" in intent.entities:
        projects = [project["name"] for project in facts["projects"] if "ai" in project["tags"]]
        if intent.question_operator == "count":
            return f"The project overview lists {len(projects)} projects involving AI or machine learning."
        if intent.quantity == "one":
            return f"One AI-related project is the {projects[0]}."
        return "Projects involving AI or machine learning:\n\n" + _numbered(projects)
    if intent.ordinal is not None and intent.ordinal <= len(facts["projects"]):
        project = facts["projects"][intent.ordinal - 1]
        return f"Project {intent.ordinal}: {project['name']}."
    if intent.question_operator == "count":
        return f"The curated overview lists {len(facts['projects'])} projects. This is a selection of James's work, not a count of everything he has ever built."
    if intent.quantity == "one":
        return f"One of James's projects is his {facts['projects'][0]['name']}."
    return "James's projects include:\n\n" + _numbered([project["name"] for project in facts["projects"]])


def _format_travel(facts: dict, intent: QueryIntent) -> str:
    travel = facts["travel"]
    if "training" in intent.entities and "visited" not in intent.entities:
        return "Through ice hockey, James trained or competed in:\n\n" + _bullets(travel["hockey_training_or_competition"])
    if "visited" in intent.entities and "training" not in intent.entities:
        return "James has visited:\n\n" + _bullets(travel["visited"])
    return (
        "James has visited:\n\n"
        + _bullets(travel["visited"])
        + "\n\nThrough ice hockey, he also trained or competed in:\n\n"
        + _bullets(travel["hockey_training_or_competition"])
    )


def _body_without_heading(chunk: dict) -> str:
    return extractive_answer(chunk).strip()


def _format_destination(chunks: list[dict], intent: QueryIntent) -> str | None:
    """Turn a destination follow-up into a focused answer, not the travel index."""

    destination_titles = {
        "travel_italy": "Italy (Tuscany)",
        "travel_greece": "Greece (Athens, Ionian Sea)",
        "travel_japan": "Japan (Hokkaido)",
        "travel_xinjiang": "Xinjiang, China",
        "travel_russia": "Russia",
        "travel_united_states": "United States (Los Angeles)",
    }
    for entity, title in destination_titles.items():
        if entity not in intent.entities:
            continue
        chunk = next((item for item in chunks if item.get("metadata", {}).get("title") == title), None)
        if chunk is not None:
            answers = {
                "travel_italy": "James travelled to Italy, specifically Tuscany, where he photographed the landscape at sunset, capturing black and orange tones.",
                "travel_greece": "James travelled to Greece, filmed an 8K video about Athens and the Ionian Sea, and photographed the National Observatory of Athens.",
                "travel_japan": "James travelled to Japan, specifically Hokkaido, where he filmed the 4K video “Japan Winter” and photographed snowy night scenes.",
                "travel_xinjiang": "James filmed a video in Xinjiang in 2026 using a Nikon Z8 and an iPhone 13 Pro, then posted it on Bilibili.",
                "travel_russia": "James competed in international ice hockey matches in Russia with local teams.",
                "travel_united_states": "James trained in ice hockey in Los Angeles with coaches from the Los Angeles Kings.",
            }
            return answers[entity]
    return None


def _format_additional_hobbies(chunks: list[dict]) -> str | None:
    """Summarize less-central interests for contextual questions like 'what else?'"""

    by_title = {chunk.get("metadata", {}).get("title"): chunk for chunk in chunks}
    required = {
        "Fun fact: cosplay",
        "3D printer interest",
        "Founding clubs",
        "Tactile Book Project",
    }
    if not required.issubset(by_title):
        return None
    return (
        "Beyond James's main hobbies, he has also mentioned:\n\n"
        "- doing cosplay\n"
        "- wanting a 3D printer as an extension of his 3D modeling and engineering interests\n"
        '- co-founding the "InnoviDesign: Engineering & SolidWorks Club"\n'
        "- participating in a tactile picture-book project for visually impaired children"
    )


def _has_category(chunks: list[dict], category: str) -> bool:
    return any(chunk.get("metadata", {}).get("category") == category for chunk in chunks)


def _format_profile_answer(question: str, chunks: list[dict], intent: QueryIntent, facts: dict) -> str | None:
    """Answer high-value public-profile fields without relying on free-form generation."""

    if intent.relation == "favorite" and intent.object_type == "photograph":
        photo_chunk = next(
            (chunk for chunk in chunks if chunk.get("metadata", {}).get("title") == "Curated photography picks"),
            None,
        )
        if photo_chunk is not None:
            match = re.search(r"\b(\d+)\s+featured", photo_chunk.get("text", ""))
            if match:
                return (
                    f"James has {match.group(1)} curated photo picks, rather than one documented favorite photograph. "
                    "You can explore the selection in his photography gallery."
                )

    if "camera" in intent.entities and "lens" in intent.entities and any(
        chunk.get("metadata", {}).get("title") == "Photography and videography" for chunk in chunks
    ):
        photography = facts["photography"]
        return (
            f"James's primary camera is a {photography['primary_camera']}; he also uses a "
            f"{photography['additional_cameras'][0]} and an {photography['additional_cameras'][1]}. "
            f"His lenses are a {photography['lenses'][0]} and a {photography['lenses'][1]}."
        )

    contract = intent.contract
    if contract is not None:
        if contract.domain == "photography" and contract.relation == "uses" and contract.object_type in {"camera", "lens"} and any(
            chunk.get("metadata", {}).get("title") == "Photography and videography" for chunk in chunks
        ):
            photography = facts["photography"]
            if contract.object_type == "lens":
                return f"James uses a {photography['lenses'][0]} lens and a {photography['lenses'][1]} lens."
            return f"James's primary camera is a {photography['primary_camera']}. He also uses a {photography['additional_cameras'][0]} and an {photography['additional_cameras'][1]}."
        if contract.domain == "projects" and contract.relation == "learned_by" and contract.object_type == "method":
            coding = facts["coding_learning"]
            return f"James learned {coding['language']} independently during {coding['time']}. He also works with {', '.join(coding['other_languages'][:-1])}, and {coding['other_languages'][-1]}."
        if contract.domain == "education" and contract.relation == "studies" and contract.object_type == "school_subject":
            return "James's current Higher Level subjects are:\n\n" + _bullets(facts["education"]["higher_level_subjects"])
        if contract.domain == "education" and contract.relation == "favorite" and contract.object_type == "school_subject":
            return _format_favorite_school_subject(facts)
        if contract.domain == "travel" and contract.relation == "visited" and contract.object_type == "place":
            return "James has visited:\n\n" + _bullets(facts["travel"]["visited"])
        if contract.domain == "travel" and contract.relation == "favorite" and contract.object_type == "place":
            return _format_favorite_place(facts)
        if contract.domain == "photography" and contract.relation == "photographed_in" and contract.object_type == "place":
            return "Examples of places James has photographed include:\n\n" + _bullets(facts["photographed_locations"])
        if contract.domain == "games" and contract.relation == "reason" and contract.object_type == "explanation":
            return facts["gaming_reasons"]["answer"]
        if contract.domain == "favorites" and contract.relation == "lists" and contract.object_type == "unresolved":
            return _format_favorites_overview(facts)
        if contract.domain == "writing" and contract.relation == "method" and contract.object_type == "paper":
            paper = next((item for item in chunks if item.get("metadata", {}).get("title") == "Histology classification research paper"), None)
            if paper is not None:
                return _body_without_heading(paper)
        if contract.domain == "sports" and contract.relation == "started" and contract.object_type == "sport":
            return _format_sports(facts, intent, question)

    if (intent.topic == "bio" or (contract is not None and contract.domain == "bio")) and _has_category(chunks, "bio"):
        profile = facts["public_profile"]
        return (
            f"{profile['name']}'s public profile describes him as a {profile['age']}-year-old student living in {profile['location']}. "
            f"He describes himself as a {', '.join(profile['roles'])}; his tagline is “{profile['tagline']}.”"
        )
    if (intent.topic == "personality" or (contract is not None and contract.domain == "personality")) and _has_category(chunks, "personality"):
        if "aspirations" in intent.entities:
            return (
                "James's documented future academic interests include engineering, semiconductors and aerospace, "
                "and quantum computing. He has applied to related programs at Purdue, the University of Michigan, and Penn."
            )
        return facts["personality_summary"]
    if "favorites_overview" in intent.entities and _has_category(chunks, "favorites"):
        return _format_favorites_overview(facts)
    if "photographed_places" in intent.entities and (
        _has_category(chunks, "travel")
        or _has_category(chunks, "photography")
        or any(
            chunk.get("metadata", {}).get("title") == "Photography and videography"
            for chunk in chunks
        )
    ):
        return "Examples of places James has photographed include:\n\n" + _bullets(facts["photographed_locations"])
    if "instrument" in intent.entities and _has_category(chunks, "hobbies"):
        guitar = facts["guitar"]
        if intent.temporal_relation == "continuation":
            return f"Yes — James's public profile lists electric guitar among his hobbies. He started in {guitar['started']}."
        if intent.temporal_relation == "cessation":
            return (
                "No — James's profile says he plays electric guitar and started in 2025; "
                "it does not document that he stopped."
            )
        if re.search(r"\b(?:learn|learned|learning|self-taught|method)\b", question, re.IGNORECASE):
            return f"James learned electric guitar through self-taught study using online tutorials."
        if re.search(r"\b(?:genre|genres|kind|type)\b", question, re.IGNORECASE):
            return f"James focuses on {', '.join(guitar['genres'][:-1])}, and {guitar['genres'][-1]} on electric guitar."
        if re.search(r"\b(?:when|what year)\b", question, re.IGNORECASE) and re.search(
            r"\b(?:start|started|begin|began)\b", question, re.IGNORECASE
        ):
            return f"James started playing electric guitar in {guitar['started']}."
    if intent.relation in {"supports", "favorite"} and intent.object_type == "team" and _has_category(chunks, "favorites"):
        team = facts["favorite_football_team"]
        return f"James's favorite football team is {team['team']}, {team['detail']}."
    if intent.relation == "playing_position" and intent.object_type == "position":
        if re.search(r"\b(?:ice\s+)?hockey\b", question, re.IGNORECASE) and _has_category(chunks, "favorites"):
            return "James started playing ice hockey in 2015 and plays as a defender."
        if re.search(r"\bsoccer\b", question, re.IGNORECASE) and _has_category(chunks, "favorites"):
            return "James plays soccer as a forward."
        if _has_category(chunks, "favorites") or _has_category(chunks, "sports"):
            return "James plays ice hockey as a defender and soccer as a forward."
    if intent.relation == "created" and intent.object_type == "project" and intent.constraints.get("technology") == "python":
        python_projects = [
            project["name"] for project in facts["projects"] if "python" in {tag.lower() for tag in project.get("tags", [])}
        ]
        if python_projects:
            return "Projects James built with Python include:\n\n" + _bullets(python_projects)
    if intent.topic == "sports" and _has_category(chunks, "sport") and re.search(
        r"\b(?:ice\s+)?hockey\b", question, re.IGNORECASE
    ):
        return "James started playing ice hockey in 2015 and plays as a defender."
    if (intent.topic == "contact" or (contract is not None and contract.domain == "contact")) and _has_category(chunks, "contact"):
        by_title = {chunk.get("metadata", {}).get("title", ""): chunk for chunk in chunks}
        def contact_value(title: str) -> str:
            chunk = by_title.get(title)
            return _body_without_heading(chunk) if chunk is not None else "Not listed"

        youtube = contact_value("YouTube channel")
        github = contact_value("GitHub profile")
        website = contact_value("Personal website")
        email = contact_value("Public email")
        if "youtube" in intent.entities:
            return f"James's YouTube channel is {youtube}."
        if "github" in intent.entities:
            return f"James's GitHub profile is {github}."
        if "website" in intent.entities:
            return f"James's personal website is {website}."
        return (
            "James's public contact links are:\n\n"
            f"- Email: {email}\n"
            f"- YouTube: {youtube}\n"
            f"- GitHub: {github}\n"
            f"- Website: {website}"
        )
    if intent.topic == "videos" and _has_category(chunks, "video") and not {
        "video_greece", "video_japan", "video_xinjiang"
    }.intersection(intent.entities):
        videos = [chunk for chunk in chunks if chunk.get("metadata", {}).get("category") == "video"]
        if not videos:
            return None
        formatted: list[str] = []
        for chunk in videos:
            title = chunk.get("metadata", {}).get("title", "Video")
            body = _body_without_heading(chunk)
            year = re.search(r"\b(20\d{2})\b", body)
            quality = re.search(r"\b(\dK(?:60)?)\b", body, re.IGNORECASE)
            detail = re.sub(
                r"^James filmed a video titled ['\"]?[^.'\"]+['\"]?\s*\([^)]*\)\.\s*",
                "",
                body,
                flags=re.IGNORECASE,
            )
            detail = re.sub(
                r"^Filmed \d{4}, captured \dK(?:60)?(?: on the [^.]+)?\.\s*",
                "",
                detail,
                flags=re.IGNORECASE,
            ).strip()
            detail = re.sub(r"\bmy experience\b", "James's experience", detail, flags=re.IGNORECASE)
            label = title
            if quality or year:
                label += f" ({quality.group(1).upper() if quality else ''}{', ' if quality and year else ''}{year.group(1) if year else ''})"
            formatted.append(f"{label} — {detail}")
        return "James has made these videos:\n\n" + _bullets(formatted)
    if "graduation" in intent.entities and _has_category(chunks, "education"):
        return f"James is expected to graduate in {facts['education']['expected_graduation']}."
    if "higher_level_subjects" in intent.entities and _has_category(chunks, "education"):
        return "James's IBDP Higher Level subjects are:\n\n" + _bullets(facts["education"]["higher_level_subjects"])
    if "drawing" in intent.entities and (_has_category(chunks, "hobbies") or _has_category(chunks, "hobby")):
        return "Yes — James does digital drawing as a creative outlet."
    if "publication" in intent.entities and _has_category(chunks, "achievements"):
        return "James published a research paper on large language models in the Curieux Academic Journal."
    if "anime_influence" in intent.entities:
        anime_chunk = next(
            (chunk for chunk in chunks if chunk.get("metadata", {}).get("title") == "Anime influence"),
            None,
        )
        if anime_chunk is not None:
            return (
                "Anime has influenced James's taste in visual styles, particularly Japanese visual aesthetics. "
                "He also enjoys watching anime in his free time."
            )
    destination_answer = _format_destination(chunks, intent)
    if destination_answer is not None:
        return destination_answer
    return None


def format_entity_answer(question: str, chunks: list[dict], intent: QueryIntent) -> str | None:
    """Answer focused entity questions from a single evidence chunk."""

    if not chunks:
        return None
    chunk = chunks[0]
    metadata = chunk.get("metadata", {})
    category = metadata.get("category", "")
    title = metadata.get("title", "")
    lower = question.lower()
    facts = load_profile_facts()
    if "fft_tuner" in intent.entities and title == "Tune-app (FFT Guitar Tuner)":
        if re.search(r"\b(?:called|name|named|title)\b", lower):
            return "James's guitar tuner is called Tune-app (FFT Guitar Tuner), a browser-based FFT Frequency Analyzer."
        return _body_without_heading(chunk)
    if "medical_platform" in intent.entities and title == "智愈APP (Zhiyu App) — Flutter medical platform":
        return _body_without_heading(chunk)
    if "cs_inspiration" in intent.entities and category == "education":
        return _body_without_heading(chunk)
    if "uniswap_project" in intent.entities and category == "projects_skills":
        return (
            "James's project is titled “Uniswap V3 EE experiment.” "
            + _body_without_heading(chunk)
        )
    if "qiu_competition" in intent.entities and category == "achievements":
        if "qiu_win" in intent.entities or re.search(r"\b(?:win|won|winner)\b", lower):
            return "James participated in the 丘成桐中学科学奖 (Qiu Competition); the public profile does not say that he won it."
        return "The competition is named 丘成桐中学科学奖 (Qiu Competition)."
    if "camera_xinjiang" in intent.entities and category == "travel":
        return "In Xinjiang, James used a Nikon Z8 and an iPhone 13 Pro to film a video that he posted on Bilibili."
    video_answers = {
        "video_greece": "James filmed “Greece” in 8K in 2024, exploring Athens and the Ionian Sea.",
        "video_japan": "James filmed “Japan Winter” in 4K in 2025, featuring snowy scenes in Hokkaido.",
        "video_xinjiang": "James filmed a video in Xinjiang in 2026 using a Nikon Z8 and an iPhone 13 Pro, then posted it on Bilibili.",
    }
    for entity, answer in video_answers.items():
        if entity in intent.entities and category == "video":
            return answer
    if "coding_origin" in intent.entities and category in {"projects_skills", "education"}:
        coding = facts["coding_learning"]
        return (
            f"James learned {coding['language']} independently during {coding['time']}. "
            f"He also works with {', '.join(coding['other_languages'][:-1])}, and {coding['other_languages'][-1]}."
        )
    if "gaming_reason" in intent.entities and category in {"hobby", "gaming", "personality"}:
        return facts["gaming_reasons"]["answer"]
    if intent.temporal_relation == "cessation" and "instrument" in intent.entities:
        return (
            "No — James's profile says he plays electric guitar and started in 2025; "
            "it does not document that he stopped."
        )
    if intent.negated and "apex_game" in intent.entities and intent.topic == "games":
        return "No — Apex Legends is one of James's competitive favorite games."
    if category == "apex_rank" and re.search(r"\bseason\b", lower) and not re.search(r"\brank\b", lower):
        apex_rank = load_profile_facts().get("apex_rank", {})
        if apex_rank.get("rank") and apex_rank.get("season"):
            return f"James reached {apex_rank['rank']} in {apex_rank['season']}."
    if category == "apex_rank" and re.search(r"\b(?:rank|diamond|season)\b", lower):
        return _body_without_heading(chunk)

    if re.search(r"\bposition\b", lower) and re.search(r"\b(?:hockey|soccer)\b", lower):
        return "James plays ice hockey as a defender and soccer as a forward."

    if category in {"video", "essay", "writing", "sport", "travel", "projects_skills", "education"}:
        if category == "video" and re.search(r"\b(?:film|filmed|video|shot|record)\b", lower):
            return _body_without_heading(chunk)
        if category in {"essay", "writing", "projects_skills"} and re.search(r"\b(?:essay|paper|research|project|built|about)\b", lower):
            return _body_without_heading(chunk)
        if category in {"sport", "travel", "education"} and intent.topic in {"sports", "travel", "education"}:
            return _body_without_heading(chunk)

    return None


def format_structured_answer(
    question: str, chunks: list[dict], intent: QueryIntent | None = None
) -> str | None:
    """Return a deterministic answer when a curated summary can answer safely."""

    if not chunks:
        return None
    chunk = chunks[0]
    title = chunk.get("metadata", {}).get("title", "")
    intent = intent or detect_intent(question)
    facts = load_profile_facts()
    focused = focused_chunks(intent.entities, chunks)
    if focused:
        if GENERATIVE_ENTITIES.intersection(intent.entities) or re.search(
            r"\b(?:results?|conclusions?|limitations?|architecture|hyperparameters?|accuracy|how many|cost|price)\b", question, re.IGNORECASE
        ):
            return None
        if "hockey_lessons" in intent.entities:
            return "Ice hockey has given James experience with teamwork, handling pressure in intense games, and coping with defeat against stronger opponents."
        return " ".join(_body_without_heading(item) for item in focused)
    if not summary_can_answer(question, intent):
        return None
    profile_answer = _format_profile_answer(question, chunks, intent, facts)
    if profile_answer is not None:
        return profile_answer
    if "additional_hobbies" in intent.entities:
        return _format_additional_hobbies(chunks)
    if title not in STRUCTURED_SUMMARY_TITLES:
        return format_entity_answer(question, chunks, intent)
    if not _summary_matches_intent(title, intent):
        return None
    if title == "Favorite games":
        return _format_games(facts, intent, question)
    if title in {"Favorite anime", "Anime (top favorites)"}:
        return _format_favorite_anime(facts)
    if title == "Favorite movie":
        return _format_favorite_movie(facts)
    if title == "Favorite book series":
        return _format_favorite_book(facts)
    if title == "Favorite place":
        return _format_favorite_place(facts)
    if title == "Favorite school subject":
        return _format_favorite_school_subject(facts)
    if title == "IDE/editor usage":
        return _format_ide_usage(facts)
    if title == "Favorite food":
        food = facts["favorite_food"]
        return f"James's favorite food is {food['primary']}. He also enjoys {' and '.join(food['also_enjoys'])}."
    if title == "Favorite season":
        if "dislikes" in intent.entities:
            dislike = facts["dislikes"][0]
            if re.search(r"\bwinter\b", question, re.IGNORECASE):
                return "James's profile lists winter as his favorite season, especially with snow. The season he explicitly dislikes is summer."
            return f"James has explicitly said that he dislikes {dislike['item']} because {dislike['reason']}. I don't have a complete list of things he dislikes."
        season = facts["favorite_season"]
        return f"James's favorite season is {season['primary']}, {season['detail']}."
    if title == "Favorite music":
        return _format_music(facts, intent)
    if title == "Electric guitar":
        guitar = facts["guitar"]
        if intent.temporal_relation == "cessation":
            return (
                "No — James's profile says he plays electric guitar and started in 2025; "
                "it does not document that he stopped."
            )
        return f"Yes — James plays {guitar['instrument']}. He started in {guitar['started']} and is {guitar['learning']}. He focuses on {', '.join(guitar['genres'][:-1])}, and {guitar['genres'][-1]}."
    if title == "Photography and videography":
        photography = facts["photography"]
        if "camera" in intent.entities and "lens" in intent.entities:
            return (
                f"James's primary camera is a {photography['primary_camera']}; he also uses a "
                f"{photography['additional_cameras'][0]} and an {photography['additional_cameras'][1]}. "
                f"His lenses are a {photography['lenses'][0]} and a {photography['lenses'][1]}."
            )
        if "lens" in intent.entities:
            return f"James uses a {photography['lenses'][0]} lens and a {photography['lenses'][1]} lens."
        if "camera" in intent.entities:
            if "favorite" in intent.qualifiers and intent.quantity == "singular":
                return f"James's primary camera is a {photography['primary_camera']}; his profile does not identify a separate favorite camera."
            return f"James's primary camera is a {photography['primary_camera']}. He also uses a {photography['additional_cameras'][0]} and an {photography['additional_cameras'][1]}."
        if intent.topic == "photography":
            return _format_photography_overview(facts)
    if title == "Travel":
        return _format_travel(facts, intent)
    if title == "Sports":
        return _format_sports(facts, intent, question)
    if title in {"Projects & Skills", "Programming languages"}:
        if "coding_origin" in intent.entities:
            coding = facts["coding_learning"]
            return (
                f"James learned {coding['language']} independently during {coding['time']}. "
                f"He also works with {', '.join(coding['other_languages'][:-1])}, and {coding['other_languages'][-1]}."
            )
        return _format_projects(facts, intent, question)
    if title == "Education":
        education = facts["education"]
        if "programming_languages" in intent.entities:
            return "James works with:\n\n" + _bullets(facts["programming_languages"])
        return (
            f"James's profile lists the {education['program']} at {education['school']}, "
            f"with {education['grade']} recorded for the {education['grade_as_of']}. "
            f"His Higher Level subjects are {', '.join(education['higher_level_subjects'])}."
        )
    if title == "Writing & Essays":
        details = facts.get("writing_details", {})
        if "apex_essay" in intent.entities:
            return details.get("math_ia", "James's Math IA applies a Markov chain model to Apex Legends.")
        if re.search(r"\bextended essay\b|\buniswap\b", question, re.IGNORECASE):
            return details.get("extended_essay", "James's Extended Essay is about Uniswap V3.")
        if re.search(r"\bmath ia\b|\bmathematics ia\b", question, re.IGNORECASE):
            return details.get("math_ia", "James's Math IA applies a Markov chain model to Apex Legends.")
        if re.search(r"\bphysics ia\b|\bguitar tuner\b", question, re.IGNORECASE):
            return details.get("physics_ia", "James's IB Physics IA investigates an FFT guitar tuner.")
        return "James has written or researched:\n\n" + _numbered(facts["writing"])
    if title == "Achievements & Awards":
        return "James's achievements include:\n\n" + _bullets(facts["achievements"])
    if title == "Hobbies & Interests":
        return "James's hobbies include:\n\n" + _bullets(facts["hobbies"])
    return extractive_answer(chunk)
