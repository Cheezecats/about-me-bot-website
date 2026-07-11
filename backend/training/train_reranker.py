from __future__ import annotations

import json
import math
import random

import torch
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


def _run_epoch(
    model,
    tokenizer,
    rows: list[dict],
    device: torch.device,
    batch_size: int,
    optimizer: AdamW | None = None,
    scheduler=None,
) -> tuple[float, float]:
    is_train = optimizer is not None
    model.train(is_train)
    order = list(range(len(rows)))
    if is_train:
        random.Random(42).shuffle(order)
    total_loss = 0.0
    total_correct = 0
    total = 0
    for start in range(0, len(order), batch_size):
        batch_idx = order[start : start + batch_size]
        questions = [rows[i]["question"] for i in batch_idx]
        texts = [rows[i]["text"] for i in batch_idx]
        labels = torch.tensor(
            [rows[i]["label"] for i in batch_idx], dtype=torch.long, device=device
        )
        enc = _encode_batch(tokenizer, questions, texts)
        enc = {k: v.to(device) for k, v in enc.items()}
        if is_train:
            optimizer.zero_grad()
        with torch.set_grad_enabled(is_train):
            outputs = model(**enc, labels=labels)
            loss = outputs.loss
            if is_train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
        total_loss += loss.item() * len(batch_idx)
        preds = outputs.logits.argmax(dim=-1)
        total_correct += (preds == labels).sum().item()
        total += len(batch_idx)
    return total_loss / max(total, 1), total_correct / max(total, 1)


def _copy_state(model) -> dict:
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def train() -> None:
    if not config.TRAIN_PATH.exists() or not config.VAL_PATH.exists():
        raise SystemExit(
            "data/train.jsonl or data/val.jsonl not found. "
            "Run `python -m backend.training.build_dataset` first."
        )

    random.seed(42)
    torch.manual_seed(42)

    train_rows = _load_jsonl(config.TRAIN_PATH)
    val_rows = _load_jsonl(config.VAL_PATH)
    device = _device()
    print(
        f"[train] device={device} train_rows={len(train_rows)} val_rows={len(val_rows)}"
    )

    tokenizer = AutoTokenizer.from_pretrained(config.BASE_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.BASE_MODEL_NAME, num_labels=2
    )
    model.to(device)
    optimizer = AdamW(
        model.parameters(), lr=config.TRAIN_LEARNING_RATE, weight_decay=0.01
    )
    steps_per_epoch = math.ceil(len(train_rows) / config.TRAIN_BATCH_SIZE)
    total_steps = steps_per_epoch * config.TRAIN_EPOCHS
    warmup_steps = int(0.1 * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    best_val_loss = float("inf")
    best_state: dict | None = None
    patience = 1
    epochs_no_improve = 0
    history_epochs: list[dict] = []

    for epoch in range(1, config.TRAIN_EPOCHS + 1):
        train_loss, train_acc = _run_epoch(
            model,
            tokenizer,
            train_rows,
            device,
            config.TRAIN_BATCH_SIZE,
            optimizer,
            scheduler,
        )
        val_loss, val_acc = _run_epoch(
            model, tokenizer, val_rows, device, config.TRAIN_BATCH_SIZE
        )
        print(
            f"[train] epoch {epoch}/{config.TRAIN_EPOCHS} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        history_epochs.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
            }
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = _copy_state(model)
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            print(f"[train] val loss did not improve ({epochs_no_improve}/{patience})")
            if epochs_no_improve >= patience:
                print("[train] early stopping triggered")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    config.RERANKER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(config.RERANKER_MODEL_DIR)
    tokenizer.save_pretrained(config.RERANKER_MODEL_DIR)

    history = {
        "epochs": history_epochs,
        "best_val_loss": best_val_loss,
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
        f"(best val_loss={best_val_loss:.4f})"
    )
    print(f"[train] saved training history to {training_history_path}")


def main() -> None:
    train()


if __name__ == "__main__":
    main()
