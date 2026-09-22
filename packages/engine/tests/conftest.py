"""Every test runs against the local copy of the database, never the live one (ADR 0025).

This runs before any test module is imported, so before anything can connect. Importing `engine.core.db`
reads the repo's `.env`; `DATABASE_URL` is then pointed at the copy `bin/testdb` builds on this Mac,
and the run stops outright if that copy is anywhere else. Subprocesses a test starts (`bin/engine
…`) inherit the same address.
"""

import os

import pytest

from engine.core import db

if os.environ.get("TEST_DATABASE_URL"):
    try:
        os.environ["DATABASE_URL"] = db.local_copy()
    except RuntimeError as refused:
        pytest.exit(str(refused), returncode=4)
elif os.environ.get("DATABASE_URL"):
    # This machine can reach a real database but names no copy: stop, rather than test on it.
    pytest.exit(
        "refusing to run tests: DATABASE_URL is set but TEST_DATABASE_URL is not — run bin/testdb "
        "and add TEST_DATABASE_URL to .env",
        returncode=4,
    )


@pytest.fixture
def every_kind_trusted(monkeypatch):
    """ADR 0032's gate out of the way: every kind of question as if the reader had earned 95% on it, so
    a test about marking or signing off measures that and not the reader's standing on the copy."""
    from engine.w3_read import profiles

    monkeypatch.setattr(
        profiles,
        "kind_trust",
        lambda conn, window=50: {f: {"n": 50, "right": 50, "trusted": True} for f in profiles.KIND_WORDS},
    )


def _old_row(expr, rung="R9", fmt="legacy_bare"):
    """An old paper's question as the database holds it: `"425 - 38"` → its row (ADR 0034's shape)."""
    a, op, b = expr.split()
    skill = {"+": "NUM.OPS.01", "-": "NUM.OPS.02"}[op]
    spec = {"a": int(a), "b": int(b), "op": op, "expr": expr, "kind": "bare", "skill": skill}
    return {"fmt": fmt, "stem": f"{expr} =", "spec": spec, "rung_code": rung, "skill_codes": [skill]}


def _old_paper(conn, answers):
    """One child, one old paper, one answer per (expr, status, mistakes); the questions placed as `engine legacy
    paper` places them and every answer confirmed. Returns the child."""
    import json

    from engine.w3_read import place

    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    batch = conn.execute("select substr(md5(random()::text), 1, 6) as b").fetchone()["b"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,'TESTPLACE','G3') returning id",
        (tenant, batch),
    ).fetchone()["id"]
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, week) values (%s,'G3','2026-W38') returning id",
        (tenant,),
    ).fetchone()["id"]
    inst = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id)"
        " values (%s, 'CSP' || %s, %s, %s) returning id",
        (tenant, batch, tpl, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, sheet_instance_id) values (%s,'test/place.pdf',%s) returning id",
        (tenant, inst),
    ).fetchone()["id"]
    for n, (expr, status, codes) in enumerate(answers):
        r = _old_row(expr)
        item = conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem, spec,"
            " responses, source) values (%s,%s,'legacy',%s,%s,'Procedural',%s,%s,%s,'[]','legacy') returning id",
            (tenant, f"legacy/TEST-{batch}/{n}", r["rung_code"], r["skill_codes"], r["fmt"], r["stem"],
             json.dumps(r["spec"])),
        ).fetchone()["id"]  # fmt: skip
        conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, status, misconception_codes)"
            " values (%s,%s,%s,'a',%s,%s)",
            (tenant, cap, item, status, codes),
        )
    place.place(conn)
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    return child


@pytest.fixture
def old_row():
    return _old_row


@pytest.fixture
def old_paper():
    return _old_paper


@pytest.fixture
def conn():
    """The copy of the database, rolled back after the test. Skips where there is none (CI)."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()
