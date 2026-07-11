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
BASE_MODEL_NAME = "distilbert-base-uncased"

TOP_K = 10
CONFIDENCE_THRESHOLD = 0.40
MAX_HISTORY_TURNS = 3
MAX_QUERY_LEN = 500

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

REFUSAL_MESSAGE = "I don't have that information about James."

GROUNDING_SYSTEM_PROMPT = (
    "You are an assistant that answers questions about James Sui, a student in Shanghai. "
    "Answer the user's question using ONLY the provided context. "
    "If the context does not contain the answer, respond exactly: "
    "\"I don't have that information about James.\" "
    "Do not guess, do not use outside knowledge, and do not add facts that are not in the context."
)

TRAIN_LEARNING_RATE = 2e-5
TRAIN_EPOCHS = 3
TRAIN_BATCH_SIZE = 16
TRAIN_VAL_SPLIT = 0.15
TRAIN_TEST_SPLIT = 0.15
NEGATIVES_PER_POSITIVE = 4
TARGET_PRECISION_AT_1 = 0.70

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
