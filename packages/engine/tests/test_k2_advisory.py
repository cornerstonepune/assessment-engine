"""A style rule is a note on a recorded page, not a reason to hold it back (goals/m1-12p-advisory-rules.yaml).

Nimish, 7 Nov: pages are editable by teachers, so loosen the checks. A page that breaks only a style or format rule is
kept with a note; the rules about a child (gendered, comparing) and an empty or malformed page still hold it back."""

from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_format as fmt
from tests.test_k2_format import FMT, ROWS, RULES, VOCAB, WANT, page

ADVISORY = [
    "step_word_unlisted",
    "uses_unlisted",
    "keyword_length",
    "spot_length",
    "step_too_long",
    "steps_too_many",
    "idea_too_long",
]
SOFT = FMT | {"advisory_rules": ADVISORY}
LONG = "Show the child ten beads on the floor and ask the child to count every single bead out loud twice."


def judge(over, fmt_row=SOFT):
    j = fmt.judger(ROWS, VOCAB, fmt_row, RULES)
    good, bad = j([page(**over)], WANT)
    return good, bad, j.notes


def test_with_no_advisory_rule_every_rule_holds_a_page_back_as_before():
    good, bad, notes = judge({"steps": [LONG]}, FMT)
    assert good == {} and "words" in bad["A"] and notes == {}


def test_a_step_that_is_too_long_is_kept_with_a_note():
    good, bad, notes = judge({"steps": [LONG, "Count them."]})
    assert bad == {} and good["A"]["steps"] == [LONG, "Count them."]
    assert [batch.rule_of(n) for n in notes["A"]] == ["step_too_long"]


def test_too_many_steps_a_long_keyword_and_a_long_idea_are_each_kept_with_a_note():
    many = [f"Do thing {i}." for i in range(9)]
    slip = {"keyword": "counts a single bead twice again", "spot": "The finger returns."}
    idea = " ".join(["Each bead is touched once and only once"] * 4)
    good, bad, notes = judge({"steps": many, "slips": [slip], "idea": idea})
    assert bad == {} and len(good["A"]["steps"]) == 9
    assert good["A"]["thinking"]["slips"] == [slip] and good["A"]["thinking"]["idea"] == idea
    assert sorted(batch.rule_of(n) for n in notes["A"]) == [
        "idea_too_long",
        "keyword_length",
        "steps_too_many",
    ]


def test_a_step_that_names_a_prop_the_materials_do_not_is_kept_with_a_note():
    good, bad, notes = judge({"steps": ["Show the beads.", "Then use the rope."], "uses": ["Beads"]})
    assert bad == {} and "steps" in good["A"]
    assert [batch.rule_of(n) for n in notes["A"]] == ["step_word_unlisted"]


def test_a_page_that_is_empty_or_malformed_is_still_held_back():
    for over, rule in (
        ({"steps": []}, "steps_empty"),
        ({"steps": "not a list"}, "steps_not_list"),
        ({"idea": ""}, "idea_empty"),
        ({"slips": []}, "slips_count"),
        ({"slips": ["x"]}, "slip_shape"),
    ):
        good, bad, _ = judge(over)
        assert good == {} and batch.rule_of(bad["A"]) == rule, over


def test_a_page_that_says_he_or_she_of_a_child_is_still_held_back():
    good, bad, _ = judge({"idea": "He counts each bead."})
    assert good == {} and batch.rule_of(bad["A"]) == "gendered"


def test_a_blocking_fault_wins_over_a_note_and_the_notes_of_a_held_page_are_not_kept():
    good, bad, notes = judge({"steps": [LONG], "idea": ""})
    assert good == {} and batch.rule_of(bad["A"]) == "idea_empty" and "A" not in notes


def test_the_notes_are_only_for_the_latest_pages_a_judge_accepted():
    j = fmt.judger(ROWS, VOCAB, SOFT, RULES)
    j([page(steps=[LONG])], WANT)
    assert "A" in j.notes
    j([page()], WANT)
    assert "A" not in j.notes, "a clean draft of the page clears its notes"


def test_the_notes_ride_on_the_proposal_and_its_reason_and_change_neither_status_nor_confidence():
    from engine.w1_bank import k2_check as chk

    note = ["steps line 2 has 20 words, at most 14"]
    base = chk.proposal("A", {"steps": []}, {"confidence": 0.9}, ("agree", []), [], 0.7, False)
    noted = chk.proposal("A", {"steps": []}, {"confidence": 0.9}, ("agree", []), [], 0.7, False, notes=note)
    assert noted.status == base.status == "auto_passed" and noted.confidence == base.confidence
    assert noted.proposal["notes"] == note and noted.reason.endswith("| notes: " + note[0])
    assert base.proposal["notes"] == []


def test_a_page_recorded_from_a_kept_draft_says_the_checker_has_not_read_it():
    from engine.w1_bank import k2_check as chk

    p = chk.proposal("A", {}, {"confidence": 0.9}, None, [], 0.7, False, unread=True)
    assert (
        p.status == "needs_person" and p.reason == "recorded from a kept draft; the checker has not read it"
    )


def test_the_seed_names_the_style_rules_as_advisory_and_none_of_the_rules_that_must_hold():
    import json
    from pathlib import Path

    seed = json.loads((Path(__file__).parents[3] / "supabase/seed/config.json").read_text())["config"]
    soft = set(next(r for r in seed if r["key"] == "k2.format")["value"]["advisory_rules"])
    assert soft == set(ADVISORY)
    must = {
        "steps_not_list",
        "steps_empty",
        "slips_count",
        "slip_shape",
        "idea_empty",
        "part_empty",
        "missing",
    }
    must |= {"answered_twice", "levels_alike", "gendered", "compares"}
    assert not soft & must and soft <= {name for _, name in batch.RULES}
