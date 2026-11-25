"""Repo-relative default locations, so commands work from any directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RULES_DIR = DATA_DIR / "rules"
LAW_PACK = DATA_DIR / "ng-tax-2026.rl"
PATTERNS_DIR = ROOT / "patterns"
