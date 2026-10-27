"""Tương thích ngược: logic nằm ở `app/storage/recipe_metadata.py` (dùng chung với API)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.storage.recipe_metadata import *  # noqa: E402,F401,F403
from app.storage.recipe_metadata import (  # noqa: E402,F401
    OVERLAY_KEYS,
    OVERLAY_PATH,
    RULES_PATH,
    apply_overlay,
    apply_storage_rules,
    load_rules,
    primary_rule,
    rule_matches,
)
