from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from backend import config
from backend.generation.answer import (
    answer_or_refuse,
    merge_compound_results,
    split_compound_question,
)
from backend.generation.conversation import ConversationState
from backend.reranker.inference import Reranker, RerankerUnavailable
from backend.retrieval.bm25 import BM25Index, load_chunks, load_or_build, retrieve

_ROOT = config.ROOT_DIR


def _load_index() -> BM25Index:
    return load_or_build()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.bm25_index = _load_index()
    app.state.chunks = load_chunks()
    app.state.reranker = None
    app.state.reranker_loaded = False
    app.state.reranker_enabled = config.RERANKER_ENABLED
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
    app.state.conversations = {}
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

_allowed_hosts = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    session_id: str | None = None

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


class ChatResponse(BaseModel):
    status: str
    answer: str
    confidence: float
    sources: list[ChatSource]
    fallback_used: bool
    retrieval_score: float = 0.0
    retrieval_method: str = "none"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "reranker_enabled": getattr(app.state, "reranker_enabled", False),
        "reranker_loaded": getattr(app.state, "reranker_loaded", False),
        "bm25_loaded": getattr(app.state, "bm25_index", None) is not None,
        "retrieval_method": "reranker" if getattr(app.state, "reranker_loaded", False) else "bm25",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    question = request.question
    index: BM25Index = app.state.bm25_index
    chunks: list[dict] = app.state.chunks

    conversations: dict[str, ConversationState] = app.state.conversations
    state: ConversationState | None = None
    if request.session_id:
        state = conversations.get(request.session_id)
        if state is None:
            state = ConversationState()
            conversations[request.session_id] = state

    reranker: Reranker | None = app.state.reranker
    fallback_used = False
    history = state.build_history_messages() if state is not None else None
    questions = split_compound_question(question)
    clause_results: list[dict] = []

    try:
        for clause in questions:
            query = state.augment_query(clause) if state is not None else clause
            candidates = retrieve(query, index, chunks, k=config.TOP_K)
            if reranker is not None:
                reranked = reranker.rerank(clause, candidates)
            else:
                reranked = candidates
                fallback_used = True
            clause_results.append(
                answer_or_refuse(
                    clause,
                    reranked,
                    history=history,
                    enforce_confidence_threshold=reranker is not None,
                )
            )
    except (SystemExit, Exception):
        unavailable = ChatResponse(
            status="unavailable",
            answer="",
            confidence=0.0,
            sources=[],
            fallback_used=fallback_used,
            retrieval_method="reranker" if reranker is not None else "bm25",
        )
        return JSONResponse(status_code=503, content=unavailable.model_dump())

    result = clause_results[0] if len(clause_results) == 1 else merge_compound_results(questions, clause_results)

    confidence = 0.0 if fallback_used else float(result["confidence"])
    status = result.get("status", "answered")
    if fallback_used and status == "answered":
        status = "answered"

    sources = [
        ChatSource(
            chunk_id=s["chunk_id"],
            text=s["text"],
            category=s["category"],
        )
        for s in result.get("sources", [])
    ]
    retrieval_score = float(result.get("confidence", 0.0)) if sources else 0.0
    retrieval_method = "reranker" if reranker is not None else ("bm25" if sources else "none")

    if state is not None:
        topic = sources[0].category if sources else "unknown"
        state.record(question, result["answer"], topic)

    return ChatResponse(
        status=status,
        answer=result["answer"],
        confidence=confidence,
        sources=sources,
        fallback_used=fallback_used or result.get("fallback_used", False),
        retrieval_score=retrieval_score,
        retrieval_method=retrieval_method,
    )


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
