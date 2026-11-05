"""M1-11: a K2 activity page has no part the engine cannot see empty (goals/m1-11-k2-complete-v1.yaml).

The pure half (counting empties, finding a name and an objective that disagree) needs no database. The rest runs on a
database built from the migrations: the sheet's lesson plan is kept as the activity's steps and marked the school's,
a part has a source, and the catalogue of materials and the proposal ledger take what an agent will draft later.
"""

import csv
import json
import os
from pathlib import Path

import psycopg
import pytest

from engine.core import db
from engine.w1_bank import k2_gaps as gaps
from engine.w1_bank import k2_upload as up

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
SEED = db.REPO_ROOT / "supabase" / "seed"

STEPS = "• The educator will make the children sit in a circle and demonstrate.\n• She will show them the shapes.\n"


def test_each_part_of_a_page_is_counted_empty_and_a_blank_cell_of_spaces_is_empty():
    rows = [
        {
            "code": "A",
            "name": "x",
            "objective": "o",
            "steps": "s",
            "thinking": "",
            "materials": "m",
            "level_0": "a",
            "level_1": "b",
            "level_2": "c",
            "level_3": "d",
        },
        {
            "code": "B",
            "name": "y",
            "objective": "  ",
            "steps": "",
            "thinking": "",
            "materials": "",
            "level_0": "",
            "level_1": "b",
            "level_2": "",
            "level_3": "",
        },
    ]
    assert gaps.empties(rows) == {
        "objective": 1,
        "steps": 1,
        "thinking": 2,
        "materials": 1,
        "level_0": 1,
        "level_1": 0,
        "level_2": 1,
        "level_3": 1,
    }, "every part the page has is named, a part nobody lacks counted as 0"


def test_a_name_and_an_objective_that_give_different_number_ranges_are_flagged_for_a_person():
    row = {
        "code": "ACT-K2-0100",
        "name": "Number names 11-20",
        "objective": "Children recognise numbers from 6-10",
    }
    assert gaps.inconsistencies([row]) == [("ACT-K2-0100", "name says 11-20, objective says 6-10")]


def test_agreeing_ranges_overlapping_ranges_and_no_range_are_not_flagged():
    agree = {"code": "A", "name": "Number names 11-20", "objective": "Names the numbers 11 to 20"}
    inside = {"code": "B", "name": "Counting 1-20", "objective": "counts objects up to 10 (1-10)"}
    plain = {"code": "C", "name": "Pink Tower", "objective": "Develops eye hand co-ordination"}
    assert gaps.inconsistencies([agree, inside, plain]) == []


def test_the_report_names_each_part_with_its_count_in_the_sheet_and_in_the_database():
    sheet_rows = [
        {
            "code": "",
            "name": "n",
            "objective": "",
            "steps": "s",
            "thinking": "",
            "materials": "m",
            "level_0": "",
            "level_1": "",
            "level_2": "",
            "level_3": "",
        }
    ]
    text = gaps.report(sheet_rows, [])
    assert "steps" in text and "thinking" in text and "inconsisten" in text.lower()
    assert "objective" in text and "1 of 1" in text


def test_the_sheet_seed_names_the_lesson_plan_column_so_the_steps_are_read():
    cfg = json.loads((SEED / "k2_sheet.json").read_text())
    assert cfg["columns"]["steps"] == "J", "the sheet's LESSON PLANS column"


def _csv(tmp_path: Path, **cells: str) -> Path:
    path = tmp_path / "tab.csv"
    row = [""] * 44
    for letters, v in cells.items():
        row[up._col(letters)] = v
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["header"] * 44)
        w.writerow(row)
    return path


def test_the_lesson_plan_is_read_as_the_activitys_steps(tmp_path):
    rows, skipped = up.read_csv(
        _csv(tmp_path, B="1", C="Block Room", D="Critical Thinking", F="SR KG", G="Pink Tower", J=STEPS)
    )
    assert skipped == [] and rows[0].values["steps"] == STEPS.strip()


@pytest.fixture
def conn():
    with db.connect() as c:
        c.info_tenant = c.execute(  # type: ignore[attr-defined]
            "select id from tenant where slug = %s", (db.tenant_slug(),)
        ).fetchone()["id"]
        yield c
        c.rollback()


@needs_db
def test_an_upload_keeps_the_lesson_plan_as_steps_marks_it_the_schools_and_a_second_run_changes_nothing(
    tmp_path, conn
):
    path = _csv(tmp_path, B="1", C="Block Room", D="Critical Thinking", F="SR KG", G="Pink Tower", J=STEPS)
    rows, _ = up.read_csv(path)
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    first = up.plan(rows, dbrows, edited)
    assert first.changes and "steps" in first.changes[0][2]
    code = first.changes[0][0]
    up.apply(conn, conn.info_tenant, first, "K2 upload — test")
    steps = conn.execute("select steps from activity where code = %s", (code,)).fetchone()["steps"]
    assert steps == STEPS.strip()
    src = conn.execute(
        "select source from activity_part_source where activity_code = %s and part = 'steps'", (code,)
    ).fetchone()
    assert src["source"] == "school"
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    second = up.plan(rows, dbrows, edited)
    assert not second.changes and second.same == 1
    kept = conn.execute(
        "select changed_by from curriculum_edit where record = 'activity' and code = %s and field = 'steps'",
        (code,),
    ).fetchall()
    assert [k["changed_by"] for k in kept] == ["K2 upload — test"], "the history keeps who loaded the steps"


@needs_db
def test_a_part_has_one_source_and_it_is_the_schools_a_drafts_or_a_persons(conn):
    t = conn.info_tenant
    code = conn.execute("select code from activity where band = 'K2' order by code limit 1").fetchone()[
        "code"
    ]
    for part, source in (("thinking", "drafted"), ("steps", "school"), ("level_2", "person")):
        conn.execute(
            "insert into activity_part_source (tenant_id, activity_code, part, source) values (%s,%s,%s,%s)",
            (t, code, part, source),
        )
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "insert into activity_part_source (tenant_id, activity_code, part, source) values (%s,%s,'objective','agent')",
            (t, code),
        )
    conn.rollback()


@needs_db
def test_a_drafted_part_made_the_schools_by_a_later_upload_is_marked_the_schools_but_a_persons_edit_stays(
    conn,
):
    t = conn.info_tenant
    code = conn.execute("select code from activity where band = 'K2' order by code limit 1").fetchone()[
        "code"
    ]
    conn.execute(
        "insert into activity_part_source (tenant_id, activity_code, part, source) values (%s,%s,'steps','drafted')",
        (t, code),
    )
    conn.execute(
        "insert into activity_part_source (tenant_id, activity_code, part, source) values (%s,%s,'level_1','person')",
        (t, code),
    )
    up.mark_school(conn, t, code, ["steps", "level_1"])
    got = {
        r["part"]: r["source"]
        for r in conn.execute(
            "select part, source from activity_part_source where activity_code = %s", (code,)
        ).fetchall()
    }
    assert got == {"steps": "school", "level_1": "person"}


@needs_db
def test_materials_are_a_catalogue_and_a_line_per_activity_with_a_quantity_and_a_unit(conn):
    t = conn.info_tenant
    code = conn.execute("select code from activity where band = 'K2' order by code limit 1").fetchone()[
        "code"
    ]
    conn.execute(
        "insert into material_item (tenant_id, code, name, unit) values (%s,'MAT-0001','Wooden cube','piece')",
        (t,),
    )
    conn.execute(
        "insert into activity_material (tenant_id, activity_code, material_code, quantity, ord) values (%s,%s,'MAT-0001',10,1)",
        (t, code),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "insert into activity_material (tenant_id, activity_code, material_code, quantity, ord) values (%s,%s,'MAT-0001',0,2)",
            (t, code),
        )
    conn.rollback()


@needs_db
def test_an_item_has_a_home_and_a_value_that_stay_empty_until_a_person_says_and_are_never_made_up(conn):
    t = conn.info_tenant
    conn.execute("insert into material_item (tenant_id, code, name) values (%s,'MAT-0002','Clay')", (t,))
    row = conn.execute("select home, unit_value from material_item where code = 'MAT-0002'").fetchone()
    assert row["home"] is None and row["unit_value"] is None, (
        "a drafted item comes with neither: flagged, not guessed"
    )
    conn.execute("update material_item set home = 'school', unit_value = 450 where code = 'MAT-0002'")
    for bad in ("update material_item set home = 'moon'", "update material_item set unit_value = -1"):
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(bad + " where code = 'MAT-0002'")
        conn.rollback()
        conn.execute("insert into material_item (tenant_id, code, name) values (%s,'MAT-0002','Clay')", (t,))


@needs_db
def test_the_proposal_ledger_takes_a_page_part_and_a_material_and_still_refuses_anything_else(conn):
    t = conn.info_tenant
    base = "insert into curriculum_proposal (tenant_id, run_id, kind, subject_code, status, machine) values (%s, gen_random_uuid(), %s, 'ACT-K2-0001', 'needs_person', 'code:test')"
    for kind in ("page_part", "material"):
        conn.execute(base, (t, kind))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(base, (t, "poem"))
    conn.rollback()


def test_the_k2_prompts_are_rows_with_a_schema_and_none_is_active_before_its_eval():
    rows = {
        (p["purpose"], p["version"]): p
        for p in json.loads((SEED / "prompts.json").read_text())["prompts"]
        if p["purpose"].startswith("k2_")
    }
    assert {k[0] for k in rows} == {
        "k2_page_draft",
        "k2_page_validate",
        "k2_page_check",
        "k2_page_check_b",
        "k2_materials_split",
    }
    assert all(p["active"] is False and p["json_schema"] for p in rows.values()), (
        "rule 7: not active before an eval"
    )
    for version in (1, 2, 3):
        draft, check = rows["k2_page_draft", version], rows["k2_page_validate", version]
        assert draft["model"] != check["model"], "the validator is another model"
    for version in (4,):
        assert rows["k2_page_draft", version]["model"] != rows["k2_page_check", 1]["model"]
        assert rows["k2_page_check", 1]["model"] == "claude-opus-5-5", (
            "the checker is the stronger model (M1-12a)"
        )
    for p in rows.values():
        text = (SEED / p["text_file"]).read_text()
        assert "teacher" not in text.lower() and "borrow" not in text.lower(), "the school's words"
        assert "{{" in text, "the activity's own words go in as data"


def test_the_batched_rows_ask_for_several_pages_a_call_and_only_the_key_is_demanded_by_the_schema():
    """The schema asks for a list and a key; whether each page is complete is judged page by page by code
    (k2_batch), so a page missing a part does not make the whole reply fail and cost the others."""
    rows = {
        p["purpose"]: p
        for p in json.loads((SEED / "prompts.json").read_text())["prompts"]
        if p["version"] == 3
    }
    lists = {"k2_page_draft": "pages", "k2_page_validate": "verdicts", "k2_materials_split": "lists"}
    for purpose, name in lists.items():
        item = rows[purpose]["json_schema"]["properties"][name]["items"]
        assert (
            "key" in item["required"]
            and "{{" + ("lists" if name == "lists" else "pages") + "}}"
            in (SEED / rows[purpose]["text_file"]).read_text()
        )
    assert rows["k2_page_draft"]["json_schema"]["properties"]["pages"]["items"]["required"] == ["key"]


def test_the_mapping_validator_gets_a_new_version_on_haiku_and_version_one_is_left_as_it_was():
    rows = {
        p["version"]: p
        for p in json.loads((SEED / "prompts.json").read_text())["prompts"]
        if p["purpose"] == "curriculum_map_validate"
    }
    assert rows[1]["model"] == "claude-opus-5-5" and rows[1]["effort"] == "low" and rows[1]["active"] is False
    assert rows[2]["model"] == "claude-haiku-4-5" and rows[2]["active"] is False and "effort" not in rows[2]
    assert rows[2]["json_schema"] == rows[1]["json_schema"]
    assert (SEED / rows[2]["text_file"]).read_text() == (SEED / rows[1]["text_file"]).read_text()


def test_the_batch_sizes_and_rounds_are_a_config_row_not_numbers_in_code():
    cfg = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}[
        "k2.drafting"
    ]
    assert (
        cfg["batch_pages"],
        cfg["batch_materials"],
        cfg["batch_rounds"],
        cfg["stop_after_bad_replies"],
    ) == (4, 10, 2, 3)
    keys = {t["key"] for t in json.loads((SEED / "thresholds.json").read_text())["thresholds"]}
    assert not {k for k in keys if k.startswith("k2.") or k == "llm.stale_minutes"}, (
        "not thresholds: see the guide test"
    )


@needs_db
def test_an_upload_never_writes_over_steps_a_person_edited_and_never_empties_a_filled_cell(tmp_path, conn):
    path = _csv(tmp_path, B="1", C="Block Room", D="Critical Thinking", F="SR KG", G="Pink Tower", J=STEPS)
    rows, _ = up.read_csv(path)
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    code = up.plan(rows, dbrows, edited).changes[0][0]
    up.apply(conn, conn.info_tenant, up.plan(rows, dbrows, edited), "K2 upload — first")
    conn.execute("select set_config('app.changed_by', 'a member of staff', true)")
    conn.execute(
        "update activity set steps = 'Sit in a circle. (changed by an educator)' where code = %s", (code,)
    )
    again, _ = up.read_csv(
        _csv(
            tmp_path, B="1", C="Block Room", D="Critical Thinking", F="SR KG", G="Pink Tower", J="Other words"
        )
    )
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    second = up.plan(again, dbrows, edited)
    assert all("steps" not in diff for _, _, diff in second.changes), (
        "the person's words are not written over"
    )
    assert (code, "steps", "edited on the site; the sheet's words are not written over it") in second.kept
    up.apply(conn, conn.info_tenant, second, "K2 upload — second")
    got = conn.execute("select steps from activity where code = %s", (code,)).fetchone()["steps"]
    assert got == "Sit in a circle. (changed by an educator)"
    empty, _ = up.read_csv(
        _csv(tmp_path, B="1", C="Block Room", D="Critical Thinking", F="SR KG", G="Pink Tower", J="")
    )
    dbrows, edited = up.snapshot(conn, conn.info_tenant)
    assert all("steps" not in diff for _, _, diff in up.plan(empty, dbrows, edited).changes), (
        "an empty cell empties nothing"
    )
