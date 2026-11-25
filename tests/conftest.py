from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "data" / "rules"


@pytest.fixture
def law_pack(tmp_path):
    """A fresh law pack built from the real rule YAML (unverified allowed)."""
    from inforce import loader
    out = tmp_path / "law.rl"
    report = loader.load(RULES, out, allow_unverified=True)
    return out, report
