"""Every model eval is held to a bar, and the bar is a row (goals/p1-done-means-every-check.yaml).

The bars are the seed's `eval.<purpose>.<measure>` threshold rows; these drive `engine eval` through its own command
with each eval's result stood in for the model, so what is checked is the command's verdict on a score.
"""

import json
import os
import re

import pytest
from typer.testing import CliRunner

from engine import cli
from engine.checks import bars
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SEED = json.loads((db.REPO_ROOT / "supabase" / "seed" / "thresholds.json").read_text())["thresholds"]
# every purpose `engine eval` scores; item_generate has had no score recorded since it was made active (STATE.md,
# "not yet run across all four sets"), so it has no bar yet, and its eval cannot pass until it has one
NONE_ON_RECORD = {"item_generate"}


def _seeded(conn, purpose):
    head = f"eval.{purpose}."
    return {t["key"].removeprefix(head): float(t["value"]) for t in SEED if t["key"].startswith(head)}


def _eval(monkeypatch, *args):
    monkeypatch.setattr(bars, "bars", _seeded)  # the seed's bars, loaded or not on this copy
    return CliRunner().invoke(cli.app, ["eval", *args])


def test_every_eval_holds_its_score_to_a_bar_on_record():
    """Each purpose `engine eval` scores has its bar rows, but the one with no score on record; each row says where
    its number comes from: a bar Nimish set, or the score its prompt was made active on."""
    rows = [t for t in SEED if t["key"].startswith("eval.")]
    assert set(cli.EVALS) >= {"story_shape", "language_review", "item_generate"}, cli.EVALS
    assert {t["key"].split(".")[1] for t in rows} == set(cli.EVALS) - NONE_ON_RECORD
    for t in rows:
        assert re.search(r"DECISIONS-LOG|STATE\.md|goals/", t["description"]), f"{t['key']} says no source"
        assert t["unit"] == ("count" if t["key"].endswith(bars.CEILING) else "proportion"), t["key"]


def test_a_score_below_its_bar_fails_and_says_by_how_much(monkeypatch):
    held = _seeded(None, "story_shape")
    assert bars.short({"shape_right": 63 / 65, "wrong_answers": 0}, held) == []
    assert bars.short({"shape_right": 60 / 65, "wrong_answers": 0}, held) == [
        "shape_right 0.9231, below its bar of 0.9692"
    ]
    assert bars.short({"shape_right": 1.0, "wrong_answers": 1}, held) == [
        "wrong_answers 1, above its bar of 0"
    ]
    assert bars.short({"wrong_answers": 0}, held) == ["shape_right: not measured by this eval"]
    result = {"misses": [], "named": 65, "n": 65, "keyed": 44, "wrong_answer": 0, "left": 0, "unanswered": 0}
    monkeypatch.setattr(cli.story_shape, "evaluate", lambda conn: {**result, "right": 60})
    r = _eval(monkeypatch, "story_shape")
    assert r.exit_code == 1 and "below its bar of 0.9692" in r.output, r.output
    monkeypatch.setattr(cli.story_shape, "evaluate", lambda conn: {**result, "right": 63})
    r = _eval(monkeypatch, "story_shape")
    assert r.exit_code == 0 and "every bar met" in r.output, r.output
    monkeypatch.setattr(cli.review, "evaluate", lambda conn, purpose, gold: {
        "cases": 6, "agreed": 5, "reason_agreed": 5, "rate": 0.83, "disagreements": [], "model": "m",
        "cost_inr": 0.1, "calls": 1,
    })  # fmt: skip
    r = _eval(monkeypatch, "language_review")
    assert r.exit_code == 1 and "agreed 0.83, below its bar of 1" in r.output, r.output


def test_an_eval_with_no_bar_on_record_does_not_pass(monkeypatch):
    """A score nothing holds to a bar proves nothing: the eval prints it and fails, until its score is written down
    and becomes its bar."""
    assert bars.short({"pass_rate": 1.0}, {})[0].startswith("no bar on record")
    monkeypatch.setattr(
        cli.bank, "fill", lambda conn, code, d, n, dry_run: ({"accepted": 9, "returned": 9}, {}, None)
    )
    r = _eval(monkeypatch, "item_generate", "--only", "SUB.2D2D", "--n", "1")
    assert r.exit_code == 1 and "pass rate" in r.output and "no bar on record" in r.output, r.output
