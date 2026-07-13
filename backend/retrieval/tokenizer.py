from __future__ import annotations

import re

_TOKEN_SPLIT = re.compile(r"[^\w]+", re.UNICODE)

ALIASES = {
    "csgo": "csgo",
    "cs:go": "csgo",
    "cs2": "csgo",
    "ee": "extended essay",
    "ia": "internal assessment",
    "tok": "theory of knowledge",
    "nyt": "new york times",
    "jpop": "jpop",
    "j-pop": "jpop",
    "j pop": "jpop",
    "pc": "pc",
}

_ALIAS_PATTERN = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(re.escape(k) for k in sorted(ALIASES, key=len, reverse=True))
    + r")(?![a-z0-9])"
)

STOPWORDS = frozenset(
    """
    a an the and or but if then else when while of at by for with about against between
    into through during before after above below to from up down in out on off over under
    again further is are was were be been being am do does did doing have has had having
    i you he she it we they them his her its their our your my me him us
    this that these those there here what which who whom whose how why where
    s t can will just don should now d ll m re ve y all any both each few more most other
    some such no nor only own same so than too very can would could should may might
    as also get got go goes
    """.split()
)

# Query-only normalization. Documents keep their original tokens so the
# index remains stable, while common user variations can still match the
# same fact (for example, "favorite game" -> "favorite games").
QUERY_CORRECTIONS = {
    "favoriate": "favorite",
    "favouite": "favorite",
    "favrite": "favorite",
    "favorate": "favorite",
    "photographt": "photography",
    "photograpy": "photography",
    "photograhpy": "photography",
    "hobbys": "hobbies",
    "travelled": "traveled",
    "travelling": "traveling",
    "countries": "country",
    "ank": "rank",
    "acheivements": "achievements",
    "acheivement": "achievement",
    "achievments": "achievements",
    "musci": "music",
    "insturment": "instrument",
    "instruement": "instrument",
}

QUERY_EXPANSIONS = {
    "game": ("games", "favorite", "favorites", "competitive", "noncompetitive"),
    "games": ("game", "favorite", "favorites", "competitive", "noncompetitive"),
    "hobby": ("hobbies", "interest", "interests"),
    "hobbies": ("hobby", "interest", "interests"),
    "favorite": ("favourite",),
    "favourite": ("favorite",),
    "photography": ("photographer", "videography", "camera", "nikon", "lenses"),
    "photographer": ("photography", "videography", "camera"),
    "essay": ("essays", "paper", "papers", "research", "writing"),
    "essays": ("essay", "paper", "papers", "research", "writing"),
    "paper": ("papers", "essay", "essays", "research", "writing"),
    "papers": ("paper", "essay", "essays", "research", "writing"),
    "sports": ("sport", "skiing", "hockey", "tennis", "floorball", "soccer"),
    "sport": ("sports", "skiing", "hockey", "tennis", "floorball", "soccer"),
    "music": ("song", "artist", "artists", "band", "bands", "guitar", "jpop", "rock"),
    "song": ("songs", "music", "like", "likes", "favorite", "favorites", "artist", "band"),
    "songs": ("song", "music", "like", "likes", "favorite", "favorites", "artist", "band"),
    "track": ("tracks", "song", "songs", "music", "favorite"),
    "tracks": ("track", "song", "songs", "music", "favorite"),
    "band": ("bands", "music", "favorite", "favorites", "artist"),
    "bands": ("band", "music", "favorite", "favorites", "artist"),
    "like": ("likes", "enjoy", "enjoys", "favorite", "favorites", "music"),
    "likes": ("like", "enjoy", "enjoys", "favorite", "favorites", "music"),
    "enjoy": ("enjoys", "like", "likes", "favorite", "favorites"),
    "enjoys": ("enjoy", "like", "likes", "favorite", "favorites"),
    "instrument": ("instruments", "guitar"),
    "instruments": ("instrument", "guitar"),
    "traveled": ("travel", "travelled", "visited"),
    "travel": ("traveled", "travelled", "visited"),
    "visit": ("visited", "travel", "traveled", "country", "countries"),
    "visited": ("visit", "travel", "traveled", "country", "countries"),
    "country": ("countries", "visited", "travel", "traveled"),
    "training": ("train", "hockey", "abroad", "russia", "united", "states"),
    "train": ("training", "hockey", "abroad", "russia", "united", "states"),
    "programming": ("language", "languages", "python", "typescript", "solidity"),
    "languages": ("language", "programming", "python", "typescript", "solidity"),
    "project": ("projects", "built", "created", "website", "research"),
    "projects": ("project", "built", "created", "website", "research"),
    "school": ("education", "studies", "attend", "ibdp"),
    "attend": ("school", "education", "studies"),
    "study": ("studies", "school", "education"),
    "award": ("awards", "achievement", "achievements", "earned", "silver"),
    "awards": ("award", "achievement", "achievements", "earned", "silver"),
    "achievement": ("achievements", "award", "awards", "earned"),
    "achievements": ("achievement", "award", "awards", "earned"),
    "won": ("earned", "award", "awards", "achievement"),
    "dislike": ("dislikes", "disliked", "summer", "season", "favorite"),
    "dislikes": ("dislike", "disliked", "summer", "season", "favorite"),
    "disliked": ("dislike", "dislikes", "summer", "season", "favorite"),
}


def _normalize_aliases(text: str) -> str:
    return _ALIAS_PATTERN.sub(lambda m: ALIASES[m.group(1)], text)


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    lowered = _normalize_aliases(text.lower())
    tokens = _TOKEN_SPLIT.split(lowered)
    return [t for t in tokens if t and t not in STOPWORDS]


def tokenize_query(text: str) -> list[str]:
    """Tokenize a user query with conservative spelling and form expansion."""

    base_tokens = tokenize(text)
    tokens: list[str] = []
    for token in base_tokens:
        normalized = QUERY_CORRECTIONS.get(token, token)
        if normalized not in tokens:
            tokens.append(normalized)
        for expansion in QUERY_EXPANSIONS.get(normalized, ()):
            if expansion not in tokens:
                tokens.append(expansion)
    return tokens
