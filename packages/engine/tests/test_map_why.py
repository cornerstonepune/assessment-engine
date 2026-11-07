"""What the 165 proposals that passed on their own were like, in counts only (goals/m1-12n-map-why.yaml)."""

import json

from engine.w1_bank import map_why as mw
from tests.test_map_replay import needs_db, prop

NAMES = {
    "A1": "Count beads",
    "A2": "Count beads",
    "A3": "Sort shells",
    "A4": "Thread beads",
    "A5": "Pinch seeds",
}
STRAND = {"A1": "Maths", "A2": "Maths", "A3": "Maths", "A4": "Maths", "A5": "Art"}
LINKED = {  # what people linked: A2 shares A1's name, A3 and A4 are the same section, A5 another
    "A1": frozenset({"NUM.CNT.01"}),
    "A2": frozenset({"NUM.CNT.01", "NUM.CNT.02"}),
    "A3": frozenset({"NUM.SRT.01"}),
    "A4": frozenset({"MOT.FMS.01"}),
    "A5": frozenset({"ART.CLAY.01"}),
}


def made():
    return [
        prop("A1", ["NUM.CNT.01"], "auto_passed", 0.95),  # one skill, right
        prop(
            "A1", ["NUM.CNT.01", "NUM.CNT.02"], "auto_passed", 0.85
        ),  # adds a skill a same-name activity has
        prop("A3", ["NUM.SRT.01", "MOT.FMS.01"], "auto_passed", 0.85),  # adds a skill of the same section
        prop("A4", ["ART.CLAY.01"], "auto_passed", 0.75),  # another family
        prop("A5", ["ART.CLAY.01"], "needs_person", 0.9),  # not a pass: not counted
    ]


def run():
    return mw.why(made(), LINKED, NAMES, STRAND)


def test_only_the_proposals_that_passed_on_their_own_are_counted():
    assert run()["passed"] == 4


def test_the_wrong_rate_is_given_by_how_many_skills_a_proposal_named():
    by = run()["by_skills"]
    assert by["1"] == {"n": 2, "right": 1} and by["2+"] == {"n": 2, "right": 0}


def test_the_wrong_rate_is_given_by_confidence_band_from_the_data_not_from_fixed_edges():
    by = run()["by_confidence"]
    assert by == {"0.7": {"n": 1, "right": 0}, "0.8": {"n": 2, "right": 0}, "0.9": {"n": 1, "right": 1}}


def test_an_added_skill_is_looked_for_where_people_linked_it_to_a_like_activity():
    adds = run()["adds"]
    assert adds["proposals"] == 2 and adds["extra_skills"] == 2
    assert adds["extra_linked_to_a_same_name_activity"] == 1
    assert adds["extra_linked_in_the_same_section"] == 1
    assert adds["extra_linked_nowhere_alike"] == 0
    assert adds["extra_in_a_family_people_linked"] == 1


def test_what_the_precision_would_be_if_only_one_skill_passed_or_the_adds_were_offers():
    s = run()["if"]
    assert s["one_skill_only"]["passed"] == 2 and s["one_skill_only"]["right"] == 1
    assert s["adds_offered"]["passed"] == 2 + 2 and s["adds_offered"]["right"] == 1 + 2
    assert len(s["one_skill_only"]["interval"]) == 2


def test_the_summary_names_no_activity_and_no_skill():
    text = json.dumps(run())
    assert "A1" not in text and "NUM." not in text and "Count beads" not in text


def test_nothing_passed_is_all_zero_not_an_error():
    assert mw.why([], {}, {}, {})["passed"] == 0


@needs_db
def test_the_held_out_run_kept_in_the_database_is_summed_up_in_counts_and_names_nothing():
    import pytest
    from psycopg.types.json import Json

    from engine.core import db
    from engine.w1_bank import cli_map
    from engine.w1_bank.map_agents import PROPOSE
    from tests.test_map_ledger import _band

    said = {
        "skills": ["NUM.CNT.01"],
        "objective_code": "",
        "objective_text": "",
        "levels": {},
        "confidence": 0.9,
        "reason": "r",
    }
    with db.connect() as conn:
        _band(conn)
        conn.execute("update threshold set value = 1 where key = 'map.dev_count'")
        monkey = pytest.MonkeyPatch()
        monkey.setattr(cli_map, "config", lambda: {"band": "KX"})
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        _, held = cli_map.gold_split(conn, cli_map.read_band(conn, tenant, "KX"))
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, request, result)"
            " values (%s, %s, 'engine:held_out', %s, %s)",
            (tenant, PROPOSE, Json({"about": sorted(held)[0]}), Json({"reply": said, "outcome": "accepted"})),
        )
        line = cli_map.why_report(conn, 10)
        conn.rollback()
        monkey.undo()
    got = json.loads(line)
    assert {"passed", "by_skills", "by_confidence", "adds", "if"} <= set(got)
    assert "ACT-KX" not in line and "NUM." not in line
