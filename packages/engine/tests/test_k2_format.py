"""A drafted page is a list of short bullets and a list of slips, and code refuses what does not fit
(goals/m1-12a-page-format.yaml).

Nimish, 2026-11-05: the site shows bullets with the keywords highlighted, never a wall of text, and a ten-second video is
made from each activity later. So steps are a list (at most 8 lines of about 12 words), the thinking is one line and a
list of slips (a keyword of 2 to 4 words and how to spot it), and no step uses a thing the school's materials do not name.
Pure code: no database and no model.
"""

from engine.w1_bank import k2_format as fmt

FMT = {
    "steps_max": 8, "step_words": 14, "slips_min": 1, "slips_max": 4, "keyword_words_min": 2,
    "keyword_words_max": 4, "spot_words": 20, "idea_words": 25, "always_there": ["child", "educator", "floor"],
}  # fmt: skip
RULES = {"gendered": ["she", "he"], "compare": []}
ROWS = {
    "A": {"materials": "Beads, Number cards 1-10, Chart paper (1 per child)"},
    "B": {"materials": "Chalk, Rope"},
    "C": {"materials": ""},
}
VOCAB = fmt.vocabulary(r["materials"] for r in ROWS.values())
WANT = {"A": ["objective", "steps", "thinking", "level_0", "level_1", "level_2", "level_3"]}


def page(**over):
    base = {
        "key": "A",
        "objective": "The child counts beads to 10.",
        "steps": ["Show ten beads on the floor.", "Ask the child to count them aloud."],
        "uses": ["Beads"],
        "idea": "Each bead is touched once.",
        "slips": [{"keyword": "counts a bead twice", "spot": "The child's finger returns to a bead."}],
        "level_0": "Does not sit for the count.",
        "level_1": "Watches and names the beads.",
        "level_2": "Counts after the educator.",
        "level_3": "Counts alone and says how many.",
    }
    return base | over


def judged(**over):
    return fmt.judger(ROWS, VOCAB, FMT, RULES)([page(**over)], WANT)


def test_a_page_in_the_new_shape_is_kept_with_its_lists_as_lists():
    good, bad = judged()
    assert bad == {}
    parts = good["A"]
    assert parts["steps"] == ["Show ten beads on the floor.", "Ask the child to count them aloud."]
    assert parts["thinking"] == {
        "idea": "Each bead is touched once.",
        "slips": [{"keyword": "counts a bead twice", "spot": "The child's finger returns to a bead."}],
    }
    assert "uses" not in parts and parts["objective"].startswith("The child")


def test_too_many_steps_or_a_long_one_is_refused_with_the_number():
    assert "9 lines" in judged(steps=[f"Do thing {i}." for i in range(9)])[1]["A"]
    long = "Show the child ten beads and ask the child to count every single bead out loud twice."
    assert "steps line 1" in judged(steps=[long])[1]["A"]


def test_steps_that_are_not_a_list_of_lines_are_refused():
    assert "list" in judged(steps="• one\n• two")[1]["A"]
    assert "list" in judged(steps=[1, 2])[1]["A"]
    assert "empty" in judged(steps=[])[1]["A"]


def test_the_slips_are_one_to_four_each_with_a_keyword_of_two_to_four_words_and_a_spot():
    slip = {"keyword": "counts twice", "spot": "Finger goes back."}
    assert "slips" in judged(slips=[])[1]["A"]
    assert "slips" in judged(slips=[slip] * 5)[1]["A"]
    assert "keyword" in judged(slips=[{"keyword": "twice", "spot": "x y"}])[1]["A"]
    assert "keyword" in judged(slips=[{"keyword": "one two three four five", "spot": "x y"}])[1]["A"]
    assert "spot" in judged(slips=[{"keyword": "counts twice"}])[1]["A"]
    assert "slips" in judged(slips=["counts twice"])[1]["A"]
    assert "idea" in judged(idea="")[1]["A"]


def test_a_step_that_uses_a_thing_the_materials_do_not_name_is_refused_naming_the_thing():
    why = judged(steps=["Draw a line with chalk on the floor."])[1]["A"]
    assert "chalk" in why and "materials" in why
    assert judged(steps=["Count the beads with the child.", "Draw on the chart paper."])[1] == {}


def test_what_is_always_in_the_room_needs_no_list_and_a_page_with_no_list_may_use_nothing_else():
    ok = fmt.judger(ROWS, VOCAB, FMT, RULES)
    steps = ["The educator sits with the child on the floor."]
    assert ok([page(key="C", steps=steps, uses=[])], {"C": WANT["A"]})[1] == {}
    assert (
        "rope" in ok([page(key="C", steps=["Lay a rope on the floor."], uses=[])], {"C": WANT["A"]})[1]["C"]
    )


def test_a_material_the_page_says_it_uses_must_be_one_the_school_names():
    assert "uses" in judged(uses=["Beads", "Chalk"])[1]["A"]
    assert judged(uses=["Chart paper"])[1] == {}


def test_the_house_rules_still_reach_a_slip_and_the_levels_must_still_differ():
    gendered = [{"keyword": "counts twice", "spot": "She goes back."}]
    assert "she" in judged(slips=gendered)[1]["A"].lower()
    assert "say the same" in judged(level_1="Same.", level_2="Same.")[1]["A"]


def test_only_the_parts_asked_for_are_kept_and_a_part_not_asked_for_is_ignored():
    got = fmt.judger(ROWS, VOCAB, FMT, RULES)([page(steps=[], slips=[], idea="")], {"A": ["objective"]})
    assert got == ({"A": {"objective": "The child counts beads to 10."}}, {})


def test_a_part_is_written_as_text_for_the_columns_the_site_already_reads():
    good, _ = judged()
    assert fmt.render("steps", good["A"]["steps"]) == (
        "• Show ten beads on the floor.\n• Ask the child to count them aloud."
    )
    assert fmt.render("thinking", good["A"]["thinking"]) == (
        "Each bead is touched once.\n• counts a bead twice: The child's finger returns to a bead."
    )
    assert fmt.render("objective", "text") == "text"


def test_the_checker_is_shown_a_page_as_the_school_wrote_it_and_the_draft_as_bullets():
    shown = fmt.shown_draft(judged()[0]["A"])
    assert "steps:\n  • Show ten beads" in shown and "slip: counts a bead twice" in shown
