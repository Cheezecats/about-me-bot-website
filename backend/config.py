from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
KB_EXTRA_DIR = ROOT_DIR / "kb_extra"
CONTENT_TS_PATH = ROOT_DIR / "src" / "data" / "content.ts"

CHUNKS_PATH = DATA_DIR / "chunks.json"
CONTENT_EXPORT_PATH = DATA_DIR / "content_export.json"
BM25_INDEX_PATH = DATA_DIR / "bm25_index.json"
QA_PAIRS_PATH = DATA_DIR / "qa_pairs.jsonl"
TRAIN_PATH = DATA_DIR / "train.jsonl"
VAL_PATH = DATA_DIR / "val.jsonl"
TEST_PATH = DATA_DIR / "test.jsonl"
EVAL_RESULTS_PATH = DATA_DIR / "eval_results.json"

RERANKER_MODEL_DIR = MODELS_DIR / "reranker"
# Keep experimental rerankers out of the live request path until they have
# beaten the BM25 baseline and passed threshold calibration. Set
# RERANKER_ENABLED=true only for a validated model.
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "false").lower() in {"1", "true", "yes"}
RERANKER_BACKEND = os.getenv("RERANKER_BACKEND", "zeroshot_cross_encoder")
ZEROSHOT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
BASE_MODEL_NAME = "distilbert-base-uncased"

TOP_K = 10
CONFIDENCE_THRESHOLD = 0.40
MAX_HISTORY_TURNS = 3
MAX_QUERY_LEN = 500
CHATBOT_NAME = "JamChat"
# Facts James has decided not to present through the public chatbot. Keep the
# raw source corpus intact for private project maintenance, but never index or
# retrieve these chunks in the live chat path.
HIDDEN_CHAT_CHUNK_IDS = frozenset({"projects_skills_flappy_bird_game_012"})
MAX_SESSION_ID_LEN = 128
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
SESSION_TTL_SECONDS = 60 * 60
MAX_CONVERSATIONS = 1000
QUERY_PLANNER_ENABLED = os.getenv("QUERY_PLANNER_ENABLED", "true").lower() in {"1", "true", "yes"}

BM25_K1 = 1.5
BM25_B = 0.75

MAX_CHUNK_WORDS = 60

LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "https://cheezecats.github.io,http://localhost:5173").split(
        ","
    )
    if o.strip()
]

REFUSAL_MESSAGE = (
    "That detail isn't in James's public profile, so I won't guess. I can help with "
    "his public projects, hobbies, sports, photography, essays, achievements, "
    "travel, or favorites."
)
UNAVAILABLE_MESSAGE = "I couldn't generate an answer right now. Please try again in a moment."
CLARIFICATION_MESSAGE = (
    "Which topic should I continue with—James's projects, hobbies, sports, photography, "
    "essays, travel, or favorites?"
)

GROUNDING_SYSTEM_PROMPT = (
    "You are an assistant that answers questions about James Sui, a student in Shanghai. "
    "Answer the user's question using ONLY the provided context. "
    "If the context does not contain the answer, respond exactly with the configured refusal message. "
    "Do not guess, do not infer ages from years, do not infer favorites from general usage, "
    "do not use outside knowledge, and do not add facts that are not in the context. "
    "For lists, use concise bullets. For comparisons, keep each category separate. "
    "For ambiguous follow-up questions, answer only when the conversation and context identify one topic; otherwise ask the user to clarify."
)

TRAIN_LEARNING_RATE = 2e-5
TRAIN_EPOCHS = 8
# Number of question groups per batch. Each group contains one positive chunk
# and four negatives, so this is not a flat pair-classification batch size.
TRAIN_BATCH_SIZE = 16
TRAIN_EARLY_STOPPING_PATIENCE = 2
TRAIN_VAL_SPLIT = 0.15
TRAIN_TEST_SPLIT = 0.15
NEGATIVES_PER_POSITIVE = 4
TARGET_PRECISION_AT_1 = 0.70
RANDOM_SEED = 42

# Threshold selection is performed on validation data only. A threshold is
# deployable only when it meets both operational error-rate requirements.
MAX_FALSE_REFUSAL_RATE = 0.20
MAX_UNSAFE_ANSWER_RATE = 0.10
UNANSWERABLE_CALIBRATION_SPLIT = 0.70

PII_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{3,30}(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)\b",
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    r"\b1[3-9]\d{9}\b",
    r"\b\d{17}[\dXx]\b",
    r"\b(?:QQ|WeChat|微信|qq)\s*[:：]?\s*\w+\b",
]
PRIVATE_KB_PATTERNS = PII_PATTERNS + [
    r"\bpassword\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:19|20)\d{2}-\d{1,2}-\d{1,2}\b",
]
