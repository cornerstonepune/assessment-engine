"""The spine page can be read without getting lost (goals/spine-readable.yaml).

Nimish, 2026-09-28: "is there a way that you can design this html better such that its more easily understood and the
connections are untuitive - i am getting lost in the artifact". research/spine_page.py puts every item on the same
five steps (why, what NCF-SE asks, in the grade, when, how we check) and shows its thread through them;
research/spine_thread.py works the threads out and research/plan_build.py the fortnights. These tests hold that data to
what the page promises: every item it shows opens a thread on the five steps, every link says where it comes from,
every unit and outcome of Grades 1-7 reaches a capability (or says why it cannot) and its fortnights, the fortnights
keep the syllabus's order and pace, and the page's own words are the school's. They read the tracked docs/spine/
files, so no PDF and no database is needed.
"""

import html.parser
import importlib
import json
import re
import sys

import pytest

from engine.core import db

RESEARCH = db.REPO_ROOT / "research"
SPINE = db.REPO_ROOT / "docs" / "spine"


def research(name):
    if str(RESEARCH) not in sys.path:
        sys.path.insert(0, str(RESEARCH))
    return importlib.import_module(name)


plan_build, spine_links, spine_page, spine_thread = (
    research(m) for m in ("plan_build", "spine_links", "spine_page", "spine_thread")
)


@pytest.fixture(scope="module")
def page():
    return spine_page.page_data()


@pytest.fixture(scope="module")
def plan():
    return json.loads((SPINE / "plan.json").read_text())


def ids_in(group):
    return [*([group["head"]] if group.get("head") else []), *group.get("ids", [])]


def thread_of(page, item, grade=None):
    """The thread the page opens when an item is clicked, in a grade's context when it has one."""
    return page["threads"].get(spine_thread.key(item, grade)) or page["threads"][page["open"][item]]


def test_every_item_on_the_page_opens_a_thread_on_the_same_five_steps(page):
    """Wherever an item shows up, in a thread or in a grade's year, clicking it opens its own thread; every thread is
    laid out on the same five steps in the same order, with the item on its own step."""
    items, threads = page["items"], page["threads"]
    assert len(threads) > 2000, f"only {len(threads)} threads were built"
    for key, t in threads.items():
        assert tuple(t["steps"]) == spine_thread.STEPS, key
        home = t["steps"][spine_thread.HOME[items[t["id"]]["layer"]]]
        assert any(t["id"] in ids_in(g) for g in home), f"{key}: the item is not on its own step"
    shown = {i for t in threads.values() for groups in t["steps"].values() for g in groups for i in ids_in(g)}
    year = page["plan"]["year"]
    shown |= {x for slots in year.values() for cells in slots.values() for cell in cells for x, _ in cell}
    dead = sorted(i for i in shown if i not in page["open"] and items[i]["layer"] != "grade")
    assert not dead, f"{len(dead)} items on the page would open nothing, such as {dead[:5]}"
    assert all(k in threads for k in page["open"].values())
    assert page["start"] in threads


def test_every_link_in_a_thread_says_where_it_comes_from(page):
    """Each group of links carries its source (NCF-SE or NCERT, the school's own map, a proposal nobody has signed, or
    an inference from a shared competency), and where the spine records a link, the thread says what the spine says."""
    items, threads = page["items"], page["threads"]
    for key, t in threads.items():
        for step, groups in t["steps"].items():
            for g in groups:
                if ids_in(g) or g.get("f"):
                    assert g.get("k") in spine_links.KINDS, f"{key} · {step}: {g.get('t')!r} gives no source"
                else:
                    assert g.get("note"), f"{key} · {step}: an empty group with nothing to say"

    spine = json.loads((SPINE / "spine.json").read_text())
    feeds, goal_of = {}, {}
    for e in spine["edges"]:
        if e["kind"] == "feeds":
            feeds.setdefault(e["from"], set()).add(e["to"])
        if e["kind"] == "has_competency":
            goal_of[e["to"]] = e["from"]

    def groups_of(t, step, layer):
        return [g for g in t["steps"][step] if any(items[i]["layer"] == layer for i in ids_in(g))]

    for layer in ("competency", "outcome", "unit", "behaviour"):
        for key, t in ((k, t) for k, t in threads.items() if items[t["id"]]["layer"] == layer):
            caps = groups_of(t, "why", "capability")
            if layer == "competency":
                assert {i for g in caps for i in g["ids"]} == feeds.get(t["id"], set()), key
                assert [g["k"] for g in t["steps"]["asks"] if g.get("head") == goal_of[t["id"]]] == [
                    "official"
                ], key
            if layer == "unit":
                assert all(g["k"] == "school" for g in groups_of(t, "check", "skill")), key
                assert all(g["k"] == "inferred" for g in groups_of(t, "grade", "outcome")), key
            assert all(g["k"] == "proposed" for g in caps if t["id"] not in g["ids"]), key


BUILD_WORDS = re.compile(
    r"\b(nodes?|layers?|edges?|seats?|crosswalks?|acads|twau|generated|teachers?|borrow\w*)\b", re.I
)


class Visible(html.parser.HTMLParser):
    """The words a reader sees in the template: text outside scripts and styles, and the labels of controls."""

    def __init__(self):
        super().__init__()
        self.words, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        self.hidden += tag in ("script", "style")
        self.words += [v for k, v in attrs if k in ("placeholder", "aria-label", "title") and v]

    def handle_endtag(self, tag):
        self.hidden -= tag in ("script", "style")

    def handle_data(self, data):
        if not self.hidden:
            self.words.append(data)


def js_strings(src):
    """The strings in a script, with the code inside template literals taken out."""
    src = re.sub(r"(^|\s)//[^\n]*", r"\1", src)
    while re.search(r"\$\{[^{}]*\}", src):
        src = re.sub(r"\$\{[^{}]*\}", " ", src)
    return re.findall(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", src)


def test_the_page_speaks_the_schools_words_not_the_builds(page):
    """What the reader sees is in the school's words: no nodes, layers, edges or seats, no bare R1 for a language (R1 is
    a rung on the engine's ladder), educator not teacher, exchange not borrow. The data's own text (NCF-SE's and
    NCERT's sentences, the school's map) is quoted as it is and not held to this."""
    parser = Visible()
    parser.feed(spine_page.TEMPLATE.read_text())
    seen = parser.words + [s for f in spine_page.SCRIPTS for s in js_strings(f.read_text())]
    design = page["plan"]["design"]
    names = list(design["slot_names"].values())
    seen += names + [s["label"] for s in design["scenarios"]] + [design["anatomy_note"]]
    seen += [v for m in design["modes"].values() for v in (m["label"], m["what"], m["group"])]
    found = sorted({m.group(0) for s in seen for m in BUILD_WORDS.finditer(s)})
    assert not found, f"the page says {found}; say it in the school's words"
    assert not [n for n in names if re.search(r"\bR\d\b", n)], names


def test_every_unit_and_outcome_of_grades_1_to_7_reaches_a_capability_and_a_fortnight(page):
    """Every unit of the school's map (Grades 1-4) and every NCERT outcome standing in (Grades 5-7) that the year
    places has a thread that climbs to a capability, or says why it cannot, and names the fortnights it is taught in."""
    items, lost, n = page["items"], [], 0
    for grade, slots in page["plan"]["year"].items():
        for slot, cells in slots.items():
            placed = {}
            for f, cell in enumerate(cells, 1):
                for x, _ in cell:
                    placed.setdefault(x, []).append(f)
            for x, fortnights in placed.items():
                n += 1
                t = thread_of(page, x, int(grade))
                caps = [
                    i
                    for g in t["steps"]["why"]
                    for i in g.get("ids", [])
                    if items[i]["layer"] == "capability"
                ]
                reason = items[x].get("why")
                if not caps and not (reason and any(g.get("note") == reason for g in t["steps"]["why"])):
                    lost.append(f"Grade {grade} {slot}: {x} reaches no capability and does not say why")
                when = [g for g in t["steps"]["when"] if g.get("g") == int(grade) and g.get("slot") == slot]
                if sorted({f for g in when for f in g["f"]}) != fortnights:
                    lost.append(
                        f"Grade {grade} {slot}: {x} is in fortnights {fortnights}; its thread says {when}"
                    )
    assert n > 700, f"only {n} units and outcomes placed"
    assert not lost, f"{len(lost)} of {n}: " + "; ".join(lost[:5])


def test_each_grades_syllabus_is_paced_across_its_fortnights_in_order(plan):
    """Each grade's syllabus, subject by subject, is cut into the year's fortnights in its own order, nothing dropped
    or repeated, and each fortnight carries its share of the teaching days to within one item."""
    base = plan["scenarios"][0]["calendar"]
    days, per = base["days"], plan["design"]["calendar"]["fortnight_days"]
    assert sum(days) == base["teach"] and len(days) == -(-base["teach"] // per)
    assert sorted(plan["year"]) == [str(g) for g in range(1, 8)]
    for grade, slots in plan["year"].items():
        assert sorted(slots) == sorted(plan["grades"][grade]["slots"]), grade
        for slot, cells in slots.items():
            want = plan_build.flat(plan["grades"][grade]["slots"][slot])
            assert len(cells) == len(days), (grade, slot)
            assert [x for cell in cells for x, k in cell for _ in range(k)] == want, (grade, slot)
            for d, cell in zip(days, cells, strict=True):
                assert abs(sum(k for _, k in cell) - len(want) * d / sum(days)) < 1, (grade, slot, cell)


def test_the_tracked_plan_is_what_its_inputs_build(plan):
    """docs/spine/plan.json is what research/plan_build.py makes of today's design, map and NCERT rows, so the page
    never shows a plan its inputs no longer give. The official numbers are the ones already checked on their page."""
    design = json.loads((SPINE / "plan_design.json").read_text())
    assert json.loads(json.dumps(plan_build.build(design, plan["official"]))) == plan


def test_the_day_adds_up(plan):
    """Each band's week fills the instruction time of five days, and its day by mode fills the whole day."""
    design = plan["design"]
    day = design["day"]["instruction"] + design["day"]["community"]
    for name, band in design["bands"].items():
        assert sum(m for _, _, m in band["week"]) == 5 * design["day"]["instruction"], name
        assert abs(sum(plan["composition"][name].values()) - day) < 1e-9, name


def test_the_page_builds_from_the_tracked_files():
    html_text = spine_page.render()
    assert not re.search(r"__[A-Z]+__", html_text)
    assert len(html_text.encode()) < 16 * 2**20
    data = re.search(r'<script id="page-data" type="application/json">(.*?)</script>', html_text, re.S)
    assert json.loads(data.group(1).replace("<\\/", "</"))["threads"]
