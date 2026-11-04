"""Names stay in pii (CLAUDE.md rule 6): who signed a people load is a staff id, never a typed name or email.

goals/fix-staff-by-id.yaml. `--by` takes the signer's EMAIL; the engine looks it up (public.staff_of_email) and stores the
staff id, as text, in staff_role_grant.granted_by and enrolment.recorded_by. Every person here is a PLACEHOLDER
(ann@example.test, "Placeholder Ann"); the test database only."""

import pytest

from engine.core import db
from tests.test_people import SIGN_IN, children, listing, needs_db, rows, run
from tests.test_people import school as school  # the fixture, named so usefixtures finds it

pytestmark = pytest.mark.usefixtures("forgets_what_it_commits")

SIGNER = "cy@example.test"  # the coordinator of the placeholder sign-in list
FROM = "2026-11-05"
PLACEHOLDER_WORDS = ("placeholder", "example.test")  # every name and email the fixtures hold


def staff_id(email: str) -> str:
    with db.connect() as conn:
        found = conn.execute("select staff_id from pii.staff where email = %s", (email,)).fetchone()
    return str(found["staff_id"])


def written() -> tuple[int, int, int]:
    n = rows(
        "select (select count(*) from staff) s, (select count(*) from staff_role_grant) g, (select count(*) from enrolment) e"
    )[0]
    return n["s"], n["g"], n["e"]


@needs_db
@pytest.mark.usefixtures("school")
def test_the_first_staff_import_is_signed_by_an_email_on_the_sign_in_list_and_stores_the_staff_id():
    done = run("staff", "import", "--apply", "--by", "CY@Example.Test ")  # any case, a stray space
    assert done.exit_code == 0, done.output_plain
    cy = staff_id(SIGNER)
    signed = {g["granted_by"] for g in rows("select granted_by from staff_role_grant")}
    assert signed == {cy}  # every grant, the signer's own included, carries the id
    assert (
        len(rows("select 1 from staff_role_grant")) == 3
    )  # ann, bea (educator) and cy (coordinator); dee is a class role


@needs_db
@pytest.mark.usefixtures("school")
def test_enrolment_is_signed_by_the_staff_id_of_the_email(tmp_path):
    assert run("staff", "import", "--apply", "--by", SIGNER).exit_code == 0
    done = run(
        "enrol", "k2", listing(tmp_path), "--apply", "--by", "Cy@example.test", "--from", FROM,
        "--teacher", "ann@example.test",
    )  # fmt: skip
    assert done.exit_code == 0, done.output_plain
    cy = staff_id(SIGNER)
    assert {e["recorded_by"] for e in rows("select recorded_by from enrolment")} == {cy}
    teacher = rows("select granted_by from staff_role_grant where role_code = 'class_teacher'")
    assert [t["granted_by"] for t in teacher] == [cy]


@needs_db
@pytest.mark.usefixtures("school")
@pytest.mark.parametrize("who", ["nobody@example.test", "Placeholder Cy", "tester", "cy@example"])
def test_a_signer_who_is_not_staff_is_refused_before_any_write_in_a_dry_run_too(tmp_path, who):
    assert run("staff", "import", "--apply", "--by", SIGNER).exit_code == 0
    before = written()
    for extra in ([], ["--apply"]):
        out = run("enrol", "k2", listing(tmp_path), *extra, "--by", who, "--from", FROM)
        assert out.exit_code != 0, out.output_plain
        assert "--by" in out.output_plain and "staff" in out.output_plain
        assert who not in out.output_plain  # the refusal does not echo what was typed
    assert written() == before


@needs_db
@pytest.mark.usefixtures("school")
def test_the_staff_import_refuses_a_signer_who_is_not_on_the_list_and_writes_nothing():
    for extra in ([], ["--apply"]):
        out = run("staff", "import", *extra, "--by", "stranger@example.test")
        assert out.exit_code != 0 and "--by" in out.output_plain, out.output_plain
        assert "stranger" not in out.output_plain
    assert written() == (0, 0, 0)
    ok = run("staff", "import", "--by", SIGNER)  # on the list: the dry run is fine, and writes nothing
    assert ok.exit_code == 0 and "dry run" in ok.output_plain, ok.output_plain
    assert written() == (0, 0, 0)


@needs_db
@pytest.mark.usefixtures("school")
def test_only_the_staff_import_may_name_a_signer_before_the_staff_exist(tmp_path):
    out = run("enrol", "k2", listing(tmp_path, children(2)), "--apply", "--by", SIGNER, "--from", FROM)
    assert out.exit_code != 0 and "--by" in out.output_plain, out.output_plain
    assert written() == (0, 0, 0)


@needs_db
@pytest.mark.usefixtures("school")
def test_a_second_run_signed_by_the_same_email_adds_nothing(tmp_path):
    load = [
        "enrol",
        "k2",
        listing(tmp_path),
        "--apply",
        "--by",
        SIGNER,
        "--from",
        FROM,
        "--teacher",
        "ann@example.test",
    ]
    assert run("staff", "import", "--apply", "--by", SIGNER).exit_code == 0
    assert run(*load).exit_code == 0
    first = written()
    assert run("staff", "import", "--apply", "--by", SIGNER).exit_code == 0
    assert run(*load).exit_code == 0
    assert written() == first


@needs_db
@pytest.mark.usefixtures("school")
def test_no_name_or_email_is_in_any_text_column_of_the_people_tables_after_a_full_load(tmp_path):
    began = rows("select clock_timestamp() t")[0][
        "t"
    ]  # the access log is never cleared: only this run's rows count
    assert run("staff", "import", "--apply", "--by", SIGNER).exit_code == 0
    done = run(
        "enrol",
        "k2",
        listing(tmp_path),
        "--apply",
        "--by",
        SIGNER,
        "--from",
        FROM,
        "--teacher",
        "ann@example.test",
    )
    assert done.exit_code == 0, done.output_plain
    tables = (
        "campus",
        "academic_year",
        "school_class",
        "enrolment",
        "staff",
        "staff_role_grant",
        "role",
        "child",
        "access_log",
    )
    cols = rows(
        "select table_name t, column_name c from information_schema.columns where table_schema = 'public'"
        " and table_name = any(%s) order by 1, 2",
        list(tables),
    )
    assert {c["t"] for c in cols} == set(tables)  # every column of every table, whatever its type, as text
    new = "and occurred_at >= %s"
    found: list[str] = []
    for col in cols:
        for word in PLACEHOLDER_WORDS:
            mine = (new, began) if col["t"] == "access_log" else ("", None)
            sql = f'select 1 from "{col["t"]}" where "{col["c"]}"::text ilike %s {mine[0]} limit 1'
            hit = rows(sql, f"%{word}%", *([mine[1]] if mine[1] else []))
            if hit:
                found.append(f"{col['t']}.{col['c']} holds {word!r}")
    assert found == []
    assert {
        g["a"] for g in rows("select distinct actor a from access_log where occurred_at >= %s", began)
    } <= {
        staff_id(SIGNER),
        "staff_of_email",
        "engine enrol k2 (dry run)",
    }


@needs_db
@pytest.mark.usefixtures("school")
def test_no_report_prints_the_signers_email_or_name_or_a_childs_name(tmp_path):
    seen = [run("staff", "import", "--by", SIGNER), run("staff", "import", "--apply", "--by", SIGNER)]
    path = listing(tmp_path)
    for extra in ([], ["--apply"]):
        seen.append(
            run("enrol", "k2", path, *extra, "--by", SIGNER, "--from", FROM, "--teacher", "ann@example.test")
        )
    for out in seen:
        assert out.exit_code == 0, out.output_plain
        text = out.output_plain.lower()
        assert "@" not in text and "placeholder" not in text, out.output_plain
    assert len(SIGN_IN) == 4  # the fixture the scan above relies on
