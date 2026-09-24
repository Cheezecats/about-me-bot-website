"""Curated destinations, independent of model-generated text and URLs."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from backend import config
from backend.generation.policies import is_sensitive_request, is_non_profile_request
from backend.generation.query_plan import _clean


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict]:
    entries = json.loads((config.DATA_DIR / 'chat_destinations.json').read_text())
    return {entry['id']: entry for entry in entries}


@lru_cache(maxsize=1)
def facts() -> dict:
    return json.loads((config.DATA_DIR / 'profile_facts.json').read_text())


def _source(section: str, text: str, category: str) -> list[dict]:
    return [dict(chunk_id=f'navigation_{section}', text=text, category=category,
                 title=section.replace('_', ' ').title(), label=section.replace('_', ' ').title(),
                 source='kb_extra/favorites.md')]


def _reply(answer: str, actions: list[str], sources: list[dict] | None = None, status: str = 'answered') -> dict:
    return dict(status=status, answer=answer, actions=[id for id in actions if id in catalog()],
                sources=sources or [], confidence=1.0 if sources else 0.0,
                fallback_used=False, reason='navigation', retrieval_method='catalog')


def _subject_ids(subject: str) -> list[str]:
    return [id for id, entry in catalog().items() if entry['subject'] == subject]


_GAME_PATTERNS = (
    (r'\bapex(?:\s+legends)?\b', 'game-apex'),
    (r'\b(?:counter[- ]?strike(?:\s*2)?|cs\s*:?\s*go|cs2)\b', 'game-cs2'),
    (r'\bvalorant\b', 'game-valorant'),
    (r'\bcyberpunk(?:\s+2077)?\b', 'game-cyberpunk'),
    (r'\b(?:gta\s*(?:5|v)|grand\s+theft\s+auto\s*(?:5|v))\b', 'game-gta5'),
    (r'\boverwatch(?:\s*2)?\b', 'game-overwatch'),
    (r'\bcivilization(?:\s*(?:vi|vii|6|7))?\b', 'game-civilization'),
    (r'\bmario\s+kart\b', 'game-mario-kart'),
)
_TOP_GAMES = ('game-apex', 'game-cs2', 'game-valorant')
_SENNEN = re.compile(r'千恋[＊*]?万花|\bsennen\s*(?:koi\s*hana|banka)\b', re.I)


def _named_games(text: str) -> list[str]:
    return [subject for pattern, subject in _GAME_PATTERNS if re.search(pattern, text)]


def subject_reply(subject: str) -> dict:
    ids = _subject_ids(subject)
    if subject == 'authors-choice':
        try:
            photos = json.loads(config.CONTENT_EXPORT_PATH.read_text()).get('photos', [])
            count = sum(bool(photo.get('featured')) for photo in photos)
        except (OSError, ValueError):
            count = 0
        if not count:
            return _reply("I can't verify James's curated picks right now. You can explore his photography gallery.", ['photography'])
        return _reply(f"James has {count} curated photo picks, rather than one documented favorite. Explore his selection below.", ids)
    if subject == 'song':
        music = facts()['favorite_music']
        text = f"James's documented favorite song is “{music['song']}” by {music['song_artist']}. Choose where to listen."
        return _reply(text, ids, _source('favorite_music', text, 'music'))
    if subject == 'football':
        team = facts()['favorite_football_team']
        text = f"James's favorite football team is {team['team']}, {team['detail']}."
        return _reply(text, ids, _source('favorite_football_team', text, 'sports'))
    if subject == 'games':
        return _reply("Explore James's three ranked competitive favorites.",
                      [id for game in _TOP_GAMES for id in _subject_ids(game)])
    if subject.startswith('game-'):
        name = catalog()[subject]['label'].removeprefix('Explore ')
        return _reply(f"Explore {name} on its official site.", ids)
    if subject in {'deco27', 'miku', 'yorushika', 'hitorie', 'kohana'}:
        music = facts()['favorite_music']
        names = dict(deco27=music['artist'], miku=music['alternate_artist'],
                     yorushika=music['bands'][0], hitorie=music['bands'][1], kohana=music['song_artist'])
        text = f"Explore {names[subject]} on either service. These links open search results."
        evidence = f"Favorite song: {music['song']} by {music['song_artist']}. Favorite artists: {music['artist']} or {music['alternate_artist']}. Favorite bands: {', '.join(music['bands'])}."
        return _reply(text, ids, _source('favorite_music', evidence, 'music'))
    labels = {'photography': "Explore James's photography gallery.", 'videos': "Watch James's videos.",
              'essays': "Explore James's research and essays.", 'hobbies': "Explore James's hobbies.",
              'sports': "Explore James's sports timeline."}
    return _reply(labels[subject], ids)


def _subjects(text: str, contract=None) -> list[str]:
    subjects = []
    if contract is not None:
        if contract.object_type == 'photograph':
            subjects.append('authors-choice' if contract.relation == 'favorite' else 'photography')
        elif contract.domain == 'photography' and contract.object_type in {'camera', 'lens', 'place'}:
            subjects.append('photography')
        elif contract.domain == 'videos':
            subjects.append('videos')
        elif contract.domain == 'writing':
            subjects.append('essays')
        elif contract.domain == 'hobbies':
            subjects.append('hobbies')
        elif contract.domain == 'sports' and contract.object_type != 'team':
            if re.search(r'\b(?:sports?|skiing|hockey|tennis|floorball|soccer)\b', text):
                subjects.append('sports')
        elif contract.domain == 'sports' and contract.object_type == 'team':
            subjects.append('football')
        elif contract.domain == 'games':
            subjects.extend(_named_games(text) or (['games'] if re.search(r'\b(?:games?|gaming)\b', text) else []))
        elif contract.domain == 'music':
            named = contract.constraints.get('named_entity')
            if contract.object_type == 'song':
                subjects.append('song')
            elif contract.object_type == 'band':
                subjects.extend(['yorushika', 'hitorie'])
            elif contract.object_type == 'artist' and named:
                subjects.append(named)
    if not subjects and re.search(r'\b(?:pictures?|photos?|photographs?|photography|gallery|pics)\b', text):
        subjects.append('authors-choice' if re.search(r"\b(?:favorite|favourite|picks|curated|choice)\b", text) else 'photography')
    for pattern, subject in [(r'\b(?:videos?|vlogs?|films)\b', 'videos'), (r'\b(?:essays?|papers?|research|writing)\b', 'essays'), (r'\b(?:hobbies|hobby|interests)\b', 'hobbies'), (r'\b(?:(?:football|soccer) team|real madrid|royal madrid|cr7|cristiano ronaldo)\b', 'football')]:
        if re.search(pattern, text): subjects.append(subject)
    if re.search(r'\b(?:sports?|skiing|hockey|tennis|floorball)\b', text):
        subjects.append('sports')
    named_games = _named_games(text)
    subjects.extend(named_games)
    if not named_games and re.search(r'\b(?:games?|gaming)\b', text) and not _SENNEN.search(text):
        subjects.append('games')
    artists = [(r'deco\s*\*?\s*27', 'deco27'), (r'hatsune miku|初音ミク', 'miku'), (r'yorushika|ヨルシカ', 'yorushika'), (r'hitorie|ヒトリエ', 'hitorie'), (r'kohana(?: lam)?|こはならむ', 'kohana')]
    named = [subject for pattern, subject in artists if re.search(pattern, text)]
    if re.search(r'\b(?:song|songs|track|music|playlist)\b|君の神様になりたい', text):
        # A song with its documented performer still means the song.
        subjects.append('song' if not named or re.search(r'\bsong\b|君の神様になりたい', text) else named[0])
    else:
        subjects.extend(named)
        if not named and re.search(r'\bfavou?rite artist\b', text): subjects.append('deco27')
        if not named and re.search(r'\bfavou?rite bands?\b', text): subjects.extend(['yorushika', 'hitorie'])
    return list(dict.fromkeys(subjects))


_NAV = re.compile(r'\b(?:direct me|take me|show (?:me|us|his|james)|link|where can (?:i|we) (?:see|find|read|view|listen|hear|watch)|go to|navigate|(?:want|like) to (?:listen|hear|watch|view))\b|^(?:(?:please|can you|could you) )?(?:open|visit|listen|hear|watch|view)\b')
_REFERENCE = re.compile(r'\b(?:there|that|it|those|these|them|first one|second one)\b')


def navigation_reply(question: str, state=None, *, contract=None) -> dict | None:
    text = _clean(question).lower()
    subjects = _subjects(text, contract)
    navigating = contract is not None and contract.response_mode in {'navigation', 'both'}
    navigating = navigating or bool(_NAV.search(text))
    football_fact = (
        contract is not None
        and contract.domain == 'sports'
        and contract.object_type == 'team'
        and contract.relation in {'favorite', 'supports', 'likes'}
        and bool(re.search(r'\bwhat\s+about\b', text))
    ) or ('football' in subjects and bool(re.search(r'\bwhat\s+about\b', text)))
    if not navigating and not football_fact:
        return None
    if is_sensitive_request(text) or is_non_profile_request(text) or re.search(r'flappy\s*bird|https?://|javascript:|\bprivate\b', text):
        return _reply(config.REFUSAL_MESSAGE, [], status='refused')
    # Do not replace unsupported requested details with a broad destination.
    if re.search(r'\b(?:why|when|cost|price|settings|before|least|except|not|dislike)\b', text):
        return None
    if _SENNEN.search(text):
        return _reply("James lists 千恋万花 among his favorite games. JamChat doesn't offer a destination for it.", [])
    if re.search(r'\b(?:that|this) song\b', text):
        remembered = [s for s in getattr(state, 'navigation_subjects', ()) if s == 'song']
        subjects = remembered if getattr(state, 'navigation_subjects', ()) else subjects
    elif re.search(r'\b(?:that|this) artist\b', text):
        remembered = [s for s in getattr(state, 'navigation_subjects', ()) if s in {'deco27', 'miku', 'yorushika', 'hitorie', 'kohana'}]
        subjects = remembered if getattr(state, 'navigation_subjects', ()) else subjects
    if not subjects and _REFERENCE.search(text) and not re.search(r'\b(?:that|this) (?:song|artist)\b', text):
        subjects = list(getattr(state, 'navigation_subjects', ()))
    if not subjects:
        return _reply("Which destination do you mean—James's photography, videos, essays, hobbies, sports, music, or games?", [], status='clarification')
    if len(subjects) > 1 and _REFERENCE.search(text):
        return _reply("Which destination do you mean? Please name the page, artist, or interest.", [], status='clarification')
    replies = [subject_reply(subject) for subject in subjects]
    result = _reply('\n\n'.join(r['answer'] for r in replies),
                    [id for r in replies for id in r['actions']],
                    [source for r in replies for source in r['sources']])
    services = [service for service in ('youtube', 'spotify') if service in text]
    if len(services) == 1 and all(catalog()[id]['subject'] in {'song', 'deco27', 'miku', 'yorushika', 'hitorie', 'kohana'} for id in result['actions']):
        result['actions'] = [id for id in result['actions'] if id.endswith('-' + services[0])]
    if state is not None:
        remembered_subjects = tuple(subject for item in subjects for subject in (_TOP_GAMES if item == 'games' else (item,)))
        if remembered_subjects != state.navigation_subjects:
            state.clear_profile_context()
        state.navigation_subjects = remembered_subjects
    return result


def answer_actions(question: str, intent) -> list[str]:
    """Only attach destinations to successful grounded ordinary answers."""
    text = _clean(question).lower()
    contract = getattr(intent, 'contract', None)
    if contract is not None:
        # Ordinary factual answers get only the destination that matches the
        # resolved object. In particular, an artist question must not inherit
        # the song links, and unsupported relations must not get a CTA.
        if contract.domain == 'photography' and contract.relation == 'favorite' and contract.object_type == 'photograph':
            return _subject_ids('authors-choice')
        if contract.domain == 'photography' and contract.object_type in {'camera', 'lens', 'place'}:
            return _subject_ids('photography')
        if contract.domain == 'sports' and contract.object_type == 'team' and contract.relation in {'supports', 'favorite', 'likes'}:
            return _subject_ids('football')
        if contract.domain == 'sports' and contract.relation == 'lists' and contract.object_type != 'team':
            return _subject_ids('sports')
        if contract.domain == 'games':
            named = _named_games(text)
            if named and contract.relation in {'favorite', 'likes', 'lists', 'rank'}:
                return [id for subject in named for id in _subject_ids(subject)][:3]
            if contract.relation in {'favorite', 'likes', 'lists'} and contract.object_type == 'game' and not _SENNEN.search(text):
                return [id for game in _TOP_GAMES for id in _subject_ids(game)]
            return []
        if contract.domain == 'music' and contract.object_type == 'song' and contract.relation in {'favorite', 'likes', 'listens_to'}:
            return _subject_ids('song')
        if contract.domain == 'music' and contract.object_type == 'artist' and contract.relation in {'favorite', 'likes', 'listens_to'}:
            named = contract.constraints.get('named_entity')
            return _subject_ids(named if isinstance(named, str) and named in {'deco27', 'miku', 'kohana'} else 'deco27')
        if contract.domain == 'music' and contract.object_type == 'band' and contract.relation in {'favorite', 'likes', 'listens_to'}:
            return _subject_ids('yorushika') + _subject_ids('hitorie')
        if contract.domain == 'writing' and contract.relation == 'method' and contract.object_type == 'paper':
            return _subject_ids('essays')
        if contract.domain == 'music' and contract.relation in {'favorite', 'likes', 'lists', 'listens_to'} and re.search(r'\bmusic\b', text):
            return _subject_ids('song')
        if contract.domain == 'videos' and contract.relation in {'lists', 'favorite', 'likes'}:
            return _subject_ids('videos')
        if contract.domain == 'writing' and contract.object_type == 'paper' and contract.relation in {'lists', 'method'}:
            return _subject_ids('essays')
        if contract.domain == 'hobbies' and contract.relation == 'lists' and contract.object_type == 'unresolved':
            return _subject_ids('hobbies')
        return []

    subjects = _subjects(text, None)
    if getattr(intent, 'topic', None) == 'music' and not subjects:
        subjects = ['song']
    return list(dict.fromkeys(id for subject in subjects for id in _subject_ids(subject)))[:6]
