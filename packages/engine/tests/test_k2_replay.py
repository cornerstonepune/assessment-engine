"""The kept replies of a draft run, judged again by code (goals/m1-12d-draft-replay.yaml).

A paid reply is kept on its flow_run row. Judging those replies again with the run's own judge says which rule each
page broke on each ask, with no model call and no page text: counts and rule names only (the job log is public)."""

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from engine.w1_bank import k2_replay as rp
from tests import test_k2_draft as base
from tests.test_k2_format import FMT, ROWS, RULES, VOCAB, WANT, fmt, page

conn = base.conn
JUDGE = fmt.judger(ROWS, VOCAB, FMT, RULES)
LONG = ["Show ten beads on the floor and ask the child to count each one aloud twice, slowly."]


def tally(*replies, want=None):
    return rp.tally([("accepted", r) for r in replies], want or WANT, JUDGE)


MATERIALS = {k: v["materials"] for k, v in ROWS.items()}
WANT_C = {"C": WANT["A"]}


def unlisted(*replies, want=None):
    kept = [("accepted", r) for r in replies]
    return rp.tally(kept, want or WANT, JUDGE, MATERIALS)["unlisted"]


def test_each_ask_of_a_page_is_counted_with_the_rule_it_broke():
    got = tally([page(steps=LONG)], [page(steps=LONG)], [page()])
    assert got["replies"] == 3 and got["refused"] == 0
    assert got["attempts"] == [
        {"attempt": 1, "asked": 1, "good": 0, "faults": {"step_too_long": 1}},
        {"attempt": 2, "asked": 1, "good": 0, "faults": {"step_too_long": 1}},
        {"attempt": 3, "asked": 1, "good": 1, "faults": {}},
    ]
    assert got["pages_good"] == 1 and got["pages_never_good"] == 0


def test_a_reply_in_the_prompts_own_shape_an_object_holding_the_pages_is_judged_as_the_run_judged_it():
    got = tally({"pages": [page()]}, {"pages": [page(steps=LONG)]})
    assert got["pages_good"] == 1 and got["pages_never_good"] == 0
    assert got["attempts"][0] == {"attempt": 1, "asked": 1, "good": 1, "faults": {}}
    assert got["attempts"][1]["faults"] == {"step_too_long": 1}, "never 'missing': the page is in the reply"


def test_a_page_never_good_is_counted_and_a_refused_reply_is_a_reply_with_nothing_in_it():
    got = rp.tally([("refused", [page()]), ("accepted", [page(steps=LONG)])], WANT, JUDGE)
    assert got["replies"] == 2 and got["refused"] == 1
    assert got["pages_good"] == 0 and got["pages_never_good"] == 1
    assert got["attempts"][0]["faults"] == {"step_too_long": 1}


def test_a_key_nobody_asked_for_is_not_counted_and_the_output_holds_no_page_text():
    got = tally([page(key="ZZ", steps=LONG), page(steps=LONG)])
    assert got["attempts"][0]["asked"] == 1
    assert "beads" not in json.dumps(got).casefold() and "child" not in json.dumps(got).casefold()


def test_the_rules_are_named_in_the_report_most_often_broken_first():
    lines = rp.lines(tally([page(steps=LONG)], [page(steps=LONG)]))
    assert json.loads(lines[0]) == {"replies": 2, "refused": 0, "pages_good": 0, "pages_never_good": 1}
    assert json.loads(lines[1])["faults"] == {"step_too_long": 1}


def test_a_step_naming_a_prop_the_page_does_not_list_is_counted_as_the_word_and_how_it_relates_to_the_list():
    got = unlisted([page(steps=["Hand out the chalk."])], [page(steps=["Hand out the chalk."])])
    assert got["step_word_unlisted"]["words"] == {"chalk": 2}
    assert got["step_word_unlisted"]["kinds"] == {"not_related": 2}


def test_a_use_that_adds_words_to_a_listed_thing_or_misspells_it_is_told_from_one_that_is_not_listed_at_all():
    got = unlisted([page(uses=["number cards 1 to 10"])], [page(uses=["Beadz"])], [page(uses=["Rope"])])[
        "uses_unlisted"
    ]
    assert got["kinds"] == {"some_words_listed": 1, "near_spelling": 1, "not_related": 1}


def test_a_page_whose_materials_text_is_empty_is_counted_apart_because_no_prop_can_be_listed_for_it():
    got = unlisted([page(key="C", uses=["Rope"])], want=WANT_C)["uses_unlisted"]
    assert got["kinds"] == {"page_has_no_materials": 1}


def test_no_printed_key_holds_a_space_so_no_phrase_of_the_schools_ever_reaches_the_log():
    reply = [page(uses=["number cards 1 to 10"])]
    got = unlisted(reply, reply, [page(steps=["Hand out the chalk."])], [page(steps=["Hand out the chalk."])])
    assert got["uses_unlisted"]["words"] == {}, (
        "a use is a phrase of the school's own text: only its kind is counted"
    )
    assert got["uses_unlisted"]["kinds"] == {"some_words_listed": 2}
    assert got["step_word_unlisted"]["words"] == {"chalk": 2}

    def keys(x):
        return [k for k, v in x.items()] + [k for v in x.values() if isinstance(v, dict) for k in keys(v)]

    assert not [k for k in keys(got) if " " in k]


def test_only_plain_words_of_at_most_twelve_letters_are_ever_printed():
    shown = rp._unlisted(
        {
            "step_word_unlisted": {
                "words": Counter({"chalk": 3, "a b": 4, "x" * 13: 5, "ok-1": 6, "rope": 2, "once": 1}),
                "kinds": Counter(),
            },
            "uses_unlisted": {"words": Counter({"beads": 9}), "kinds": Counter()},
        }
    )
    assert shown["step_word_unlisted"]["words"] == {"chalk": 3, "rope": 2}
    assert shown["uses_unlisted"]["words"] == {}


def test_a_word_seen_once_is_not_printed_so_the_log_holds_only_what_repeats():
    got = unlisted([page(steps=["Hand out the chalk."])], [page(steps=["Use the rope."])])
    words = got["step_word_unlisted"]["words"]
    assert words == {} and got["step_word_unlisted"]["once"] == 2


pytestmark_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)"
)


@pytestmark_db
def test_the_latest_run_is_read_from_the_rows_of_the_stage_and_an_older_run_is_left_out(conn):
    now = datetime.now(UTC)

    def keep(minutes, outcome, reply):
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, status, started_at, result)"
            " values (%s, 'k2_page_draft', 'engine:dev_eval', 'ok', %s, %s)",
            (conn.t, now + timedelta(minutes=minutes), json.dumps({"outcome": outcome, "reply": reply})),
        )

    keep(0, "accepted", [{"key": "OLD"}])
    keep(60, "accepted", [{"key": "NEW1"}])
    keep(61, "refused", [])
    got = rp.stored(conn, "dev_eval", gap_minutes=10.0)
    assert [o for o, _ in got][-2:] == ["accepted", "refused"] and all(r != [{"key": "OLD"}] for _, r in got)


def test_a_use_whose_words_are_all_listed_is_told_apart_by_where_the_list_has_them():
    one = rp.kind_of("cards number", "Beads, Number cards 1-10")  # one piece, the wrong order
    many = rp.kind_of("beads chalk", "Beads, Chalk")  # two pieces of the list
    assert one == "one_piece_not_contiguous" and many == "spans_pieces"
    assert rp.kind_of("rope", "") == "page_has_no_materials" and rp.kind_of("rope", "Beads") == "not_related"


def test_a_word_is_counted_as_one_whatever_its_form_so_colour_and_colours_are_one_line():
    reply = [page(steps=["Hand out the chalks."])]
    got = unlisted(reply, [page(steps=["Hand out the chalk."])])
    assert got["step_word_unlisted"]["words"] == {"chalk": 2}


def test_the_first_draft_the_judge_accepts_is_kept_for_each_page_and_a_page_never_good_has_none():
    good1, bad1 = page(), page(steps=LONG)
    kept = [
        ("accepted", [good1]),
        ("accepted", [bad1]),  # a later, worse answer for the same page
        ("refused", [page(key="C")]),
    ]
    got = rp.kept_drafts(kept, {"A": WANT["A"]}, JUDGE)
    assert got == {"A": good1}
    assert rp.kept_drafts([("accepted", [bad1])], {"A": WANT["A"]}, JUDGE) == {}


def test_a_page_answered_badly_then_well_keeps_the_good_answer():
    bad, good = page(steps=LONG), page()
    assert rp.kept_drafts(
        [("accepted", [bad]), ("accepted", {"pages": [good]})], {"A": WANT["A"]}, JUDGE
    ) == {"A": good}


@pytestmark_db
def test_the_pages_still_wanted_get_the_first_draft_the_stage_already_paid_for(conn):
    base._act(conn, "KX-1", "A page", materials="Beads")
    base._act(conn, "KX-2", "Another page", materials="Beads")
    good = {"key": "KX-1", **base.drafted(uses=["Beads"], steps=["Count the beads."])}
    bad = {"key": "KX-2", **base.drafted(steps=[" "])}
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, started_at, result)"
        " values (%s, 'k2_page_draft', 'engine:dev_eval', 'ok', now(), %s)",
        (conn.t, json.dumps({"outcome": "accepted", "reply": {"pages": [good, bad]}})),
    )
    got = rp.reusable(conn, conn.t, base.BAND, "dev_eval")
    assert set(got) == {"KX-1"} and got["KX-1"]["key"] == "KX-1"
