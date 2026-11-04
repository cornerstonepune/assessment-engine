"""M0-02: the K2 team's activity sheet, uploaded (goals/m0-02-k2-curriculum-upload.yaml).

The three activities below are the first rows of the K2 team's own tab, as the sheet shows them; the other rows in the
file are the kinds of row the tab holds around them (a heading, another year, a #REF! number, no name)."""

import csv
import re
from pathlib import Path

import psycopg
import pytest
from typer.testing import CliRunner

from engine import cli
from engine.core import db
from engine.w1_bank import k2_upload as up

BLOCK = {
    "B": "1",
    "C": "Block Room",
    "D": "Critical Thinking",
    "E": "IG",
    "F": "SR KG",
    "G": "A True Experience Of Art And Forms",
    "H": "Green and yellow Arch-1 each, yellow, red, white, blue triangle-1each",
    "M": "• To develop, motivate and encourage one’s own imagination and intellectual\nskills\n"
    "• To sharpen intelligences and indirectly creates interest for mathematics and\nits uses \n\n",
    "P": "Doesn't sit for the class",
    "Q": "Knows names of all the shapes",
    "R": "Builds different patterns as demonstrated",
    "S": "Builds new patterns through imagination",
}
PINK = {
    "B": "2",
    "C": "Block Room",
    "D": "Critical Thinking",
    "E": "IG",
    "F": "SR KG",
    "G": "Pink Tower",
    "H": "10 wooden cubes ranging in size from 1cm3 to 10cm3., ",
    "M": "• Children will develop eye hand co-ordination.\n• Helps in increasing concentration as the body and mind "
    "work in union with total concentration.\n• Children will develop eye hand co-ordination.\n"
    "• Helps in increasing concentration as the body and mind work in union with total concentration.\n",
    "P": "Doesn't sit quietly",
    "Q": "Observes keenly when demonstrated",
    "R": "Is excited about the activity but is unable to stack as per ascending order",
    "S": "Is able to stack it in a proper order",
}
OTHERS = [
    {"B": "", "C": "CRITICAL THINKING"},
    {"B": "", "C": "CLASS", "D": "SUBJECT"},
    {"B": "", "C": "Music", "D": "Creativity", "E": "IG", "F": "Nursery", "G": "A Nursery Song"},
    {"B": "#REF!", "C": "Dance", "D": "Creativity", "E": "IG", "F": "SR KG", "G": "#REF!"},
    {"B": "#REF!", "C": "Dance", "D": "Creativity", "E": "IG", "F": "SR KG", "G": ""},
]


def sheet(tmp_path: Path, *rows: dict[str, str]) -> Path:
    path = tmp_path / "tab.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["header"] * 44)
        for r in rows:
            cells = [""] * 44
            for letters, v in r.items():
                cells[up._col(letters)] = v
            w.writerow(cells)
    return path


def test_a_row_is_read_as_the_sheet_wrote_it_and_every_other_row_says_why_it_is_skipped(tmp_path):
    rows, skipped = up.read_csv(sheet(tmp_path, BLOCK, *OTHERS[:2], PINK, *OTHERS[2:]))
    assert [r.values["name"] for r in rows] == ["A True Experience Of Art And Forms", "Pink Tower"]
    assert rows[0].values["level_0"] == "Doesn't sit for the class"
    assert rows[0].values["materials"].startswith("Green and yellow Arch-1")
    assert rows[0].values["sheet_no"] == "1" and rows[0].pillar == "Critical Thinking"
    assert dict(skipped) == {
        3: "a heading or spacer row",
        4: "a heading or spacer row",
        6: "not SR KG (year 'Nursery')",
        7: "activity name is #REF!",
        8: "no activity name",
    }


def test_an_activity_number_that_is_not_a_number_is_kept_as_none_and_the_row_is_still_loaded(tmp_path):
    odd = {**BLOCK, "B": "#REF!", "G": "Rain Dance"}
    rows, skipped = up.read_csv(sheet(tmp_path, odd))
    assert rows[0].values["sheet_no"] == "" and skipped == []


def test_outcomes_are_separate_wrapped_lines_are_joined_and_a_repeat_is_kept_once():
    found, dropped = up.bullets(BLOCK["M"])
    assert (
        found
        == [
            "To develop, motivate and encourage one’s own imagination and intellectual skills",
            "To sharpen intelligences and indirectly creates interest for mathematics and its uses",
        ]
        and dropped == 0
    )
    found, dropped = up.bullets(PINK["M"])
    assert len(found) == 2 and dropped == 2


@pytest.fixture
def conn():
    with db.connect() as c:
        tenant = c.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        c.info_tenant = tenant  # type: ignore[attr-defined]
        yield c
        c.rollback()  # a test never leaves a row behind


def _plan(conn, rows):
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    return up.plan(rows, dbrows, edited)


def test_the_comparison_matches_an_activity_by_its_strand_and_name_and_says_what_would_change(tmp_path, conn):
    rows, _ = up.read_csv(sheet(tmp_path, BLOCK, PINK))
    p = _plan(conn, rows)
    assert not p.inserts, "both are already among the 590"
    changed = {code: diff for code, _, diff in p.changes}
    first = changed["ACT-K2-0001"]
    assert first["materials"][0] == "" and first["level_0"][0] == ""  # the two columns the database lacked
    assert "objective" in first  # the sheet's line breaks, where the seed had joined them with ' / '


def test_a_dry_run_writes_nothing_and_an_upload_twice_changes_nothing_the_second_time(tmp_path, conn):
    rows, _ = up.read_csv(sheet(tmp_path, BLOCK, PINK))
    before = conn.execute("select count(*) as n from curriculum_edit").fetchone()["n"]
    first = _plan(conn, rows)
    assert conn.execute("select count(*) as n from curriculum_edit").fetchone()["n"] == before
    up.apply(conn, conn.info_tenant, first, "K2 upload — test")
    second = _plan(conn, rows)
    assert not second.changes and not second.inserts and second.same == 2
    made = conn.execute("select count(*) as n from learning_objective where band = 'K2'").fetchone()["n"]
    up.apply(conn, conn.info_tenant, second, "K2 upload — test again")
    assert (
        conn.execute("select count(*) as n from learning_objective where band = 'K2'").fetchone()["n"] == made
    )


def test_every_outcome_becomes_a_k2_learning_objective_linked_to_its_activity(tmp_path, conn):
    rows, _ = up.read_csv(sheet(tmp_path, BLOCK, PINK))
    up.apply(conn, conn.info_tenant, _plan(conn, rows), "K2 upload — test")
    got = conn.execute(
        "select a.activity_code, a.ord, l.title, l.band, l.subject from activity_objective a"
        " join learning_objective l on l.tenant_id = a.tenant_id and l.code = a.lo_code"
        " where a.activity_code in ('ACT-K2-0001', 'ACT-K2-0002') order by 1, 2"
    ).fetchall()
    assert [(g["activity_code"], g["ord"], g["band"]) for g in got] == [
        ("ACT-K2-0001", 1, "K2"),
        ("ACT-K2-0001", 2, "K2"),
        ("ACT-K2-0002", 1, "K2"),
        ("ACT-K2-0002", 2, "K2"),
    ]
    assert got[0]["title"].startswith("To develop") and got[0]["subject"] == "Critical Thinking"


def test_every_change_is_kept_with_who_and_when_and_the_history_cannot_be_changed(tmp_path, conn):
    rows, _ = up.read_csv(sheet(tmp_path, BLOCK))
    up.apply(conn, conn.info_tenant, _plan(conn, rows), "K2 upload — Tester")
    kept = conn.execute(
        "select field, before, after, changed_by, created_at from curriculum_edit"
        " where code = 'ACT-K2-0001' and field = 'level_0'"
    ).fetchall()
    assert len(kept) == 1 and kept[0]["after"] == "Doesn't sit for the class"
    assert kept[0]["changed_by"] == "K2 upload — Tester" and kept[0]["created_at"] is not None
    with pytest.raises(Exception, match="append|change|ledger|never"):
        conn.execute("update curriculum_edit set after = 'x'")


def test_a_word_a_person_edited_on_the_site_is_not_written_over_by_the_sheet(tmp_path, conn):
    conn.execute("select set_config('app.changed_by', 'An Educator', true)")
    conn.execute("update activity set level_1 = 'Knows the names of the blocks' where code = 'ACT-K2-0001'")
    rows, _ = up.read_csv(sheet(tmp_path, BLOCK))
    p = _plan(conn, rows)
    assert (
        "ACT-K2-0001",
        "level_1",
        "edited on the site; the sheet's words are not written over it",
    ) in p.kept
    up.apply(conn, conn.info_tenant, p, "K2 upload — test")
    now = conn.execute("select level_1 from activity where code = 'ACT-K2-0001'").fetchone()["level_1"]
    assert now == "Knows the names of the blocks"


def test_an_empty_cell_never_empties_a_filled_field_and_nothing_is_deleted(tmp_path, conn):
    bare = {**BLOCK, "Q": "", "R": "", "S": ""}
    n = conn.execute("select count(*) as n from activity where band = 'K2'").fetchone()["n"]
    rows, _ = up.read_csv(sheet(tmp_path, bare))
    p = _plan(conn, rows)
    assert not any(f.startswith("level_") and f != "level_0" for _, _, diff in p.changes for f in diff)
    up.apply(conn, conn.info_tenant, p, "K2 upload — test")
    assert conn.execute("select count(*) as n from activity where band = 'K2'").fetchone()["n"] == n
    assert conn.execute("select level_1 from activity where code = 'ACT-K2-0001'").fetchone()["level_1"] != ""


def test_an_activity_the_database_lacks_is_added_with_the_next_code_and_its_outcomes_linked(tmp_path, conn):
    new = {**BLOCK, "B": "9999", "G": "A Game The Database Lacks"}
    rows, _ = up.read_csv(sheet(tmp_path, new))
    p = _plan(conn, rows)
    assert len(p.inserts) == 1
    up.apply(conn, conn.info_tenant, p, "K2 upload — test")
    top = conn.execute("select max(code) as c from activity where band = 'K2'").fetchone()["c"]
    assert top == "ACT-K2-0591"
    assert (
        conn.execute(
            "select count(*) as n from activity_objective where activity_code = %s", (top,)
        ).fetchone()["n"]
        == 2
    )


def _an_activity_with(conn, has_levels: bool) -> dict:
    return conn.execute(
        "select code, strand, name, level_1, level_2, level_3 from activity where band = 'K2'"
        " and ((level_1 <> '' or level_2 <> '' or level_3 <> '') = %s) order by code limit 1",
        (has_levels,),
    ).fetchone()


def _row_for(a: dict, **cells: str) -> dict[str, str]:
    return {"B": "1", "C": a["strand"], "D": "Critical Thinking", "F": "SR KG", "G": a["name"], **cells}


def test_levels_are_filled_where_the_sheet_has_them_listed_where_it_has_none_and_kept_where_the_database_has_them(
    tmp_path, conn
):
    """The K2 activities that had no levels: filled from the sheet where it has them, listed where it has none; an
    activity that has its levels keeps them when the sheet's cells are empty."""
    bare = _an_activity_with(conn, False)
    bare_too = conn.execute(
        "select code, strand, name from activity where band = 'K2' and level_1 = '' and level_2 = '' and level_3 = ''"
        " and code <> %s order by code limit 1",
        (bare["code"],),
    ).fetchone()
    held = _an_activity_with(conn, True)
    rows, _ = up.read_csv(
        sheet(
            tmp_path,
            _row_for(bare, Q="Sees the blocks", R="Names the blocks", S="Builds with the blocks"),
            _row_for(bare_too),  # the sheet has no levels for this one either
            _row_for(held),  # empty cells over an activity that has its levels
        )
    )
    p = _plan(conn, rows)
    assert bare["code"] in p.levels_filled and bare["code"] not in p.levels_missing
    assert bare_too["code"] in p.levels_missing and bare_too["code"] not in p.levels_filled
    assert held["code"] not in p.levels_filled + p.levels_missing
    text = up.report(p, [], len(rows), 590)
    assert f"levels filled from the sheet: {bare['code']}" in text
    assert bare_too["code"] in text.split("levels still missing")[1].splitlines()[0]
    up.apply(conn, conn.info_tenant, p, "K2 upload — test")
    now = conn.execute(
        "select code, level_1, level_2, level_3 from activity where code in (%s, %s, %s)",
        (bare["code"], bare_too["code"], held["code"]),
    ).fetchall()
    by_code = {r["code"]: r for r in now}
    assert by_code[bare["code"]]["level_2"] == "Names the blocks"
    assert by_code[bare_too["code"]]["level_1"] == ""
    assert (held["level_1"], held["level_2"], held["level_3"]) == tuple(
        by_code[held["code"]][f"level_{i}"] for i in (1, 2, 3)
    )


def test_a_dry_run_runs_in_a_read_only_transaction_so_it_cannot_write_even_if_apply_code_is_reached(
    tmp_path, monkeypatch
):
    seen = up.snapshot

    def snapshot_then_try_to_write(conn, tenant):
        got = seen(conn, tenant)
        conn.execute("update activity set note = note where false")  # what an apply would do first
        return got

    monkeypatch.setattr(up, "snapshot", snapshot_then_try_to_write)
    # the history is not empty on a fresh copy: the seed's own links are in it (M1-05 keeps every link change)
    with db.connect() as conn:
        before = conn.execute("select count(*) as n from curriculum_edit").fetchone()["n"]
    result = CliRunner().invoke(cli.app, ["curriculum", "k2", str(sheet(tmp_path, BLOCK))])
    assert isinstance(result.exception, psycopg.errors.ReadOnlySqlTransaction)
    with db.connect() as conn:
        assert conn.execute("select count(*) as n from curriculum_edit").fetchone()["n"] == before


def test_apply_without_by_is_refused_before_the_sheet_is_read_or_the_database_opened(tmp_path, monkeypatch):
    def never(*_a, **_k):
        raise AssertionError("the database was opened")

    monkeypatch.setattr(db, "connect", never)
    result = CliRunner().invoke(cli.app, ["curriculum", "k2", str(sheet(tmp_path, BLOCK)), "--apply"])
    plain = " ".join(
        re.sub(r"[│╭╮╰╯─]", " ", re.sub(r"\x1b\[[0-9;]*m", "", result.output)).split()
    )  # whatever colours or wraps it
    assert result.exit_code != 0 and "--by is required with --apply" in plain
    assert not isinstance(result.exception, AssertionError)
