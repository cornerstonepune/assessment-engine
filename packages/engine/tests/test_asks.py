"""What the engine drafts for a person to answer, and who decides what (goals/ny1-needs-you.yaml): each question a row,
`supabase/seed/asks.json`, that its person agrees with or corrects on the site in their own name (`engine/core/asks.py`),
and each kind of thing waiting on a person said to be someone's (`people.decides`)."""

import json
import os
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
TAXONOMY = ROOT / "docs" / "design" / "multiplication-division-taxonomy.md"
# the kinds of thing Today shows waiting on a person, each a card of its own (apps/web/app/(app)/today/page.tsx)
WAITING = {"answers", "papers", "home_papers", "class_papers", "skills", "topics"}
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def _asks():
    return json.loads((SEED / "asks.json").read_text())["asks"]


def _config(key):
    return next(c for c in json.loads((SEED / "config.json").read_text())["config"] if c["key"] == key)


def _roles():
    """The staff list's own roles, as its row names them."""
    words = re.search(r"Roles: ([a-z, ]+)\.", _config("app.staff")["description"])
    assert words, "the staff list names its roles"
    return {r.strip() for r in words[1].split(",")}


def _to_achal():
    """{goal: [what it drafts for Achal]}: every goal's line to do by hand that is addressed to him."""
    out = {}
    for p in sorted((ROOT / "goals").glob("*.yaml")):
        for line in yaml.safe_load(p.read_text()).get("manual") or []:
            if re.match(r"^[^:]*\bAchal\b[^:]*:", line):
                out.setdefault(f"goals/{p.name}", []).append(line.split(":", 1)[1].strip())
    return out


def test_every_question_drafted_for_achal_is_a_row():
    """Nimish, 2026-10-10: "for Achal to validate". Everything drafted for Achal is a question on the site: the taxonomy
    the engine drafted, each of its twelve assumptions as the document's own table states it, and every decision a goal
    drafted for him (its line to do by hand addressed to him), each word for word. None is only in a goal file or a pull
    request, and every question is for a role the staff list has."""
    asks, roles = _asks(), _roles()
    assert len({a["code"] for a in asks}) == len(asks), "one row per question"
    assert all(a["for_role"] in roles and a["question"] and a["drafted"] and a["source"] for a in asks)
    by_code = {a["code"]: a for a in asks}
    assert by_code["MD.TAXONOMY"]["source"] == str(TAXONOMY.relative_to(ROOT))
    table = re.findall(r"^\| (A\d+) \| (.+?) \| (.+?) \| (.+?) \|$", TAXONOMY.read_text(), re.M)
    assert [a for a, *_ in table] == [f"A{i}" for i in range(1, 13)]
    for code, assumed, means, why in table:
        ask = by_code[f"MD.{code}"]
        assert (ask["question"], ask["drafted"], ask["why"]) == (f"{code}: {assumed}", means, why), code
        assert ask["for_role"] == "specialist"
    drafted = _to_achal()
    assert len(drafted) >= 8, "the slices that drafted a decision for Achal"
    for source, lines in drafted.items():
        held = sorted(a["drafted"] for a in asks if a["source"] == source)
        assert held == sorted(lines), source


def test_every_kind_of_waiting_names_who_decides_it():
    """Nimish, 2026-10-10: "I'm not even now able to figure out what all papers I need to validate or for Achal to
    validate". Each kind of thing that waits on a person is someone's: a row says whose, by the staff list's roles, so
    a school moves a decision to another person by changing a row."""
    row = _config("people.decides")
    assert not row.get("seed_once"), "a deploy carries a change to who decides what"
    assert set(row["value"]) == WAITING
    assert all(row["value"][k] and set(row["value"][k]) <= _roles() for k in WAITING), row["value"]


@needs_db
def test_an_answered_question_is_never_changed_by_a_reload():
    """A question the engine rewords is asked again in its new words until someone answers it; once answered, it keeps
    the words it was answered on and the answer, whatever a reload of the rows says."""
    from engine.core import asks, db, settings

    rows = settings.seed("asks.json", "asks")
    reworded = [dict(a, question=a["question"] + " (reworded)") for a in rows]
    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        asks.load(conn, tenant, settings.seed)
        conn.execute(
            "update ask set answer = 'corrected', correction = 'Grade 3 teaches it too', answered_by = 'Achal',"
            " answered_at = now() where code = 'MD.A2'"
        )
        asks.load(conn, tenant, lambda name, key: reworded)
        got = {
            r["code"]: r
            for r in conn.execute(
                "select code, question, answer, correction, answered_by from ask where code in ('MD.A2', 'MD.A3')"
            ).fetchall()
        }
        conn.rollback()
    first = {a["code"]: a for a in rows}
    assert got["MD.A2"]["question"] == first["MD.A2"]["question"]
    assert (got["MD.A2"]["answer"], got["MD.A2"]["correction"], got["MD.A2"]["answered_by"]) == (
        "corrected",
        "Grade 3 teaches it too",
        "Achal",
    )
    assert got["MD.A3"]["question"] == first["MD.A3"]["question"] + " (reworded)"
    assert got["MD.A3"]["answer"] is None


@needs_db
def test_engine_asks_prints_every_answer():
    """What a person answered reaches whoever builds next: `engine asks` prints each question with its answer, who gave
    it and when, a correction in full; `--open` the ones still waiting."""
    from engine.core import asks, db, settings

    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        asks.load(conn, tenant, settings.seed)
        conn.execute(
            "update ask set answer = 'agreed', answered_by = 'Achal', answered_at = now() where code = 'MD.A1'"
        )
        conn.execute(
            "update ask set answer = 'corrected', correction = 'Long division only from Grade 4',"
            " answered_by = 'Achal', answered_at = now() where code = 'MD.A2'"
        )
        every, still = asks.report(conn), asks.report(conn, waiting=True)
        conn.rollback()
    text = "\n".join(every)
    assert re.search(r"MD\.A1\b.*agreed.*Achal", text)
    assert re.search(r"MD\.A2\b.*corrected.*Achal", text) and "Long division only from Grade 4" in text
    assert not any(re.search(r"MD\.A[12]\b", line) for line in still)
    assert any(re.search(r"MD\.A3\b", line) for line in still)
