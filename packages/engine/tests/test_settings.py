"""The settings the engine reads, as their seed files hold them (core/settings.py)."""

import ast

from engine.core import db, settings


def _named_in_code() -> set[str]:
    """Every string the engine's code holds whole; a purpose it asks a prompt for is one of them."""
    named: set[str] = set()
    for path in (db.REPO_ROOT / "packages/engine/engine").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                named.add(node.value)
    return named


def test_every_prompt_the_seed_makes_active_is_one_the_engine_asks_for():
    """Rule 7: a prompt is made active once its eval is scored, so an active prompt no code asks for claims a use and a
    score it does not have. `read_cells` and `word_context` did, from the first seed until 2026-10-01; a prompt
    designed for a later step stays inactive until that step asks for it (goals/p1-no-loose-ends.yaml)."""
    active = {p["purpose"] for p in settings.seed("prompts.json", "prompts") if p.get("active")}
    assert sorted(active - _named_in_code()) == []
