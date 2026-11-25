"""Local CPU embeddings (model2vec). Optional: everything works without them (full-text only).

The law pack stores precomputed rule embeddings, so building or shipping it needs the model
once; `ask` needs it only to embed the question, and falls back to full-text when the model
is not installed or not cached (e.g. offline).
"""
from __future__ import annotations

from functools import cache

MODEL = "minishlab/potion-base-8M"  # 256 dimensions (checked 2026-11-25; schema.cypher matches)
DIMENSIONS = 256


@cache
def load_model():
    """The model, or None if model2vec is missing or the model is neither cached nor downloadable."""
    try:
        from model2vec import StaticModel
    except ImportError:
        return None
    try:
        # force_download defaults to True in model2vec: it would hit the network on every call.
        return StaticModel.from_pretrained(MODEL, force_download=False)
    except Exception:  # noqa: BLE001 - offline, no cache, hub error: fall back to full-text
        return None


def embed(texts: list[str]) -> list[list[float]] | None:
    model = load_model()
    if model is None:
        return None
    return [[float(x) for x in v] for v in model.encode(texts)]


def rule_text(rule: dict) -> str:
    """What is embedded for a rule: its topic words and text."""
    return f"{(rule.get('topic') or '').replace('_', ' ')}: {rule.get('text') or ''}"
