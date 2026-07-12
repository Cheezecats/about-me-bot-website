from __future__ import annotations

import json
import math
import random

import torch
import torch.nn.functional as F
from torch.optim import AdamW
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from backend import config


def _load_jsonl(path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _encode_batch(tokenizer, questions: list[str], texts: list[str]) -> dict:
    return tokenizer(
        questions,
        texts,
        truncation=True,
        padding=True,
        max_length=256,
        return_tensors="pt",
    )


def _group_rows(rows: list[dict]) -> list[list[dict]]:
    """Return one positive-plus-negatives group for every training question."""

    by_question: dict[str, list[dict]] = {}
    for row in rows:
        by_question.setdefault(row["question"], []).append(row)

    groups: list[list[dict]] = []
    for question, group in sorted(by_question.items()):
        positives = [row for row in group if row["label"] == 1]
        if len(positives) != 1:
            raise ValueError(
                f"Expected exactly one positive row for question {question!r}; "
                f"found {len(positives)}."
            )
        if len(group) < 2:
            raise ValueError(f"Question {question!r} has no negative candidates.")
        groups.append(group)
    return groups


def _run_epoch(
    model,
    tokenizer,
    groups: list[list[dict]],
    device: torch.device,
    batch_size: int,
    optimizer: AdamW | None = None,
    scheduler=None,
) -> tuple[float, float, float]:
    """Train/evaluate a listwise reranker and return loss, P@1, and MRR."""

    is_train = optimizer is not None
    model.train(is_train)
    order = list(range(len(groups)))
    if is_train:
        random.shuffle(order)
    total_loss = 0.0
    top1_correct = 0
    reciprocal_rank_sum = 0.0
    total_questions = 0
    for start in range(0, len(order), batch_size):
        batch_idx = order[start : start + batch_size]
        batch_groups = [groups[i] for i in batch_idx]
        candidates_per_question = len(batch_groups[0])
        if any(len(group) != candidates_per_question for group in batch_groups):
            raise ValueError("All question groups in a batch must have the same size.")

        questions = [row["question"] for group in batch_groups for row in group]
        texts = [row["text"] for group in batch_groups for row in group]
        targets = torch.tensor(
            [next(i for i, row in enumerate(group) if row["label"] == 1) for group in batch_groups],
            dtype=torch.long,
            device=device,
        )
        enc = _encode_batch(tokenizer, questions, texts)
        enc = {k: v.to(device) for k, v in enc.items()}
        if is_train:
            optimizer.zero_grad()
        with torch.set_grad_enabled(is_train):
            outputs = model(**enc)
            # The positive-class logit margin is monotonic with the softmax
            # score used by inference, while cross entropy compares all five
            # candidates for the same question directly.
            pair_scores = (outputs.logits[:, 1] - outputs.logits[:, 0]).reshape(
                len(batch_groups), candidates_per_question
            )
            loss = F.cross_entropy(pair_scores, targets)
            if is_train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
        total_loss += loss.item() * len(batch_groups)
        ranked = pair_scores.argsort(dim=1, descending=True)
        ranks = (ranked == targets.unsqueeze(1)).nonzero(as_tuple=False)[:, 1] + 1
        top1_correct += (ranks == 1).sum().item()
        reciprocal_rank_sum += (1.0 / ranks.float()).sum().item()
        total_questions += len(batch_groups)
    return (
        total_loss / max(total_questions, 1),
        top1_correct / max(total_questions, 1),
        reciprocal_rank_sum / max(total_questions, 1),
    )


def _copy_state(model) -> dict:
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def train() -> None:
    if not config.TRAIN_PATH.exists() or not config.VAL_PATH.exists():
        raise SystemExit(
            "data/train.jsonl or data/val.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )

    random.seed(config.RANDOM_SEED)
    torch.manual_seed(config.RANDOM_SEED)

    train_rows = _load_jsonl(config.TRAIN_PATH)
    val_rows = _load_jsonl(config.VAL_PATH)
    train_groups = _group_rows(train_rows)
    val_groups = _group_rows(val_rows)
    device = _device()
    print(
        f"[train] device={device} train_questions={len(train_groups)} "
        f"val_questions={len(val_groups)} candidates_per_question={len(train_groups[0])}"
    )

    tokenizer = AutoTokenizer.from_pretrained(config.BASE_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.BASE_MODEL_NAME, num_labels=2
    )
    model.to(device)
    optimizer = AdamW(
        model.parameters(), lr=config.TRAIN_LEARNING_RATE, weight_decay=0.01
    )
    steps_per_epoch = math.ceil(len(train_groups) / config.TRAIN_BATCH_SIZE)
    total_steps = steps_per_epoch * config.TRAIN_EPOCHS
    warmup_steps = int(0.1 * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    best_val_mrr = float("-inf")
    best_state: dict | None = None
    patience = config.TRAIN_EARLY_STOPPING_PATIENCE
    epochs_no_improve = 0
    history_epochs: list[dict] = []

    for epoch in range(1, config.TRAIN_EPOCHS + 1):
        train_loss, train_p1, train_mrr = _run_epoch(
            model,
            tokenizer,
            train_groups,
            device,
            config.TRAIN_BATCH_SIZE,
            optimizer,
            scheduler,
        )
        val_loss, val_p1, val_mrr = _run_epoch(
            model, tokenizer, val_groups, device, config.TRAIN_BATCH_SIZE
        )
        print(
            f"[train] epoch {epoch}/{config.TRAIN_EPOCHS} "
            f"train_loss={train_loss:.4f} train_p@1={train_p1:.4f} train_mrr={train_mrr:.4f} "
            f"val_loss={val_loss:.4f} val_p@1={val_p1:.4f} val_mrr={val_mrr:.4f}"
        )
        history_epochs.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_precision_at_1": train_p1,
                "train_mrr": train_mrr,
                "val_loss": val_loss,
                "val_precision_at_1": val_p1,
                "val_mrr": val_mrr,
            }
        )

        if val_mrr > best_val_mrr:
            best_val_mrr = val_mrr
            best_state = _copy_state(model)
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            print(f"[train] val MRR did not improve ({epochs_no_improve}/{patience})")
            if epochs_no_improve >= patience:
                print("[train] early stopping triggered")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    config.RERANKER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(config.RERANKER_MODEL_DIR)
    tokenizer.save_pretrained(config.RERANKER_MODEL_DIR)

    history = {
        "objective": "listwise_cross_entropy",
        "candidates_per_question": len(train_groups[0]),
        "epochs": history_epochs,
        "best_val_mrr": best_val_mrr,
        "total_steps": total_steps,
        "warmup_steps": warmup_steps,
        "weight_decay": 0.01,
        "learning_rate": config.TRAIN_LEARNING_RATE,
    }
    training_history_path = config.DATA_DIR / "training_history.json"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    training_history_path.write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[train] saved model+tokenizer to {config.RERANKER_MODEL_DIR} "
        f"(best val_mrr={best_val_mrr:.4f})"
    )
    print(f"[train] saved training history to {training_history_path}")


def main() -> None:
    train()


if __name__ == "__main__":
    main()
