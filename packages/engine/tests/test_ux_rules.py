"""The educator's site is held to its rules (docs/ux-rules.md, goals/uxf-ux-foundation.yaml).

A page either keeps the rules by being built on the shared blocks (`PageShell`, `DataTable`), or is named in
`workflows.json` under `ux.frozen`, with the rules it still breaks. The list only shrinks: a page that keeps a rule
must leave it (so it cannot grow back unseen), a page not on it must keep every rule, and CI's ratchet refuses a
commit that adds to it (`engine ratchet`). The rendered rules (a table past the row limit, an empty column, a count
that differs from the menu's, a line past the limit) are held by apps/web/tests/u51-ux-rules.spec.ts for every page
off the list; what a listed page shows depends on the rows in the database, so it is measured there, not frozen.
"""

import json
import re

from engine.core import db

APP = db.REPO_ROOT / "apps" / "web" / "app"
UX = json.loads((db.REPO_ROOT / "workflows.json").read_text())["ux"]
PURPOSE_MAX = int(
    re.search(r"PURPOSE_MAX = (\d+)", (db.REPO_ROOT / "apps/web/lib/ux-rules.ts").read_text())[1]
)
SOURCE_RULES = {"shell", "purpose", "table"}


def route(page):
    parts = [p for p in page.parent.relative_to(APP).parts if not (p.startswith("(") and p.endswith(")"))]
    return "/" + "/".join(parts)


def pages():
    """{route: the page's own source}: its page.tsx and the components beside it (not the routes below it)."""
    return {
        route(p): "\n".join(f.read_text() for f in sorted(p.parent.glob("*.tsx")) if f.name != "loading.tsx")
        for p in sorted(APP.rglob("page.tsx"))
        if p.relative_to(APP).parts[0] != "login"
    }


def broken(src):
    out = set()
    if "<PageShell" not in src:
        out.add("shell")
    if any(len(m) > PURPOSE_MAX for m in re.findall(r'\b(?:sub|purpose)="([^"]*)"', src)):
        out.add("purpose")
    if "<table" in src:
        out.add("table")
    return out


def test_every_page_has_a_main_action_and_a_next_step_or_is_on_the_list():
    """`PageShell` takes `action` and `next` as required props, so a page built on it has both."""
    bad = [r for r, s in pages().items() if "shell" in broken(s) and "shell" not in UX["frozen"].get(r, [])]
    assert not bad, (
        f"build these on PageShell (a main action, a next-step link), or name them in ux.frozen: {bad}"
    )


def test_no_purpose_line_runs_past_the_limit_or_the_page_is_on_the_list():
    bad = [
        r for r, s in pages().items() if "purpose" in broken(s) and "purpose" not in UX["frozen"].get(r, [])
    ]
    assert not bad, f"the line under the title of {bad} is over {PURPOSE_MAX} characters: shorten it"


def test_no_hand_built_table_or_the_page_is_on_the_list():
    """A table is a `DataTable`: it holds the row limit, hides a column of zeros or dashes and is a list on a phone."""
    bad = [r for r, s in pages().items() if "table" in broken(s) and "table" not in UX["frozen"].get(r, [])]
    assert not bad, f"use DataTable on {bad}, or name them in ux.frozen"


def test_the_list_only_shrinks():
    seen = pages()
    for r, rules in UX["frozen"].items():
        assert r in seen, f"{r} is on ux.frozen but is not a page: take it off"
        assert set(rules) <= SOURCE_RULES, f"{r} names a rule that does not exist: {rules}"
        still = broken(seen[r])
        assert set(rules) == still, (
            f"{r} lists {sorted(rules)} but breaks {sorted(still)}: write down what it breaks now"
        )
        if "<PageShell" in seen[r]:
            raise AssertionError(f"{r} is built on PageShell: take it off ux.frozen")
