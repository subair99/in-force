"""`inforce ask "<question>" --on D`: which rules answer this, and are they in force on D?

Hybrid retrieval over the law pack: a vector search on precomputed rule embeddings
(model2vec, local CPU) and a full-text search, fused by reciprocal rank. Each hit's status on
the date comes from the same Cypher as every other verdict; a repealed hit shows what
replaced it. Without the embedding model (offline, not cached) it runs full-text only and
says so. It retrieves rules; it does not write an answer.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import law
from .check import DISCLAIMER
from .cite_parser import extract
from .embed import embed
from .store import open_store

RRF_K = 60
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how", "i", "in", "is",
    "it", "my", "of", "on", "or", "the", "to", "under", "what", "when", "which", "who", "will", "with", "much",
    "now", "still", "there", "this", "that", "any", "s",
}


def fulltext_query(question: str) -> str | None:
    """Plain terms joined with OR: the full-text parser rejects field prefixes (:) and parentheses."""
    terms = [t for t in re.findall(r"[A-Za-z]+|\d[\d,]*", question.lower()) if t not in STOPWORDS and len(t) > 1]
    return " OR ".join(dict.fromkeys(terms)) or None


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", text or "")}


def _cited_rules(store, question: str) -> list[dict[str, Any]]:
    """Rules the question names, by the same patterns `check` uses (e.g. "CRA", "first N300,000 at 7%")."""
    out: list[str] = []
    for c in extract(question):
        if c.kind == "concept":
            out.append(c.rule)
        elif c.kind == "figure":
            for rid in law.rules_by_value(store, c.topic, c.value):
                r = store.run("rule_info", id=rid)
                if r and (not c.amount or c.amount in _numbers(r[0]["text"])):
                    out.append(rid)
    return [{"id": rid} for rid in dict.fromkeys(out)]


def _amount_rules(store, question: str) -> list[dict[str, Any]]:
    """Rules whose text contains an amount (>= 1,000) written in the question."""
    amounts = {n for n in _numbers(question) if len(n) >= 4}
    if not amounts:
        return []
    return [{"id": r["id"]} for r in store.run("all_rules") if amounts & _numbers(r["text"])]


def ask(question: str, on: str, law_pack: str | Path, top: int = 5, log=None) -> dict[str, Any]:
    vec = embed([question])
    mode = "hybrid" if vec else "fulltext"
    ft = fulltext_query(question)
    with open_store(law_pack, read_only=True, log=log) as store:
        ranks: dict[str, dict[str, Any]] = {}
        # Exact signals first (and counted twice): rules named by citation patterns, then by amount.
        sources = [("cited", _cited_rules(store, question))] * 2 + [("amount", _amount_rules(store, question))]
        if vec:
            sources.append(("vector", store.run("ask_vector", q=vec[0])))
        if ft:
            sources.append(("fulltext", store.run("ask_fulltext", q=ft)))
        for name, rows in sources:
            for rank, row in enumerate(rows, 1):
                hit = ranks.setdefault(row["id"], {"id": row["id"], "score": 0.0, "via": []})
                hit["score"] += 1.0 / (RRF_K + rank)
                if name not in hit["via"]:
                    hit["via"].append(name)
        hits = sorted(ranks.values(), key=lambda h: (-h["score"], h["id"]))[:top]
        items = []
        for h in hits:
            r = law.rule_status(store, h["id"], on)
            succ = r["successors"][0] if r["successors"] else None
            scale = r.get("scale")
            items.append({
                "rule": r["id"], "text": r["text"], "status": r["status"], "verified": r["verified"],
                "provision": r["provision"], "source": r["source"], "endedOn": r["endedOn"],
                "successor": succ["text"] if succ else (law.scale_text(scale) if scale else None),
                "successorRef": succ["id"] if succ else (scale["provision"] if scale else None),
                "related": [{"id": x["id"], "text": x["text"]} for x in r.get("related", [])],
                "score": round(h["score"], 5), "via": h["via"], "path": r["path"],
            })
    # The answer follows the best hit: itself if live on the date, else what replaced it (if anything).
    answer = None
    if items:
        topi = items[0]
        if topi["status"] in law.LIVE:
            answer = {"ref": topi["rule"], "text": topi["text"], "status": topi["status"], "how": "in force"}
        elif topi["successorRef"]:
            answer = {"ref": topi["successorRef"], "text": topi["successor"], "status": "IN_FORCE",
                      "how": f"{topi['rule']} is {topi['status']}; replaced by"}
        else:
            answer = {"ref": None, "text": None, "status": topi["status"],
                      "how": f"{topi['rule']} is {topi['status']} with no replacement"}
    return {"question": question, "on": on, "mode": mode, "query": ft,
            "verdict": "FOUND" if items else "NO_MATCH", "answer": answer,
            "items": items, "disclaimer": DISCLAIMER}
