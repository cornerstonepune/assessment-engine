"""M0-05: people and enrolment, first slice (goals/m0-05-people-enrolment.yaml).

Every person and child here is a PLACEHOLDER made up for the test ("Placeholder Child 07", ann@example.test); the
Children List itself is Nimish's, arrives outside git, and is never in a test. Runs only on the local test database."""

import json
import os
from datetime import date

import psycopg
import pytest

from engine.core import db, people
from tests.test_cli import run

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
FROM = "2026-11-05"
SIGN_IN = [  # placeholders; the password field is a stand-in for a hash and must never reach the staff tables
    {
        "email": "ann@example.test",
        "name": "Placeholder Ann",
        "role": "educator",
        "password": "scrypt$X$fake",
        "classes": ["K2"],
    },
    {
        "email": "bea@example.test",
        "name": "Placeholder Bea",
        "role": "educator",
        "password": "scrypt$X$fake",
        "classes": [],
    },
    {
        "email": "cy@example.test",
        "name": "Placeholder Cy",
        "role": "coordinator",
        "password": "scrypt$X$fake",
        "classes": [],
    },
]


def born(i: int) -> str:
    return f"{i % 27 + 1:02d}/{i % 12 + 1:02d}/{date.today().year - 5}"


def children(n: int = 22) -> list[str]:
    return ["number,name,birthday", *(f"{i},Placeholder Child {i:02d},{born(i)}" for i in range(1, n + 1))]


def listing(tmp_path, lines=None, name="list.csv"):
    path = tmp_path / name
    path.write_text("\n".join(lines or children()) + "\n")
    return str(path)


def wipe(conn):
    """Everything this slice makes, in the test database only (db.local_copy refuses any other)."""
    conn.execute("delete from staff_role_grant")
    conn.execute("delete from enrolment")
    conn.execute("delete from school_class")
    conn.execute("delete from academic_year")
    conn.execute("delete from staff")
    # a child is never deleted (their evidence cannot be); a test's children are moved off the class and set aside
    conn.execute(
        "update child set active = false, section = 'SL-OLD-' || substr(id::text, 1, 8)"
        " where section in ('K2', 'SL-THREE')"
    )


@pytest.fixture
def school():
    with db.connect() as conn:
        was = conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]
        wipe(conn)
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(SIGN_IN),))
        conn.commit()
    yield
    with db.connect() as conn:
        wipe(conn)
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(was),))
        conn.commit()


def rows(sql, *params):
    with db.connect() as conn:
        return conn.execute(sql, params).fetchall()


def load_everything(tmp_path, *flags):
    imported = run("staff", "import", "--apply", "--by", "tester")
    assert imported.exit_code == 0, imported.output_plain
    return run("enrol", "k2", listing(tmp_path), "--apply", "--by", "tester", "--from", FROM, *flags)


@needs_db
def test_the_k2_educator_her_class_and_its_children_with_roll_numbers_are_all_in_the_tables(tmp_path, school):
    done = load_everything(tmp_path, "--teacher", "ann@example.test")
    assert done.exit_code == 0, done.output_plain
    teacher = rows(
        "select p.name, c.section, c.grade_code, y.label, g.from_date, g.granted_by"
        " from staff_role_grant g join pii.staff p on p.staff_id = g.staff_id"
        " join school_class c on c.id = g.class_id join academic_year y on y.id = c.academic_year_id"
        " where g.role_code = 'class_teacher' and g.to_date is null"
    )
    assert [(t["name"], t["section"], t["grade_code"], t["label"], str(t["from_date"])) for t in teacher] == [
        ("Placeholder Ann", "K2", "K2", "2026-27", FROM)
    ]
    kids = rows(
        "select e.roll_no, p.first_name, p.last_name from enrolment e join school_class c on c.id = e.class_id"
        " join child k on k.id = e.child_id join pii.child p on p.child_id = k.id"
        " where c.section = 'K2' and e.to_date is null"
    )
    assert sorted(int(k["roll_no"]) for k in kids) == list(range(1, 23))
    assert all(k["first_name"] == "Placeholder" for k in kids)
    # the child's own row says the same class and roll number the old pages read
    assert (
        rows("select count(*) n from child where section = 'K2' and band = 'K2' and roll_no ~ '^[0-9]+$'")[0][
            "n"
        ]
        == 22
    )


@needs_db
def test_a_child_is_in_a_class_only_through_an_enrolment_and_a_move_closes_one_and_opens_another(
    tmp_path, school
):
    assert load_everything(tmp_path).exit_code == 0
    with db.connect() as conn:
        child = conn.execute("select id from child where section = 'K2' and roll_no = '3'").fetchone()["id"]
        t = conn.execute("select id from tenant").fetchone()["id"]
        k2 = conn.execute(
            "select id, campus_id, academic_year_id from school_class where section = 'K2'"
        ).fetchone()
        g3 = conn.execute(
            "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
            " values (%s,%s,%s,'G3','SL-THREE') returning id",
            (t, k2["campus_id"], k2["academic_year_id"]),
        ).fetchone()["id"]
        assert conn.execute(
            "select enrol_child(%s,%s,'3',%s,'t') r", (child, k2["id"], date(2026, 11, 5))
        ).fetchone()["r"] == {"changed": False}
        moved = conn.execute(
            "select enrol_child(%s,%s,'9',%s,'t') r", (child, g3, date(2027, 1, 4))
        ).fetchone()["r"]
        assert moved["changed"] is True
        history = conn.execute(
            "select class_id, roll_no, from_date, to_date from enrolment where child_id = %s order by from_date",
            (child,),
        ).fetchall()
        assert [(h["class_id"], h["roll_no"], h["to_date"]) for h in history] == [
            (k2["id"], "3", date(2027, 1, 4)),
            (g3, "9", None),
        ]
        # the child is the same row throughout: nothing that hangs off their id moved
        assert (
            conn.execute("select id from child where section = 'K2' and roll_no = '3'").fetchone()["id"]
            == child
        )
        # earlier than where they are now is refused, and a second open row cannot be made by hand
        with pytest.raises(psycopg.errors.RaiseException, match="date_before_current"):
            conn.execute("select enrol_child(%s,%s,'3',%s,'t')", (child, k2["id"], date(2026, 12, 1)))
        conn.rollback()
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "insert into enrolment (tenant_id, child_id, class_id, roll_no, from_date, recorded_by)"
                " values (%s,%s,%s,'4','2027-02-01','t')",
                (t, child, k2["id"]),
            )
        conn.rollback()


@needs_db
def test_a_second_class_teacher_warns_and_is_allowed_only_with_a_recorded_reason(tmp_path, school):
    assert load_everything(tmp_path, "--teacher", "ann@example.test").exit_code == 0
    again = ["enrol", "k2", listing(tmp_path), "--apply", "--by", "tester", "--from", FROM, "--teacher"]
    warned = run(*again, "bea@example.test")
    assert warned.exit_code == 1 and "already has a class educator" in warned.output_plain
    assert "--override-reason" in warned.output_plain
    assert rows("select count(*) n from staff_role_grant where role_code = 'class_teacher'")[0]["n"] == 1
    allowed = run(
        *again, "bea@example.test", "--override-reason", "Ann is on leave; Bea covers until January"
    )
    assert allowed.exit_code == 0, allowed.output_plain
    held = rows(
        "select override_reason from staff_role_grant where role_code = 'class_teacher' order by created_at"
    )
    assert [h["override_reason"] for h in held] == [None, "Ann is on leave; Bea covers until January"]
    # the rule lives in the database: a hand-written insert meets the same warning, and a class role needs its class
    with db.connect() as conn:
        t = conn.execute("select id from tenant").fetchone()["id"]
        k2 = conn.execute("select id from school_class").fetchone()["id"]
        cy = conn.execute("select staff_id from pii.staff where email = 'cy@example.test'").fetchone()[
            "staff_id"
        ]
        sql = "insert into staff_role_grant (tenant_id, staff_id, role_code, class_id, from_date, granted_by) values (%s,%s,%s,%s,'2026-12-01','t')"
        with pytest.raises(psycopg.errors.RaiseException, match="one_per_class"):
            conn.execute(sql, (t, cy, "class_teacher", k2))
        conn.rollback()
        with pytest.raises(psycopg.errors.RaiseException, match="needs_class"):
            conn.execute(sql, (t, cy, "class_teacher", None))
        conn.rollback()
        with pytest.raises(psycopg.errors.RaiseException, match="not_for_a_class"):
            conn.execute(sql, (t, cy, "educator", k2))
        conn.rollback()


@needs_db
def test_staff_import_copies_the_staff_list_leaves_the_config_and_changes_nothing_the_second_time(
    tmp_path, school
):
    def config():
        return rows("select value from config where key = 'app.staff'")[0]["value"]

    before = config()
    dry = run("staff", "import")
    assert dry.exit_code == 0 and "staff added: 3" in dry.output_plain and "dry run" in dry.output_plain
    assert rows("select count(*) n from staff")[0]["n"] == 0
    refused = run("staff", "import", "--apply")
    assert refused.exit_code != 0 and "--by" in refused.output_plain
    done = run("staff", "import", "--apply", "--by", "tester")
    assert done.exit_code == 0, done.output_plain
    assert rows("select count(*) n from staff")[0]["n"] == 3
    got = rows(
        "select p.email, g.role_code from pii.staff p join staff_role_grant g on g.staff_id = p.staff_id order by p.email"
    )
    assert [(g["email"], g["role_code"]) for g in got] == [
        ("ann@example.test", "educator"),
        ("bea@example.test", "educator"),
        ("cy@example.test", "coordinator"),
    ]
    assert config() == before  # left in place, hashes and all
    assert "scrypt" not in json.dumps(
        rows("select to_jsonb(s) from staff s") + rows("select to_jsonb(p) from pii.staff p"), default=str
    )
    again = run("staff", "import", "--apply", "--by", "tester")
    assert (
        again.exit_code == 0
        and "already there: 3" in again.output_plain
        and "added" not in again.output_plain
    )
    assert rows("select count(*) n from staff_role_grant")[0]["n"] == 3
    # an entry whose role is no role is refused in words and nothing is written
    bad = [
        *SIGN_IN,
        {
            "email": "d@example.test",
            "name": "Placeholder D",
            "role": "wizard",
            "password": "x",
            "classes": [],
        },
    ]
    with db.connect() as conn:
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(bad),))
        conn.commit()
    refused = run("staff", "import", "--apply", "--by", "tester")
    assert refused.exit_code == 1 and "'wizard' is not a role" in refused.output_plain
    assert rows("select count(*) n from staff")[0]["n"] == 3


@needs_db
def test_enrol_k2_is_a_dry_run_until_applied_and_a_second_run_changes_nothing(tmp_path, school):
    path = listing(tmp_path)
    dry = run("enrol", "k2", path, "--from", FROM)
    assert dry.exit_code == 0 and "children added: 22" in dry.output_plain and "dry run" in dry.output_plain
    assert rows("select count(*) n from child where section = 'K2'")[0]["n"] == 0
    assert rows("select count(*) n from school_class")[0]["n"] == 0
    assert run("enrol", "k2", path, "--apply").exit_code != 0  # --by is needed
    assert run("enrol", "k2", path, "--apply", "--by", "tester", "--from", FROM).exit_code == 0

    def state():
        return (
            rows("select id, updated_at from child where section = 'K2' order by roll_no"),
            rows("select id, updated_at from enrolment order by roll_no"),
            rows("select count(*) n from school_class")[0]["n"],
            rows(
                "select count(*) n from pii.child p join child c on c.id = p.child_id"
                " where c.section = 'K2' and p.birthday is not null"
            )[0]["n"],
        )

    first = state()
    again = run("enrol", "k2", path, "--apply", "--by", "tester", "--from", FROM)
    assert (
        again.exit_code == 0
        and "already there: 22" in again.output_plain
        and "added" not in again.output_plain
    )
    assert state() == first
    assert first[3] == 22


@needs_db
def test_a_list_with_a_duplicate_or_a_bad_row_is_refused_in_words_and_writes_nothing(tmp_path, school):
    lines = children(3) + [
        f"2,Placeholder Other,{born(8)}",  # roll 2 twice
        f"7,Placeholder Child 01,{born(1)}",  # the same child as roll 1, under another number
        "x y,Placeholder Bad,01/01/2020",  # not a roll number
        "8,Placeholder Old,01/01/1990",  # not a K2 child's age
        "9,Placeholder Slip,31/02/2021",  # not a date
        "10,,01/01/2021",  # no name
    ]
    out = run("enrol", "k2", listing(tmp_path, lines), "--apply", "--by", "tester", "--from", FROM)
    text = out.output_plain
    assert out.exit_code == 1 and "nothing was written" in text
    for line, why in (
        (5, "also on line 3"),
        (6, "same child as line 2"),
        (7, "not a roll number"),
        (8, "not a K2 child's"),
        (9, "birthday not read"),
        (10, "no name"),
    ):
        assert f"line {line}:" in text and why in text, text
    assert rows("select count(*) n from child where section = 'K2'")[0]["n"] == 0
    assert rows("select count(*) n from school_class")[0]["n"] == 0
    # a missing column is refused whole
    short = run("enrol", "k2", listing(tmp_path, ["number,name", "1,Placeholder X"], name="s.csv"))
    assert short.exit_code != 0 and "no column called birthday" in short.output_plain
    # a roll number already held by a different child is refused, never overwritten; --match-existing is the way to say "same"
    assert (
        run(
            "enrol",
            "k2",
            listing(tmp_path, children(2), name="a.csv"),
            "--apply",
            "--by",
            "t",
            "--from",
            FROM,
        ).exit_code
        == 0
    )
    other = run(
        "enrol",
        "k2",
        listing(tmp_path, ["number,name,birthday", f"1,Placeholder Someone Else,{born(1)}"], name="b.csv"),
        "--apply",
        "--by",
        "t",
    )
    assert other.exit_code == 1 and "already a different child" in other.output_plain


@needs_db
def test_no_name_email_phone_or_birthday_is_outside_pii_and_no_report_prints_one(tmp_path, school):
    owned = rows(
        "select table_schema, table_name, column_name from information_schema.columns where table_name in"
        " ('campus','academic_year','school_class','enrolment','staff','role','staff_role_grant')"
        " and table_schema = 'public'"
    )
    assert owned
    assert not [
        c
        for c in owned
        if any(w in c["column_name"] for w in ("name", "email", "phone", "birth", "dob"))
        and c["column_name"] != "name"
    ], owned
    assert {c["column_name"] for c in owned if c["column_name"] == "name"} == {
        "name"
    }  # campus and nothing person-shaped
    assert {c["table_name"] for c in owned if c["column_name"] == "name"} == {"campus"}
    pii_cols = {
        r["column_name"]
        for r in rows(
            "select column_name from information_schema.columns where table_schema = 'pii' and table_name = 'staff'"
        )
    }
    assert {"name", "email", "phone"} <= pii_cols
    for role in ("app_web", "app_engine"):
        assert rows("select has_table_privilege(%s, 'pii.staff', 'select') p", role)[0]["p"] is False
    out = (
        run("staff", "import", "--apply", "--by", "tester").output_plain
        + load_everything(tmp_path, "--teacher", "ann@example.test").output_plain
    )
    for private in ("Placeholder", "example.test", f"/{date.today().year - 5}"):
        assert private not in out
    # the one way to read a staff member's contact details writes who asked
    with db.connect() as conn:
        sid = conn.execute("select staff_id from pii.staff where email = 'ann@example.test'").fetchone()[
            "staff_id"
        ]
        who = conn.execute("select * from pii.read_staff(%s, 'tester')", (sid,)).fetchone()
        assert who["name"] == "Placeholder Ann" and who["email"] == "ann@example.test"
        assert (
            conn.execute(
                "select count(*) n from access_log where actor = 'tester' and action = 'read_pii_staff'"
            ).fetchone()["n"]
            == 1
        )
        conn.rollback()
    assert (
        people.year_label(date(2027, 3, 31)) == "2026-27" and people.year_label(date(2027, 4, 1)) == "2027-28"
    )
