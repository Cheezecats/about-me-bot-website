from __future__ import annotations

import re
from dataclasses import dataclass, replace

from backend.generation import policies
from backend.generation.contracts import SemanticContract, unresolved_contract
from backend.generation.evidence import focused_subjects, focused_topic


@dataclass(frozen=True)
class QueryIntent:
    """Small, explainable intent representation used before retrieval."""

    kind: str
    topic: str | None = None
    entities: tuple[str, ...] = ()
    followup: bool = False
    comparison: bool = False
    before_year: int | None = None
    ordinal: int | None = None
    question_operator: str | None = None
    quantity: str | None = None
    qualifiers: tuple[str, ...] = ()
    negated: bool = False
    certainty: str | None = None
    temporal_relation: str | None = None
    contract: SemanticContract | None = None

    @property
    def original_text(self) -> str:
        return self.contract.original_text if self.contract else ""

    @property
    def subject(self) -> str | None:
        return self.contract.subject if self.contract else None

    @property
    def domain(self) -> str | None:
        return self.contract.domain if self.contract else self.topic

    @property
    def relation(self) -> str:
        return self.contract.relation if self.contract else "unresolved"

    @property
    def object_type(self) -> str:
        return self.contract.object_type if self.contract else "unresolved"

    @property
    def constraints(self) -> dict[str, object]:
        return self.contract.constraints if self.contract else {}

    @property
    def response_mode(self) -> str:
        return self.contract.response_mode if self.contract else "information"

    @property
    def context_resolution(self) -> str:
        return self.contract.context_resolution if self.contract else "unresolved"

    @property
    def antecedent_id(self) -> str | None:
        return self.contract.antecedent_id if self.contract else None

    @property
    def supporting_spans(self) -> tuple[str, ...]:
        return self.contract.supporting_spans if self.contract else ()

    @property
    def provenance(self) -> str:
        return self.contract.provenance if self.contract else "unresolved"


_TOPIC_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?:\b(?:what\s+is|who\s+is|tell\s+me\s+about|about)\s+james(?=\s*$|[?.!,])|\bjames'?s?\s+bio(?:graphy)?\b|\b(?:hometown|born|how\s+old\s+(?:is|was)\s+james|what\s+age\s+is\s+james|live|lives|from\s+shanghai)\b)", "bio"),
    (r"\b(?:personality|person|like\s+as\s+a\s+person|values?|believe(?:s|d)?|beliefs?|mindset|aspiration|aspirations|future\s+(?:plans?|academic\s+interests?)|academic\s+interests?|teamwork|collaboration|individual\s+work|failure|democratiz\w*|accessible\s+technology)\b", "personality"),
    (r"\b(?:contact|email|e-mail|youtube|github|bilibili|socials?|website|channel)\b", "contact"),
    (r"\b(?:videos?|vlogs?|video\s+projects?|filmed|filming)\b", "videos"),
    (r"\b(?:camera|cameras|lens|lenses|photograph|photography|photographed|photographs?|photo|photos?|picture|pictures?|videograph|video|film|filmed|filming|gear)\b", "photography"),
    (r"\b(?:favorite|favourite)\s+(?:game|games)\b|\b(?:game|games|gaming|apex|valorant|csgo|cyberpunk)\b", "games"),
    (r"\b(?:food|eat|eating|ramen|ice cream)\b", "food"),
    (r"\b(?:season|winter|summer|spring|autumn|fall)\b", "season"),
    (r"\b(?:music|song|songs|track|tracks|artist|band|bands|listen|singer|playlist)\b", "music"),
    (r"\b(?:hobbies|hobby|interests?|instrument|guitar|drawing|pc building|pastime|free time|fun)\b", "hobbies"),
    (r"\b(?:sports?|skiing|hockey|tennis|floorball|soccer|footballer|football\s+player|soccer\s+player|athlete|team|club|pitch|position|support(?:s|ed)?)\b", "sports"),
    (r"\b(?:travel(?:ed|led|ing)?|visited|visit|been|went|countries|country|trip|abroad)\b", "travel"),
    (r"\b(?:italy|tuscany|greece|athens|japan|hokkaido|xinjiang|russia|united\s+states|los\s+angeles)\b", "travel"),
    (r"\b(?:essay|essays|paper|papers|research|writing|written|wrote|write|publish(?:ed)?|publication|ia|internal assessment)\b", "writing"),
    (r"\b(?:award|awards|achievement|achievements|accomplishment|accomplishments|won|victory|medal)\b", "achievements"),
    (r"\b(?:favorite|favourite)\s+(?:anime|movie|movies|film|films|book|books|series|place|subject|subjects)\b", "favorites"),
    (r"\b(?:favorites|favourites)\b", "favorites"),
    (r"\b(?:school|study|studies|education|curriculum|grade|graduat(?:e|ion)|ibdp|igcse|subjects?)\b", "education"),
    (r"\b(?:project|projects|build|built|created|developed|skills?|programming|code|coding|language|python|typescript|solidity)\b", "projects"),
)

_FOLLOWUP_PATTERN = re.compile(
    r"\b(?:what about|tell me more|when did (?:he|james) start|where was that|which one|the first|the second|the third|continue|go on|keep going|is that all)\b"
    r"|\b(?:anything else|what else|anything more|something else|anything to add|and|also)\b",
    re.IGNORECASE,
)


def is_additional_detail_request(question: str) -> bool:
    """Detect natural-language requests for more items in the current topic."""

    lower = question.strip().lower().strip(" ,;?!")
    if re.search(r"\b(?:anything|what|something)\s+(?:else|more)\b", lower):
        return True
    if re.search(
        r"\b(?:tell me more|more about|other|additional|another|besides|anything to add|what about the rest|is that all|go on|keep going)\b",
        lower,
    ):
        return True
    if re.search(r"\b(?:more|some more)\s+(?:hobbies?|interests?|activities?|things)\b", lower):
        return True
    if lower in {"and", "also", "more", "other", "another", "continue", "go on", "keep going", "is that all"} or re.search(
        r"\b(?:and|also|more|continue)\s*$", lower
    ):
        return True
    if re.match(r"^(?:and|also)\b", lower) and not re.search(
        r"\b(?:what|which|list|name)\b.*\b(?:hobbies?|interests?)\b", lower
    ):
        return True
    return False


def _ordinal(question: str) -> int | None:
    match = re.search(r"\b(first|second|third|1st|2nd|3rd)\b", question, re.IGNORECASE)
    if not match:
        return None
    return {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}[match.group(1).lower()]


def _contract_fields(question: str) -> dict[str, object]:
    """Extract answer-contract signals before canonicalization can erase them."""

    lower = question.strip().lower()
    if re.search(r"\bhow\s+many\b", lower):
        operator = "count"
    elif re.search(r"\bwhy\b", lower):
        operator = "why"
    elif re.search(r"\bhow\b", lower):
        operator = "how"
    elif re.search(r"\bwhere\b", lower):
        operator = "where"
    elif re.search(r"\bwhen\b", lower):
        operator = "when"
    elif re.search(r"\bwhich\b", lower):
        operator = "which"
    elif re.search(r"\bwho\b", lower):
        operator = "who"
    elif re.match(r"(?:does|did|is|are|has|have|can|could)\b", lower):
        operator = "yes_no"
    else:
        operator = "what"

    quantity: str | None = None
    if re.search(r"\b(?:name|give|list)\s+(?:me\s+)?one\b|\bone\s+(?:competitive|non[- ]competitive)?\s*(?:game|band|artist|project|sport)\b", lower):
        quantity = "one"
    elif re.search(r"\b(?:all|every|each|full\s+list)\b", lower):
        quantity = "all"
    elif operator == "count":
        quantity = "count"
    elif re.search(r"\b(?:games|bands|artists|cameras|projects|sports|videos|essays|hobbies|interests)\b", lower):
        quantity = "plural"
    elif re.search(r"\b(?:game|band|artist|camera|project|sport|video|essay|hobby|interest)\b", lower):
        quantity = "singular"

    qualifiers: list[str] = []
    if re.search(r"(?<!non-)(?<!non )\bcompetitive(?:ly)?\b", lower):
        qualifiers.append("competitive")
    if re.search(r"\bnon[- ]?competitive(?:ly)?\b", lower):
        qualifiers.append("non-competitive")
    if re.search(r"\b(?:ai|llm|machine\s+learning|computer\s+vision)\b", lower):
        qualifiers.append("ai")
    if re.search(r"\b(?:favorite|favourite)\b", lower):
        qualifiers.append("favorite")

    temporal_relation = None
    if re.search(r"\bbefore\b", lower):
        temporal_relation = "before"
    elif re.search(r"\bafter\b", lower):
        temporal_relation = "after"
    elif re.search(r"\b(?:still|currently|continue|continuing)\b", lower):
        temporal_relation = "continuation"
    elif re.search(r"\b(?:stop|stopped|no\s+longer)\b", lower):
        temporal_relation = "cessation"

    return {
        "question_operator": operator,
        "quantity": quantity,
        "qualifiers": tuple(qualifiers),
        "negated": bool(re.search(r"\b(?:not|never|no\s+longer|doesn't|isn't|don't|hasn't|didn't)\b", lower)),
        "certainty": "certainty" if re.search(r"\b(?:definitely|certainly|actually|really)\b", lower) else None,
        "temporal_relation": temporal_relation,
    }


def derive_semantic_contract(
    question: str,
    *,
    topic: str | None,
    entities: tuple[str, ...],
    question_operator: str | None,
    quantity: str | None,
    qualifiers: tuple[str, ...],
    negated: bool,
    before_year: int | None,
    ordinal: int | None,
    comparison: bool,
    temporal_relation: str | None,
) -> SemanticContract:
    """Interpret a clause once, retaining the requested relationship.

    These are reusable linguistic patterns over relation/object vocabulary;
    they are intentionally not a catalogue of complete visitor questions.
    """

    lower = question.lower()
    subject = "james" if topic or entities or re.search(r"\b(?:he|him|his|james)\b", lower) else None
    domain = topic
    # Prefer an explicit artifact/activity cue over a broad topic inherited
    # from a canonical alias (for example “study” in a research question).
    if re.search(r"\b(?:histology|paper|research|essay|methodology|limitations?|drawbacks?|weak\s+points?)\b", lower):
        domain = "writing"
    elif re.search(r"\b(?:photograph(?:y|ed|s)?|photo(?:s)?|picture(?:s)?|camera|lens|gallery|gear|shoot|capture)\b", lower):
        domain = "photography"
    elif domain is None and re.search(r"\b(?:football|soccer|footballer|player|team|club|pitch|position|defender|forward)\b", lower):
        domain = "sports"
    elif domain is None and re.search(r"\b(?:song|track|artist|band|music|listen|singer|musician)\b", lower):
        domain = "music"
    elif domain is None and re.search(r"\b(?:anime|movie|film|book|series)\b", lower) and re.search(r"\b(?:favorite|favourite|like|likes|enjoy|top|best)\b", lower):
        domain = "favorites"
    elif domain is None and re.search(r"\b(?:camera|lens|photograph|photography|photo|picture|gallery|gear|shoot|capture)\b", lower):
        domain = "photography"
    elif domain is None and re.search(r"\b(?:visited|visit|travel|place|places|country|countries|location|locations|destination|destinations|trip|trips|been)\b", lower):
        domain = "travel"
    elif domain is None and re.search(r"\b(?:subject|subjects|school|class(?:es)?|course(?:s)?|study|studies|take|physics|education)\b", lower):
        domain = "education"
    elif domain is None and re.search(r"\b(?:project|build|built|created|coding|code|python|programming|made)\b", lower):
        domain = "projects"
    elif domain is None and re.search(r"(?:deco\s*\*?\s*27|hatsune\s+miku|yorushika|hitorie|kohana)", lower):
        domain = "music"
    if topic == "favorites" or domain == "favorites":
        if re.search(r"\b(?:song|track|artist|band|bands|music|singer|musician)\b", lower):
            domain = "music"
        elif re.search(r"\bplace\b", lower):
            domain = "travel"
        elif re.search(r"\b(?:school\s+)?subjects?\b", lower):
            domain = "education"
        elif re.search(r"\b(?:game|games|gaming)\b", lower):
            domain = "games"
        elif re.search(r"\b(?:anime|movie|film|book|series)\b", lower):
            domain = "favorites"
    if "fft_tuner" in entities:
        domain = "projects"
    if domain in {"videos", "travel", "hobbies"} and re.search(r"\b(?:game|games|gaming|apex(?:\s+legends)?)\b", lower):
        domain = "games"
    if domain is None and re.search(r"\b(?:anime|movie|film|book|series)\b", lower) and re.search(r"\b(?:into|enjoy|likes?|like)\b", lower):
        domain = "favorites"
    if domain is None and re.search(r"\b(?:overall|in\s+general|top\s+picks?)\b", lower) and re.search(r"\b(?:favorite|favourite|like|likes|best|top)\b", lower):
        domain = "favorites"
    if domain != "music" and re.search(r"\b(?:favorite|favourite)\s+(?:things?|items?)\b|\bfavorite(?:s| favourites?)\b", lower):
        domain = "favorites"
    if re.search(r"\b(?:public\s+profile|background|bio(?:graphy)?|where\s+is\s+james\s+from)\b", lower):
        domain = "bio"
    if re.search(r"\b(?:award|awards|achievement|achievements|accomplishment|honou?r|honou?rs)\b", lower):
        domain = "achievements"
    if re.search(r"\b(?:contact|public\s+links?|social\s+links?|online\s+profiles?)\b", lower):
        domain = "contact"

    if re.search(r"\b(?:what\s+(?:did|has)|lessons?)\b.*\blearn\w*\b.*\bfrom\b", lower):
        relation = "reason"
    elif re.search(r"\b(?:highest|peak|rank|ranking)\b", lower) and domain == "games":
        relation = "rank"
    elif re.search(r"\b(?:limitations?|drawbacks?|weaknesses?)\b", lower):
        relation = "limitations"
    elif re.search(r"\bfail(?:ure|ures|ing)\b", lower) and re.search(r"\blead\w*\s+to\b", lower):
        relation = "result"
    elif re.search(r"\b(?:results?|findings?|conclusions?)\b", lower):
        relation = "result"
    elif re.search(r"\b(?:why|reason|because)\b", lower):
        relation = "reason"
    elif re.search(r"\b(?:what\s+does|what\s+do)\b.*\b(?:like|enjoy|get)\b.*\b(?:about|from)\b|\bwhat\s+makes\b", lower):
        relation = "reason"
    elif re.search(r"\b(?:how\s+(?:did|does|was)|method|methodology|approach|technique|way)\b", lower) and re.search(
        r"\b(?:paper|research|histology|build|built|work|study)\b", lower
    ):
        relation = "method"
    elif re.search(r"\b(?:learn|learned|self[- ]taught|taught|teach\s+himself|teach\s+yourself)\b", lower):
        relation = "learned_by"
    elif re.search(r"\b(?:how\s+long|how\s+many\s+years?|duration|last(?:ed)?|experience\s+length)\b", lower):
        relation = "duration"
    elif re.search(r"\b(?:before|after|first|earliest|latest)\b", lower) and re.search(
        r"\b(?:start|started|begin|began|take\s+up)\b", lower
    ):
        relation = "started"
    elif re.search(r"\b(?:when|what\s+year)\b", lower) and re.search(
        r"\b(?:start|started|begin|began|take\s+up|graduate|graduation)\b", lower
    ):
        relation = "started"
    elif temporal_relation in {"continuation", "cessation"} and re.search(
        r"\b(?:play|plays|playing|use|uses|study|studies|guitar|instrument|sport)\b", lower
    ):
        relation = "current_participation"
    elif re.search(r"\b(?:where|which\s+(?:places?|locations?|countries|destinations?)|what\s+(?:places?|locations?|countries|destinations?))\b", lower) and re.search(
        r"\b(?:photograph|photo|picture|shot|shoot|capture|filmed)\w*\b", lower
    ):
        relation = "photographed_in"
    elif domain == "sports" and re.search(r"\b(?:where|what\s+position|which\s+position|what\s+role|where\s+.*line\s+up|defender|forward)\b", lower) and re.search(
        r"\b(?:pitch|position|play|plays|field|line\s+up|role|defender|forward)\b", lower
    ):
        relation = "playing_position"
    elif "ai_learning" in entities and re.search(r"\b(?:ai|llm)\b.*\b(?:learn\w*|study\w*)\b", lower):
        relation = "uses"
    elif "democratizing_technology" in entities and re.search(r"\b(?:democratiz\w*|accessib\w*)\b|\bmake\b.*\btechnology\b", lower):
        relation = "reason"
    elif "school_challenge" in entities and re.search(r"\b(?:hardest|difficult\w*|challeng\w*|struggl\w*)\b", lower):
        relation = "reason"
    elif "engineering_motivation" in entities and re.search(r"\b(?:skill\w*|creative|logic|design|important|combine)\b", lower):
        relation = "reason"
    elif re.search(r"\bpreferred\b", lower):
        relation = "favorite"
    elif "teamwork_view" in entities and re.search(r"\b(?:prefer\w*|teamwork|individual\s+work)\b", lower):
        relation = "likes"
    elif re.search(r"\bprefer\w*\b", lower):
        relation = "likes"
    elif re.search(r"\b(?:favorite|favourite|favorites|favourites|most|best|top\s+pick|preferred|top)\b", lower):
        relation = "favorite"
    elif re.search(r"\b(?:support|supports|back|backs|follow|follows|stand\s+behind)\b", lower):
        relation = "supports"
    elif re.search(r"\b(?:listen|listens|heard|hear)\b", lower):
        relation = "listens_to"
    elif re.search(r"\b(?:use|uses|shoot|shoots|shooting|gear)\b", lower):
        relation = "uses"
    elif re.search(r"\b(?:build|built|create|created|develop|developed|make|made)\b", lower):
        relation = "created"
    elif re.search(r"\b(?:take|takes|study|studies|enrolled|enrollment|class(?:es)?|course(?:s)?|schedule)\b", lower):
        relation = "studies"
    elif re.search(r"\b(?:visited|visit|travelled|traveled|went|trip|destination)\b", lower) or (
        domain == "travel" and re.search(r"\b(?:been|places?|countries?)\b", lower)
    ):
        relation = "visited"
    elif re.search(r"\b(?:like|likes|liked|enjoy|enjoys|love|loves|into)\b", lower):
        relation = "likes"
    elif question_operator == "count":
        relation = "count"
    elif domain:
        relation = "lists"
    else:
        relation = "unresolved"
    if domain == "videos" and relation == "created":
        relation = "lists"
    if domain == "projects" and re.search(r"\b(?:python|py)\b", lower) and re.search(r"\b(?:project|build|built|made|code|created|developed)\b", lower):
        relation = "created"
    if domain == "sports" and re.search(r"\b(?:start|started|begin|began|take\s+up|earliest|first)\b", lower):
        relation = "started"
    if domain == "hobbies" and re.search(r"\b(?:still|currently|continue|continuing|stop|stopped|no\s+longer)\b", lower):
        relation = "current_participation"
    if re.search(r"\b(?:guitar\s+tun(?:er|ing)|tune\s+(?:a\s+)?guitar|tuning\s+app|app\b.*\btun(?:e|ing))\b", lower) and re.search(r"\b(?:build|built|create|created|make|made|project|app|called|name)\b", lower):
        domain = "projects"
        relation = "created"
    if "fft_tuner" in entities and re.search(r"\b(?:build|built|create|created|make|made|project|app|called|name)\b", lower):
        relation = "created"
    if domain == "photography" and re.search(r"\b(?:picture|photo|photograph)\w*\b", lower) and re.search(
        r"\b(?:favorite|favourite|best|most|top\s+pick|choose|choice)\b", lower
    ):
        relation = "favorite"
    if domain == "photography" and re.search(r"\b(?:shoot|shot|capture|photograph|photo|picture)\w*\b", lower) and re.search(
        r"\b(?:japan|hokkaido|greece|athens|italy|tuscany|xinjiang|russia|location|place|country|destination)\b", lower
    ):
        relation = "photographed_in"
    if domain == "photography" and re.search(r"\b(?:camera|cameras|lens|lenses|gear|kit|glass|setup)\b", lower) and relation in {"lists", "studies", "unresolved"}:
        relation = "uses"
    if domain == "sports" and re.search(r"\b(?:position|role|line\s+up|defender|forward)\b", lower) and relation in {"lists", "unresolved"}:
        relation = "playing_position"
    if domain == "projects" and re.search(r"\b(?:learn|coding|code|programming|python|self[- ]taught|teach\s+himself|get\s+into)\b", lower) and re.search(
        r"\b(?:how|method|learn|taught|teach|get\s+into)\b", lower
    ) and not re.search(r"\b(?:project|projects|build|built|made|created)\b", lower):
        relation = "learned_by"
    if domain == "writing" and re.search(r"\b(?:weak\s+points?|fall\s+short|drawbacks?)\b", lower):
        relation = "limitations"
    if domain == "personality" and relation == "likes" and re.search(r"\b(?:person|personality|as\s+a\s+person)\b", lower):
        relation = "describes"

    if re.search(r"\b(?:lens|lenses|glass)\b", lower):
        object_type = "lens"
    elif re.search(r"\b(?:camera|cameras)\b", lower):
        object_type = "camera"
    elif relation != "playing_position" and re.search(r"\b(?:footballer|football\s+player|soccer\s+player|athlete|individual\s+player|player)\b", lower):
        object_type = "athlete"
    elif domain == "sports" and relation == "playing_position":
        object_type = "position"
    elif re.search(r"\b(?:team|club)\b", lower):
        object_type = "team"
    elif relation == "playing_position" or re.search(r"\bposition\b", lower):
        object_type = "position"
    elif re.search(r"\b(?:song|songs|track|tracks)\b", lower):
        object_type = "song"
    elif re.search(r"\b(?:artist|artists|singer|singers)\b", lower):
        object_type = "artist"
    elif re.search(r"\b(?:band|bands)\b", lower):
        object_type = "band"
    elif re.search(r"\b(?:game|games|gaming|videogame|videogames)\b", lower):
        object_type = "game"
    elif re.search(r"\banime\b", lower):
        object_type = "anime"
    elif domain == "videos" and re.search(r"\b(?:video|videos?|film|films|vlog|vlogs?)\b", lower):
        object_type = "video"
    elif domain == "photography" and re.search(r"\bgallery\b", lower):
        object_type = "photograph"
    elif re.search(r"\b(?:movie|movies|film|films)\b", lower):
        object_type = "movie"
    elif re.search(r"\b(?:book|books|series)\b", lower):
        object_type = "book"
    elif re.search(r"(?:deco\s*\*?\s*27|hatsune\s+miku|yorushika|hitorie|kohana)", lower):
        object_type = "artist"
    elif relation == "reason":
        object_type = "explanation"
    elif "instrument" in entities and relation in {"learned_by", "method"}:
        object_type = "instrument"
    elif relation == "method" and re.search(r"\b(?:paper|research|essay)\b", lower):
        object_type = "paper"
    elif relation in {"learned_by", "method"} and re.search(r"\b(?:learn|coding|code|programming|method)\b", lower):
        object_type = "method"
    elif relation == "rank":
        object_type = "rank"
    elif "fft_tuner" in entities or re.search(r"\b(?:project|build|built|created|coding|code|made|app)\b", lower):
        object_type = "project"
    elif re.search(r"\b(?:instrument|guitar)\b", lower):
        object_type = "instrument"
    elif re.search(r"\b(?:subject|subjects|physics|class(?:es)?|course(?:s)?|schedule)\b", lower):
        object_type = "school_subject"
    elif relation in {"limitations", "result"}:
        object_type = "paper" if domain == "writing" else "unresolved"
    elif relation in {"visited", "photographed_in"} or re.search(r"\b(?:place|places|location|country|countries)\b", lower):
        object_type = "place"
    elif re.search(r"\b(?:papers?|essays?|research)\b", lower):
        object_type = "paper"
    else:
        object_type = "unresolved"

    if relation == "reason":
        object_type = "explanation"
    elif relation in {"started", "current_participation"} and domain == "sports" and object_type == "unresolved":
        object_type = "sport"
    elif domain == "sports" and relation == "playing_position":
        object_type = "position"
    elif domain == "travel" and relation in {"visited", "favorite"} and object_type == "unresolved":
        object_type = "place"
    elif domain == "photography" and relation == "photographed_in" and object_type in {"unresolved", "photograph"}:
        object_type = "place"
    elif domain == "favorites" and relation == "favorite" and object_type == "unresolved":
        if re.search(r"\banime\b", lower): object_type = "anime"
        elif re.search(r"\b(?:movie|film)\b", lower): object_type = "movie"
        elif re.search(r"\bbook|series\b", lower): object_type = "book"
    elif domain == "projects" and relation in {"created", "lists"} and object_type == "unresolved":
        object_type = "project"

    if domain == "writing" and relation in {"method", "limitations", "result"} and object_type == "unresolved":
        object_type = "paper"
    if domain == "sports" and relation in {"started", "current_participation"} and object_type == "unresolved":
        object_type = "sport"
    if domain == "sports" and object_type == "athlete" and re.search(r"\b(?:favorite|favourite|top|best)\b", lower):
        relation = "favorite"
    if domain == "sports" and re.search(r"\b(?:team|club|real\s+madrid)\b", lower):
        object_type = "team"
    if domain == "music" and re.search(r"\b(?:musician|music\s+artist|listening\s+rotation)\b", lower):
        object_type = "artist"
    if domain == "music" and re.search(r"\b(?:music\s+groups?|groups?)\b", lower):
        object_type = "band"
    if relation == "learned_by" and domain == "projects":
        object_type = "method"
    if domain == "projects" and re.search(r"\b(?:python|py)\b", lower) and object_type == "unresolved":
        object_type = "project"
    if domain == "projects" and relation == "created" and re.search(r"\b(?:tune|tuner|tuning|app)\b", lower):
        object_type = "project"
    if domain == "photography" and re.search(r"\b(?:shoot|shoots|shot|capture|takes?|photograph|photo|picture)\b", lower) and not re.search(r"\b(?:lens|lenses|glass)\b", lower) and object_type == "unresolved":
        object_type = "camera"
    if domain == "hobbies" and re.search(r"\b(?:guitar|guitarist|instrument)\b", lower) and object_type == "unresolved":
        object_type = "instrument"
    if domain == "sports" and object_type == "unresolved" and re.search(r"\b(?:sport|skiing|hockey|tennis|floorball|soccer|activity)\b", lower):
        object_type = "sport"
    if domain == "favorites" and object_type == "book" and re.search(r"\b(?:anime|animated)\b", lower):
        object_type = "anime"
    if domain == "favorites" and object_type == "unresolved" and re.search(r"\b(?:anime|movie|film|book|series)\b", lower):
        object_type = "anime" if re.search(r"\b(?:anime|animated)\b", lower) else "movie" if re.search(r"\b(?:movie|film)\b", lower) else "book"
    if domain == "music" and object_type == "artist" and re.search(r"\b(?:listen\w*|hear|hears|listening)\b", lower) and relation in {"favorite", "lists"}:
        relation = "listens_to"
    if domain == "travel" and relation == "visited" and object_type == "unresolved":
        object_type = "place"
    if domain == "travel" and relation == "visited" and object_type == "unresolved":
        object_type = "place"
    if domain == "hobbies" and relation == "created" and re.search(r"\b(?:tune|tuning|tuner|app)\b", lower):
        domain = "projects"
        object_type = "project"
    if domain == "favorites" and object_type == "unresolved" and re.search(r"\b(?:like|likes)\b.*\bbest\b|\btop\s+picks?\b", lower):
        relation = "lists"
    if domain == "education" and object_type == "school_subject" and relation == "lists":
        relation = "studies"
    if domain == "travel" and re.search(r"\b(?:trip|trips|destination|destinations)\b", lower) and relation == "lists":
        relation = "visited"
    if domain == "favorites" and object_type == "unresolved" and re.search(r"\b(?:favorite|favourite|favorites|top\s+picks?|favorite\s+things?)\b", lower):
        relation = "lists"
    if domain == "travel" and relation == "visited":
        object_type = "place"

    # Bare topic prompts are shorthand for the corresponding favorite item;
    # retain that relation so the exact favorite evidence can answer without
    # invoking generation.
    if domain == "favorites" and relation == "lists" and object_type in {"anime", "movie", "book"}:
        relation = "favorite"

    # A photograph preference is a documented curation, not an equipment fact.
    if object_type == "unresolved" and re.search(r"\b(?:picture|photo|photograph)\w*\b", lower):
        object_type = "photograph"

    constraints: dict[str, object] = {}
    if quantity:
        constraints["quantity"] = quantity
    if qualifiers:
        constraints["qualifiers"] = qualifiers
    if ordinal is not None:
        constraints["ordinal"] = ordinal
    if before_year is not None:
        constraints["before_year"] = before_year
    if temporal_relation:
        constraints["temporal_relation"] = temporal_relation
    if comparison:
        constraints["comparison"] = True
    if negated:
        constraints["negated"] = True
    if re.search(r"\b(?:python|py)\b", lower):
        constraints["technology"] = "python"
    named_artist = re.search(r"(?:deco\s*\*?\s*27|hatsune\s+miku|yorushika|hitorie|kohana)", lower)
    if named_artist:
        alias = re.sub(r"\s+", "", named_artist.group(0).lower()).replace("*", "")
        constraints["named_entity"] = (
            "deco27" if alias.startswith("deco") else
            "miku" if alias.startswith("hatsune") else
            "yorushika" if alias.startswith("yorushika") else
            "hitorie" if alias.startswith("hitorie") else
            "kohana" if alias.startswith("kohana") else alias
        )
    exclusions = re.findall(r"\b(?:except|excluding|other than)\s+([^?.!,]+)", lower)
    if exclusions:
        constraints["exclusions"] = tuple(exclusions)
    if re.search(r"\b(?:one|single)\b", lower):
        constraints["rank"] = "single"
    elif re.search(r"\b(?:favorite|favourite|most|best)\b", lower):
        constraints["rank"] = "superlative"

    navigation = bool(
        re.search(
            r"\b(?:show|open|navigate|direct|take\s+me|link|where\s+can\s+(?:i|we)\s+(?:see|find|read|listen|hear|watch|view))\b",
            lower,
        )
        or re.match(r"^(?:please\s+)?visit\b", lower)
    )
    response_mode = "navigation" if navigation else "information"
    if object_type == "photograph" and relation == "favorite":
        response_mode = "both"

    spans = tuple(dict.fromkeys(re.findall(
        r"\b(?:favorite|favourite|likes?|listens?|support(?:s|ed)?|uses?|camera|cameras|lens(?:es)?|"
        r"picture|pictures|photo(?:s|graph)?|photograph(?:ed|y)?|footballer|player|team|club|pitch|position|"
        r"song|track|artist|band|learn(?:ed)?|coding|built?|python|project(?:s)?|subject(?:s)?|why|method|"
        r"visited|travel(?:ed|led)?|place|paper|research|limitations?)\b",
        lower,
    )))
    if not spans and question.strip():
        spans = (question.strip(),)
    known = relation != "unresolved" and object_type != "unresolved" and subject is not None
    return SemanticContract(
        original_text=question,
        subject=subject,
        domain=domain,
        relation=relation,
        object_type=object_type,
        constraints=constraints,
        response_mode=response_mode,
        context_resolution="explicit" if subject else "unresolved",
        supporting_spans=spans,
        provenance="deterministic",
        confidence=0.96 if known else 0.35,
    )


def _attach_contract(
    intent: QueryIntent, question: str, *, interpretation_question: str | None = None
) -> QueryIntent:
    interpreted = interpretation_question or question
    contract = derive_semantic_contract(
        interpreted,
        topic=intent.topic,
        entities=intent.entities,
        question_operator=intent.question_operator,
        quantity=intent.quantity,
        qualifiers=intent.qualifiers,
        negated=intent.negated,
        before_year=intent.before_year,
        ordinal=intent.ordinal,
        comparison=intent.comparison,
        temporal_relation=intent.temporal_relation,
    )
    return replace(intent, contract=replace(contract, original_text=question))


def _topic(question: str) -> str | None:
    for pattern, topic in _TOPIC_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return topic
    return None


def detect_intent(question: str) -> QueryIntent:
    question = question.strip()
    lower = question.lower()

    if policies.is_sensitive_request(question):
        return _attach_contract(QueryIntent("privacy"), question)
    if policies.is_small_talk(question):
        return _attach_contract(QueryIntent("small_talk"), question)
    if policies.is_product_meta_request(question):
        return _attach_contract(QueryIntent("product_meta"), question)
    if policies.is_ambiguous_request(question):
        return _attach_contract(QueryIntent("ambiguous"), question)
    if policies.is_non_profile_request(question):
        return _attach_contract(QueryIntent("unsupported"), question)

    if re.search(r"\bfavorite\s+(?:programming\s+)?language\b", lower):
        return _attach_contract(QueryIntent("unsupported", topic="projects"), question)

    if focused_topic(question):
        topic = focused_topic(question)
    elif re.search(r"\b(?:fft(?:\s+guitar)?\s+tuner|guitar\s+tuner|tune[- ]?app)\b", lower):
        topic = "projects"
    elif re.search(r"\b(?:who\s+(?:inspired|sparked)|inspiration|inspired).*\bcomputer\s+science\b", lower):
        topic = "education"
    elif re.search(r"\b(?:essay|essays|ia|internal\s+assessment|paper|research)\b", lower) and re.search(
        r"\bapex(?:\s+legends)?\b", lower
    ):
        topic = "writing"
    elif re.search(r"\b(?:instrument|guitar)\b", lower) and re.search(
        r"\b(?:music|genre|genres|play|plays)\b", lower
    ):
        topic = "hobbies"
    elif re.search(r"\b(?:school|academic|class(?:room)?)\s+projects?\b", lower):
        topic = "projects"
    elif re.search(r"\b(?:film|filmed|filming|shot|recorded)\b", lower) and re.search(
        r"\b(?:what|which|did|has|have)\b", lower
    ):
        topic = "videos"
    elif re.search(
        r"\b(?:favorite|favourite)\s+(?:anime|movie|movies|film|films|book|books|series|place|school\s+subject|subject)\b",
        lower,
    ) or re.fullmatch(
        r"(?:james'?s?\s+)?(?:favorite|favourite)?\s*(?:anime|movie|film|book(?:\s+series)?|series|place|subject)",
        lower,
    ) or re.search(r"\b(?:ide|editor|editors|vscode|vs\s+code|zed|workbuddy|trae)\b", lower):
        topic = "favorites"
    elif re.search(r"\b(?:dislike|dislikes|disliked|least favorite|hate|hates)\b", lower):
        topic = "preferences"
    elif re.search(r"\b(?:train|training|competed|competition)\b", lower) and re.search(r"\bhockey\b", lower):
        topic = "travel"
    elif re.search(r"\b(?:background|public\s+profile|bio(?:graphy)?|where\s+is\s+james\s+from)\b", lower):
        topic = "bio"
    elif re.search(r"\b(?:award|awards|achievement|achievements|accomplishment|honou?r|honou?rs|competition(?:s)?)\b", lower):
        topic = "achievements"
    elif re.search(r"\b(?:class(?:es)?|course(?:s)?|enrolled|schedule)\b", lower):
        topic = "education"
    elif re.search(r"\b(?:anime|movie|film|book|series)\b", lower) and re.search(
        r"\b(?:favorite|favourite|like|likes|enjoy|top|best|choose)\b", lower
    ):
        topic = "favorites"
    elif re.search(r"\bguitar(?:ist)?\b", lower) and not re.search(r"\b(?:photograph|camera|lens)\b", lower):
        topic = "hobbies"
    elif re.search(r"\b(?:what|which)\b.*\b(?:favorite|favourite)\s+(?:things?|items?)\b|\bfavorite\s+things?\b|\blike\b.*\bbest\b.*\boverall\b", lower):
        topic = "favorites"
    else:
        topic = _topic(question)
    if re.search(r"(?:qiu\s*(?:competition|award)?|丘成桐中学科学奖)", lower):
        topic = "achievements"
    if re.search(r"\b(?:medical\s+recovery|recovery\s+platform|zhiyu|flutter\s+medical)\b", lower):
        topic = "projects"
    comparison = bool(
        re.search(r"\b(?:compare|versus|vs\.?|which|before|earliest|first|latest|most|different)\b", lower)
    )
    before_match = re.search(r"\bbefore\s+(20\d{2})\b", lower)
    followup = bool(_FOLLOWUP_PATTERN.search(question)) or bool(
        re.fullmatch(
            r"(?:what|where|when|how|which)\s+(?:does|did|is|are|has|have|can|could)\s+(?:he|she|they|it)\b.*",
            question.strip(),
            flags=re.IGNORECASE,
        )
    )
    additional_hobby_request = bool(
        is_additional_detail_request(question)
        and re.search(r"\b(?:fun|hobbies?|interests?|pastimes?)\b", lower)
    )
    entities = tuple(
        entity
        for entity in (
            "camera" if re.search(r"\bcameras?\b", lower) else None,
            "lens" if re.search(r"\blens(?:es)?\b", lower) else None,
            "instrument" if re.search(r"\b(?:instrument|guitar)\b", lower) else None,
            "sport_skiing" if re.search(r"\bskiing\b", lower) else None,
            "sport_ice_hockey" if re.search(r"\bice\s+hockey\b|\bhockey\b", lower) else None,
            "sport_tennis" if re.search(r"\btennis\b", lower) else None,
            "sport_floorball" if re.search(r"\bfloorball\b", lower) else None,
            "sport_soccer" if re.search(r"\bsoccer\b", lower) else None,
            "fft_tuner" if re.search(r"\b(?:fft(?:\s+guitar)?\s+tun(?:er|ing)|guitar\s+tun(?:er|ing)|tune[- ]?app|tuning\s+app|tune\s+(?:a\s+)?guitar|app\b.*\btun(?:e|ing))\b", lower) else None,
            "medical_platform" if re.search(r"\b(?:medical\s+recovery|recovery\s+platform|zhiyu|flutter\s+medical)\b", lower) else None,
            "cs_inspiration" if re.search(r"\b(?:who\s+(?:inspired|sparked)|inspiration|inspired).*\bcomputer\s+science\b", lower) else None,
            "uniswap_project" if re.search(r"\buniswap\b", lower) and re.search(r"\b(?:project|title|experiment|essay)\b", lower) else None,
            "qiu_competition" if re.search(r"(?:qiu(?:\s+competition)?|丘成桐中学科学奖)", lower) else None,
            "qiu_win" if re.search(r"(?:qiu(?:\s+competition)?|丘成桐中学科学奖)", lower) and re.search(r"\b(?:win|won|winner|medal|award)\b", lower) else None,
            "photographed_places" if re.search(
                r"\b(?:where|what\s+(?:places?|locations?)|which\s+(?:places?|countries?))\b", lower
            ) and re.search(
                r"\b(?:photograph(?:y|ed|s)?|photo(?:s)?|picture(?:s)?|filmed|shot)\b", lower
            ) else None,
            "competitive" if re.search(r"(?<!non-)(?<!non )\bcompetitive(?:ly)?\b", lower) else None,
            "non-competitive" if re.search(r"\bnon[- ]?competitive", lower) else None,
            "ai" if re.search(r"\b(?:ai|llm|machine learning|computer vision)\b", lower) else None,
            "programming_languages" if re.search(r"\bprogramming\s+languages?\b|\blanguages?\s+does", lower) else None,
            "visited" if re.search(r"\b(?:visit|visited|travel(?:ed|led)?)\b", lower) else None,
            "travel_italy" if re.search(r"\b(?:italy|tuscany)\b", lower) else None,
            "travel_greece" if re.search(r"\b(?:greece|athens)\b", lower) else None,
            "travel_japan" if re.search(r"\b(?:japan|hokkaido)\b", lower) else None,
            "travel_xinjiang" if re.search(r"\bxinjiang\b", lower) else None,
            "travel_russia" if re.search(r"\brussia\b", lower) else None,
            "travel_united_states" if re.search(r"\b(?:united\s+states|los\s+angeles)\b", lower) else None,
            "training" if re.search(r"\b(?:train|training|competed|competition)\b", lower) else None,
            "music_overview" if re.search(r"(?:最喜欢|喜欢).*(?:音乐|歌曲|歌)", lower) else None,
            "song" if re.search(r"\b(?:song|songs|track|tracks)\b", lower) else None,
            "band" if re.search(r"\bbands?\b", lower) else None,
            "artist" if re.search(r"\b(?:artists?|singers?)\b", lower) else None,
            "dislikes" if re.search(r"\b(?:dislike|dislikes|disliked|least favorite|hate|hates)\b", lower) else None,
            "additional_hobbies" if additional_hobby_request else None,
            "gaming_reason" if re.search(r"\b(?:why|because|relax|relaxation|unwind|decompress|social|connect|friends|peers|matter)\b", lower) and re.search(r"\b(?:game|games|gaming|apex|valorant|csgo)\b", lower) else None,
            "coding_origin" if re.search(r"\b(?:learn|learned|self-taught|taught|start|started|begin|began)\b", lower) and re.search(r"\b(?:code|coding|programming|python|software)\b", lower) else None,
            "apex_rank" if re.search(r"\bapex\s+legends\b", lower) and re.search(r"\brank\b", lower) else None,
            "apex_game" if re.search(r"\bapex(?:\s+legends)?\b", lower) else None,
            "anime" if re.search(r"\banime\b", lower) else None,
            "movie" if re.search(r"\b(?:movie|movies)\b", lower) and not re.search(r"\b(?:film|filmed|filming|shot|recorded)\b", lower) else None,
            "book" if re.search(r"\b(?:book|books|series)\b", lower) else None,
            "place" if re.search(r"\bplace\b", lower) else None,
            "school_subject" if re.search(r"\b(?:school\s+)?subjects?\b", lower) else None,
            "ide" if re.search(r"\b(?:ide|editor|editors|vscode|vs\s+code|zed|workbuddy|trae)\b", lower) else None,
            "graduation" if re.search(r"\b(?:graduate|graduation|finish(?:ing)?\s+school)\b", lower) else None,
            "higher_level_subjects" if re.search(r"\b(?:hl|higher\s+level|subjects?\s+(?:does|do)\s+(?:he|james)\s+(?:take|study)|(?:his|james'?s?)\s+hls?)\b", lower) else None,
            "aspirations" if re.search(r"\b(?:want(?:s)?|wanna)\s+(?:to\s+)?study\b|\bstudy\s+(?:later|afterward|after)\b|\b(?:future\s+(?:plans?|(?:academic\s+)?interests?)|(?:academic\s+)?aspirations?)\b", lower) else None,
            "drawing" if re.search(r"\b(?:draw|drawing|digital\s+art)\b", lower) else None,
            "youtube" if re.search(r"\byoutube\b", lower) else None,
            "github" if re.search(r"\bgithub\b", lower) else None,
            "website" if re.search(r"\b(?:personal\s+)?website\b", lower) else None,
            "public_contact" if re.search(r"\b(?:contact|email|e-mail|socials?)\b", lower) else None,
            "publication" if re.search(r"\b(?:publish|published|publication|curieux)\b", lower) else None,
            "research_overview" if re.search(r"\bresearch(?:ed|ing)?\b", lower) else None,
            "apex_essay" if re.search(r"\b(?:essay|essays|ia|internal\s+assessment)\b", lower) and re.search(r"\bapex(?:\s+legends)?\b", lower) else None,
            "anime_influence" if re.search(r"\banime\b", lower) and re.search(r"\b(?:influence|influenced|impact|style)\b", lower) else None,
            "best_sport" if re.search(r"\b(?:best|strongest|better)\s+(?:at\s+)?sport\b|\bsport\s+is\s+(?:he|james)\s+(?:best|strongest)\b", lower) else None,
            "video_overview" if re.search(r"\b(?:what|which|tell).*(?:videos?|vlogs?)\b", lower) else None,
            "video_greece" if re.search(r"\b(?:film|filmed|video|shot|recorded)\b", lower) and re.search(r"\b(?:greece|athens)\b", lower) else None,
            "video_japan" if re.search(r"\b(?:film|filmed|video|shot|recorded)\b", lower) and re.search(r"\b(?:japan|hokkaido)\b", lower) else None,
            "video_xinjiang" if re.search(r"\b(?:film|filmed|video|shot|recorded)\b", lower) and re.search(r"\bxinjiang\b", lower) else None,
            "camera_xinjiang" if re.search(r"\b(?:camera|cameras|gear)\b", lower) and re.search(r"\bxinjiang\b", lower) else None,
            "favorites_overview" if re.fullmatch(r"(?:what\s+are\s+)?(?:james'?s?\s+)?favorites?", lower.strip(" ,;?!")) else None,
        )
        if entity
    )

    entities = tuple(dict.fromkeys((*focused_subjects(question), *entities)))
    contract = _contract_fields(question)
    return _attach_contract(QueryIntent(
        kind="profile" if topic else "unknown",
        topic=topic,
        entities=entities,
        followup=followup,
        comparison=comparison,
        before_year=int(before_match.group(1)) if before_match else None,
        ordinal=_ordinal(question),
        **contract,
    ), question)
