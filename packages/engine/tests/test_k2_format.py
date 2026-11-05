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
    # its steps are the checker's to read; what it declares it uses must be empty, as it has no list
    assert "uses" in ok([page(key="C", steps=steps, uses=["Rope"])], {"C": WANT["A"]})[1]["C"]


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


def _judge_with(materials, steps=None, uses=None, function_words=("and",)):
    rows = {"A": {"materials": materials}, "Z": {"materials": "Pictures to draw, Cut out and place, Beads"}}
    vocab = fmt.vocabulary((r["materials"] for r in rows.values()), function_words)
    fmt_row = FMT | {"function_words": list(function_words)}
    one = page(steps=steps or ["Count the beads."], uses=uses if uses is not None else [])
    return fmt.judger(rows, vocab, fmt_row, RULES)([one], {"A": WANT["A"]})


def test_a_use_copied_from_the_list_with_its_quantity_is_found_though_the_quantity_has_digits():
    # the school writes "Beads (10 per child)"; the draft's `uses` drops the digits, the text kept them between the words
    good, bad = _judge_with("Beads (10 per child), Chalk", uses=["Beads (10 per child)"])
    assert bad == {} and "A" in good
    good, bad = _judge_with("Number cards 1-10, Beads", uses=["Number cards 1-10"])
    assert bad == {}


def test_a_use_may_run_over_several_pieces_of_the_list_each_run_inside_one_piece():
    assert _judge_with("Beads, Number cards 1-10", uses=["Beads and number cards"])[1] == {}
    assert _judge_with("Beads, Number cards 1-10", uses=["Beads cards"])[1] == {}


def test_a_use_with_a_word_the_list_does_not_have_is_still_refused_naming_the_use():
    assert "uses 'Beads and rope'" in _judge_with("Beads, Number cards 1-10", uses=["Beads and rope"])[1]["A"]
    assert "uses" in _judge_with("Beads", uses=["Rope"])[1]["A"]


def test_the_verb_a_step_starts_with_is_not_a_prop_whatever_the_lists_of_other_pages_end_in():
    # another page's list ends in "draw"/"place": a step "Draw ..." / "Place ..." names no prop
    assert _judge_with("Beads", steps=["Draw a circle.", "Place the beads in it."])[1] == {}


def test_a_word_of_the_language_that_ends_a_list_piece_is_not_a_prop():
    # "Pictures to cut out" is a clause of the list, not the name of a thing
    assert fmt.vocabulary(["Cards for the, Pictures to cut out"], ["for", "the", "out", "to"]) == {"card"}
    toks = fmt.vocabulary(["Chart paper, markers as needed"], ["as", "needed"])
    assert toks == {"paper", "marker"}


def test_a_prop_named_later_in_a_step_that_the_page_does_not_list_is_still_refused():
    rows = {"A": {"materials": "Beads"}, "B": {"materials": "Chalk"}}
    judge = fmt.judger(rows, fmt.vocabulary(["Beads", "Chalk"]), FMT, RULES)
    why = judge([page(steps=["Show the child some chalk."], uses=[])], {"A": WANT["A"]})[1]["A"]
    assert "chalk" in why and "materials" in why


def test_a_use_that_copies_a_listed_thing_with_commas_inside_its_brackets_is_found():
    good, bad = _judge_with(
        "Crayons (red, blue, green), Paper", steps=["Count the crayons."], uses=["Crayons (red, blue, green)"]
    )
    assert bad == {} and "A" in good


FW = ["the", "to", "at", "in", "a", "for", "as", "needed", "of", "and"]


def test_only_a_short_name_is_a_prop_a_clause_of_the_list_is_not():
    texts = ["Cards to point at, Things to feel, Place the blocks, Big box, Beads (10 per child)"]
    assert fmt.vocabulary(texts, FW, not_props=["thing", "big"]) == {"box", "bead"}
    assert fmt.vocabulary(["Markers as needed, Cards for the"], FW) == {"marker", "card"}


def test_a_name_ending_in_a_generic_word_keeps_the_word_before_it():
    assert fmt.vocabulary(["Puzzle pieces, Sorting items"], not_props=["piece", "item"]) == {
        "puzzle",
        "sorting",
    }


def test_a_prop_is_a_noun_that_names_a_material_on_enough_pages_of_the_band():
    texts = ["Rope", "Rope, Beads", "Rope, Chalk", "Beads"]
    assert fmt.vocabulary(texts, FW, min_pages=3) == {"rope"}
    assert fmt.vocabulary(texts, FW, min_pages=1) == {"rope", "bead", "chalk"}


def test_a_page_that_has_no_list_is_not_judged_by_the_word_check_the_checker_reads_its_steps():
    rows = {
        "A": {"materials": ""},
        "B": {"materials": "Chalk"},
        "C": {"materials": "Chalk"},
        "D": {"materials": "Chalk"},
    }
    rows["E"] = {"materials": "Beads"}
    vocab = fmt.vocabulary((r["materials"] for r in rows.values()), FW, min_pages=3)
    judge = fmt.judger(rows, vocab, FMT | {"function_words": FW}, RULES)
    step = ["Hand out the chalk."]
    assert judge([page(steps=step, uses=[])], {"A": WANT["A"]})[1] == {}
    assert "chalk" in judge([page(key="E", steps=step, uses=[])], {"E": WANT["A"]})[1]["E"]
