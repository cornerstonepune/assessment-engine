"""A K2 spoken note read by code from its typed transcript (engine/w3_read/voice_note.py, goals/m1-01-voice-intake.yaml).

Every transcript here is typed, with placeholder numbers: no school data, no audio (D-056).
"""

import json

import pytest

from engine.core import settings
from engine.w3_read import voice_note as vn

PLAIN = (
    "Activity number 12. Above: 3, 7 and 19. Below: none. Not willing: 4. Absent: twenty one. "
    "The rest did as expected. 4 shared the sand tray with everyone."
)


def numbers(draft, section):
    line = draft.line(section)
    return line.numbers if line else None


def test_the_template_is_read_into_one_line_per_section_each_beside_its_own_words():
    d = vn.read(PLAIN)
    assert not d.blocked
    assert [x.section for x in d.lines] == [
        "activity",
        "above",
        "below",
        "not_willing",
        "absent",
        "rest",
        "sentence",
    ]
    assert numbers(d, "activity") == (12,)
    assert numbers(d, "above") == (3, 7, 19)
    assert numbers(d, "below") == ()
    assert numbers(d, "not_willing") == (4,)
    assert numbers(d, "absent") == (21,)
    assert d.line("rest").said
    assert d.line("sentence").text == "4 shared the sand tray with everyone"
    assert d.line("above").words == "Above: 3, 7 and 19"
    assert d.line("absent").words == "Absent: twenty one"
    for line in d.lines:  # each line's words are the transcript's own, in place
        assert line.words in PLAIN


def test_hindi_number_words_are_read_in_latin_letters_and_in_devanagari_and_devanagari_digits_too():
    d = vn.read("Activity 4. Above teen, saat, unnees. Below सत्रह, बीस. Absent १२.")
    assert not d.blocked, d.problems
    assert numbers(d, "above") == (3, 7, 19)
    assert numbers(d, "below") == (17, 20)
    assert numbers(d, "absent") == (12,)


def test_a_number_said_twice_is_one_child_and_the_educator_is_told():
    d = vn.read("Activity 2. Above seven, seven, 9.")
    assert numbers(d, "above") == (7, 9)
    assert "7 said more than once" in d.line("above").notes
    assert not d.blocked


def test_a_number_corrected_aloud_is_replaced_and_the_correction_is_shown():
    d = vn.read("Activity 2. Above twelve, no, thirteen. Below 5, sorry, 6.")
    assert numbers(d, "above") == (13,)
    assert numbers(d, "below") == (6,)
    assert "12 corrected to 13" in d.line("above").notes
    assert not d.blocked


def test_one_seven_is_two_numbers_never_seventeen():
    assert numbers(vn.read("Activity 1. Above one seven."), "above") == (1, 7)


def test_an_unclear_or_misheard_word_is_could_not_read_and_blocks_confirm():
    d = vn.read("Activity 3. Above 3, sebben, 8. Below 4.")
    line = d.line("above")
    assert line.numbers == (3, 8)
    assert line.problems == ("could not read 'sebben'",)
    assert d.blocked


def test_filler_words_are_not_problems():
    d = vn.read("Umm, activity number 6. Above, uh, roll number 3 and 5. Absent: child 9.")
    assert not d.blocked, (d.problems, [x.problems for x in d.lines])
    assert numbers(d, "above") == (3, 5)


def test_words_before_the_template_starts_are_could_not_read():
    d = vn.read("Good morning. Activity 6. Above 3.")
    assert "could not read 'Good'" in d.problems and d.blocked


def test_no_activity_number_blocks_confirm():
    d = vn.read("Above 3, 5. The rest did as expected.")
    assert "could not read: no activity number" in d.problems


def test_two_activity_numbers_block_confirm():
    d = vn.read("Activity 6, 7. Above 3.")
    assert d.line("activity").problems == ("one number expected, heard 6, 7",)


def test_a_heading_with_nothing_after_it_is_could_not_read_but_none_is_an_answer():
    d = vn.read("Activity 1. Below. Absent nobody.")
    assert d.line("below").problems == ("could not read: no number heard",)
    assert d.line("absent").numbers == () and not d.line("absent").problems


def test_none_and_numbers_together_block_confirm():
    d = vn.read("Activity 1. Below none, 4.")
    assert "said none, and numbers too" in d.line("below").problems


def test_a_correction_with_nothing_after_it_blocks_confirm():
    d = vn.read("Activity 1. Above 3, no")
    assert "a correction with no number after it" in d.line("above").problems


def test_a_child_in_two_lists_blocks_confirm():
    d = vn.read("Activity 1. Above 3, 7. Not willing 7.")
    assert "7 is in both above and not willing" in d.problems


def test_a_heading_said_twice_is_read_together():
    d = vn.read("Activity 1. Above 3. Below 4. Above 8.")
    assert numbers(d, "above") == (3, 8)
    assert "'above' said twice: read together" in d.line("above").notes


def test_a_note_that_starts_with_incident_is_an_incident_and_is_never_read_for_lists():
    d = vn.read("Incident. 10:30, number 5 fell near the slide, above the knee; the coordinator was told.")
    assert d.kind == "incident"
    assert [x.section for x in d.lines] == ["incident"]
    assert d.line("incident").text.startswith("10:30, number 5 fell")
    assert not d.blocked


def test_an_incident_said_inside_a_note_is_kept_apart_and_its_words_are_not_lists():
    d = vn.read("Activity 1. Above 3. Incident, 4 fell below the window.")
    assert d.kind == "observation"
    assert numbers(d, "above") == (3,)
    assert d.line("below") is None
    assert d.line("incident").text == "4 fell below the window"
    assert d.line("incident").notes


def test_the_one_sentence_she_saw_has_no_heading_and_follows_the_last_list_after_a_full_stop():
    d = vn.read("Activity 6. Below 2. Not willing 9. He sang the whole song to 4.")
    assert numbers(d, "not_willing") == (9,)
    assert d.line("sentence").text == "He sang the whole song to 4"
    assert not d.blocked


def test_a_list_carried_into_a_second_sentence_stays_a_list():
    d = vn.read("Activity 6. Absent 2. 8 and 11.")
    assert numbers(d, "absent") == (2, 8, 11)
    assert d.line("sentence") is None


def test_a_sentence_run_into_a_list_with_no_full_stop_is_could_not_read_never_guessed():
    d = vn.read("Activity 6. Absent 2 she was kind to 4")
    assert d.blocked
    assert "could not read 'kind'" in d.line("absent").problems


def test_after_the_rest_did_as_expected_every_word_is_the_sentence():
    d = vn.read("Activity 1. Above 3. The rest did as expected. They were unafraid of the paint")
    assert d.line("rest").said and not d.line("rest").problems
    assert d.line("sentence").text == "They were unafraid of the paint"


def test_the_rest_did_as_expected_is_read_and_it_gives_its_children_as_expected():
    assert vn.read("Activity 1. The rest did as expected.").line("rest").said
    assert vn.template().outcomes["rest"] == "as_expected"


def test_nothing_is_ticked_a_draft_holds_no_confirmation():
    fields = {f for f in vn.Line.__dataclass_fields__} | {f for f in vn.Draft.__dataclass_fields__}
    assert not {"confirmed", "ticked", "accepted"} & fields


SEED = json.loads((settings.SEED / "voice_template.json").read_text())["template"]


@pytest.mark.parametrize("n, words", sorted(SEED["number_words"].items(), key=lambda kv: int(kv[0])))
def test_every_number_word_in_the_rows_reads_as_its_number(n, words):
    for w in words:
        assert numbers(vn.read(f"Activity 1. Above {w}."), "above") == (int(n),), w


def test_no_number_word_means_two_numbers_and_no_heading_is_a_number():
    seen = {}
    for n, words in SEED["number_words"].items():
        for w in words:
            assert seen.setdefault(w, n) == n, f"'{w}' is both {seen[w]} and {n}"
    headings = {w for s in SEED["sections"] for w in s["words"]}
    assert not headings & set(seen)


def test_the_forms_levels_are_kept_as_rows_with_no_mapping_written():
    assert SEED["form_levels"]["words"] == ["Level 1", "Level 2", "Level 3", "Not Attended"]
    assert SEED["form_levels"]["mapping_to_outcomes"] is None


def test_the_template_is_rows_a_new_heading_is_an_insert():
    rows = json.loads(json.dumps(SEED))
    next(x for x in rows["sections"] if x["code"] == "above")["words"].append(
        "upar"
    )  # a Hindi heading, if the school adds one: a row, no code
    d = vn.read("Activity 1. Upar 3.", vn.template_from(rows))
    assert numbers(d, "above") == (3,)


def test_the_level_she_expected_is_read_after_the_activity_and_defaults_to_its_row():
    tpl = vn.template()
    d = vn.read("Activity 2, level 3. Above 4.")
    assert d.line("activity").numbers == (2,) and d.expected_level(tpl) == 3 and not d.blocked
    assert vn.read("Activity 2. Above 4.").expected_level(tpl) == tpl.default_level == 2
    assert "level 5 is not a level (0, 1, 2, 3)" in vn.read("Activity 2 level 5. Above 4.").problems
