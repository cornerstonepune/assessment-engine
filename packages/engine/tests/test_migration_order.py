"""A migration a change adds sorts after the newest one main holds, so migrate live can apply it.

Live records every migration main has applied. `supabase db push`, which migrate live runs, refuses a local
migration older than the newest one live recorded ("Found local migration files to be inserted before the last
migration on remote database", supabase/cli `findPendingMigrations`) unless given `--include-all`, so such a
migration turns migrate live red after the merge and holds the website's deploy. The rehearsal applies migrations
with psql, in any order, and cannot see it. 2026-10-21: B2's 20261125090000 was written before main took
20261126090000 and would have done exactly that.

Reads `origin/main` from git. CI's checkout fetches the whole history (`fetch-depth: 0`), so it is there; on a
machine that never fetched it the test skips, and in CI it fails instead, so it can never pass by skipping.
"""

import os
import subprocess

import pytest

from engine.core import db

MIGRATIONS = "supabase/migrations"


def out_of_order(on_main: list[str], here: list[str]) -> list[str]:
    """The migration files here that main lacks and that sort at or before main's newest."""
    newest = max(on_main)[:14]
    return sorted(f for f in set(here) - set(on_main) if f[:14] <= newest)


def shared_versions(names: list[str]) -> dict[str, list[str]]:
    """{version: the files that carry it} for every version more than one migration has."""
    by_version: dict[str, list[str]] = {}
    for n in sorted(names):
        by_version.setdefault(n.split("_", 1)[0], []).append(n)
    return {v: files for v, files in by_version.items() if len(files) > 1}


def test_the_check_names_two_migrations_that_share_a_version():
    """Several branches took the same version number and the live update stopped: `supabase db push` records a migration
    by its version alone, so the second of two files with one version is never applied (or fails the insert)."""
    a, b = "20261217090000_one.sql", "20261217090000_another.sql"
    assert shared_versions([a, b, "20261218090000_c.sql"]) == {"20261217090000": [b, a]}
    assert shared_versions([a, "20261218090000_c.sql"]) == {}


def test_no_two_migrations_share_a_version():
    here = [p.name for p in (db.REPO_ROOT / MIGRATIONS).glob("*.sql")]
    assert here, "no migrations found: the folder moved"
    shared = shared_versions(here)
    assert not shared, "\n".join(
        f"version {v} is on {len(files)} migrations ({', '.join(files)}): give each a version of its own, after main's newest"
        for v, files in shared.items()
    )


def _on_main() -> list[str] | None:
    run = subprocess.run(
        ["git", "ls-tree", "--name-only", "origin/main", f"{MIGRATIONS}/"],
        cwd=db.REPO_ROOT,
        capture_output=True,
        text=True,
    )
    names = [p.rsplit("/", 1)[-1] for p in run.stdout.split() if p.endswith(".sql")]
    return names if run.returncode == 0 and names else None


def test_the_check_names_a_migration_older_than_mains_newest():
    main = [
        "20261124090000_the_site_reads_a_skills_levels_from_their_rows.sql",
        "20261126090000_a_check_is_an_answer_a_person_was_shown.sql",
    ]
    old, new = "20261125090000_question_types_are_rows.sql", "20261126100000_question_types_are_rows.sql"
    assert out_of_order(main, [*main, old]) == [old]
    assert out_of_order(main, [*main, new]) == []


def test_every_migration_this_change_adds_sorts_after_mains_newest():
    on_main = _on_main()
    if on_main is None:
        if os.environ.get("CI"):
            pytest.fail(
                "origin/main is not fetched, so the migrations' order is unchecked: fetch it in ci.yml"
            )
        pytest.skip("origin/main is not fetched here: git fetch origin main")
    here = [p.name for p in (db.REPO_ROOT / MIGRATIONS).glob("*.sql")]
    late = out_of_order(on_main, here)
    newest = max(on_main)[:14]
    assert not late, "\n".join(
        f"{MIGRATIONS}/{f} sorts before main's newest migration {newest}, which live has already applied; "
        f"`supabase db push` would refuse it and migrate live would fail. Rename it to a version after {newest}, "
        f"e.g. {int(newest) + 10000}_{f[15:]}"
        for f in late
    )
