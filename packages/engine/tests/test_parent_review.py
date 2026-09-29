"""The parent report's second reader (engine/w4_close/parent_review.py): scored on every bad sentence of the gold set
flagged, and nothing else flagged."""

import json

from engine.core import db
from engine.w4_close import parent_review as R

GOLD = json.loads((db.REPO_ROOT / R.GOLD).read_text())


def test_the_gold_set_holds_right_drafts_and_wrong_ones_and_no_name():
    cases = GOLD["cases"]
    assert [c for c in cases if not c["bad"]] and [c for c in cases if c["bad"]]
    for c in cases:
        for b in c["bad"]:
            assert b in json.dumps(c["draft"], ensure_ascii=False), (c["ref"], b)
        assert "next" not in c["facts"]
    assert "first_name" not in json.dumps(GOLD)


def test_the_reviewer_is_scored_on_every_bad_sentence_and_on_nothing_else():
    by_draft = {json.dumps(c["draft"], sort_keys=True): c for c in GOLD["cases"]}

    def perfect(conn, purpose, variables, meta=None, version=None):
        c = by_draft[json.dumps(variables["draft"], sort_keys=True)]
        return {"unsupported": [{"quote": b, "why": c["note"]} for b in c["bad"]]}

    r = R.evaluate(None, ask=perfect)
    assert r["caught"] == r["bad"] > 0 and r["false_flags"] == 0 and not r["misses"]

    def fussy(conn, purpose, variables, meta=None, version=None):
        return {"unsupported": [{"quote": variables["draft"]["summary"][:40], "why": "tone"}]}

    r = R.evaluate(None, ask=fussy)
    assert r["false_flags"] > 0 and r["misses"]
