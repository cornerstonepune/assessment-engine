"""The Guide cannot drift from the site it explains (goals/guide_for_educators.yaml).

Nimish, 27 Oct 2026: "a guide page where everything is well explained ... so that people don't come to me ... how
something is defined or calculated ... so that it's a transparent system." The guide's words are files
(apps/web/guide/*.json). These tests read them with no database, beside the menu, the map (workflows.json), the
website's routes and its source:

- every menu item has a guide page, and every guide page a menu item;
- every step of the map is in the guide, with who does it;
- every route the guide links to exists, and every button it quotes is a label in the website's code;
- no number is typed into the guide's text: a number is a token naming a threshold row, filled from the row in force,
  so when the school changes 80% to 75% the guide changes itself; levels, grades and a child's states are tokens too;
- the text keeps the school's words and short sentences.
"""

import json
import re

import pytest

from engine.core import db

WEB = db.REPO_ROOT / "apps" / "web"
GUIDE = WEB / "guide"
APP = WEB / "app"
SEED = db.REPO_ROOT / "supabase" / "seed"
MAP = json.loads((db.REPO_ROOT / "workflows.json").read_text())
THRESHOLDS = {r["key"]: r["value"] for r in json.loads((SEED / "thresholds.json").read_text())["thresholds"]}
VOCAB = json.loads((SEED / "vocabulary.json").read_text())
SUBJECTS = json.loads((SEED / "subjects.json").read_text())["subjects"]

WHO = {"educator", "coordinator", "the engine"}
TOKEN = re.compile(r"\{([^}]+)\}")
BUTTON = re.compile(r"\[\[([^\]]+)\]\]")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# A label with a part the page fills in ("Approve, as …"): each fixed part must be in the code.
FILLED = "…"
# Words a reader at the school would not know, or the school does not use (CLAUDE.md, Language and naming).
JARGON = re.compile(
    r"\b(ring|rings|evidence_event|evidence event|RLS|migration|migrations|rung|rungs|taxonomy|borrow|borrowing|"
    r"teacher|teachers|LLM|OCR|API|Jev|prompt|seed|schema|ADR|SQL|JSON|database|threshold|thresholds|query|"
    r"delve|leverage|seamless|robust|elevate|unlock|empower|streamline|holistic)\b",
    re.I,
)
NUMBER_WORDS = {
    2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    12: "twelve", 15: "fifteen", 20: "twenty", 21: "twenty-one", 30: "thirty", 48: "forty-eight", 50: "fifty",
}  # fmt: skip
LONGEST_SENTENCE = 30


def menu_pages():
    """(href, label) of every page of the menu, in its order: lib/menu.ts, read as the site reads it."""
    src = (WEB / "lib" / "menu.ts").read_text()
    return re.findall(r'\{ href: "([^"]+)", label: "([^"]+)"', src)


def slug(label):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z]+", "-", label.lower()))


def guide_pages():
    return {p.stem: json.loads(p.read_text()) for p in sorted((GUIDE / "pages").glob("*.json"))}


def articles():
    return {
        p.stem: json.loads(p.read_text())
        for p in sorted(GUIDE.glob("*.json"))
        if p.stem not in {"start", "steps"}
    }


def every_file():
    return {p.relative_to(GUIDE).as_posix(): json.loads(p.read_text()) for p in sorted(GUIDE.rglob("*.json"))}


TEXT_KEYS = {
    "name",
    "title",
    "purpose",
    "forWhat",
    "area",
    "shows",
    "steps",
    "does",
    "doesNot",
    "note",
    "paras",
    "sees",
    "label",
}


def texts(node, key=None):
    """Every sentence of the guide a reader sees: the values under the text keys, never an address or an id."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from texts(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from texts(v, key)
    elif isinstance(node, str) and key in TEXT_KEYS:
        yield node


def all_texts():
    return [(name, t) for name, data in every_file().items() for t in texts(data)]


def prose(text):
    """What a reader reads as the guide's own words: tokens, quoted buttons and link targets taken out."""
    text = TOKEN.sub(" ", text)
    text = BUTTON.sub(" ", text)
    return LINK.sub(lambda m: m.group(1), text)


def routes():
    """The website's routes, each as a pattern: a [segment] matches any one segment."""
    out = []
    for p in APP.rglob("*"):
        if p.name not in ("page.tsx", "route.ts"):
            continue
        parts = [x for x in p.parent.relative_to(APP).parts if not (x.startswith("(") and x.endswith(")"))]
        out.append("^/" + "/".join("[^/]+" if x.startswith("[") else re.escape(x) for x in parts) + "$")
    return out


def anchors():
    """The guide's own addresses and the sections on each: what an "I want to" button or a link may land on."""
    out = {"/guide": {"want", "flow", "menu"}, "/guide/workflows": {s["code"] for s in MAP["steps"]}}
    for href, label in menu_pages():
        page = next((p for p in guide_pages().values() if p["menu"] == href), None)
        ids = {"for", "layout", "buttons"} | {j["id"] for j in page["jobs"]} if page else set()
        out[f"/guide/{slug(label)}"] = ids
    for name, a in articles().items():
        out[f"/guide/{name}"] = {s["id"] for s in a["sections"]}
    return out


def link_problem(href, the_routes, the_anchors):
    path, _, anchor = href.partition("#")
    path = path.split("?")[0]
    if path.startswith("/guide"):
        if path not in the_anchors:
            return f"{href}: no guide page has that address"
        if anchor and anchor not in the_anchors[path]:
            return f"{href}: that guide page has no section {anchor!r}"
        return None
    if not any(re.match(r, path) for r in the_routes):
        return f"{href}: the website has no such page"
    return None


def app_source():
    """The website's code, the guide's own aside: where a button the guide quotes must be written."""
    files = [
        *(WEB / "app").rglob("*.tsx"),
        *(WEB / "components").rglob("*.tsx"),
        *(WEB / "lib").rglob("*.ts"),
    ]
    text = "\n".join(f.read_text() for f in files if f.name != "guide.ts" and "guide" not in f.parts)
    return quotes(text)


def quotes(text):
    """One apostrophe: a page writes it as &rsquo; or &apos; in its markup, and the guide as a plain one."""
    return text.replace("&rsquo;", "'").replace("&apos;", "'").replace("\u2019", "'")


def button_problem(label, source):
    parts = [p.strip() for p in quotes(label).split(FILLED) if p.strip()]
    missing = [p for p in parts if p not in source]
    return f"{label!r}: no page of the website says {missing[0]!r}" if missing or not parts else None


def token_problem(raw):
    kind, _, rest = raw.partition(":")
    arg = rest.split("|")[0]
    if kind == "t":
        return None if arg in THRESHOLDS else f"{{{raw}}}: no threshold row is called {arg!r}"
    if kind == "levels" or kind == "grades":
        return None
    if kind == "level":
        ok = re.fullmatch(r"-?\d+", arg) and -len(VOCAB["difficulties"]) <= int(arg) < len(
            VOCAB["difficulties"]
        )
        return None if ok else f"{{{raw}}}: there is no such level"
    if kind == "state":
        return (
            None
            if arg in {s["code"] for s in VOCAB["child_states"]}
            else f"{{{raw}}}: no child state is {arg!r}"
        )
    if kind == "colour":
        return (
            None if arg in {c["code"] for c in VOCAB["state_colours"]} else f"{{{raw}}}: no colour is {arg!r}"
        )
    return f"{{{raw}}}: not a kind of token"


def typed_numbers(text):
    """A number written by hand: any digit, or a threshold row's value in words ("eight children"), or a share."""
    words = prose(text)
    found = re.findall(r"\d+", words)
    values = {int(v) for v in THRESHOLDS.values() if float(v).is_integer()}
    found += [w for n, w in NUMBER_WORDS.items() if n in values and re.search(rf"\b{w}\b", words, re.I)]
    found += re.findall(r"\b(?:percent|per cent|half)\b", words, re.I)
    return found


def typed_vocabulary(text):
    """A level, a grade, a state, a colour's words or a subject written by hand instead of read from its row."""
    words = prose(text)
    found = [lvl["code"] for lvl in VOCAB["difficulties"] if re.search(rf"\b{lvl['code']}\b", words)]
    found += [
        g["name"]
        for g in VOCAB["grades"]
        if not g["name"][-1].isdigit() and re.search(rf"\b{g['name']}\b", words)
    ]
    said = {s["words"] for s in VOCAB["child_states"]} | {
        c[k] for c in VOCAB["state_colours"] for k in ("words", "count_words")
    }
    found += [w for w in sorted(said) if re.search(rf"\b{re.escape(w)}\b", words, re.I)]
    found += [s["label"] for s in SUBJECTS if re.search(rf"\b{s['label']}\b", words, re.I)]
    return found + re.findall(r"\b(?:Maths|Mathematics)\b", words, re.I)


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", prose(text)) if s.strip()]


# --- the menu and the map ---------------------------------------------------------------------------------------------


def test_every_menu_item_has_a_guide_page():
    """One guide page per menu item, named after it, and no guide page for a menu item that is gone."""
    pages = guide_pages()
    hrefs = [h for h, _ in menu_pages()]
    assert hrefs, "the menu could not be read from lib/menu.ts"
    for href, label in menu_pages():
        assert slug(label) in pages, (
            f"the menu's {label!r} has no guide page apps/web/guide/pages/{slug(label)}.json"
        )
        assert pages[slug(label)]["menu"] == href, (
            f"{slug(label)}.json says it is for {pages[slug(label)]['menu']}"
        )
    stale = sorted(set(pages) - {slug(label) for _, label in menu_pages()})
    assert not stale, f"guide pages for menu items that do not exist: {stale}"


@pytest.mark.parametrize("name", sorted(p.stem for p in (GUIDE / "pages").glob("*.json")))
def test_every_guide_page_says_what_to_see_where_and_the_usual_jobs(name):
    page = guide_pages()[name]
    assert page["forWhat"], f"{name}: says nothing of what the page is for"
    assert len(page["layout"]) >= 3, (
        f"{name}: the drawing of the page needs at least its top, its middle and its end"
    )
    assert all(a["area"] and a["shows"] for a in page["layout"]), (
        f"{name}: an area of the drawing says nothing"
    )
    assert page["jobs"] and all(j["steps"] for j in page["jobs"]), (
        f"{name}: no usual job, or a job with no steps"
    )
    assert page["buttons"], f"{name}: says what no button does"
    ids = [j["id"] for j in page["jobs"]]
    assert len(ids) == len(set(ids)), f"{name}: two jobs share an address"


def test_every_step_of_the_map_is_in_the_guide():
    """The twelve steps of workflows.json, each with who does it and what they see; none the map does not have."""
    steps = json.loads((GUIDE / "steps.json").read_text())
    codes = [s["code"] for s in MAP["steps"]]
    assert sorted(steps) == sorted(codes), (
        f"the guide's steps {sorted(steps)} are not the map's {sorted(codes)}"
    )
    for code, s in steps.items():
        assert s["who"] and set(s["who"]) <= WHO, f"{code}: who does it must be among {sorted(WHO)}"
        assert s["sees"] and s["name"], (
            f"{code}: has no name in the school's words, or says nothing of what they see"
        )


def test_every_i_want_to_lands_on_a_section_that_exists():
    start = json.loads((GUIDE / "start.json").read_text())
    the_anchors = anchors()
    assert len(start["wants"]) >= 8, "Start here offers fewer than the eight jobs asked for"
    for w in start["wants"]:
        assert "#" in w["href"] or w["href"] in the_anchors, f"{w['label']!r} lands on no section"
        assert link_problem(w["href"], routes(), the_anchors) is None, link_problem(
            w["href"], routes(), the_anchors
        )


# --- routes and buttons -----------------------------------------------------------------------------------------------


def test_every_route_the_guide_names_exists():
    the_routes, the_anchors = routes(), anchors()
    links = [m.group(2) for _, t in all_texts() for m in LINK.finditer(t)]
    assert links, "the guide links to nothing"
    bad = [p for p in (link_problem(h, the_routes, the_anchors) for h in links) if p]
    assert not bad, "\n".join(bad)


def test_every_button_the_guide_quotes_exists_in_the_app():
    source = app_source()
    quoted = [m.group(1) for _, t in all_texts() for m in BUTTON.finditer(t)]
    quoted += [b["label"] for p in guide_pages().values() for b in p["buttons"]]
    assert quoted, "the guide quotes no button"
    bad = [p for p in (button_problem(b, source) for b in quoted) if p]
    assert not bad, "\n".join(dict.fromkeys(bad))


# --- numbers and the school's vocabulary ------------------------------------------------------------------------------


def test_no_number_is_typed_into_the_guide():
    bad = [f"{name}: {found} in {t[:80]!r}" for name, t in all_texts() if (found := typed_numbers(t))]
    assert not bad, (
        "a number is written by hand; name its row instead, as {t:key} or {t:key|pct}:\n" + "\n".join(bad)
    )


def test_every_number_in_the_guide_is_a_threshold_row():
    used = [m.group(1) for _, t in all_texts() for m in TOKEN.finditer(t)]
    assert any(u.startswith("t:") for u in used), "the guide reads no threshold row"
    bad = [p for p in (token_problem(u) for u in used) if p]
    assert not bad, "\n".join(dict.fromkeys(bad))
    for need in (
        "calibration.too_easy_share",
        "calibration.min_children",
        "state.min_events",
        "next_sheet.promote_at",
    ):
        assert any(u.startswith(f"t:{need}") for u in used), f"How it is worked out does not say {need}"


def test_no_level_grade_or_state_is_typed_into_the_guide():
    bad = [f"{name}: {found} in {t[:80]!r}" for name, t in all_texts() if (found := typed_vocabulary(t))]
    assert not bad, "a level, grade, state or subject is written by hand; use its token:\n" + "\n".join(bad)


def test_the_guide_uses_the_schools_words_and_short_sentences():
    bad = []
    for name, t in all_texts():
        if m := JARGON.search(prose(t)):
            bad.append(f"{name}: {m.group()!r} in {t[:80]!r}")
        if "—" in prose(t):
            bad.append(f"{name}: an em dash in {t[:80]!r}")
        bad += [
            f"{name}: a sentence of {len(s.split())} words: {s[:80]!r}"
            for s in sentences(t)
            if len(s.split()) > LONGEST_SENTENCE
        ]
    assert not bad, "\n".join(bad)


def test_the_scans_see_what_they_should():
    """The checks are not blind: each catches what it is for, and passes what it should."""
    assert typed_numbers("A level is reviewed at 80% of children.") == ["80"]
    assert typed_numbers("at least eight children") == ["eight"]
    assert typed_numbers("under half right") == ["half"]
    assert not typed_numbers(
        "at least {t:calibration.min_children} children, {t:calibration.too_easy_share|pct}"
    )
    assert typed_vocabulary("set at Advance") == ["Advance"]
    assert "secure" in typed_vocabulary("the child is secure")
    assert not typed_vocabulary("the child is {state:secure} at {level:-1}; press [[Needs help]]")
    assert (
        JARGON.search("a new migration")
        and JARGON.search("the teacher")
        and not JARGON.search("the educator")
    )
    assert (
        token_problem("t:no.such.row")
        and token_problem("state:nope")
        and not token_problem("t:state.min_events")
    )
    assert link_problem("/no/such/page", routes(), anchors()) and not link_problem(
        "/growth/abc", routes(), anchors()
    )
    assert button_problem("A button nobody wrote", app_source())
    assert not button_problem("Make an assessment", app_source())
