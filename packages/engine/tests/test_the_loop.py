"""M5a: every new skill through the whole loop (goals/md5a-the-loop.yaml).

For each multiplication and division skill set at each level: its topic switched on, as an educator does on the site; a
library worksheet of it printed for a child; its boxes filled with known answers, one named mistake planted wherever its
questions can show it and the key everywhere else; the copy read and marked; what the reader held, confirmed by a person
as the child wrote it; the paper signed off. Then, stage by stage, the planted mistake must come back: named on every
answer it was planted on, counted as evidence on the skill set's rung, repeating in the child's graph, the subject of the
child's next paper, and said by its own name on the class card and in the parent report's facts. Then round again
(M5b): that next paper printed for the child, the mistake made on it again, read back by its code, named and counted.

The handwriting reader is stood in (as `test_every_answer.py` does): what it reads is the answer written. Reading
handwriting is scored on its own (`engine eval`); this is about everything after it. The planted answers are each
question's own stored wrong answer for the mistake (`responses[].misconceptions`), so a stage that loses or renames the
mistake fails here, whatever made it.
"""

import json
import uuid
from collections import Counter

import pytest

from engine.adapters import ocr
from engine.assess import focus, graph
from engine.core import db, mistake_names
from engine.w2_print import focus_paper, handout
from engine.w3_read import boxes, copies, marking, second_reader
from engine.w4_close import card, parent_facts
from engine.w4_close.report import _hint
from tests.test_each_answer import _wrote
from tests.test_sorting import _scanned as _scanned_file

SEED = db.REPO_ROOT / "supabase" / "seed"
LEVELS = ("Easy", "Medium", "Hard", "Advance")
NEW = sorted(
    s["code"]
    for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
    if s["code"].split(".")[0] in ("MUL", "DIV", "MD")
)
PERSON = "End-to-end loop"
WEEK = "2026-W42"


@pytest.fixture
def conn():
    import os

    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def _sheet(conn, code, level):
    return conn.execute(
        "select t.code, t.band, t.item_ids, s.rung_code, s.topic_code, s.level_band ->> t.difficulty as grade"
        " from sheet_template t join skill s"
        " on s.code = t.skill_set_code where t.source = 'library' and t.retired_at is null"
        " and t.skill_set_code = %s and t.difficulty = %s"
        " order by t.code limit 1",
        (code, level),
    ).fetchone()


def _slots(conn, ids):
    """[(item_id, rid, key, {mistake: its wrong answer})] of every answer box on the sheet, in the order printed."""
    rows = {r["id"]: r for r in conn.execute("select id, responses from item where id = any(%s)", (ids,))}
    return [
        (i, x["rid"], str(x["answer"]), {m: str(v) for m, v in (x.get("misconceptions") or {}).items()})
        for i in ids
        for x in rows[i]["responses"]
    ]


def _planted(slots):
    """The mistake the sheet can show on the most answers — a number, or a tick, the key is not — and the slots it
    goes on. Every mistake that ties for most is a fair choice; the first by name is taken, so a run is repeatable."""
    can = Counter(m for _, _, key, wrong in slots for m, v in wrong.items() if v and v != key)
    if not can:
        return None, []
    most = max(can.values())
    m = min(c for c, n in can.items() if n == most)
    return m, [(i, rid) for i, rid, key, wrong in slots if wrong.get(m, key) != key]


def _in_the_window(rows, window):
    """How many planted answers a skill's window holds. `rows` = [(the question's place on the paper, planted)], in the
    paper's order; the window is the paper's last questions of the skill, whole, while they fit: one that ends inside a
    question is not counted on, since which of its boxes are kept is the graph's chance order."""
    kept = []
    for place in sorted({p for p, _ in rows}, reverse=True):
        asked = [planted for p, planted in rows if p == place]
        if len(kept) + len(asked) > window:
            break
        kept += asked
    return sum(kept)


def _skills_of(item, planted):
    """The skills an answer is evidence for — the rules of confirm_results(): a right answer, every skill the question
    was made for; a planted wrong one, the skill that mistake belongs to."""
    if planted is not None:
        return [(item["mistake_skills"] or {}).get(planted) or item["own"]]
    return item["skill_codes"] if item["source"] == "generated" and item["skill_codes"] else [item["own"]]


def _bank_shows_again(conn, after, ids, mistake, skill):
    """Whether the child's next paper can put `mistake` in front of them again. `after` = (skill set, level, grade) of
    the paper just done. The next paper is worked at the level `focus_paper._where_it_shows` chooses for that mistake
    (asked of the code itself, not copied here), and takes there, before any question the child was just given, those
    they were not; of those it puts first the ones made for the skill the mistake is counted on (`_draw`). So: the bank
    holds a question at that level, not one of `ids`, made for `skill`, that can show `mistake`."""
    code, level, grade = after
    area = focus_paper._where_it_shows(
        conn, focus.Area(code, skill, level, 0, 0, mistake, "repeating"), focus_paper._levels(conn, grade)
    )
    return conn.execute(
        "select exists (select 1 from drawable_item i, jsonb_array_elements(i.responses) r"
        " where i.skill_set_code = %s and i.difficulty = %s and not (i.id = any(%s)) and %s = any(i.skill_codes)"
        " and jsonb_typeof(r -> 'misconceptions') = 'object' and (r -> 'misconceptions') ? %s) as yes",
        (code, area.level, ids, skill, mistake),
    ).fetchone()["yes"]


def _planted_to_repeat(conn, ids, slots, after=None):
    """`_planted`, but of the mistakes the paper can show, the one the graph can SEE repeating (M0-04).

    The graph reads only a skill's latest `state.window_answers` answers at a level, and a mistake repeats there only
    on `state.repeat_min` of them. A paper that puts more answers on one skill than the window holds pushes the early
    answers out of it, so a mistake planted on those is real evidence yet not "repeating". How many answers a skill gets
    on its paper depends on which questions a build of the bank happened to draw, so choosing the mistake by raw count
    failed on some builds ("graph []", 2026-11-03) and passed on the next. This takes the mistake with most answers
    inside one skill's window, among those the parent report can say what to do about. → (mistake, the slots it goes on),
    or (None, []) when none shows `repeat_min` times.

    M0-04b (CI, 2026-11-03: "no next question can show M_LAST_DIGIT_RULE_MISAPPLIED"): the loop's last stages print the
    child's next paper, which `focus_paper._draw` fills with questions the child has not just been given before it
    takes any they have. The paper just signed off gave the child every question of its own that shows the mistake, so
    a mistake whose only questions in the bank are on that paper cannot be shown again. A build draws its bank at
    random: one holds four questions that show a mistake at a level, another none (measured on four fresh builds,
    docs/notes/m0-04b-loop-test-bank.md). So, given `after` = (skill set, level, grade), a mistake is a fair choice only
    if the bank holds a question outside `ids` that shows it, for the skill it is counted on (`_bank_shows_again`)."""
    value = {
        r["key"]: int(r["value"])
        for r in conn.execute(
            "select key, value from threshold where key in ('state.window_answers', 'state.repeat_min')"
        )
    }
    window, repeat_min = value.get("state.window_answers", 10), value.get("state.repeat_min", 2)
    items = {
        r["id"]: r
        for r in conn.execute(
            "select id, source, skill_codes, mistake_skills, spec ->> 'op' as op,"
            " coalesce(spec ->> 'skill', skill_codes[1]) as own"
            " from item where id = any(%s)",
            (ids,),
        )
    }
    hint_of = mistake_names.names(conn, "repair_hint")
    best = (0, None)
    for m in sorted({m for _, _, key, wrong in slots for m, v in wrong.items() if v and v != key}):
        on = {(i, rid) for i, rid, key, wrong in slots if wrong.get(m, key) != key}
        if not all(  # the parent report must be able to say what the school does about it, as report.py looks it up
            _hint(hint_of, m, items[i]["op"], _skills_of(items[i], m)[0]) for i in {i for i, _ in on}
        ):
            continue  # the vocabulary holds no such hint for that operation yet: the school's wording, not the test's
        by_skill: dict[str, list[tuple[int, bool]]] = {}
        for i, rid, _key, _wrong in slots:
            for u in _skills_of(items[i], m if (i, rid) in on else None):
                by_skill.setdefault(u, []).append((ids.index(i), (i, rid) in on))
        seen, on_skill = max((_in_the_window(rows, window), u) for u, rows in by_skill.items())
        if after and not _bank_shows_again(conn, after, ids, m, on_skill):
            continue  # the paper shows it, but the bank holds no other question to show it again on the next paper
        if seen > best[0]:
            best = (seen, m)
    if best[0] < repeat_min:
        return None, []
    return best[1], [(i, rid) for i, rid, key, wrong in slots if wrong.get(best[1], key) != key]


def _a_child(conn, section, band):
    """A child of the grade the level is for: a child's next paper is drawn from the levels of their own grade."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '7', %s, %s) returning id",
        (tenant, band, section),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Mira')", (tenant, child)
    )
    return child


def _read(conn, pdf, ids, wrote, scan_at, monkeypatch):
    """A copy printed for its child (`pdf`, the child's own code on it), scanned and read by that code; the reader
    stood in to read what `wrote` says each box holds. A tick or a reason comes back for a person, as the box reader
    returns them. → what the reading says of the copy."""
    monkeypatch.setattr(copies, "CUT", scan_at.parent / "scans")
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(second_reader, "propose", lambda conn, r, *a, **k: (r, ""))
    by_key = {
        r["item_key"]: r["id"]
        for r in conn.execute("select id, item_key from item where id = any(%s)", (ids,))
    }

    def read_page(img, page_no, pdf, geometry, wanted, cfg, frame=None, keep=None, for_a_person=()):
        out = {}
        for slot, (item_key, rid) in wanted.items():
            if slot in for_a_person:
                out[slot] = {"child_answer": "", "answer_state": "for_a_person", "why": boxes.FOR_A_PERSON,
                             "box": [0.1, 0.1, 0.2, 0.1], "confidence": 0.0, "working_shown": "none"}  # fmt: skip
            else:
                out[slot] = {**_wrote(wrote[(by_key[item_key], rid)]), "confidence": 99.0}
        return out

    monkeypatch.setattr(boxes, "read_page", read_page)
    (got,) = copies.read(conn, _scanned_file([pdf], scan_at), "", [], PERSON)
    return got


def _results(conn, child, qr):
    return conn.execute(
        "select r.id, r.item_id, r.rid, r.status, r.misconception_codes from item_result r"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.qr_code = %s and si.child_id = %s and c.superseded_by is null",
        (qr, child),
    ).fetchall()


def _round(conn, child, qr, pdf, ids, mistake, scan_at, monkeypatch, what):
    """One turn of the loop on one printed copy: `mistake` planted wherever its questions can show it, the key
    everywhere else; read by its code onto that copy; each held answer confirmed by a person as the child wrote it;
    each planted answer named, and the key marked right; then signed off. → how many answers were planted."""
    slots = _slots(conn, ids)
    on = [(i, rid) for i, rid, key, wrong in slots if wrong.get(mistake, key) != key]
    wrote = {(i, rid): (wrong[mistake] if (i, rid) in on else key) for i, rid, key, wrong in slots}
    got = _read(conn, pdf, ids, wrote, scan_at, monkeypatch)
    assert got["child_id"] == child and got["by_code"] and not got.get("skipped"), f"{what}: read as {got}"
    for r in _results(conn, child, qr):  # a person confirms each held answer as the child wrote it
        if r["status"] != "needs_teacher":
            continue
        if (
            wrote[(r["item_id"], r["rid"])] == "None"
        ):  # a reason, which only a person marks: Right, on the site
            conn.execute("select resolve_result(%s, 'correct', '{}'::text[], %s)", (r["id"], PERSON))
        else:
            marking.correct(conn, r["id"], wrote[(r["item_id"], r["rid"])], PERSON)
    marked = {(r["item_id"], r["rid"]): r for r in _results(conn, child, qr)}
    assert set(marked) == set(wrote), f"{what}: every answer box is read once"
    missed = [k for k in on if mistake not in (marked[k]["misconception_codes"] or [])]
    assert not missed, f"{what}: {len(missed)} of {len(on)} planted answers not named {mistake}"
    wrong_key = [
        (k, wrote[k], marked[k]["status"]) for k in set(wrote) - set(on) if marked[k]["status"] != "correct"
    ]
    assert not wrong_key, f"{what}: the key marked wrong {wrong_key}"
    marking.confirm(conn, child, PERSON)
    return len(on)


def _counted(conn, child, mistake, rung=None):
    return conn.execute(
        "select count(*) as n from evidence_event where child_id = %s and %s = any(misconception_codes)"
        " and (%s::text is null or rung_code = %s)",
        (child, mistake, rung, rung),
    ).fetchone()["n"]


@pytest.mark.parametrize("code,level", [(c, lv) for c in NEW for lv in LEVELS])
def test_a_mistake_planted_on_a_new_skills_paper_comes_back_through_every_stage(
    conn, tmp_path, monkeypatch, every_kind_trusted, code, level
):
    _round_the_loop(conn, tmp_path, monkeypatch, code, level)


@pytest.mark.parametrize("code,level", [(c, lv) for c in NEW for lv in LEVELS])
def test_the_bank_holds_a_mistake_the_loop_can_plant_and_show_again(conn, code, level):
    """M0-04b: the loop needs, at every level of a new skill set, a mistake that at least two questions can show: one
    for a paper, one left for the child's next. A fresh bank is drawn at random (`w1_bank/refill.py`), so this is read
    from the bank each time, not assumed; when it fails, the bank is short, and the test above must not be blamed."""
    if level not in [
        lv
        for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
        if s["code"] == code
        for lv in s["difficulty"]
    ]:
        pytest.skip(f"{code} has no {level} level")
    shown = conn.execute(
        "select m.k as mistake, count(*) as questions from drawable_item i,"
        " lateral (select distinct jsonb_object_keys(r -> 'misconceptions') as k from jsonb_array_elements(i.responses) r"
        "   where jsonb_typeof(r -> 'misconceptions') = 'object') m"
        " where i.skill_set_code = %s and i.difficulty = %s group by m.k order by 2 desc, 1",
        (code, level),
    ).fetchall()
    assert any(r["questions"] >= 2 for r in shown), (
        f"BANK DEFECT {code} {level}: no mistake is shown by two questions of the level: {shown}"
    )


@pytest.mark.parametrize("code,level", [("MD.MULTIPLES", "Easy"), ("MD.EQUALITY", "Easy")])
def test_a_mistake_the_bank_cannot_show_again_is_not_the_one_planted(conn, code, level):
    """M0-04b, the CI failure of 2026-11-03 ("no next question can show M_LAST_DIGIT_RULE_MISAPPLIED") made certain on
    any build, which needs a build whose bank happens to be short: the mistake the paper alone would plant is taken out
    of every other question of the skill set, at any level, as in a build that drew none of them. The bank keeps its
    size (retiring the questions instead would shrink the level until the next paper had to repeat the paper's own).
    Then the choice must pass over it, because the child's next paper could not show it; choosing from the paper alone
    fails the whole loop at its next-paper stage with that message (measured in docs/notes/m0-04b-loop-test-bank.md)."""
    sheet = _sheet(conn, code, level)
    slots = _slots(conn, sheet["item_ids"])
    after = (code, level, sheet["grade"] or sheet["band"])
    on_paper, _ = _planted_to_repeat(conn, sheet["item_ids"], slots)
    assert on_paper, f"{code} {level}: the paper shows no mistake twice, so there is nothing to take out"
    taken = conn.execute(
        "update item set responses = (select jsonb_agg(case when jsonb_typeof(r -> 'misconceptions') = 'object'"
        "   then jsonb_set(r, '{misconceptions}', (r -> 'misconceptions') - %s) else r end)"
        "   from jsonb_array_elements(responses) r)"
        " where skill_set_code = %s and not (id = any(%s))"
        " and exists (select 1 from jsonb_array_elements(responses) r where jsonb_typeof(r -> 'misconceptions') = 'object'"
        "   and (r -> 'misconceptions') ? %s)",
        (on_paper, code, sheet["item_ids"], on_paper),
    ).rowcount
    assert taken, f"{code} {level}: no other question showed {on_paper}, so the bank was already short"
    still = conn.execute(
        "select count(*) as n from drawable_item i where i.skill_set_code = %s and not (i.id = any(%s))"
        " and exists (select 1 from jsonb_array_elements(i.responses) r where jsonb_typeof(r -> 'misconceptions') = 'object'"
        "   and (r -> 'misconceptions') ? %s)",
        (code, sheet["item_ids"], on_paper),
    ).fetchone()["n"]
    assert not still, f"{code} {level}: {still} other questions still show {on_paper}"
    chosen, _ = _planted_to_repeat(conn, sheet["item_ids"], slots, after)
    assert chosen != on_paper, (
        f"{code} {level}: still plants {on_paper}, with {taken} other questions unable to show it"
    )


@pytest.mark.parametrize("code,level", [("MD.EQUALITY", "Easy"), ("MD.MULTIPLES", "Easy")])
def test_the_loop_holds_when_the_graph_reads_fewer_answers_than_a_paper_has(
    conn, tmp_path, monkeypatch, every_kind_trusted, code, level
):
    """M0-04, the CI failure of 2026-11-03 made certain: these two papers put 12 and 20 answers on the skill their
    planted mistake lands on, so a build that drew a few more questions, or a graph that reads a few fewer answers,
    pushed the mistake planted on the early boxes out of the window ("graph []"). A window of 6 is that case here, on
    any build: the mistake planted must be one the graph can still see, and every later stage must follow."""
    conn.execute("update threshold set value = 6 where key = 'state.window_answers'")
    _round_the_loop(conn, tmp_path, monkeypatch, code, level)


def _round_the_loop(conn, tmp_path, monkeypatch, code, level):
    sheet = _sheet(conn, code, level)
    if sheet is None and level not in [
        lv
        for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
        if s["code"] == code
        for lv in s["difficulty"]
    ]:
        pytest.skip(f"{code} has no {level} level")
    assert sheet, f"{code} {level}: no library worksheet to print"
    conn.execute(
        "update skill set taught = true, taught_by = %s, taught_at = now() where code = %s",
        (PERSON, code),
    )
    slots = _slots(conn, sheet["item_ids"])
    after = (code, level, sheet["grade"] or sheet["band"])
    mistake, on = _planted_to_repeat(conn, sheet["item_ids"], slots, after)
    if not mistake:  # say which it is: the paper, or the bank (M0-04b)
        paper_only, _ = _planted_to_repeat(conn, sheet["item_ids"], slots)
        assert not paper_only, (
            f"{code} {level}: BANK DEFECT, not a test fault: the paper shows {paper_only} twice among the last answers"
            f" of one skill, but no other question of the level can show it again on the child's next paper, nor can"
            f" any other mistake the paper shows"
        )
    assert mistake and len(on) >= 2, (
        f"{code} {level}: no mistake its paper shows twice among the last answers of one skill"
    )

    # the first turn: the worksheet, printed for the child as an educator does on the site (Make papers, `handout`)
    section = f"L{uuid.uuid4().hex[:5]}"
    child = _a_child(conn, section, sheet["grade"] or sheet["band"])
    pdf = handout.for_children(conn, sheet["code"], [child], WEEK, PERSON, tmp_path / "print")
    qr = conn.execute("select qr_code from sheet_instance where child_id = %s", (child,)).fetchone()[
        "qr_code"
    ]
    planted = _round(
        conn,
        child,
        qr,
        pdf,
        sheet["item_ids"],
        mistake,
        tmp_path / "first.pdf",
        monkeypatch,
        f"{code} {level}",
    )
    seen = _counted(conn, child, mistake, sheet["rung_code"])
    assert seen == planted, (
        f"{code} {level}: {seen} of {planted} planted answers counted on {sheet['rung_code']}"
    )

    graph.rebuild(conn, child)
    state = conn.execute(
        "select state, repeating_misconception from child_skill_state where child_id = %s and rung_code = %s"
        " and repeating_misconception is not null",
        (child, sheet["rung_code"]),
    ).fetchall()
    assert any(s["repeating_misconception"] == mistake for s in state), f"{code} {level}: graph {state}"

    nxt = focus_paper.plan(conn, child, WEEK)["areas"]
    assert nxt and nxt[0]["skill_set"] == code and nxt[0]["mistake"] == mistake, (
        f"{code} {level}: next {nxt[:1]}"
    )
    assert any(q["shows_mistake"] for q in nxt[0]["questions"]), (
        f"{code} {level}: no next question can show {mistake} — {nxt[0]['level']}, skill {nxt[0]['skill']},"
        f" {[(q['fmt'], q['text'][:40]) for q in nxt[0]['questions']]}"
    )

    name = mistake_names.names(conn)(mistake)
    line = next(k for k in card.build(conn, section)["children"] if k["child_id"] == str(child))
    assert line["home"] and line["home"]["mistake"] == mistake and line["home"]["mistake_name"], line
    facts = parent_facts.facts(conn, child)
    said = [w for w in facts["working_on"] if w["id"] == mistake]
    assert said and said[0]["mistake"] and said[0]["what_we_do"], (
        f"{code} {level}: parent facts {facts['working_on']}"
    )
    assert "borrow" not in (name + line["home"]["mistake_name"] + said[0]["mistake"]).lower(), (
        "the school's words"
    )

    # the second turn (M5b): that next paper, approved and printed for the child, comes back from its scan by its code,
    # the mistake made again named on it, and counted once signed off
    made = focus_paper.make(conn, child, WEEK, PERSON)
    ids = conn.execute(
        "select t.item_ids from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
        " where si.qr_code = %s",
        (made["qr"],),
    ).fetchone()["item_ids"]
    again = _round(
        conn,
        child,
        made["qr"],
        made["pdf_path"],
        ids,
        mistake,
        tmp_path / "next.pdf",
        monkeypatch,
        f"{code} {level}, its next paper",
    )
    assert again >= 1, f"{code} {level}: the next paper's questions could not show {mistake}"
    assert _counted(conn, child, mistake) == planted + again, (
        f"{code} {level}: the next paper's mistakes counted"
    )
