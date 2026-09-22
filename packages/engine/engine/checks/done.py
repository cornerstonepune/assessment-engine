"""The done-report: written by the machine, not by whoever did the work (goals/promises-kept.yaml).

`engine done <goal>` prints the goal's sentence; each of Nimish's own words in it with the test that
proves it, run now on the copy of the database and marked passed or failed; what is still manual; and
what is not live yet — the branch not on main, migrations not on the live database. It exits 1 unless
every one of his sentences is proved and nothing is left out of live, so "done" is a command's answer,
not a summary.
"""

import os
import subprocess

from engine.checks import goal as goals
from engine.core import db

ENGINE = db.REPO_ROOT / "packages" / "engine"
WEB = db.REPO_ROOT / "apps" / "web"


def _copy_env():
    """The copy of the database for every test this runs: tests never touch the live one."""
    env = goals.env()
    copy = os.environ.get("TEST_DATABASE_URL")
    return {**env, "DATABASE_URL": copy} if copy else env


def run_proof(proved_by, timeout=900):
    """→ (passed, last line of output) for one `path::name` test."""
    path, name = (x.strip() for x in proved_by.split("::", 1))
    if path.endswith(".py"):
        rel = str((db.REPO_ROOT / path).relative_to(ENGINE))
        cmd, cwd = (
            [
                str(ENGINE / ".venv" / "bin" / "python"),
                "-m",
                "pytest",
                f"{rel}::{name}",
                "-q",
                "-o",
                "addopts=",
            ],
            ENGINE,
        )
    else:
        rel = str((db.REPO_ROOT / path).relative_to(WEB))
        cmd, cwd = ["npx", "playwright", "test", rel, "-g", name], WEB
    try:
        p = subprocess.run(cmd, cwd=cwd, env=_copy_env(), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    lines = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
    ran = any(" passed" in ln or " failed" in ln for ln in lines)
    return p.returncode == 0 and ran, (lines[-1] if lines else "no output")


def not_live(conn=None):
    """What this checkout holds that the live system does not: the branch not merged to main, and
    migrations the live database has not had."""
    out = []
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=db.REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    on_main = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", head, "origin/main"], cwd=db.REPO_ROOT
        ).returncode
        == 0
    )
    if not on_main:
        out.append("this work is not on main yet, so the live website and engine do not have it")
    files = sorted(p.stem.split("_", 1)[0] for p in (db.REPO_ROOT / "supabase" / "migrations").glob("*.sql"))
    try:
        with conn or db.connect() as c:
            applied = {
                r["version"]
                for r in c.execute("select version from supabase_migrations.schema_migrations").fetchall()
            }
    except Exception as e:  # noqa: BLE001 — a report says what it could not check, it does not crash
        return [*out, f"could not read the live database's migrations: {type(e).__name__}"]
    missing = [v for v in files if v not in applied]
    if missing:
        out.append(f"{len(missing)} migration(s) not on the live database: {', '.join(missing)}")
    return out


def report(name, run=run_proof, live=not_live):
    """→ (lines for a person, every sentence proved and nothing left out of live)."""
    spec = goals.load(name)
    lines = [
        f"GOAL  {spec['goal'].strip()}",
        "",
        "Your words, and the test that proves each (run now, on the copy):",
    ]
    ok = True
    says = spec.get("says") or []
    if not says:
        lines.append("  (this goal names none of your words — it cannot be reported done)")
        ok = False
    for s in says:
        passed, last = run(s["proved_by"])
        ok &= passed
        lines.append(f'  {"PROVED" if passed else "NOT PROVED"}  "{s["words"]}"')
        lines.append(f"            {s['proved_by']}  — {last}")
    lines += ["", "Still manual:"]
    lines += [f"  - {m}" for m in spec.get("manual") or []] or ["  nothing"]
    gaps = live()
    lines += ["", "Not live yet:"] + ([f"  - {g}" for g in gaps] or ["  nothing: all of it is live"])
    ok &= not gaps
    lines += ["", "DONE" if ok else "NOT DONE"]
    return lines, ok
