"""One roll order, in the database (goals/p0-one-answer-counts-once.yaml).

A class is listed by the number in its rolls: "2" before "10", "12A" after "12", a roll with no number last. The rule
was written out twelve times; three website copies wrote '\\D' inside a JS template, which reaches Postgres as 'D', so a
roll such as "12A" broke the class page's `::int`, and `card.py` sorted "10" before "2" (code review, 2026-09-30).
"""

import re

import pytest

from engine.core import db

CODE = [*(db.REPO_ROOT / "packages" / "engine" / "engine").rglob("*.py")]
WEB = db.REPO_ROOT / "apps" / "web"
CODE += [p for d in ("lib", "app") for p in (WEB / d).rglob("*.ts*")] if WEB.exists() else []


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_a_class_is_listed_by_the_number_in_its_rolls(conn):
    rolls = ["10", "2", "12A", "12", "A", "1", " 3", "", "007"]
    got = conn.execute(
        "select array_agg(r order by roll_order(r), r) as rolls from unnest(%s::text[]) as r", (rolls,)
    ).fetchone()["rolls"]
    assert got == ["1", "2", " 3", "007", "10", "12", "12A", "", "A"]


def test_no_query_orders_rolls_its_own_way():
    own = [
        f"{p.relative_to(db.REPO_ROOT)}:{n}"
        for p in CODE
        for n, line in enumerate(p.read_text().splitlines(), 1)
        if re.search(r"order by[^\"`]*roll_no", line, re.I)
        and "roll_order(" not in line
        or re.search(r"regexp_replace\(\s*(?:\w+\.)?roll_no", line)
    ]
    assert own == []
