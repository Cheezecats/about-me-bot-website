from __future__ import annotations

import torch


def score_logits(logits: torch.Tensor) -> tuple[list[float], list[float]]:
    probs = torch.softmax(logits, dim=-1)
    class_1_probs = probs[:, 1].tolist()
    margins = (logits[:, 1] - logits[:, 0]).tolist()
    return class_1_probs, margins


def rank_scores(logits: torch.Tensor) -> list[float]:
    probs = torch.softmax(logits, dim=-1)
    return probs[:, 1].tolist()
