"""The skill links' scenario: a database as it is, a person's list of pairs, and what the views show before and after
(`engine goal m1-15-skill-links`). On a copy of live the database is live's own links; the second input is the list.

The run counts the links that are there, loads the list as proposals, counts again, has one placeholder member of staff
confirm one, and counts a third time. What it asserts holds on any database, so it holds on live's copy whatever live
holds: the rows that were there are the rows that are there; a proposal is read by nobody; a confirmation is read by
everybody and only that one. The caller rolls everything back; the staff member is a placeholder on a reserved domain.
"""

import os
from pathlib import Path

from engine.core import db
from engine.w3_read import skill_links

PLACEHOLDER = "scenario.checker@school.invalid"


def _counts(conn):
    """Every figure the scenario compares, from the views and the audit view only: the rows by status, and what a
    reader sees."""
    return dict(
        conn.execute(
            "select (select count(*) from skill_prerequisite_audit)::int as steps,"
            " (select count(*) from skill_prerequisite_audit where confirmed_by is not null)::int as steps_confirmed,"
            " (select count(*) from skill_prerequisite_confirmed)::int as steps_read,"
            " (select count(*) from skill_link_confirmed)::int as links_read"
        ).fetchone()
    )


def _staff(conn, school):
    campus = db.one(conn, "select id from campus where tenant_id = %s limit 1", (school,))["id"]
    sid = db.one(
        conn, "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (school, campus)
    )["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'A placeholder', %s)",
        (school, sid, PLACEHOLDER),
    )


def measure(conn, sc):
    path = os.environ.get("SKILL_LINK_PAIRS") or str(db.REPO_ROOT / sc["pairs"])
    school = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    before = _counts(conn)
    wanted = skill_links.pairs(Path(path))
    first = skill_links.load(conn, Path(path))
    after = _counts(conn)
    again = skill_links.load(conn, Path(path))
    _staff(conn, school)
    one = None  # the first pair of the list nobody has confirmed yet; none left is a failure to report, not a crash
    for pair in wanted:
        row = conn.execute(
            "select id from skill_link_audit where skill_code = %s and before_code = %s and confirmed_by is null",
            (pair["after_code"], pair["before_code"]),
        ).fetchone()
        if row:
            one = row["id"]
            break
    word = skill_links.confirm(conn, str(one), PLACEHOLDER) if one else "every pair was confirmed already"
    confirmed = _counts(conn)
    return {
        "every_pair_in_the_list_is_a_link": first.added + first.there == len(wanted),
        "a_second_load_adds": again.added,
        "loading_leaves_the_micro_steps_as_they_were": before
        == {**after, "links_read": before["links_read"]},
        "micro_steps_read_after_loading": after["steps_read"],
        "loading_changes_what_a_reader_sees": after["links_read"] != before["links_read"],
        "word_on_confirming": word,
        "one_confirmation_adds_one_link_a_reader_sees": confirmed["links_read"] == before["links_read"] + 1,
        "confirming_a_link_confirms_no_micro_step": confirmed["steps_confirmed"] == before["steps_confirmed"],
    }


def run(conn, sc):
    """(measurements, failures): every expectation the scenario names, compared with what the database showed."""
    try:
        got = measure(conn, sc)
    finally:
        conn.rollback()  # a scenario proves the rule, it never leaves a link behind
    failures = [
        f"{key}: expected {want!r}, got {got[key]!r}"
        for key, want in sc["expect"].items()
        if got[key] != want
    ]
    return got, failures
