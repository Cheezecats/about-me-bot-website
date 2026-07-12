import importlib

from backend import config


def test_reranker_is_opt_in_by_default(monkeypatch):
    monkeypatch.delenv("RERANKER_ENABLED", raising=False)
    reloaded_config = importlib.reload(config)
    assert reloaded_config.RERANKER_ENABLED is False
