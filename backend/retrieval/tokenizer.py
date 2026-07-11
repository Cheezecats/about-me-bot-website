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


def _normalize_aliases(text: str) -> str:
    return _ALIAS_PATTERN.sub(lambda m: ALIASES[m.group(1)], text)


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    lowered = _normalize_aliases(text.lower())
    tokens = _TOKEN_SPLIT.split(lowered)
    return [t for t in tokens if t and t not in STOPWORDS]
