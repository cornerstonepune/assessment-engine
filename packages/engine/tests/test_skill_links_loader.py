"""Loading a person's list of pairs as proposed links, and one member of staff confirming one link
(goals/m1-15-skill-links.yaml; Nimish, approved 2026-11-04). Staff are placeholders on the reserved `.invalid` domain."""

import os
import re
import uuid

import pytest

from engine.core import db, english, topics
from engine.w3_read import skill_links
from tests.link_rows import csv_of as _csv
from tests.link_rows import link as _link
from tests.link_rows import skills as _skills
from tests.link_rows import staff as _staff
from tests.rows import tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

ROOT = db.REPO_ROOT


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


# ---- Done when 5: the loader and the confirmer ---------------------------------------------------------------------


def test_the_loader_adds_a_persons_pairs_as_proposed_links_and_a_second_run_changes_nothing(conn, tmp_path):
    t = tenant(conn)
    a, b, c = _skills(conn, 3)
    f = _csv(
        tmp_path,
        f"{a},{b},Counting comes before adding,Grade 1 list",
        f"{b},{c},Adding before taking away,Grade 1 list",
    )
    first = skill_links.load(conn, f)
    assert (first.added, first.there) == (2, 0)
    rows = conn.execute(
        "select skill_code, before_code, strength, status, source, reason from skill_link"
        " where skill_code = any(%s) order by skill_code",
        ([b, c],),
    ).fetchall()
    assert [(r["skill_code"], r["before_code"], r["status"], r["strength"]) for r in rows] == [
        (b, a, "proposed", "hard"),
        (c, b, "proposed", "hard"),
    ]
    assert rows[0]["reason"] == "Counting comes before adding" and rows[0]["source"] == "Grade 1 list"
    before = conn.execute("select id, updated_at from skill_link order by id").fetchall()
    second = skill_links.load(conn, f)
    assert (second.added, second.there) == (0, 2)
    assert conn.execute("select id, updated_at from skill_link order by id").fetchall() == before
    assert t  # the school the links belong to is the school the engine runs for


def test_a_file_that_is_wrong_anywhere_writes_nothing_and_names_the_line(conn, tmp_path):
    a, b, c = _skills(conn, 3)
    good = f"{a},{b},Counting before adding,list"
    for bad, why in (
        (f"{b},NOT.A.SKILL,r,list", "NOT.A.SKILL"),
        (f"{b},{b},r,list", "itself"),
        (f"{b},{c},,list", "reason"),
        (f"{b},{c},r,", "source"),
        (f"{b},{a},a ring,list", "ring"),
    ):
        with pytest.raises(skill_links.Refused) as e:
            with conn.transaction():
                skill_links.load(conn, _csv(tmp_path, good, bad))
        assert "line 3" in str(e.value) and why in str(e.value), str(e.value)
    assert conn.execute("select count(*) as n from skill_link").fetchone()["n"] == 0, (
        "nothing is half-written"
    )


def test_a_file_without_the_four_columns_or_with_nothing_in_it_is_refused(conn, tmp_path):
    a, b = _skills(conn, 2)
    with pytest.raises(skill_links.Refused):
        skill_links.load(conn, _csv(tmp_path, f"{a},{b},r", header="before_code,after_code,reason"))
    with pytest.raises(skill_links.Refused):
        skill_links.load(conn, _csv(tmp_path))
    with pytest.raises(skill_links.Refused):
        skill_links.load(conn, tmp_path / "no-such-file.csv")


def test_the_loader_never_unconfirms_or_rewrites_a_link_that_is_there(conn, tmp_path):
    t = tenant(conn)
    a, b = _skills(conn, 2)
    who = _staff(conn, t)
    link = _link(conn, t, b, a, reason="the first reason")
    skill_links.confirm(conn, str(link), "checker@school.invalid")
    result = skill_links.load(conn, _csv(tmp_path, f"{a},{b},a different reason,another list"))
    assert (result.added, result.there) == (0, 1)
    row = conn.execute(
        "select reason, status, confirmed_by from skill_link where id = %s", (link,)
    ).fetchone()
    assert (row["reason"], row["status"], row["confirmed_by"]) == ("the first reason", "confirmed", who)


def test_a_strength_column_is_optional_and_soft_can_be_loaded(conn, tmp_path):
    a, b = _skills(conn, 2)
    f = _csv(tmp_path, f"{a},{b},Helps,list,soft", header="before_code,after_code,reason,source,strength")
    skill_links.load(conn, f)
    assert (
        conn.execute("select strength from skill_link where skill_code = %s", (b,)).fetchone()["strength"]
        == "soft"
    )


def test_confirming_names_a_member_of_staff_and_refuses_nobody_and_nothing(conn):
    t = tenant(conn)
    a, b = _skills(conn, 2)
    who = _staff(conn, t)
    _staff(conn, t, "left@school.invalid", active=False)
    link = _link(conn, t, b, a)
    for email, link_id, why in (
        ("stranger@school.invalid", link, "staff"),
        ("", link, "staff"),
        ("left@school.invalid", link, "staff"),
        ("checker@school.invalid", uuid.uuid4(), "no link"),
        ("checker@school.invalid", "not-an-id", "id"),
    ):
        with pytest.raises(skill_links.Refused) as e:
            skill_links.confirm(conn, str(link_id), email)
        assert why in str(e.value), str(e.value)
    assert (
        conn.execute("select status from skill_link where id = %s", (link,)).fetchone()["status"]
        == "proposed"
    )
    assert skill_links.confirm(conn, str(link), "  Checker@School.invalid ") == "confirmed"
    row = conn.execute(
        "select status, confirmed_by, confirmed_at from skill_link where id = %s", (link,)
    ).fetchone()
    assert (row["status"], row["confirmed_by"]) == ("confirmed", who) and row["confirmed_at"] is not None
    stamp = row["confirmed_at"]
    _staff(conn, t, "second@school.invalid")
    assert skill_links.confirm(conn, str(link), "second@school.invalid") == "already"
    after = conn.execute(
        "select confirmed_by, confirmed_at from skill_link where id = %s", (link,)
    ).fetchone()
    assert (after["confirmed_by"], after["confirmed_at"]) == (who, stamp), "the first person's word stands"


def test_the_commands_exist_take_no_free_text_to_a_shell_and_write_nothing_when_refused(tmp_path):
    from typer.testing import CliRunner

    from engine.cli import app

    run = CliRunner().invoke
    assert run(app, ["skill-links", "--help"]).exit_code == 0
    assert run(app, ["skill-links", "confirm", "no-such-id", "--by", "nobody@school.invalid"]).exit_code == 1
    assert run(app, ["skill-links", "load", str(tmp_path / "missing.csv")]).exit_code == 1
    source = (ROOT / "packages/engine/engine/w3_read/skill_links.py").read_text()
    assert not re.search(r"\b(subprocess|os\.system|shell=True|eval|exec)\b", source)


def test_the_audit_check_still_counts_every_prerequisite_whatever_its_status(conn):
    from engine.checks import links

    got = links.compare(conn)
    assert (
        got["prerequisites"]
        == conn.execute("select count(*) as n from skill_prerequisite_audit").fetchone()["n"]
        == 282
    )
    assert not [d for d in got["disagree"] if "before itself" in d]


def test_a_row_with_too_many_values_is_refused_at_its_line_not_a_traceback(conn, tmp_path):
    """A reason is prose, and prose has commas: unquoted, the row is longer than the header."""
    a, b = _skills(conn, 2)
    f = _csv(tmp_path, f"{a},{b},Counting before adding,list", f"{b},{a},handling clay, then shaping,list")
    with pytest.raises(skill_links.Refused) as e:
        skill_links.load(conn, f)
    assert "line 3" in str(e.value) and "quotes" in str(e.value)


def test_a_reason_in_quotes_may_run_over_two_lines_and_the_next_line_is_counted_right(conn, tmp_path):
    a, b, c = _skills(conn, 3)
    f = _csv(tmp_path, f'{a},{b},"first line\nsecond line",list', f"{b},{c},,list")
    with pytest.raises(skill_links.Refused) as e:
        skill_links.load(conn, f)
    assert "line 4" in str(e.value) and "reason" in str(e.value), "the empty reason is on line 4 of the file"
    skill_links.load(conn, _csv(tmp_path, f'{a},{b},"first line\nsecond line",list'))
    row = conn.execute("select reason from skill_link where skill_code = %s", (b,)).fetchone()
    assert row["reason"] == "first line\nsecond line"


def test_every_line_is_read_before_any_is_written(conn, tmp_path):
    """A wrong line late in the list is found before the first pair is written, so the refusal needs no rollback."""
    a, b, c = _skills(conn, 3)
    f = _csv(tmp_path, f"{a},{b},r,list", f"{b},NOT.A.SKILL,r,list")
    with pytest.raises(skill_links.Refused):
        skill_links.load(conn, f)
    assert conn.execute("select count(*) as n from skill_link").fetchone()["n"] == 0


def test_a_school_with_no_confirming_state_cannot_confirm_and_is_told_so(conn):
    t = tenant(conn)
    a, b = _skills(conn, 2)
    _staff(conn, t)
    link = _link(conn, t, b, a)
    conn.execute("update link_status set confirmed = false where tenant_id = %s", (t,))
    with pytest.raises(skill_links.Refused) as e:
        skill_links.confirm(conn, str(link), "checker@school.invalid")
    assert "none that means confirmed" in str(e.value)


def test_the_words_the_seeders_give_a_draft_are_the_words_the_migration_gave_the_rows_already_there():
    sql = (ROOT / "supabase/migrations/20270103090000_skill_links.sql").read_text()
    assert f"'{topics.DRAFT_SOURCE}'" in sql
    assert f"'{topics.DRAFT_REASON}'" in sql
    assert f"'{english.DRAFT_REASON}'" in sql
