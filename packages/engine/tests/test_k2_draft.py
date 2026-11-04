"""M1-11: the run commands (goals/m1-11-k2-complete-v1.yaml). `engine curriculum draft` and `materials` fill the gaps of
K2 pages through the M1-05 ledger. No model is called here: every reply is scripted, as on a machine with no key.

Every row is a placeholder in a band of the test's own ("KX"), made inside the test's transaction and rolled back."""

import json
import os
import re
from collections import Counter

import pytest
from typer.testing import CliRunner

from engine import cli
from engine.adapters import llm
from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_draft as draft
from engine.w1_bank import map_ledger
from tests.rows import tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
BAND = "KX"
LEVELS = {
    "level_0": "sits out",
    "level_1": "names it",
    "level_2": "does it as shown",
    "level_3": "does it her way",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        c.t = tenant(c)  # type: ignore[attr-defined]
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
        field = {"k2_page_draft": "pages", "k2_page_validate": "verdicts", "k2_materials_split": "lists"}[
            purpose
        ]
        return {field: out}


def drafted(**parts):
    return {"flags": [], "confidence": 0.9, "reason": "r", **parts}


AGREE = {"verdict": "agree", "why": "describes the activity"}
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
    assert want["KX-2"] == list(draft.PAGE_PARTS)
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
    assert result.exit_code != 0 and "--by" in result.output


def test_a_run_drafts_checks_and_records_each_page_where_it_belongs_and_prints_the_spend_every_batch(conn):
    for c in ("KX-1", "KX-2", "KX-3"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted(**FULL)],
            ("k2_page_draft", "KX-2"): [
                drafted(**{**FULL, "steps": ""}),
                drafted(**FULL),
            ],  # empty the first time
            ("k2_page_draft", "KX-3"): [drafted(**FULL)],
            ("k2_page_validate", "KX-1"): [AGREE],
            ("k2_page_validate", "KX-2"): [AGREE],
            ("k2_page_validate", "KX-3"): [{"verdict": "disagree", "why": "describes another activity"}],
        }
    )
    rep = run(conn, ask)
    assert [a for a in ask.asked if a[0] == "k2_page_draft"] == [
        ("k2_page_draft", ["KX-1", "KX-2", "KX-3"]),
        ("k2_page_draft", ["KX-2"]),
    ], "KX-2 alone goes round again; the good pages are not asked twice"
    now = {r["subject_code"]: r["status"] for r in map_ledger.standing(conn, conn.t)}
    assert now == {"KX-1": "auto_passed", "KX-2": "auto_passed", "KX-3": "needs_person"}
    assert rep.calls == 3 and rep.proposals == 3 and rep.left == {}
    spend_lines = [ln for ln in rep.lines if ln.startswith("batch")]
    assert len(spend_lines) == rep.calls and all(
        "spent $" in ln and "stage dev_eval" in ln for ln in spend_lines
    )


def test_a_page_the_agent_flagged_or_was_unsure_of_goes_to_a_person_even_when_the_checker_agrees(conn):
    _act(conn, "KX-1", "Number names 11-20", objective="numbers from 6-10")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [
                drafted(**{**FULL, "flags": ["name says 11-20, objective says 6-10"]})
            ],
            ("k2_page_validate", "KX-1"): [AGREE],
        }
    )
    run(conn, ask)
    (p,) = map_ledger.standing(conn, conn.t)
    assert p["now"] == "needs_person" and "6-10" in p["reason"]


def test_a_page_still_bad_after_the_last_round_is_reported_with_why_and_nothing_is_recorded_for_it(conn):
    _act(conn, "KX-1", "A")
    rep = run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted(**{**FULL, "steps": " "})] * 3}))
    assert (
        rep.left == {"KX-1": "steps is empty"}
        and rep.proposals == 0
        and not map_ledger.standing(conn, conn.t)
    )


def test_when_the_money_runs_out_the_run_stops_keeps_the_good_pages_and_says_so(conn):
    for i in range(1, 7):
        _act(conn, f"KX-{i}", f"A{i}")
    inner = Scripted(
        {("k2_page_draft", f"KX-{i}"): [drafted(**FULL)] for i in range(1, 7)}
        | {("k2_page_validate", f"KX-{i}"): [AGREE] for i in range(1, 7)}
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
            ("k2_page_draft", "KX-1"): [drafted(**{**FULL, "objective": "ignored"})],
            ("k2_page_validate", "KX-1"): [AGREE],
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
    assert (a["thinking"], a["level_2"]) == ("t", "does it as shown")
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
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted(**FULL)], ("k2_page_validate", "KX-1"): [AGREE]}))
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
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted(**FULL)], ("k2_page_validate", "KX-1"): [AGREE]}))
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


def test_the_forecast_uses_threshold_rows_for_its_assumed_tokens_and_the_batch_size(conn):
    rows = {
        r["key"] for r in conn.execute("select key from threshold where starts_with(key, 'k2.')").fetchall()
    }
    assert {
        "k2.batch_pages",
        "k2.est_draft_in",
        "k2.est_draft_out",
        "k2.est_check_in",
        "k2.est_check_out",
        "k2.est_split_in",
        "k2.est_split_out",
    } <= rows
    assert json.dumps(batch.Done().good) == "{}"


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


def test_every_draft_is_written_to_its_empty_parts_marked_drafted_and_the_doubtful_ones_are_check_me(conn):
    """K2 version 1 has no empty part (D-071): a draft the checker disagreed with, or the drafter flagged, or was
    unsure of, is on the page too, with a second tag so it heads the review list."""
    for c in ("KX-1", "KX-2", "KX-3", "KX-4"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {
            ("k2_page_draft", "KX-1"): [drafted(**FULL)],
            ("k2_page_draft", "KX-2"): [drafted(**FULL)],
            ("k2_page_draft", "KX-3"): [drafted(**{**FULL, "flags": ["name and objective disagree"]})],
            ("k2_page_draft", "KX-4"): [drafted(**{**FULL, "confidence": 0.5})],
            ("k2_page_validate", "KX-1"): [AGREE],
            ("k2_page_validate", "KX-2"): [{"verdict": "disagree", "why": "describes another activity"}],
            ("k2_page_validate", "KX-3"): [AGREE],
            ("k2_page_validate", "KX-4"): [AGREE],
        }
    )
    run(conn, ask)
    map_ledger.apply(conn, conn.t, conn.staff, True)
    for code, check in (("KX-1", False), ("KX-2", True), ("KX-3", True), ("KX-4", True)):
        assert _marks(conn, code) == {p: ("drafted", check) for p in draft.PAGE_PARTS}, code
        page = conn.execute("select * from activity where code = %s", (code,)).fetchone()
        assert all(page[p].strip() for p in draft.PAGE_PARTS), "no empty part"


def test_nothing_the_school_wrote_is_touched_by_a_doubtful_draft_and_it_reverts_like_any_other(conn):
    _act(conn, "KX-1", "A", objective="the school's own words", level_1="the school's level one")
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", "KX-1"): [drafted(**FULL)],
                ("k2_page_validate", "KX-1"): [{"verdict": "disagree", "why": "w"}],
            }
        ),
    )
    map_ledger.apply(conn, conn.t, conn.staff, True)
    a = conn.execute("select objective, level_1, thinking from activity where code = 'KX-1'").fetchone()
    assert (a["objective"], a["level_1"], a["thinking"]) == (
        "the school's own words",
        "the school's level one",
        "t",
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


def test_the_review_list_is_check_me_first_then_the_audit_share_of_the_rest_drawn_by_code(conn):
    for c in ("KX-1", "KX-2", "KX-3"):
        _act(conn, c, f"Activity {c}")
    ask = Scripted(
        {("k2_page_draft", c): [drafted(**FULL)] for c in ("KX-1", "KX-2", "KX-3")}
        | {
            ("k2_page_validate", "KX-1"): [AGREE],
            ("k2_page_validate", "KX-2"): [AGREE],
            ("k2_page_validate", "KX-3"): [{"verdict": "disagree", "why": "w"}],
        }
    )
    run(conn, ask)
    map_ledger.apply(conn, conn.t, conn.staff, True)
    conn.execute("update threshold set value = 1 where key = 'map.audit_share'")
    everything = draft.review_list(conn, conn.t)
    assert [(r["code"], r["check_me"]) for r in everything] == [
        ("KX-3", True),
        ("KX-1", False),
        ("KX-2", False),
    ]
    conn.execute("update threshold set value = 0 where key = 'map.audit_share'")
    assert [r["code"] for r in draft.review_list(conn, conn.t)] == ["KX-3"], (
        "with no share, only the doubtful ones"
    )
    conn.execute("update threshold set value = 0.5 where key = 'map.audit_share'")
    again = [r["code"] for r in draft.review_list(conn, conn.t)]
    assert again == [r["code"] for r in draft.review_list(conn, conn.t)] and again[0] == "KX-3", (
        "the same draw every time"
    )


def test_a_stop_during_the_check_says_which_pages_were_not_checked_and_keeps_the_verdicts_it_got(conn):
    for i in (1, 2, 3, 4, 5):
        _act(conn, f"KX-{i}", f"A{i}")
    inner = Scripted(
        {("k2_page_draft", f"KX-{i}"): [drafted(**FULL)] for i in range(1, 6)}
        | {("k2_page_validate", f"KX-{i}"): [AGREE] for i in range(1, 6)}
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
    assert worst == pytest.approx(cheap * 3, rel=0.05), "rounds = 2 more passes: three times the one pass"


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
        {("k2_page_draft", f"KX-{i}"): [drafted(**FULL)] * 3 for i in range(1, 9)}
        | {("k2_page_validate", f"KX-{i}"): [AGREE] * 3 for i in range(1, 9)}
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
