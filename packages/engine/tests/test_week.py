"""W2 against the real schema, inside one transaction that is rolled back.

The properties that matter to a teacher: every child gets a paper, no two children get the same
question, a child never sees a question twice, and the prescription can always say why.
"""

import json
import os
import uuid

import pytest

from engine import assemble, db, prescribe, roster
from engine.assess import graph

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET, WEEK, SECTION = "SUB.2D.EXCH", "T2W9-test", "TESTSEC"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def children(conn, tmp_path):
    """Three children in a section of their own, so the real roster is never touched."""
    path = tmp_path / "roster.json"
    path.write_text(
        json.dumps(
            {
                "children": [
                    {"roll_no": "1", "section": SECTION, "band": "G2", "first_name": "Aarav"},
                    {"roll_no": "2", "section": SECTION, "band": "G2", "first_name": "Riya"},
                    {"roll_no": "3", "section": SECTION, "band": "G3", "first_name": "Kabir"},
                ]
            }
        )
    )
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    rows = []
    for c in json.loads(path.read_text())["children"]:
        r = conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,%s) returning id",
            (tenant, c["roll_no"], c["section"], c["band"]),
        ).fetchone()
        conn.execute(
            "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)",
            (tenant, r["id"], c["first_name"]),
        )
        rows.append(r["id"])
    return rows


def test_every_child_gets_a_prescription_and_a_reason(conn, children):
    rows = prescribe.for_class(conn, SECTION, WEEK, SET)
    assert len(rows) == 3
    assert all(r["rule"] in prescribe.RULES for r in rows)
    # No evidence exists yet, so every child falls to their band's starting difficulty.
    by_band = {r["band"]: r["difficulty"] for r in rows}
    assert by_band["G2"] == "Medium" and by_band["G3"] == "Medium"
    assert all(r["rule"] == "band_default" for r in rows)


def test_prescribing_twice_updates_rather_than_duplicating(conn, children):
    prescribe.for_class(conn, SECTION, WEEK, SET)
    prescribe.for_class(conn, SECTION, WEEK, SET)
    n = conn.execute(
        "select count(*) as n from prescription p join child c on c.id = p.child_id"
        " where c.section = %s and p.week = %s",
        (SECTION, WEEK),
    ).fetchone()["n"]
    assert n == 3


def test_a_teachers_override_survives_the_next_prescribe(conn, children):
    rows = prescribe.for_class(conn, SECTION, WEEK, SET)
    prescribe.override(conn, rows[0]["prescription_id"], "Easy", "achal", "she was away all week")
    prescribe.for_class(conn, SECTION, WEEK, SET)
    kept = conn.execute(
        "select difficulty, rule_fired, override_reason from prescription where id = %s",
        (rows[0]["prescription_id"],),
    ).fetchone()
    assert kept["difficulty"] == "Easy" and kept["rule_fired"] == "override"
    assert kept["override_reason"] == "she was away all week"


def test_an_override_needs_a_reason_and_a_real_difficulty(conn, children):
    rows = prescribe.for_class(conn, SECTION, WEEK, SET)
    with pytest.raises(ValueError, match="reason"):
        prescribe.override(conn, rows[0]["prescription_id"], "Easy", "achal", "   ")
    with pytest.raises(ValueError, match="not one of"):
        prescribe.override(conn, rows[0]["prescription_id"], "Impossible", "achal", "why")


def test_graph_says_nothing_until_there_is_confirmed_evidence(conn, children):
    assert graph.next_difficulty(conn, children[0], SET) == (None, "band_default", [])


# ---- assembly


def _prescribe_at(conn, difficulty):
    rows = prescribe.for_class(conn, SECTION, WEEK, SET)
    conn.execute(
        "update prescription set difficulty = %s where id = any(%s)",
        (difficulty, [r["prescription_id"] for r in rows]),
    )
    return rows


def test_each_child_gets_a_different_paper(conn, children):
    _prescribe_at(conn, "Hard")
    built = assemble.for_week(conn, SECTION, WEEK)
    assert len(built["sheets"]) == 3, built["short"]
    papers = [{r["item_key"] for r in s["item_rows"]} for s in built["sheets"]]
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            assert papers[i] & papers[j] == set(), "two children share a question"


def test_every_sheet_has_a_code_and_the_prescription_points_at_it(conn, children):
    _prescribe_at(conn, "Hard")
    built = assemble.for_week(conn, SECTION, WEEK)
    for s in built["sheets"]:
        assert s["qr"].startswith("CS") and len(s["qr"]) == 8
    linked = conn.execute(
        "select count(*) as n from prescription p join child c on c.id = p.child_id"
        " where c.section = %s and p.sheet_instance_id is not null",
        (SECTION,),
    ).fetchone()["n"]
    assert linked == 3


def test_a_child_is_never_shown_the_same_question_twice(conn, children):
    _prescribe_at(conn, "Hard")
    first = assemble.for_week(conn, SECTION, WEEK)
    seen = {s["child_id"]: {r["item_key"] for r in s["item_rows"]} for s in first["sheets"]}

    conn.execute("update prescription set sheet_instance_id = null where week = %s", (WEEK,))
    conn.execute("update prescription set week = %s where week = %s", (WEEK + "b", WEEK))
    second = assemble.for_week(conn, SECTION, WEEK + "b")
    for s in second["sheets"]:
        assert seen[s["child_id"]] & {r["item_key"] for r in s["item_rows"]} == set()


def test_spares_are_unnamed_and_carry_no_child(conn, children):
    _prescribe_at(conn, "Hard")
    built = assemble.for_week(conn, SECTION, WEEK)
    assert built["spares"], "a pack with no spares leaves a teacher stuck"
    for s in built["spares"]:
        assert s["child_id"] is None
        row = conn.execute(
            "select child_id from sheet_instance where id = %s", (s["instance_id"],)
        ).fetchone()
        assert row["child_id"] is None


def test_it_says_which_child_it_could_not_fill_rather_than_printing_a_short_paper(conn, children):
    # Retired for this test's own (rolled-back) transaction only — the real bank now holds items
    # at every SUB.2D.EXCH difficulty (W1 gate 2, chunk A), so "Advance" alone no longer means
    # empty. This makes the scenario true regardless of how full the bank gets.
    conn.execute(
        "update item set status = 'retired' where skill_set_code = %s and difficulty = %s", (SET, "Advance")
    )
    _prescribe_at(conn, "Advance")  # nothing available in the bank at Advance
    with pytest.raises(ValueError, match="prescriptions|nothing"):
        built = assemble.for_week(conn, SECTION, WEEK)
        assert built["sheets"] == [] and len(built["short"]) == 3
        raise ValueError("nothing assembled")


def test_reading_a_name_is_logged(conn, children):
    before = conn.execute(
        "select count(*) as n from access_log where child_id = %s", (children[0],)
    ).fetchone()["n"]
    got = roster.names(conn, [children[0]], "test-actor")
    assert got[children[0]] == "Aarav"
    after = conn.execute(
        "select actor from access_log where child_id = %s order by created_at desc limit 1", (children[0],)
    ).fetchone()
    assert after["actor"] == "test-actor"
    assert (
        conn.execute("select count(*) as n from access_log where child_id = %s", (children[0],)).fetchone()[
            "n"
        ]
        == before + 1
    )


def test_two_classes_assembled_at_the_same_moment_both_finish():
    """Two teachers declare on the same Wednesday. Both weeks must be built, not one deadlocked.

    `_store` used to bump `item.times_used` for every question it handed out, and two builders
    touching the same unit deadlocked on those rows — first on `item`, then, once the update was
    ordered, on `item_exposure`'s index. Ordering cannot fix it (Postgres locks in scan order, not
    sorted order); the counter is derived, so it moved to Ring B (`graph.refresh_item_usage`) and the
    hot path takes no locks at all. This test fails with `DeadlockDetected` against the old code.

    A deadlock needs two real transactions, so this is the one test here that commits: its own
    section, deleted in a `finally`, never the roster another test reads.
    """
    import threading

    # A section of its own per run, and the children are deactivated rather than deleted at the end:
    # `evidence_event` is append-only (rule 4) and a cascading DELETE is refused by its trigger, which
    # is also what a school does when a child leaves — the work they did stays.
    section = f"CONCURSEC-{uuid.uuid4().hex[:6]}"
    errors: list[Exception] = []

    def build(week):
        try:
            with db.connect() as c:
                prescribe.for_class(c, section, week, SET)
                assemble.for_week(c, section, week)
                c.rollback()
        except Exception as e:  # noqa: BLE001 — the test reports whatever it was
            errors.append(e)

    with db.connect() as setup:
        tenant = setup.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        for i in (1, 2):
            row = setup.execute(
                "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2') returning id",
                (tenant, str(i), section),
            ).fetchone()
            setup.execute(
                "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)",
                (tenant, row["id"], f"Concurrent {i}"),
            )
        setup.commit()
    try:
        threads = [threading.Thread(target=build, args=(f"{WEEK}-c{i}",)) for i in (1, 2)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=120)
        assert not errors, f"concurrent week builds failed: {errors}"
    finally:
        with db.connect() as done:
            done.execute("update child set active = false where section = %s", (section,))
            done.commit()
