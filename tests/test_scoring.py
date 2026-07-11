import torch

from backend.reranker.scoring import rank_scores, score_logits


def test_rank_scores_uses_softmax_not_sigmoid():
    logits = torch.tensor([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]])
    scores = rank_scores(logits)
    expected = torch.softmax(logits, dim=-1)[:, 1].tolist()
    assert scores == expected
    assert abs(scores[0] - 0.7311) < 0.001
    assert abs(scores[1] - 0.2689) < 0.001
    assert abs(scores[2] - 0.5) < 0.001


def test_rank_scores_differs_from_sigmoid():
    logits = torch.tensor([[5.0, 5.0]])
    scores = rank_scores(logits)
    sigmoid_val = torch.sigmoid(logits[:, 1]).item()
    assert abs(scores[0] - 0.5) < 0.001
    assert abs(sigmoid_val - 0.9933) < 0.001
    assert scores[0] != sigmoid_val


def test_score_logits_returns_probs_and_margins():
    logits = torch.tensor([[0.0, 2.0], [1.0, 1.0]])
    probs, margins = score_logits(logits)
    assert len(probs) == 2
    assert len(margins) == 2
    assert margins[0] == 2.0
    assert margins[1] == 0.0
    assert probs[0] > probs[1]
