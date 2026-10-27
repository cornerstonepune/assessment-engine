"""`engine staff load PATH [--apply]`: a table of staff put on the list in one go (goals/staffload_a_table_of_staff.yaml).

Nimish, 27 Oct 2026: "I will give you a table of teachers and subjects and grades and you then do the needful." The
table has names and emails in it, so it stays outside the repository and is read by path, as the class list is; every
person here is made up, on an example.test address.
"""

import copy
import json
import logging
import os
import re
import stat

import pytest

from engine.core import db, settings
from engine.core.staff import staff_hash
from tests.test_cli import run

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
SECTIONS = ("SL-ONE", "SL-TWO")
HEADER = "name,email,role,subjects,classes"


def _staff():
    with db.connect() as conn:
        return conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]


def _file(tmp_path, *lines, name="staff.csv"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def _load(path, *flags):
    return run("staff", "load", path, *flags)


def _passwords(out):
    """The `email  password` lines printed after the words, as `{email: password}`."""
    return dict(
        re.findall(r"^\s*(\S+@example\.test)\s+(\S{12,})\s*$", out.partition("Give each person")[2], re.M)
    )


@pytest.fixture
def school():
    """Two classes with a child in each, the staff list as it was put back afterwards, and nothing else changed."""
    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        was = conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]
        for section in SECTIONS:
            conn.execute(
                "insert into child (tenant_id, roll_no, section, band) values (%s, '1', %s, 'G2')"
                " on conflict (tenant_id, section, roll_no) do update set active = true",
                (tenant, section),
            )
        conn.commit()
    yield SECTIONS
    with db.connect() as conn:
        conn.execute("update child set active = false where section = any(%s)", (list(SECTIONS),))
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(was),))
        conn.commit()


@needs_db
def test_a_csv_or_a_table_pasted_from_a_spreadsheet_is_read_and_a_missing_column_is_refused_in_words(
    tmp_path, school
):
    a = "Ann One,ann@example.test,educator,Maths,SL-ONE"
    comma = _load(_file(tmp_path, HEADER, a))
    tabs = _load(_file(tmp_path, HEADER.replace(",", "\t"), a.replace(",", "\t"), name="pasted.tsv"))
    assert comma.exit_code == 0 and tabs.exit_code == 0, tabs.output_plain
    assert "ann@example.test" in comma.output_plain and "ann@example.test" in tabs.output_plain

    # several classes and subjects in one cell: commas, semicolons and spaces all separate them
    many = _load(
        _file(
            tmp_path,
            HEADER,
            'Ann One,ann@example.test,educator,"NUM, Maths; NUM","SL-ONE SL-TWO;SL-ONE"',
            name="m.csv",
        )
    )
    assert "classes SL-ONE, SL-TWO" in many.output_plain and "subjects NUM" in many.output_plain

    # a column the loader does not use is ignored with one line; a column it needs and is not there is refused
    extra = _load(_file(tmp_path, HEADER + ",phone", a + ",12345", name="x.csv"))
    assert extra.exit_code == 0 and "ignored column: phone" in extra.output_plain
    missing = _load(
        _file(tmp_path, "name,email,role,classes", "Ann One,ann@example.test,educator,SL-ONE", name="y.csv")
    )
    assert missing.exit_code != 0 and "no column called subjects" in missing.output_plain
    assert "name, email, role, subjects, classes" in missing.output_plain


@needs_db
def test_a_dry_run_changes_nothing_and_says_what_each_row_would_do(tmp_path, school):
    first = _file(tmp_path, HEADER, "Ann One,ann@example.test,educator,NUM,SL-ONE", name="first.csv")
    assert _load(first, "--apply").exit_code == 0
    before = copy.deepcopy(_staff())
    path = _file(
        tmp_path,
        HEADER,
        "Ann One,ann@example.test,educator,NUM,SL-TWO",  # the classes change
        "Ben Two,ben@example.test,educator,NUM,SL-ONE",  # a new person
    )
    r = _load(path)
    assert r.exit_code == 0, r.output_plain
    assert _staff() == before, "without --apply nothing is written"
    out = r.output_plain
    assert re.search(
        r"ann@example\.test\s+update classes and subjects from classes SL-ONE, subjects NUM to classes SL-TWO, subjects NUM",
        out,
    )
    assert re.search(r"ben@example\.test\s+add", out)
    assert "dry run" in out and "--apply" in out and "no password" in out.lower()
    # the same file as already applied says no change
    assert re.search(r"ann@example\.test\s+no change", _load(first).output_plain)


@needs_db
def test_every_refusal_is_said_in_words_and_one_refused_row_stops_the_apply(tmp_path, school):
    with db.connect() as conn:
        roles = sorted(
            {
                r
                for who in conn.execute("select value from config where key='people.decides'")
                .fetchone()["value"]
                .values()
                for r in who
            }
        )
    assert (
        _load(_file(tmp_path, HEADER, "Cy Three,cy@example.test,educator,NUM,SL-ONE"), "--apply").exit_code
        == 0
    )
    path = _file(
        tmp_path,
        HEADER,
        "Good Person,good@example.test,educator,NUM,SL-ONE",
        "No At,not-an-email,educator,NUM,SL-ONE",
        "Dup A,dup@example.test,educator,NUM,SL-ONE",
        "Dup B,DUP@example.test,educator,NUM,SL-TWO",
        "Odd Role,odd@example.test,headmaster,NUM,SL-ONE",
        "No Class,noclass@example.test,educator,NUM,SL-NOBODY",
        "No Subject,nosub@example.test,educator,Astrology,SL-ONE",
        "Cy Three,cy@example.test,coordinator,NUM,SL-ONE",  # a role is not changed by this tool
    )
    before = copy.deepcopy(_staff())
    r = _load(path)
    out = r.output_plain
    assert r.exit_code == 0 and _staff() == before
    for fragment in (
        "refused: not-an-email is not shaped like an email",
        "refused: dup@example.test is in the file more than once",
        f"refused: no one holds the role 'headmaster' (it is one of {', '.join(roles)})",
        "refused: no child is in class SL-NOBODY",
        "refused: no subject is called 'Astrology'",
        "refused: already on the list as educator",
    ):
        assert fragment in out, (fragment, out)
    assert len(re.findall(r"dup@example\.test\s+refused", out)) == 2, "both rows of a duplicate are refused"
    assert re.search(r"good@example\.test\s+add", out)

    stopped = _load(path, "--apply")
    assert (
        stopped.exit_code != 0
        and "nothing was applied" in stopped.output_plain
        and "--skip-refused" in stopped.output_plain
    )
    assert _staff() == before, "one refused row and nothing is applied"

    partial = _load(path, "--apply", "--skip-refused")
    assert partial.exit_code == 0, partial.output_plain
    emails = {s["email"] for s in _staff()} - {s["email"] for s in before}
    assert emails == {"good@example.test"}, "only the row that was fine"


@needs_db
def test_a_subject_is_read_by_its_code_or_its_name_and_the_dry_run_says_which_code(tmp_path, school):
    with db.connect() as conn:
        s = conn.execute("select code, name, label from subject limit 1").fetchone()
    rows = [
        f"A,a@example.test,educator,{s['code'].lower()},SL-ONE",
        f"B,b@example.test,educator,{s['label'].upper()},SL-ONE",
        f'C,c@example.test,educator,"{s["name"]}",SL-ONE',
    ]
    r = _load(_file(tmp_path, HEADER, *rows))
    assert r.exit_code == 0, r.output_plain
    assert f"read {s['label'].upper()!r} as {s['code']}" in r.output_plain
    assert f"read {s['name']!r} as {s['code']}" in r.output_plain
    assert len(re.findall(rf"subjects {s['code']}\b", r.output_plain)) == 3
    assert _load(_file(tmp_path, HEADER, *rows), "--apply").exit_code == 0
    assert all(p["subjects"] == [s["code"]] for p in _staff() if p["email"].endswith("@example.test"))


@needs_db
def test_apply_adds_updates_leaves_the_others_and_a_second_run_changes_nothing(tmp_path, school):
    with db.connect() as conn:
        others = [
            {
                "email": "other@example.test",
                "name": "Other",
                "role": "educator",
                "password": "scrypt$x",
                "classes": ["SL-ONE"],
            }
        ]
        conn.execute(
            "update config set value = value || %s::jsonb where key = 'app.staff'", (json.dumps(others),)
        )
        conn.commit()
    untouched = [s for s in _staff() if s["email"] == "other@example.test"]
    path = _file(
        tmp_path,
        HEADER,
        "Ann One,ann@example.test,educator,NUM,SL-ONE",
        "Ben Two,ben@example.test,educator,NUM,SL-ONE SL-TWO",
    )
    first = _load(path, "--apply")
    assert first.exit_code == 0, first.output_plain
    assert "not in the file" in first.output_plain and "left as they are" in first.output_plain
    got = {s["email"]: s for s in _staff()}
    assert got["ann@example.test"]["classes"] == ["SL-ONE"] and got["ben@example.test"]["classes"] == [
        "SL-ONE",
        "SL-TWO",
    ]
    assert got["ann@example.test"]["subjects"] == ["NUM"]
    assert [s for s in _staff() if s["email"] == "other@example.test"] == untouched

    # a second run: no change for anyone, nothing written, no password given
    after_first = copy.deepcopy(_staff())
    second = _load(path, "--apply")
    assert second.exit_code == 0 and _staff() == after_first
    assert (
        len(re.findall(r"@example\.test\s+no change", second.output_plain)) == 2
        and "Give each person" not in second.output_plain
    )

    # a changed row updates the classes and subjects of the person already there
    third = _load(
        _file(tmp_path, HEADER, "Ann One,ann@example.test,educator,NUM,SL-TWO", name="t.csv"), "--apply"
    )
    assert third.exit_code == 0 and "Give each person" not in third.output_plain
    assert {s["email"]: s for s in _staff()}["ann@example.test"]["classes"] == ["SL-TWO"]


@needs_db
def test_a_person_who_already_has_a_password_keeps_it_and_is_given_none(tmp_path, school):
    kept = staff_hash("kept-by-its-owner", "ab" * 16, 16384)
    with db.connect() as conn:
        had = [
            {
                "email": "old@example.test",
                "name": "Old Hand",
                "role": "educator",
                "password": kept,
                "password_set_at": "2026-10-01",
                "classes": [],
            }
        ]
        conn.execute(
            "update config set value = value || %s::jsonb where key = 'app.staff'", (json.dumps(had),)
        )
        conn.commit()
    r = _load(_file(tmp_path, HEADER, "Old Hand,old@example.test,educator,NUM,SL-ONE"), "--apply")
    assert r.exit_code == 0 and "Give each person" not in r.output_plain
    [me] = [s for s in _staff() if s["email"] == "old@example.test"]
    assert me["password"] == kept and me["password_set_at"] == "2026-10-01" and me["classes"] == ["SL-ONE"]


@needs_db
def test_a_new_password_is_made_by_code_hashed_as_the_site_checks_and_shown_once_only(
    tmp_path, school, caplog
):
    path = _file(
        tmp_path,
        HEADER,
        "Ann One,ann@example.test,educator,NUM,SL-ONE",
        "Ben Two,ben@example.test,educator,NUM,SL-TWO",
    )
    with caplog.at_level(logging.DEBUG):
        dry = _load(path)
        r = _load(path, "--apply")
    assert "Give each person" not in dry.output_plain, "a dry run makes and shows no password"
    pw = _passwords(r.output_plain)
    assert (
        set(pw) == {"ann@example.test", "ben@example.test"}
        and pw["ann@example.test"] != pw["ben@example.test"]
    )
    assert (
        "in person or by phone, not in a group chat" in r.output_plain and "Change password" in r.output_plain
    )
    with db.connect() as conn:
        cost = int(settings.threshold(conn, "password.scrypt_n", 16384))
    for email, password in pw.items():
        assert len(password) >= 12 and not set(password) & set("0O1lI|"), "an alphabet with no look-alikes"
        [me] = [s for s in _staff() if s["email"] == email]
        scheme, n, salt, _ = me["password"].split("$")
        assert scheme == "scrypt" and int(n) == cost and me["password"] == staff_hash(password, salt, cost)
        assert r.output_plain.count(password) == 1, "printed once"
        assert password not in json.dumps(_staff()), "never in the database in clear"
        assert password not in caplog.text and password not in dry.output_plain
    assert _passwords(_load(path, "--apply").output_plain) == {}


@needs_db
def test_a_passwords_file_is_private_and_outside_the_repository(tmp_path, school):
    path = _file(tmp_path, HEADER, "Ann One,ann@example.test,educator,NUM,SL-ONE")
    out = tmp_path / "given.txt"
    r = _load(path, "--apply", "--passwords-to", str(out))
    assert r.exit_code == 0, r.output_plain
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert _passwords(r.output_plain)["ann@example.test"] in out.read_text()

    # a file already there is never overwritten, and a place inside the repository is refused, before anything is written
    before = copy.deepcopy(_staff())
    again = _load(
        _file(tmp_path, HEADER, "Ben Two,ben@example.test,educator,NUM,SL-ONE", name="b.csv"),
        "--apply",
        "--passwords-to",
        str(out),
    )
    assert again.exit_code != 0 and "already exists" in again.output_plain and _staff() == before
    inside = _load(
        _file(tmp_path, HEADER, "Ben Two,ben@example.test,educator,NUM,SL-ONE", name="c.csv"),
        "--apply",
        "--passwords-to",
        str(db.REPO_ROOT / "x-passwords.txt"),
    )
    assert inside.exit_code != 0 and "outside the repository" in inside.output_plain and _staff() == before
    assert not (db.REPO_ROOT / "x-passwords.txt").exists()
    # the table itself is read from outside the repository too (rule 6)
    here = db.REPO_ROOT / "x-staff.csv"
    here.write_text(HEADER + "\n")
    try:
        assert _load(str(here)).exit_code != 0
    finally:
        here.unlink()


def test_the_help_says_what_the_columns_are_with_one_made_up_row():
    r = run("staff", "load", "--help")
    assert r.exit_code == 0
    # rich wraps the help in a box at the width of the terminal (80 in CI): read it as a person does, without the box
    said = " ".join(r.output_plain.replace("│", " ").split())
    for fragment in (
        "name, email, role, subjects, classes",
        "Example Teacher, teacher@example.test, educator, Maths, G3",
        "--apply",
        "--skip-refused",
        "--passwords-to",
    ):
        assert fragment in said, fragment
