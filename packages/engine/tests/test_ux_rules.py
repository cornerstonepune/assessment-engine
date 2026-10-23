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
SOURCE_RULES = {"shell", "purpose", "table", "taglist", "filter", "status"}
WEB = db.REPO_ROOT / "apps" / "web"


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
    # a list of tags where a table belongs: filter or choice chips drawn by hand (a FilterBar draws its own)
    if re.search(r'className=\{?[`"]chip\b', src):
        out.add("taglist")
    # a long list with no filter row: a table with no FilterBar over it
    if ("<DataTable" in src or "<table" in src) and "<FilterBar" not in src:
        out.add("filter")
    # a status drawn by hand, in a colour with no icon: a StatusChip draws its icon with its word
    if re.search(r"<(Mark)?Pill\b", src):
        out.add("status")
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


def test_a_status_chip_always_draws_its_icon_with_its_word():
    """Never colour alone: the one chip has no way to draw a state without an icon."""
    chip = (WEB / "components/status-chip.tsx").read_text()
    assert "<Icon" in chip and "STATUS_ICONS" in chip, "StatusChip must draw an icon for every tone"
    tones = set(re.findall(r'tone: "(\w+)"', chip))
    assert tones <= {"ok", "wait", "act", "quiet"}, f"states map to green, amber, red or quiet only: {tones}"


def test_the_top_bar_controls_are_full_size_and_the_search_is_compact():
    """Class and Subject: at least 40 px tall, 15 px text. The student search: about 240 px, never a strip."""
    rules = (WEB / "lib/ux-rules.ts").read_text()
    least = int(re.search(r"TOP_BAR_MIN_PX = (\d+)", rules)[1])
    text = int(re.search(r"TOP_BAR_TEXT_PX = (\d+)", rules)[1])
    search = int(re.search(r"SEARCH_PX = (\d+)", rules)[1])
    assert least >= 40 and text >= 15 and 200 <= search <= 280
    bar = (WEB / "components/top-bar.tsx").read_text()
    assert f"min-h-[{least}px]" in bar and f"text-[{text}px]" in bar, (
        "the selectors must be sized from the rules"
    )
    # a bare flex-1 stretches the field across the bar; one behind a breakpoint (the phone) is not the desktop's strip
    bare_flex = re.search(r"(?<![\w:-])flex-1", bar.split("function Search")[1])
    assert f"w-[{search}px]" in bar and not bare_flex, "the search is a field, not a strip"
    assert "max-w-[88px]" not in bar and "max-w-[118px]" not in bar, "the selectors may not be squeezed"


def test_a_filter_bar_has_every_part_the_pages_rely_on():
    bar = (WEB / "components/filter-bar.tsx").read_text()
    for part in ('role="search"', "data-filterbar", "data-active-filters", "Clear", 'type="search"'):
        assert part in bar, f"FilterBar lacks {part}"
