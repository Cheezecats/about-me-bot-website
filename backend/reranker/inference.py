from __future__ import annotations

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend import config
from backend.reranker.scoring import rank_scores


class RerankerUnavailable(Exception):
    pass


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class Reranker:
    def __init__(
        self,
        model_dir: Path = config.RERANKER_MODEL_DIR,
        backend: str = config.RERANKER_BACKEND,
    ) -> None:
        self.device = _device()
        self.backend = backend
        if backend == "zeroshot_cross_encoder":
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RerankerUnavailable(
                    "sentence-transformers is required for the zero-shot cross-encoder. "
                    "Install the project's ml extra."
                ) from exc
            self.cross_encoder = CrossEncoder(
                config.ZEROSHOT_CROSS_ENCODER_MODEL, device=str(self.device)
            )
            self.tokenizer = None
            self.model = None
            return
        if backend != "finetuned_distilbert":
            raise RerankerUnavailable(f"Unknown reranker backend: {backend!r}")
        if not model_dir.exists():
            raise RerankerUnavailable(
                f"Reranker model not found at {model_dir}. "
                "Train it first with `python -m backend.training.train_reranker`."
            )
        self.cross_encoder = None
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []
        texts = [c["text"] for c in chunks]
        if self.backend == "zeroshot_cross_encoder":
            pairs = [[query, text] for text in texts]
            scores = self.cross_encoder.predict(
                pairs, batch_size=32, show_progress_bar=False
            ).tolist()
            scored = [{**c, "score": round(float(s), 4)} for c, s in zip(chunks, scores)]
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored
        enc = self.tokenizer(
            [query] * len(texts),
            texts,
            truncation=True,
            padding=True,
            max_length=256,
            return_tensors="pt",
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}
        logits = self.model(**enc).logits
        probs = rank_scores(logits)
        scored = [{**c, "score": round(float(s), 4)} for c, s in zip(chunks, probs)]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
