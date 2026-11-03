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
        "email": "dee@example.test",
        "name": "Placeholder Dee",
        "role": "specialist",
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
    conn.execute(
        "set local session_replication_role = replica"
    )  # a grant is never deleted, except here, in the copy
    conn.execute("delete from staff_role_grant")
    conn.execute("delete from enrolment")
    conn.execute("delete from school_class")
    conn.execute("delete from academic_year")
    conn.execute("delete from pii.staff")
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
        "select p.name, c.section, c.grade_code, y.label, g.valid_from, g.granted_by"
        " from staff_role_grant g join pii.staff p on p.staff_id = g.staff_id"
        " join school_class c on c.id = g.school_class_id join academic_year y on y.id = c.academic_year_id"
        " where g.role_code = 'class_teacher' and g.valid_to is null"
    )
    assert [
        (t["name"], t["section"], t["grade_code"], t["label"], str(t["valid_from"])) for t in teacher
    ] == [("Placeholder Ann", "A", "K2", "2026-27", FROM)]
    kids = rows(
        "select e.roll_no, p.first_name, p.last_name from enrolment e join school_class c on c.id = e.class_id"
        " join child k on k.id = e.child_id join pii.child p on p.child_id = k.id"
        " where c.grade_code = 'K2' and c.section = 'A' and e.to_date is null"
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
            "select id, campus_id, academic_year_id from school_class where grade_code = 'K2'"
        ).fetchone()
        g3 = conn.execute(
            "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
            " values (%s,%s,%s,'G3','A') returning id",
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
        sql = "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by) values (%s,%s,%s,%s,'2026-12-01','t')"
        with pytest.raises(psycopg.errors.RaiseException, match="one_per_class"):
            conn.execute(sql, (t, cy, "class_teacher", k2))
        conn.rollback()
        with pytest.raises(psycopg.errors.RaiseException, match="needs_class"):
            conn.execute(sql, (t, cy, "class_teacher", None))
        conn.rollback()
        with pytest.raises(psycopg.errors.RaiseException, match="wrong_scope"):
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
    assert dry.exit_code == 0 and "staff added: 4" in dry.output_plain and "dry run" in dry.output_plain
    assert rows("select count(*) n from staff")[0]["n"] == 0
    refused = run("staff", "import", "--apply")
    assert refused.exit_code != 0 and "--by" in refused.output_plain
    done = run("staff", "import", "--apply", "--by", "tester")
    assert done.exit_code == 0, done.output_plain
    assert rows("select count(*) n from staff")[0]["n"] == 4
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
        and "already there: 4" in again.output_plain
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
    assert rows("select count(*) n from staff")[0]["n"] == 4


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


@needs_db
def test_the_twelve_roles_of_d026_are_rows_with_their_scope_and_the_rule_is_a_config_row(school):
    got = {r["code"]: r["scope"] for r in rows("select code, scope from role")}
    assert {c for c in got if c != "educator"} == {
        "subject_educator",
        "class_teacher",
        "mentor",
        "assistant",
        "coordinator",
        "deputy_coordinator",
        "curriculum_team",
        "head",
        "ops",
        "cover_educator",
        "special_educator",
        "specialist",
    }
    assert got["subject_educator"] == "class_subject" and got["mentor"] == "child" and got["head"] == "campus"
    assert got["class_teacher"] == "class" and got["specialist"] == "class"
    assert all(r["may_grant"] == ["head", "coordinator"] for r in rows("select may_grant from role"))
    rule = rows("select value from config where key = 'people.class_teacher_rule'")[0]["value"]
    assert rule["from_grade"] == "G1" and set(rule["core_subjects"]) == {"NUM", "ENG"}
    # a role the sign-in list holds for a class (specialist) is not granted at import; the person is added
    out = run("staff", "import", "--apply", "--by", "tester")
    assert out.exit_code == 0 and "roles left to set: 1" in out.output_plain, out.output_plain
    assert (
        rows(
            "select count(*) n from staff_role_grant g join role r on r.code = g.role_code where r.scope <> 'campus'"
        )[0]["n"]
        == 0
    )


@needs_db
def test_d039_from_grade_one_a_core_teacher_is_not_a_class_teacher_unless_a_reason_is_kept(tmp_path, school):
    assert load_everything(tmp_path, "--teacher", "ann@example.test").exit_code == 0
    grant = (
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, subject_code, valid_from,"
        " granted_by, override_reason) values (%s,%s,%s,%s,%s,'2026-12-01','t',%s)"
    )
    with db.connect() as conn:
        t = conn.execute("select id from tenant").fetchone()["id"]
        k2 = conn.execute(
            "select id, campus_id, academic_year_id from school_class where grade_code = 'K2'"
        ).fetchone()
        g3 = conn.execute(
            "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
            " values (%s,%s,%s,'G3','A') returning id",
            (t, k2["campus_id"], k2["academic_year_id"]),
        ).fetchone()["id"]
        who = {
            e: conn.execute("select staff_id from pii.staff where email = %s", (e,)).fetchone()["staff_id"]
            for e in ("bea@example.test", "cy@example.test")
        }
        bea, cy = who["bea@example.test"], who["cy@example.test"]

        def refused(*args):
            with pytest.raises(psycopg.errors.RaiseException, match="core_teacher"), conn.transaction():
                conn.execute(grant, args)

        # pre-primary (K2): Ann is the class's class teacher and may teach a core subject there
        ann = conn.execute("select staff_id from pii.staff where email = 'ann@example.test'").fetchone()[
            "staff_id"
        ]
        conn.execute(grant, (t, ann, "subject_educator", k2["id"], "NUM", None))
        # Grade 3: a teacher of a core subject made class teacher is refused; so is the other way round
        conn.execute(grant, (t, cy, "subject_educator", g3, "NUM", None))
        refused(t, cy, "class_teacher", g3, None, None)
        conn.execute(
            grant, (t, bea, "class_teacher", g3, None, "Bea takes G3 as well")
        )  # a reason: it stands
        refused(t, bea, "subject_educator", g3, "ENG", None)
        # with a reason it stands, and the reason is kept on the grant
        conn.execute(grant, (t, cy, "class_teacher", g3, None, "no one else is free in G3"))
        kept = conn.execute(
            "select staff_id, override_reason from staff_role_grant where role_code = 'class_teacher' and school_class_id = %s",
            (g3,),
        ).fetchall()
        assert {(k["staff_id"], k["override_reason"]) for k in kept} == {
            (bea, "Bea takes G3 as well"),
            (cy, "no one else is free in G3"),
        }
        conn.rollback()


@needs_db
def test_a_grant_is_never_deleted_it_ends(tmp_path, school):
    assert run("staff", "import", "--apply", "--by", "tester").exit_code == 0
    with db.connect() as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="never deleted"):
            conn.execute("delete from staff_role_grant")
        conn.rollback()
        conn.execute("update staff_role_grant set valid_to = valid_from where role_code = 'coordinator'")
        assert (
            conn.execute("select count(*) n from staff_role_grant where valid_to is not null").fetchone()["n"]
            == 1
        )
        conn.rollback()


@needs_db
def test_the_staff_id_of_a_signed_in_email_is_found_in_any_case_and_never_a_name(tmp_path, school):
    assert run("staff", "import", "--apply", "--by", "tester").exit_code == 0
    with db.connect() as conn:
        want = conn.execute("select staff_id from pii.staff where email = 'ann@example.test'").fetchone()[
            "staff_id"
        ]

        def of(email):
            return conn.execute("select public.staff_of_email(%s) as id", (email,)).fetchone()["id"]

        before = conn.execute(
            "select count(*) n from access_log where action = 'lookup_staff_by_email'"
        ).fetchone()["n"]
        assert of("ann@example.test") == want
        assert of("  Ann@Example.TEST ") == want
        assert of("nobody@example.test") is None
        assert (
            conn.execute(
                "select count(*) n from access_log where action = 'lookup_staff_by_email'"
            ).fetchone()["n"]
            == before + 2
        )
        row = conn.execute("select public.staff_of_email('ann@example.test') as r").fetchone()
        assert set(row) == {"r"} and "Placeholder" not in str(row)  # an id, not a name
        conn.rollback()
    # reachable by the engine and by nothing else: neither app role has USAGE on schema `internal`, which is why it is in `public`
    assert rows("select has_function_privilege('app_engine', 'public.staff_of_email(text)', 'execute') p")[0][
        "p"
    ]
    assert not rows("select has_function_privilege('app_web', 'public.staff_of_email(text)', 'execute') p")[
        0
    ]["p"]


@needs_db
def test_a_grant_is_never_edited_only_ended(tmp_path, school):
    assert load_everything(tmp_path, "--teacher", "ann@example.test").exit_code == 0
    with db.connect() as conn:
        grant = conn.execute("select id from staff_role_grant where role_code = 'class_teacher'").fetchone()[
            "id"
        ]
        k2 = conn.execute("select tenant_id, campus_id, academic_year_id from school_class").fetchone()
        other = conn.execute(
            "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
            " values (%s,%s,%s,'G3','A') returning id",
            (k2["tenant_id"], k2["campus_id"], k2["academic_year_id"]),
        ).fetchone()["id"]

        def refused(sql, *args):
            with (
                pytest.raises(psycopg.errors.RaiseException, match="grant_is_not_edited"),
                conn.transaction(),
            ):
                conn.execute(sql, args)

        refused("update staff_role_grant set role_code = 'assistant' where id = %s", grant)
        refused("update staff_role_grant set override_reason = 'no one will ask' where id = %s", grant)
        refused("update staff_role_grant set school_class_id = %s where id = %s", other, grant)
        refused("update staff_role_grant set valid_from = '2020-01-01' where id = %s", grant)
        # it can end, only once earlier than it was, and never be reopened or lengthened
        conn.execute("update staff_role_grant set valid_to = '2027-03-31' where id = %s", (grant,))
        conn.execute("update staff_role_grant set valid_to = '2027-02-01' where id = %s", (grant,))
        refused("update staff_role_grant set valid_to = '2027-03-31' where id = %s", grant)
        refused("update staff_role_grant set valid_to = null where id = %s", grant)
        conn.rollback()


@needs_db
def test_each_service_can_call_what_it_may_and_neither_can_delete_history(tmp_path, school):
    assert load_everything(tmp_path, "--teacher", "ann@example.test").exit_code == 0
    with db.connect() as conn:
        sid = conn.execute("select staff_id from pii.staff where email = 'ann@example.test'").fetchone()[
            "staff_id"
        ]
        enrol = conn.execute("select id from enrolment limit 1").fetchone()["id"]
        # as the engine: the lookup and the logged read both work
        conn.execute("set local role app_engine")
        assert conn.execute("select public.staff_of_email('ann@example.test') as id").fetchone()["id"] == sid
        assert (
            conn.execute("select name from pii.read_staff(%s, 'tester')", (sid,)).fetchone()["name"]
            == "Placeholder Ann"
        )
        for table in (
            "enrolment",
            "staff_role_grant",
            "school_class",
            "staff",
            "campus",
            "academic_year",
            "role",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute(f"delete from {table}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("select name from pii.staff")
        # an enrolment ends; it is not removed
        conn.execute("update enrolment set to_date = from_date where id = %s", (enrol,))
        conn.rollback()
        # as the website: it reads the school's structure, and calls neither lookup
        conn.execute("set local role app_web")
        assert conn.execute("select count(*) n from enrolment").fetchone()["n"] == 22
        for call in (
            "select public.staff_of_email('ann@example.test')",
            f"select * from pii.read_staff('{sid}', 'web')",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute(call)
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("update enrolment set to_date = from_date")
        conn.rollback()


@needs_db
def test_d039_fails_closed_when_the_rules_grade_is_not_a_grade(tmp_path, school):
    assert load_everything(tmp_path).exit_code == 0
    grant = (
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by,"
        " override_reason) values (%s,%s,'class_teacher',%s,'2026-12-01','t',%s)"
    )
    with db.connect() as conn:
        t = conn.execute("select id from tenant").fetchone()["id"]
        k2 = conn.execute("select id from school_class").fetchone()["id"]
        bea = conn.execute("select staff_id from pii.staff where email = 'bea@example.test'").fetchone()[
            "staff_id"
        ]
        conn.execute(
            "update config set value = jsonb_set(value, '{from_grade}', '\"NO-SUCH-GRADE\"')"
            " where key = 'people.class_teacher_rule'"
        )
        # the rule cannot say who it applies to, so it does not quietly let everyone through
        with (
            pytest.raises(psycopg.errors.RaiseException, match="core_teacher: the rule starts from"),
            conn.transaction(),
        ):
            conn.execute(grant, (t, bea, k2, None))
        conn.execute(
            grant, (t, bea, k2, "the rule is being corrected")
        )  # with a reason it stands, and the reason is kept
        kept = conn.execute(
            "select override_reason from staff_role_grant where staff_id = %s and role_code = 'class_teacher'",
            (bea,),
        ).fetchone()
        assert kept["override_reason"] == "the rule is being corrected"
        conn.rollback()
