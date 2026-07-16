from __future__ import annotations

import asyncio
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, Field, field_validator

from backend import config
from backend.generation.answer import (
    answer_or_refuse,
    merge_compound_results,
    split_compound_question,
)
from backend.generation.conversation import ConversationState, ConversationStore
from backend.generation.intent import QueryIntent, detect_intent
from backend.generation.query_plan import build_query_plan
from backend.generation.suggestions import build_follow_up_questions
from backend.reranker.inference import Reranker, RerankerUnavailable
from backend.retrieval.bm25 import BM25Index, load_chunks, load_or_build, retrieve

_ROOT = config.ROOT_DIR


def _load_index() -> BM25Index:
    return load_or_build()


class _RateLimiter:
    def __init__(self, limit: int = config.MAX_REQUESTS_PER_MINUTE) -> None:
        self.limit = limit
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        recent = [timestamp for timestamp in self._hits.get(key, []) if now - timestamp < 60]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        if len(self._hits) > 2000:
            self._hits = {
                client: [timestamp for timestamp in timestamps if now - timestamp < 60]
                for client, timestamps in self._hits.items()
                if any(now - timestamp < 60 for timestamp in timestamps)
            }
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = time.time()
    app.state.bm25_index = _load_index()
    app.state.chunks = load_chunks()
    app.state.reranker = None
    app.state.reranker_loaded = False
    app.state.reranker_enabled = config.RERANKER_ENABLED
    app.state.query_planner_enabled = config.QUERY_PLANNER_ENABLED
    if config.RERANKER_ENABLED:
        try:
            app.state.reranker = Reranker()
            app.state.reranker_loaded = True
        except (SystemExit, RerankerUnavailable):
            app.state.reranker = None
            app.state.reranker_loaded = False
    if config.LLM_BACKEND == "groq" and not config.GROQ_API_KEY:
        import warnings
        warnings.warn("LLM_BACKEND=groq but GROQ_API_KEY is not set; generation will fail at request time.")
    app.state.conversations = ConversationStore()
    app.state.rate_limiter = _RateLimiter()
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

_allowed_hosts = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver").split(",")
    if h.strip()
]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


@app.middleware("http")
async def security_headers(http_request: Request, call_next):
    response = await call_next(http_request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    session_id: str | None = Field(default=None, max_length=config.MAX_SESSION_ID_LEN, pattern=r"^[A-Za-z0-9._:-]+$")

    @field_validator("question")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()


class ChatSource(BaseModel):
    chunk_id: str
    text: str
    category: str
    title: str = ""
    label: str = ""
    source: str = "knowledge base"


class ChatResponse(BaseModel):
    status: str
    answer: str
    confidence: float
    sources: list[ChatSource]
    fallback_used: bool
    retrieval_score: float = 0.0
    retrieval_method: str = "none"
    reason: str = ""
    generation_fallback_used: bool = False
    reranker_fallback_used: bool = False
    normalized_query: str = ""
    planner_used: bool = False
    planner_confidence: float = 0.0
    suggested_questions: list[str] = []
    normalization_applied: bool = False


def _display_confidence(raw_score: float, *, status: str, has_sources: bool, reason: str) -> float:
    """Expose a bounded relevance indicator, while keeping the raw BM25 score separate."""

    if not has_sources or status in {"refused", "clarification", "unavailable"}:
        return 0.0
    if reason in {"small_talk", "product_meta"}:
        return 1.0
    if raw_score <= 0:
        return 0.0
    # BM25 scores are query-dependent and are not probabilities. This smooth
    # bounded transform keeps the public field useful without pretending it is
    # a calibrated probability; retrieval_score preserves the diagnostic raw value.
    return round(raw_score / (raw_score + 10.0), 3)


@app.get("/api/health")
async def health(deep: bool = False):
    llm_ready: bool | None = None
    if deep and config.LLM_BACKEND == "ollama":
        try:
            async with httpx.AsyncClient(timeout=config.OLLAMA_HEALTH_TIMEOUT_SECONDS) as client:
                response = await client.get(f"{config.OLLAMA_HOST}/api/tags")
            names = {model.get("name", "") for model in response.json().get("models", [])}
            llm_ready = response.is_success and config.LLM_MODEL in names
        except (httpx.HTTPError, ValueError):
            llm_ready = False
    return {
        "status": "ok" if llm_ready is not False else "degraded",
        "reranker_enabled": getattr(app.state, "reranker_enabled", False),
        "reranker_loaded": getattr(app.state, "reranker_loaded", False),
        "bm25_loaded": getattr(app.state, "bm25_index", None) is not None,
        "retrieval_method": "reranker" if getattr(app.state, "reranker_loaded", False) else "bm25",
        "llm_backend": config.LLM_BACKEND,
        "llm_model": config.LLM_MODEL,
        "query_planner_enabled": getattr(app.state, "query_planner_enabled", config.QUERY_PLANNER_ENABLED),
        "llm_ready": llm_ready,
        "chunks_loaded": len(getattr(app.state, "chunks", [])),
        "uptime_seconds": round(time.time() - getattr(app.state, "started_at", time.time()), 1),
        "local_only_default": os.getenv("HOST", "127.0.0.1") in {"127.0.0.1", "localhost", "::1"},
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    client_host = http_request.headers.get("CF-Connecting-IP") or (http_request.client.host if http_request.client else "unknown")
    if not app.state.rate_limiter.allow(client_host):
        limited = ChatResponse(
            status="unavailable",
            answer="Too many requests right now. Please wait a moment and try again.",
            confidence=0.0,
            sources=[],
            fallback_used=False,
            reason="rate_limited",
            generation_fallback_used=False,
            reranker_fallback_used=app.state.reranker is None,
        )
        return JSONResponse(status_code=429, content=limited.model_dump())

    question = request.question
    index: BM25Index = app.state.bm25_index
    chunks: list[dict] = app.state.chunks

    conversations: ConversationStore = app.state.conversations
    state: ConversationState | None = None
    if request.session_id:
        state = conversations.get(request.session_id)

    reranker: Reranker | None = app.state.reranker
    fallback_used = False
    normalized_queries: list[str] = []
    planner_confidences: list[float] = []
    clause_intents: list[QueryIntent] = []
    normalization_applied = False
    history = state.build_history_messages() if state is not None else None
    questions = split_compound_question(question)
    clause_results: list[dict] = []

    try:
        for clause in questions:
            base_query = state.augment_query(clause) if state is not None else clause
            if config.QUERY_PLANNER_ENABLED:
                plan = build_query_plan(base_query)
                query = plan.retrieval_query
                semantic_question = plan.normalized_question
                normalized_queries.append(plan.normalized_question)
                normalization_applied = normalization_applied or _semantic_query_changed(
                    clause, plan.normalized_question
                )
                planner_confidences.append(plan.confidence)
                clause_intents.append(plan.intent)
            else:
                query = base_query
                semantic_question = query
                normalized_queries.append(query)
                planner_confidences.append(0.0)
                clause_intents.append(detect_intent(semantic_question))
            candidates = retrieve(query, index, chunks, k=config.TOP_K)
            if reranker is not None:
                reranked = reranker.rerank(semantic_question, candidates)
            else:
                reranked = candidates
                fallback_used = True
            clause_results.append(
                await asyncio.to_thread(
                    answer_or_refuse,
                    clause,
                    reranked,
                    history=history,
                    enforce_confidence_threshold=reranker is not None,
                    intent_question=semantic_question,
                )
            )
    except SystemExit:
        raise
    except Exception:
        unavailable = ChatResponse(
            status="unavailable",
            answer=config.UNAVAILABLE_MESSAGE,
            confidence=0.0,
            sources=[],
            fallback_used=fallback_used,
            retrieval_method="reranker" if reranker is not None else "bm25",
            reason="internal_error",
            generation_fallback_used=False,
            reranker_fallback_used=reranker is None,
            normalized_query=" | ".join(normalized_queries),
            planner_used=False,
            planner_confidence=0.0,
            normalization_applied=normalization_applied,
        )
        return JSONResponse(status_code=503, content=unavailable.model_dump())

    result = clause_results[0] if len(clause_results) == 1 else merge_compound_results(questions, clause_results)
    result["normalized_query"] = " | ".join(normalized_queries)
    result["planner_used"] = config.QUERY_PLANNER_ENABLED
    result["planner_confidence"] = min(planner_confidences, default=0.0)

    # BM25-only mode is the intentional production path, not an answer
    # failure. Preserve its retrieval score for clients and diagnostics.
    raw_confidence = float(result["confidence"])
    status = result.get("status", "answered")
    if fallback_used and status == "answered":
        status = "answered"

    sources = [
        ChatSource(
            chunk_id=s["chunk_id"],
            text=s["text"],
            category=s["category"],
            title=s.get("title", ""),
            label=s.get("label", "") or s.get("title", "") or s["category"],
            source=s.get("source", "knowledge base"),
        )
        for s in result.get("sources", [])
    ]
    retrieval_score = float(result.get("confidence", 0.0)) if sources else 0.0
    retrieval_method = "reranker" if reranker is not None else ("bm25" if sources else "none")
    last_intent = clause_intents[-1] if clause_intents else None
    suggested_questions = build_follow_up_questions(last_intent, status)
    confidence = _display_confidence(
        raw_confidence,
        status=status,
        has_sources=bool(sources),
        reason=result.get("reason", ""),
    )

    if state is not None and status == "answered":
        topic = (last_intent.topic if last_intent else None) or (sources[0].category if sources else "unknown")
        entities = last_intent.entities if last_intent else ()
        state.record(
            question,
            result["answer"],
            topic,
            entities=entities,
            normalized_question=normalized_queries[-1] if normalized_queries else question,
        )

    return ChatResponse(
        status=status,
        answer=result["answer"],
        confidence=confidence,
        sources=sources,
        fallback_used=fallback_used or result.get("fallback_used", False),
        retrieval_score=retrieval_score,
        retrieval_method=retrieval_method,
        reason=result.get("reason", ""),
        generation_fallback_used=bool(result.get("fallback_used", False)),
        reranker_fallback_used=reranker is None,
        normalized_query=result["normalized_query"],
        planner_used=result["planner_used"],
        planner_confidence=result["planner_confidence"],
        suggested_questions=suggested_questions,
        normalization_applied=normalization_applied,
    )


def _semantic_query_changed(original: str, normalized: str) -> bool:
    """Ignore punctuation-only cleanup when reporting an interpretation hint."""

    def comparable(value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()

    return comparable(original) != comparable(normalized)


def _safe_file_response(directory: Path, filename: str) -> FileResponse:
    # Security: resolve the target and ensure it stays within the served
    # directory so attackers cannot escape it via "../" path traversal.
    base = directory.resolve()
    target = (directory / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=404)
    if not target.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(str(target))


if (_ROOT / "scripts").is_dir():

    @app.get("/scripts/{filename}")
    async def _serve_scripts(filename: str):
        return _safe_file_response(_ROOT / "scripts", filename)


if (_ROOT / "styles").is_dir():

    @app.get("/styles/{filename}")
    async def _serve_styles(filename: str):
        return _safe_file_response(_ROOT / "styles", filename)


if (_ROOT / "assets" / "pictures").is_dir():

    @app.get("/assets/pictures/{filename}")
    async def _serve_pictures(filename: str):
        return _safe_file_response(_ROOT / "assets" / "pictures", filename)


if (_ROOT / "assets" / "pdf").is_dir():

    @app.get("/assets/pdf/{filename}")
    async def _serve_pdf(filename: str):
        return _safe_file_response(_ROOT / "assets" / "pdf", filename)


if (_ROOT / "assets" / "thumbnails").is_dir():

    @app.get("/assets/thumbnails/{filename}")
    async def _serve_thumbnails(filename: str):
        return _safe_file_response(_ROOT / "assets" / "thumbnails", filename)


_VIEWS = _ROOT / "views"
if _VIEWS.is_dir():

    @app.get("/")
    async def _serve_index():
        return FileResponse(str(_VIEWS / "index.html"))

    @app.get("/essays")
    async def _serve_essays():
        return FileResponse(str(_VIEWS / "essays.html"))

    @app.get("/photography")
    async def _serve_photography():
        return FileResponse(str(_VIEWS / "photography.html"))

    @app.get("/videos")
    async def _serve_videos():
        return FileResponse(str(_VIEWS / "videos.html"))

    @app.get("/hobbies")
    async def _serve_hobbies():
        return FileResponse(str(_VIEWS / "hobbies.html"))
