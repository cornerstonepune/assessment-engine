"""M1-11: the run commands (goals/m1-11-k2-complete-v1.yaml). `engine curriculum draft` and `materials` fill the gaps of
K2 pages through the M1-05 ledger. No model is called here: every reply is scripted, as on a machine with no key.

Every row is a placeholder in a band of the test's own ("KX"), made inside the test's transaction and rolled back."""

import os
import re
from collections import Counter

import pytest
from typer.testing import CliRunner

from engine import cli
from engine.adapters import llm
from engine.core import db, settings
from engine.w1_bank import k2_draft as draft
from engine.w1_bank import k2_review, map_ledger
from engine.w1_bank.k2_gaps import PAGE_PARTS
from tests.rows import tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
BAND = "KX"
LEVELS = {
    "level_0": "sits out",
    "level_1": "names it",
    "level_2": "does it as shown",
    "level_3": "does it their own way",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        c.t = tenant(c)  # type: ignore[attr-defined]
        c.execute(
            "update config set value = '{\"shadow\": []}'::jsonb where key = 'k2.checkers'"
        )  # one checker
        c.staff = _staff(c, c.t)  # type: ignore[attr-defined]
        c.execute(
            "insert into grade (tenant_id, code, name, ord) values (%s, %s, 'Test band', 99)", (c.t, BAND)
        )
        yield c
        c.rollback()


def _staff(conn, t):
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    sid = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (t, campus)
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'A placeholder', 'x@school.invalid')",
        (t, sid),
    )
    return sid


def _act(conn, code, name, strand="Block Room", materials="", **parts):
    cols = {"objective": "", "steps": "", "thinking": "", **{f"level_{i}": "" for i in range(4)}, **parts}
    conn.execute(
        "insert into activity (tenant_id, code, band, strand, name, materials, objective, steps, thinking, level_0,"
        " level_1, level_2, level_3) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            conn.t,
            code,
            BAND,
            strand,
            name,
            materials,
            *[
                cols[k]
                for k in ("objective", "steps", "thinking", "level_0", "level_1", "level_2", "level_3")
            ],
        ),
    )


FULL = {"objective": "o", "steps": "s", "thinking": "t", **LEVELS}
THOUGHT = "t\n\u2022 counts twice: Finger goes back."  # the idea and the slips, as the column holds them


class Scripted:
    """Answers for (purpose, key) from a script; an entry is a reply per attempt. Remembers every call it was asked."""

    def __init__(self, script):
        self.script, self.asked, self.seen = script, [], Counter()

    def __call__(self, purpose, variables):
        text = variables.get("pages") or variables.get("lists")
        keys = re.findall(r"^key: (\S+)", text, re.M)
        self.asked.append((purpose, keys))
        out = []
        for k in keys:
            n = self.seen[purpose, k]
            self.seen[purpose, k] += 1
            replies = self.script.get((purpose, k), [])
            if n < len(replies) and replies[n] is not None:
                out.append({"key": k, **replies[n]})
        field = {
            "k2_page_draft": "pages",
            "k2_page_check": "verdicts",
            "k2_page_check_b": "verdicts",
            "k2_materials_split": "lists",
        }[purpose]
        return {field: out}


def drafted(**over):
    """A reply in the shape of draft v4: lists for the steps and the slips, and `uses` (what the steps use)."""
    return {
        "flags": [], "confidence": 0.9, "reason": "r", "objective": "o", "steps": ["s"], "uses": [],
        "idea": "t", "slips": [{"keyword": "counts twice", "spot": "Finger goes back."}], **LEVELS, **over,
    }  # fmt: skip


AGREE = {"verdict": "agree", "faults": []}
FAULT = {"verdict": "disagree", "faults": [{"part": "steps", "reason": "describes another activity"}]}
LINES = []


def run(conn, ask, **kw):
    lines: list[str] = []
    rep = draft.draft(conn, conn.t, conn.staff, BAND, "dev_eval", ask, write=True, say=lines.append, **kw)
    rep.lines = lines
    return rep


def test_only_pages_with_an_empty_part_are_wanted_and_each_says_which_parts(conn):
    _act(conn, "KX-1", "Whole", **FULL)
    _act(conn, "KX-2", "Nothing yet")
    _act(conn, "KX-3", "Half", objective="o", steps="s", level_1="a", level_2="b")
    want, _ = draft.wanted(conn, conn.t, BAND)
    assert "KX-1" not in want
    assert want["KX-2"] == list(PAGE_PARTS)
    assert want["KX-3"] == ["thinking", "level_0", "level_3"]


def test_a_dry_run_prints_the_forecast_and_makes_no_call_and_writes_nothing(conn):
    _act(conn, "KX-1", "A")
    _act(conn, "KX-2", "B")
    refuse = Scripted({})
    rep = draft.draft(conn, conn.t, conn.staff, BAND, "dev_eval", refuse, dry_run=True, say=lambda s: None)
    assert refuse.asked == [] and rep.calls == 0 and rep.proposals == 0
    assert "forecast" in rep.forecast and "2 pages" in rep.forecast and "nothing was called" in rep.forecast
    assert "assumed" in rep.forecast, "the token counts are assumptions and the forecast says so"
    assert (
        conn.execute("select count(*) as n from curriculum_proposal where kind = 'page_part'").fetchone()["n"]
        == 0
    )


def test_the_command_in_dry_run_prints_the_forecast_and_adds_no_flow_run():
    before = None
    with db.connect() as c:
        before = c.execute("select count(*) as n from flow_run").fetchone()["n"]
    result = CliRunner().invoke(cli.app, ["curriculum", "draft", "--stage", "dev_eval", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "forecast" in result.output and "nothing was called" in result.output
    with db.connect() as c:
        assert c.execute("select count(*) as n from flow_run").fetchone()["n"] == before


def test_a_real_run_without_a_member_of_staff_is_refused_before_anything_is_asked():
    result = CliRunner().invoke(cli.app, ["curriculum", "draft", "--stage", "dev_eval"])
    shown = re.sub(
        r"\x1b\[[0-9;]*m", "", result.output
    )  # CI's terminal colours the option's name; the words are the same
    assert result.exit_code != 0 and "--by" in shown


def test_a_run_drafts_checks_and_records_each_page_where_it_belongs_and_prints_the_spend_every_batch(conn):
    for c in ("KX-1", "KX-2", "KX-3"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted()],
            ("k2_page_draft", "KX-2"): [
                drafted(steps=[]),
                drafted(),
            ],  # empty the first time
            ("k2_page_draft", "KX-3"): [drafted()],
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [AGREE],
            ("k2_page_check", "KX-3"): [FAULT],
        }
    )
    rep = run(conn, ask)
    assert [a for a in ask.asked if a[0] == "k2_page_draft"] == [
        ("k2_page_draft", ["KX-1", "KX-2", "KX-3"]),
        ("k2_page_draft", ["KX-2"]),
        ("k2_page_draft", ["KX-3"]),
    ], (
        "KX-2 alone goes round again; the good pages are not asked twice; KX-3, which the checker faulted, is revised once"
    )
    now = {r["subject_code"]: r["status"] for r in map_ledger.standing(conn, conn.t)}
    assert now == {"KX-1": "auto_passed", "KX-2": "auto_passed", "KX-3": "needs_person"}
    assert rep.calls == 4 and rep.proposals == 3 and rep.left == {}
    spend_lines = [ln for ln in rep.lines if ln.startswith("batch")]
    assert len(spend_lines) == rep.calls and all(
        "spent $" in ln and "stage dev_eval" in ln for ln in spend_lines
    )


def test_a_page_the_agent_flagged_or_was_unsure_of_goes_to_a_person_even_when_the_checker_agrees(conn):
    _act(conn, "KX-1", "Number names 11-20", objective="numbers from 6-10")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted(flags=["name says 11-20, objective says 6-10"])],
            ("k2_page_check", "KX-1"): [AGREE],
        }
    )
    run(conn, ask)
    (p,) = map_ledger.standing(conn, conn.t)
    assert p["now"] == "needs_person" and "6-10" in p["reason"]


def test_a_page_still_bad_after_the_last_round_is_reported_with_why_and_nothing_is_recorded_for_it(conn):
    _act(conn, "KX-1", "A")
    rep = run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted(steps=[" "])] * 3}))
    assert (
        rep.left == {"KX-1": "steps is empty"}
        and rep.proposals == 0
        and not map_ledger.standing(conn, conn.t)
    )
    assert rep.calls == 2, "the same rule broken twice: a third ask would buy the same failure"
    assert any(ln == "rules broken: steps_empty 2; 1 pages not asked a third time" for ln in rep.lines)


def test_when_the_money_runs_out_the_run_stops_keeps_the_good_pages_and_says_so(conn):
    for i in range(1, 7):
        _act(conn, f"KX-{i}", f"A{i}")
    inner = Scripted(
        {("k2_page_draft", f"KX-{i}"): [drafted()] for i in range(1, 7)}
        | {("k2_page_check", f"KX-{i}"): [AGREE] for i in range(1, 7)}
    )
    calls = {"n": 0}

    def ask(purpose, variables):
        calls["n"] += 1
        if calls["n"] == 2:  # the second draft batch (the first holds four pages, the second two)
            raise llm.LLMBudgetError("campaign m1-11 stopped: $23.01 spent, at its limit of $23.00")
        return inner(purpose, variables)

    rep = run(conn, ask)
    assert "m1-11 stopped" in rep.stopped
    now = {r["subject_code"]: (r["status"], r["reason"]) for r in map_ledger.standing(conn, conn.t)}
    assert set(now) == {"KX-1", "KX-2", "KX-3", "KX-4"}, (
        "the four drafted pages are kept; the two never drafted are not"
    )
    assert all(v == ("needs_person", "not checked: the run stopped") for v in now.values()), (
        "no check once the money is out"
    )
    assert set(rep.left) == {"KX-5", "KX-6"} and all(
        v == "not asked: the run stopped" for v in rep.left.values()
    )


def test_applying_writes_the_drafted_parts_where_they_are_still_empty_marks_them_drafted_and_a_persons_words_stay(
    conn,
):
    _act(conn, "KX-1", "A", objective="the school's own words")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted(objective="ignored")],
            ("k2_page_check", "KX-1"): [AGREE],
        }
    )
    run(conn, ask)
    conn.execute("update activity set steps = 'an educator wrote this meanwhile' where code = 'KX-1'")
    map_ledger.apply(conn, conn.t, conn.staff, True)
    a = conn.execute(
        "select objective, steps, thinking, level_2 from activity where code = 'KX-1'"
    ).fetchone()
    assert a["objective"] == "the school's own words", "the school's text is never written over"
    assert a["steps"] == "an educator wrote this meanwhile", "nor a person's"
    assert (a["thinking"], a["level_2"]) == (THOUGHT, "does it as shown")
    src = {
        r["part"]: r["source"]
        for r in conn.execute("select part, source from activity_part_source where activity_code = 'KX-1'")
    }
    assert src["thinking"] == "drafted" and src["level_2"] == "drafted"
    assert "steps" not in src and "objective" not in src, "a part the draft did not write has no draft mark"
    history = conn.execute(
        "select changed_by from curriculum_edit where code = 'KX-1' and field = 'thinking'"
    ).fetchone()
    assert history["changed_by"].startswith("machine:")


def test_reverting_empties_only_what_is_still_the_drafts_and_takes_its_mark_away(conn):
    _act(conn, "KX-1", "A")
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [AGREE]}))
    map_ledger.apply(conn, conn.t, conn.staff, True)
    conn.execute("update activity set level_1 = 'changed by an educator' where code = 'KX-1'")
    (p,) = map_ledger.standing(conn, conn.t, "applied")
    map_ledger.revert(conn, conn.t, p["id"], conn.staff, "test")
    a = conn.execute("select thinking, level_1, level_2 from activity where code = 'KX-1'").fetchone()
    assert (a["thinking"], a["level_1"], a["level_2"]) == ("", "changed by an educator", "")
    left = {
        r["part"] for r in conn.execute("select part from activity_part_source where activity_code = 'KX-1'")
    }
    assert left == set(), "the draft's marks go with it"


def test_a_page_already_proposed_is_not_drafted_again_so_a_second_run_costs_nothing(conn):
    _act(conn, "KX-1", "A")
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [AGREE]}))
    again = Scripted({})
    rep = draft.draft(conn, conn.t, conn.staff, BAND, "draft", again, write=True, say=lambda s: None)
    assert again.asked == [] and rep.calls == 0


# ---- materials


def test_materials_text_is_split_into_lines_checked_against_the_schools_text_and_nothing_is_guessed(conn):
    _act(conn, "KX-1", "Blocks", materials="10 wooden cubes, red slabs")
    _act(conn, "KX-2", "Wands", materials="a wand")
    ask = Scripted(
        {
            ("k2_materials_split", "KX-1"): [
                {
                    "items": [
                        {"name": "wooden cube", "quantity": 10, "unit": "piece"},
                        {"name": "red slab", "quantity": None, "unit": "piece"},
                    ],
                    "reason": "",
                }
            ],
            ("k2_materials_split", "KX-2"): [
                {"items": [{"name": "magic dragon", "quantity": 1, "unit": "piece"}], "reason": ""}
            ]
            * 3,
        }
    )
    lines: list[str] = []
    rep = draft.materials(conn, conn.t, conn.staff, BAND, "draft", ask, write=True, say=lines.append)
    now = {r["subject_code"]: r["now"] for r in map_ledger.standing(conn, conn.t)}
    assert now == {"KX-1": "auto_passed", "KX-2": "needs_person"}
    assert any(
        "not in the school's text" in p for r in map_ledger.standing(conn, conn.t) for p in r["problems"]
    )
    assert rep.calls >= 1 and any(ln.startswith("batch") and "spent $" in ln for ln in lines)


def test_applying_a_material_proposal_makes_catalogue_items_with_no_invented_home_value_or_quantity(conn):
    _act(conn, "KX-1", "Blocks", materials="10 wooden cubes, red slabs")
    ask = Scripted(
        {
            ("k2_materials_split", "KX-1"): [
                {
                    "items": [
                        {"name": "wooden cube", "quantity": 10, "unit": "piece"},
                        {"name": "red slab", "quantity": None, "unit": "piece"},
                    ],
                    "reason": "",
                }
            ]
        }
    )
    draft.materials(conn, conn.t, conn.staff, BAND, "draft", ask, write=True, say=lambda s: None)
    map_ledger.apply(conn, conn.t, conn.staff, True)
    got = conn.execute(
        "select i.name, i.home, i.unit_value, m.quantity, m.source from activity_material m join material_item i"
        " on i.tenant_id = m.tenant_id and i.code = m.material_code where m.activity_code = 'KX-1' order by m.ord"
    ).fetchall()
    assert [(g["name"], g["home"], g["unit_value"], g["source"]) for g in got] == [
        ("wooden cube", None, None, "machine"),
        ("red slab", None, None, "machine"),
    ]
    assert [g["quantity"] for g in got] == [10, None], "a quantity the text does not give stays empty"
    (p,) = map_ledger.standing(conn, conn.t, "applied")
    map_ledger.revert(conn, conn.t, p["id"], conn.staff, "test")
    assert (
        conn.execute("select count(*) as n from activity_material where activity_code = 'KX-1'").fetchone()[
            "n"
        ]
        == 0
    )


def test_the_forecast_and_the_batches_read_one_config_row_not_numbers_in_code_nor_thresholds(conn):
    """Operational tuning is a config row: a threshold is a rule the school reads about itself, and the guide's own
    test refuses a number written in words when any threshold holds its value (a batch of four broke it)."""
    got = draft._settings(conn)
    assert {"batch_pages", "batch_materials", "batch_rounds", "stop_after_bad_replies"} <= set(got)
    assert {
        "est_draft_in",
        "est_draft_out",
        "est_check_in",
        "est_check_out",
        "est_split_in",
        "est_split_out",
    } <= set(got)
    assert (
        conn.execute("select count(*) as n from threshold where starts_with(key, 'k2.')").fetchone()["n"] == 0
    )


def test_every_paid_call_is_committed_at_once_so_a_crash_later_cannot_erase_the_spend_record(monkeypatch):
    class Spy:
        commits = 0

        def commit(self):
            self.commits += 1

    spy = Spy()
    monkeypatch.setattr(llm, "generate", lambda *a, **k: {"pages": []})
    draft.live_ask(spy, "dev_eval")("k2_page_draft", {"pages": "x"})
    assert spy.commits == 1

    def refused(*a, **k):
        raise llm.LLMBudgetError("campaign m1-11 stopped")

    monkeypatch.setattr(llm, "generate", refused)
    with pytest.raises(llm.LLMBudgetError):
        draft.live_ask(spy, "dev_eval")("k2_page_draft", {"pages": "x"})
    assert spy.commits == 2, (
        "a refusal or a failure commits too: nothing paid is ever left in an open transaction"
    )


def _marks(conn, code):
    rows = conn.execute(
        "select part, source, check_me from activity_part_source where activity_code = %s", (code,)
    )
    return {r["part"]: (r["source"], r["check_me"]) for r in rows.fetchall()}


def test_every_draft_is_written_to_its_empty_parts_marked_drafted_and_every_one_is_check_me_until_a_person_reviews(
    conn,
):
    """K2 version 1 has no empty part (D-071): a draft the checker disagreed with, or the drafter flagged, or was
    unsure of, is on the page too, with a second tag so it heads the review list. From 2026-11-04 every draft carries
    that tag, the ones the machine passed too, until a person has reviewed it: the checker invents facts and the drafter's
    confidence is not calibrated, so nothing counts as passed on a model's word alone. The ledger keeps what the machine
    said (auto_passed) for the calibration table."""
    for c in ("KX-1", "KX-2", "KX-3", "KX-4"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted()],
            ("k2_page_draft", "KX-2"): [drafted()],
            ("k2_page_draft", "KX-3"): [drafted(flags=["name and objective disagree"])],
            ("k2_page_draft", "KX-4"): [drafted(confidence=0.5)],
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [FAULT],
            ("k2_page_check", "KX-3"): [AGREE],
            ("k2_page_check", "KX-4"): [AGREE],
        }
    )
    run(conn, ask)
    said = {p["subject_code"]: p["now"] for p in map_ledger.standing(conn, conn.t)}
    assert said == {
        "KX-1": "auto_passed",
        "KX-2": "needs_person",
        "KX-3": "needs_person",
        "KX-4": "needs_person",
    }, "what the machine said is kept in the data for the calibration table"
    map_ledger.apply(conn, conn.t, conn.staff, True)
    for code, check in (("KX-1", True), ("KX-2", True), ("KX-3", True), ("KX-4", True)):
        assert _marks(conn, code) == {p: ("drafted", check) for p in PAGE_PARTS}, code
        page = conn.execute("select * from activity where code = %s", (code,)).fetchone()
        assert all(page[p].strip() for p in PAGE_PARTS), "no empty part"


def test_nothing_the_school_wrote_is_touched_by_a_doubtful_draft_and_it_reverts_like_any_other(conn):
    _act(conn, "KX-1", "A", objective="the school's own words", level_1="the school's level one")
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", "KX-1"): [drafted()],
                ("k2_page_check", "KX-1"): [FAULT],
            }
        ),
    )
    map_ledger.apply(conn, conn.t, conn.staff, True)
    a = conn.execute("select objective, level_1, thinking from activity where code = 'KX-1'").fetchone()
    assert (a["objective"], a["level_1"], a["thinking"]) == (
        "the school's own words",
        "the school's level one",
        THOUGHT,
    )
    assert "objective" not in _marks(conn, "KX-1") and "level_1" not in _marks(conn, "KX-1")
    (p,) = map_ledger.standing(conn, conn.t, "applied")
    map_ledger.revert(conn, conn.t, p["id"], conn.staff, "test")
    a = conn.execute("select objective, level_1, thinking from activity where code = 'KX-1'").fetchone()
    assert (a["objective"], a["level_1"], a["thinking"]) == (
        "the school's own words",
        "the school's level one",
        "",
    )
    assert _marks(conn, "KX-1") == {}


def test_the_review_list_holds_every_unreviewed_draft_whatever_the_machine_said_of_it(conn):
    for c in ("KX-1", "KX-2", "KX-3"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {("k2_page_draft", c): [drafted()] for c in ("KX-1", "KX-2", "KX-3")}
        | {
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [AGREE],
            ("k2_page_check", "KX-3"): [FAULT],
        }
    )
    run(conn, ask)
    map_ledger.apply(conn, conn.t, conn.staff, True)
    conn.execute(
        "update threshold set value = 0 where key = 'map.audit_share'"
    )  # no sample: the tag alone lists it
    assert [(r["code"], r["check_me"]) for r in k2_review.review_list(conn, conn.t)] == [
        ("KX-1", True),
        ("KX-2", True),
        ("KX-3", True),
    ], "the two the machine passed are on the list too, tagged like the one it doubted"


def test_the_review_list_is_check_me_first_then_the_audit_share_of_the_rest_drawn_by_code(conn):
    """A draft is check me until a person has approved its proposal; then it is only drawn in the audit share."""
    for c in ("KX-1", "KX-2", "KX-3"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {("k2_page_draft", c): [drafted()] for c in ("KX-2", "KX-3")}
        | {("k2_page_draft", "KX-1"): [drafted(confidence=0.5)]}  # waits for a person
        | {("k2_page_check", c): [AGREE] for c in ("KX-1", "KX-2", "KX-3")}
    )
    run(conn, ask)
    (first,) = [p for p in map_ledger.standing(conn, conn.t) if p["subject_code"] == "KX-1"]
    map_ledger.settle(
        conn, conn.t, first["id"], True, conn.staff, "read it"
    )  # a person approves KX-1's proposal
    map_ledger.apply(conn, conn.t, conn.staff, True)
    conn.execute("update threshold set value = 1 where key = 'map.audit_share'")
    assert [(r["code"], r["check_me"]) for r in k2_review.review_list(conn, conn.t)] == [
        ("KX-2", True),
        ("KX-3", True),
        ("KX-1", False),
    ]
    conn.execute("update threshold set value = 0 where key = 'map.audit_share'")
    assert [r["code"] for r in k2_review.review_list(conn, conn.t)] == ["KX-2", "KX-3"], (
        "with no share, only the unreviewed ones"
    )
    conn.execute("update threshold set value = 0.5 where key = 'map.audit_share'")
    again = [r["code"] for r in k2_review.review_list(conn, conn.t)]
    assert again == [r["code"] for r in k2_review.review_list(conn, conn.t)] and again[:2] == [
        "KX-2",
        "KX-3",
    ], "the same draw every time"


def test_a_stop_during_the_check_says_which_pages_were_not_checked_and_keeps_the_verdicts_it_got(conn):
    for i in (1, 2, 3, 4, 5):
        _act(conn, f"KX-{i}", f"A{i}")
    inner = Scripted(
        {("k2_page_draft", f"KX-{i}"): [drafted()] for i in range(1, 6)}
        | {("k2_page_check", f"KX-{i}"): [AGREE] for i in range(1, 6)}
    )
    calls = {"n": 0}

    def ask(purpose, variables):
        calls["n"] += 1
        if (
            calls["n"] == 4
        ):  # the drafts are 2 calls (4 pages + 1), the checks 3 and 4: the second check is refused
            raise llm.LLMBudgetError("campaign m1-11 stopped: $23.01 spent")
        return inner(purpose, variables)

    rep = run(conn, ask)
    now = {r["subject_code"]: (r["status"], r["reason"]) for r in map_ledger.standing(conn, conn.t)}
    assert now["KX-1"][0] == "auto_passed" and now["KX-4"][0] == "auto_passed", (
        "a verdict that came back is kept"
    )
    assert now["KX-5"] == ("needs_person", "not checked: the run stopped")
    assert "m1-11 stopped" in rep.stopped


def test_the_forecast_says_the_most_it_could_cost_if_every_page_went_round_every_time(conn):
    _act(conn, "KX-1", "A")
    text = draft.forecast(conn, "dev_eval", 10)
    assert "up to $" in text and "every page" in text.replace("\n", " ")
    cheap = float(re.search(r"about \$([0-9.]+)", text).group(1))
    worst = float(re.search(r"up to \$([0-9.]+)", text).group(1))
    share = draft._settings(conn)["est_revise_share"]
    assert worst == pytest.approx(cheap * 4 / (1 + share), rel=0.05), (
        "a page written and read, again in each of the 2 rounds, and once more for the checker's revision"
    )


def test_replies_that_keep_breaking_their_schema_stop_the_run_instead_of_paying_for_the_same_failure(conn):
    for i in range(1, 9):
        _act(conn, f"KX-{i}", f"A{i}")
    asked = {"n": 0}

    def ask(purpose, variables):
        asked["n"] += 1
        raise llm.LLMSchemaError("k2_page_draft output failed its schema: x")

    rep = run(conn, ask)
    assert asked["n"] == 3, "three replies in a row that broke their schema, then the run stops"
    assert "schema" in rep.stopped and rep.proposals == 0


def test_a_good_reply_between_the_bad_ones_starts_the_count_again(conn):
    for i in range(1, 9):
        _act(conn, f"KX-{i}", f"A{i}")
    inner = Scripted(
        {("k2_page_draft", f"KX-{i}"): [drafted()] * 3 for i in range(1, 9)}
        | {("k2_page_check", f"KX-{i}"): [AGREE] * 3 for i in range(1, 9)}
    )
    n = {"i": 0}

    def ask(purpose, variables):
        n["i"] += 1
        if n["i"] in (1, 2, 4):  # two bad, a good one, a bad one: never three in a row
            raise llm.LLMSchemaError("x")
        return inner(purpose, variables)

    assert run(conn, ask).stopped == ""


def test_reverting_a_materials_proposal_takes_away_the_catalogue_items_it_made_and_only_those(conn):
    _act(conn, "KX-1", "Blocks", materials="10 wooden cubes, red slabs, 2 paper bags")
    _act(conn, "KX-2", "More blocks", materials="3 wooden cubes")
    conn.execute(
        "insert into material_item (tenant_id, code, name, unit) values (%s,'MAT-9000','red slab','piece')",
        (conn.t,),
    )
    ask = Scripted(
        {
            ("k2_materials_split", "KX-1"): [
                {
                    "items": [
                        {"name": "wooden cube", "quantity": 10, "unit": "piece"},
                        {"name": "red slab", "quantity": None, "unit": "piece"},
                        {"name": "paper bag", "quantity": 2, "unit": "piece"},
                    ],
                    "reason": "",
                }
            ],
            ("k2_materials_split", "KX-2"): [
                {"items": [{"name": "wooden cube", "quantity": 3, "unit": "piece"}], "reason": ""}
            ],
        }
    )
    draft.materials(conn, conn.t, conn.staff, BAND, "draft", ask, write=True, say=lambda s: None)
    map_ledger.apply(conn, conn.t, conn.staff, True)
    p1 = next(p for p in map_ledger.standing(conn, conn.t, "applied") if p["subject_code"] == "KX-1")
    map_ledger.revert(conn, conn.t, p1["id"], conn.staff, "test")
    left = {
        r["name"]
        for r in conn.execute("select name from material_item where tenant_id = %s", (conn.t,)).fetchall()
    }
    assert "wooden cube" in left, "KX-2 still uses it"
    assert "red slab" in left, "a person's item (MAT-9000) is not the proposal's to remove"
    assert "paper bag" not in left, "an item only the reverted proposal made goes with it"


def test_dev_reads_the_number_of_pages_the_config_row_names_and_not_both_dev_and_a_limit():
    """The dev stage's size is `dev_pages` in the k2.drafting config row, not a number typed in a workflow."""
    ok = CliRunner().invoke(cli.app, ["curriculum", "draft", "--stage", "dev_eval", "--dev", "--dry-run"])
    assert ok.exit_code == 0 and "60 pages" in ok.output, ok.output
    two = CliRunner().invoke(
        cli.app, ["curriculum", "draft", "--stage", "dev_eval", "--dev", "--limit", "5", "--dry-run"]
    )
    assert two.exit_code != 0 and "not more" in re.sub(r"\x1b\[[0-9;]*m", "", two.output)


def test_the_dev_pages_are_a_number_in_the_config_row(conn):
    assert draft._settings(conn)["dev_pages"] == 60


def _old_draft(conn, code, proposer):
    from engine.w1_bank.map_agents import Proposal

    map_ledger.record(
        conn,
        conn.t,
        [Proposal("page_part", code, {"parts": {"steps": "old"}, "flags": []}, 0.9, proposer, "", [], "agree", "needs_person", "r")],
        conn.staff,
    )  # fmt: skip


def test_a_part_a_machine_drafted_earlier_is_not_the_schools_words_and_is_drafted_again(conn):
    _act(conn, "KX-1", "A", objective="the school's own", steps="an older machine draft")
    conn.execute(
        "insert into activity_part_source (tenant_id, activity_code, part, source, check_me)"
        " values (%s, 'KX-1', 'steps', 'drafted', true)",
        (conn.t,),
    )
    _old_draft(conn, "KX-1", "k2_page_draft v3")
    want, rows = draft.wanted(conn, conn.t, BAND)
    assert "steps" in want["KX-1"] and "objective" not in want["KX-1"]
    assert rows["KX-1"]["steps"] == "", "the checker and the maker are shown only what the school wrote"
    assert rows["KX-1"]["objective"] == "the school's own"


def test_a_page_this_makers_draft_is_on_the_ledger_for_is_not_asked_again_but_an_older_makers_is(conn):
    _act(conn, "KX-1", "A")
    _act(conn, "KX-2", "B")
    _old_draft(conn, "KX-1", "k2_page_draft v3")
    _old_draft(conn, "KX-2", f"k2_page_draft v{draft.VERSIONS['k2_page_draft']}")
    want, _ = draft.wanted(conn, conn.t, BAND)
    assert set(want) == {"KX-1"}


def test_the_checker_is_shown_the_schools_words_and_the_draft_and_the_maker_the_checkers_reasons(conn):
    _act(conn, "KX-1", "A", objective="the school's own", materials="Beads")
    seen = []

    def ask(purpose, variables):
        seen.append((purpose, variables["pages"]))
        return Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [FAULT]})(
            purpose, variables
        )

    run(conn, ask)
    check = next(t for p, t in seen if p == "k2_page_check")
    assert "objective: the school's own" in check and "materials: Beads" in check and "steps:\n  • s" in check
    assert "confidence" not in check and "the checker found" not in check
    revision = [t for p, t in seen if p == "k2_page_draft"][1]
    assert "the checker found:" in revision and "steps: describes another activity" in revision
    assert "draft: steps" in revision, "only the part at fault is asked for again"


def _two_checkers(conn):
    conn.execute(
        "update config set value = '{\"shadow\": [\"k2_page_check_b\"]}'::jsonb where key = 'k2.checkers'"
    )


def test_with_a_second_checker_on_both_read_the_same_drafts_and_the_ledger_keeps_each_verdict_by_model(conn):
    _two_checkers(conn)
    _act(conn, "KX-1", "A")
    _act(conn, "KX-2", "B")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted()],
            ("k2_page_draft", "KX-2"): [drafted()],
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [AGREE],
            ("k2_page_check_b", "KX-1"): [AGREE],
            ("k2_page_check_b", "KX-2"): [FAULT],
        }
    )
    run(conn, ask)
    assert [p for p, _ in ask.asked].count("k2_page_check_b") == 1
    by_page = {p["subject_code"]: p["proposal"]["checks"] for p in map_ledger.standing(conn, conn.t)}
    assert [(c["checker"], c["model"], c["verdict"]) for c in by_page["KX-2"]] == [
        ("k2_page_check v1", "claude-opus-5-5", "agree"),
        ("k2_page_check_b v1", "claude-sonnet-5-5", "disagree"),
    ]
    assert by_page["KX-2"][1]["faults"][0]["reason"] == "describes another activity"
    assert [p for p, _ in ask.asked].count("k2_page_draft") == 1, "the second checker's fault revised nothing"
    status = {p["subject_code"]: p["status"] for p in map_ledger.standing(conn, conn.t)}
    assert status == {"KX-1": "auto_passed", "KX-2": "auto_passed"}, "only the checker that drives decides"


def test_the_forecast_prices_the_second_checker_when_it_is_on(conn):
    one = draft.forecast(conn, "dev_eval", 60)
    _two_checkers(conn)
    two = draft.forecast(conn, "dev_eval", 60)
    cost = lambda t: float(re.search(r"about \$([0-9.]+)", t).group(1))  # noqa: E731
    assert cost(two) > cost(one)


def test_a_tranche_is_the_next_pages_not_yet_drafted_as_many_as_the_row_names(conn):
    for i in range(1, 6):
        _act(conn, f"KX-{i}", f"A{i}")
    conn.execute(
        "update config set value = jsonb_set(value, '{tranche_pages}', '2') where key = 'k2.drafting'"
    )
    n = int(draft._settings(conn)["tranche_pages"])
    run(conn, Scripted({("k2_page_draft", f"KX-{i}"): [drafted()] for i in (1, 2)}), limit=n)
    again, _ = draft.wanted(conn, conn.t, BAND, n)
    assert n == 2 and list(again) == ["KX-3", "KX-4"], "the next two, the first two being drafted"


def test_the_tranche_cannot_be_combined_with_the_dev_size_or_a_limit():
    for extra in (["--dev"], ["--limit", "5"]):
        got = CliRunner().invoke(
            cli.app, ["curriculum", "draft", "--stage", "draft", "--tranche", *extra, "--dry-run"]
        )
        assert got.exit_code != 0 and "not more" in re.sub(r"\x1b\[[0-9;]*m", "", got.output)
    ok = CliRunner().invoke(cli.app, ["curriculum", "draft", "--stage", "draft", "--tranche", "--dry-run"])
    assert ok.exit_code == 0 and "forecast" in ok.output, ok.output


def test_the_tranche_size_is_a_number_in_the_config_row(conn):
    assert draft._settings(conn)["tranche_pages"] == 250


def test_the_words_of_the_language_that_trail_a_material_are_a_config_row_the_judge_reads(conn):
    row = settings.config(conn, "k2.format")
    assert {"the", "needed", "per"} <= set(row["function_words"])
    _act(conn, "KX-1", "A", materials="Beads, Markers as needed")
    _act(conn, "KX-2", "B", materials="Beads")
    want, rows = draft.wanted(conn, conn.t, BAND)
    reply = [drafted(key="KX-2", steps=["Hand out the beads as needed."], uses=["Beads"])]
    good, bad = draft._judge(conn, rows)(reply, {"KX-2": want["KX-2"]})
    assert bad == {} and "KX-2" in good, "'needed' ends a piece on another page: it is no prop"


def test_a_kept_first_draft_is_not_paid_for_again_the_checkers_read_it_and_the_ledger_row_is_the_same(conn):
    for c in ("KX-1", "KX-2"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-2"): [drafted()],
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [AGREE],
        }
    )
    rep = run(conn, ask, reuse={"KX-1": {"key": "KX-1", **drafted()}})
    asked = [a for a in ask.asked if a[0] == "k2_page_draft"]
    assert asked == [("k2_page_draft", ["KX-2"])], "only the page without a kept draft goes to the maker"
    assert [a for a in ask.asked if a[0] == "k2_page_check"] == [("k2_page_check", ["KX-1", "KX-2"])]
    rows = {r["subject_code"]: r for r in map_ledger.standing(conn, conn.t)}
    assert set(rows) == {"KX-1", "KX-2"} and rep.proposals == 2 and rep.reused == 1
    assert rows["KX-1"]["proposal"]["history"][0].get("reused") is True
    assert "reused" not in rows["KX-2"]["proposal"]["history"][0]
    assert any(ln == "1 first drafts read from kept replies (no maker call)" for ln in rep.lines)


def test_the_forecast_leaves_the_maker_out_for_the_pages_whose_first_draft_is_kept(conn):
    _act(conn, "KX-1", "A")
    _act(conn, "KX-2", "B")
    plain = draft.forecast(conn, "dev_eval", 2)
    reused = draft.forecast(conn, "dev_eval", 2, reused=2)
    cost = lambda t: float(re.search(r"about \$([0-9.]+)", t).group(1))  # noqa: E731
    assert cost(reused) < cost(plain) and "2 first drafts kept" in reused
