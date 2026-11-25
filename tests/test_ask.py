import pytest

from inforce import ask as ask_mod
from inforce.ask import ask, fulltext_query


@pytest.mark.parametrize("q,expected", [
    ("What is (rent) relief?", "rent OR relief"),
    ("PIT: first 800,000?", "pit OR first OR 800,000"),
    ("is it?", None),
])
def test_fulltext_query_is_safe(q, expected):
    assert fulltext_query(q) == expected


@pytest.fixture(params=["hybrid", "fulltext"])
def mode(request, monkeypatch):
    if request.param == "fulltext":
        monkeypatch.setattr(ask_mod, "embed", lambda texts: None)
    return request.param


def test_named_rule_comes_first(law_pack, mode):
    path, _ = law_pack
    r = ask("Can I still claim the consolidated relief allowance?", "2026-11-25", path)
    if mode == "fulltext":
        assert r["mode"] == "fulltext"
    top = r["items"][0]
    assert (top["rule"], top["status"]) == ("ng.pit.cra.old", "REPEALED")
    assert r["answer"]["ref"] is None and "no replacement" in r["answer"]["how"]
    assert [x["id"] for x in top["related"]] == ["ng.pit.rent_relief.2026"]


def test_amount_finds_the_band(law_pack, mode):
    path, _ = law_pack
    r = ask("How much tax on the first 800,000 naira of income?", "2026-11-25", path)
    assert r["items"][0]["rule"] == "ng.pit.band1.2026"
    assert r["answer"] == {"ref": "ng.pit.band1.2026", "text": "PIT: first NGN 800,000 at 0%",
                           "status": "IN_FORCE", "how": "in force"}


def test_repealed_hit_answers_with_successor(law_pack, mode):
    path, _ = law_pack
    r = ask("Is the first ₦300,000 still taxed at 7%?", "2026-11-25", path)
    assert r["items"][0]["rule"] == "ng.pit.band1.old"
    assert r["answer"]["ref"] == "akn/ng/act/2025/7/sec_58"


def test_same_question_before_the_reform(law_pack, mode):
    path, _ = law_pack
    r = ask("Is the first ₦300,000 still taxed at 7%?", "2025-06-01", path)
    assert r["answer"] == {"ref": "ng.pit.band1.old", "text": "PIT: first NGN 300,000 at 7%",
                           "status": "IN_FORCE", "how": "in force"}


def test_no_match(law_pack, monkeypatch):
    monkeypatch.setattr(ask_mod, "embed", lambda texts: None)
    path, _ = law_pack
    r = ask("zzzz qqqq", "2026-11-25", path)
    assert r["verdict"] == "NO_MATCH" and r["answer"] is None
