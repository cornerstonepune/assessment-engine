"""Stories with × and ÷ in anyone's words → their case, place and one-step answer (goals/md4d2b1-times-story-shape.yaml,
`w1_bank/story_shape.py`). Jev is stood in for; the database is the local copy, rolled back."""

import json
import os
import re

import pytest
from typer.testing import CliRunner

from engine import cli
from engine.assess import words as W
from engine.core import db
from engine.w1_bank import story_shape as S

DB = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
SEED = db.REPO_ROOT / "supabase" / "seed"
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?!\w)")


def _story_cases(taxonomy):
    return {
        code
        for code, c in CASES.items()
        if c["taxonomy"] == taxonomy and isinstance(c["match"], dict) and "structure" in c["match"]
    }


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _saying(best, p=0.9):
    asked = []

    def ask(conn, purpose, state, options, version=None):
        asked.append((version, state, dict(options)))
        rest = [o for o in options if o != best]
        return {"choice": best, "ranked": [(best, p)] + [(o, (1 - p) / len(rest)) for o in rest]}

    return ask, asked


def _worked_here(case, text):
    """The answer a one-step story asks, worked by this test from the case's own row alone: × the two numbers, ÷ the
    larger by the smaller, used as the case says; twice and half the one number printed; None where it is not one
    step or prints more numbers than its question needs."""
    m = CASES[case]["match"]
    ns = [int(n.replace(",", "")) for n in NUMBER.findall(text)]
    if m["fmt"] != "word_1step":
        return None, None
    if m["structure"] in ("TWICE_AS_MANY", "HALF_AS_MANY") and len(ns) == 1:
        ns.append(2)
    if len(ns) != 2:
        return None, None
    if m["operation"] == "MUL":
        return ns[0] * ns[1], None
    q, r = divmod(max(ns), min(ns))
    use = m.get("remainder_use")
    assert bool(r) == bool(use), f"{case} {'needs' if use else 'leaves no'} remainder: {text}"
    return {
        None: (q, None),
        "ROUND_DOWN": (q, None),
        "ROUND_UP": (q + 1, None),
        "REMAINDER_ASKED": (r, None),
        "BOTH_ASKED": (q, r),
    }[use]


def test_every_times_story_in_the_gold_has_the_answer_worked_here_apart_from_the_engine():
    """The gold checks itself before any model is held to it, and the engine's own working agrees with it: a story
    filed under a case of the wrong operation, or of the wrong use of what is left over, fails here."""
    times = [g for g in S.gold() if CASES[g["case"]]["taxonomy"] == "MUL_DIV"]
    assert times, "the gold holds × and ÷ stories"
    for g in times:
        assert g["shape"] == CASES[g["case"]]["match"]["structure"], g["text"]
        want = _worked_here(g["case"], g["text"])
        assert (g.get("answer"), g.get("remainder")) == want, g["text"]
        assert S.worked(CASES[g["case"]]["match"], g["text"]) == want, g["text"]


def test_every_times_story_case_has_three_gold_stories_in_words_no_template_uses():
    gold = S.gold()
    held = {c: sum(g["case"] == c for g in gold) for c in _story_cases("MUL_DIV")}
    assert all(n >= 3 for n in held.values()), {c: n for c, n in held.items() if n < 3}
    assert {g["case"] for g in gold} <= _story_cases("ADD_SUB") | _story_cases("MUL_DIV")
    assert [g["text"] for g in gold if W.template_of(g["text"])] == []
    assert len({g["text"] for g in gold}) == len(gold), "no story twice"


def test_the_new_version_waits_for_its_eval_and_reads_both_taxonomies():
    """Rule 7: a new prompt version is scored before it is made active."""
    rows = [
        r for r in json.loads((SEED / "prompts.json").read_text())["prompts"] if r["purpose"] == S.PURPOSE
    ]
    by = {r["version"]: r for r in rows}
    assert by[1]["active"] and not by[2]["active"]
    assert by[2]["json_schema"] == {"type": "choice", "taxonomies": ["ADD_SUB", "MUL_DIV"]}
    assert "taxonomies" not in by[1]["json_schema"], "v1 reads + and − alone, as it was scored"


@DB
def test_the_new_version_offers_every_story_case_each_with_the_engines_own_stories(conn):
    """Nimish: "You should really deep dive into Jev and potentially figure out all the use cases that we can integrate
    and start doing that." Version 2 offers each story case of both taxonomies once, under a name of its own where two
    cases share a shape; each is shown with every one of the engine's own stories of it."""
    ask, asked = _saying("EQUAL_GROUPS")
    S.name(
        conn,
        "A baker puts 6 buns on each tray. She fills 8 trays. How many buns has she baked?",
        ask,
        version=2,
    )
    version, _, options = asked[0]
    assert version == 2
    assert len(options) == len(_story_cases("ADD_SUB") | _story_cases("MUL_DIV")) == 45
    assert {
        "GROUPING",
        "GROUPING_ROUND_DOWN",
        "GROUPING_ROUND_UP",
        "GROUPING_REMAINDER_ASKED",
        "GROUPING_BOTH_ASKED",
        "ARRAY_MUL",
        "ARRAY_DIV",
        "RATE_TOTAL",
        "RATE_TOTAL_TABLE_OR_CHART",
        "EXTRA_INFORMATION",
        "EXTRA_INFORMATION_MUL",
        "JOIN_RESULT",
    } <= set(options)
    assert "rickshaw" in options["GROUPING_ROUND_UP"] and "left over" not in options["GROUPING_ROUND_UP"]
    assert "Pen" in options["RATE_TOTAL_TABLE_OR_CHART"] and "Pen" not in options["RATE_TOTAL"]
    assert "twice as many" in options["TWICE_AS_MANY"]
    assert all(". Stories of this shape: " in m for m in options.values())

    ask, asked = _saying("JOIN_RESULT")
    S.name(conn, "Kiran had 23 shells and found 17 more. How many shells now?", ask)
    v1 = asked[0][2]
    assert set(v1) == {CASES[c]["match"]["structure"] for c in _story_cases("ADD_SUB")}, (
        "v1 offers what it did"
    )
    assert "×" not in "".join(v1.values()) and "mangoes" not in v1["EXTRA_INFORMATION"]


@DB
def test_a_times_story_in_an_educators_words_is_placed_and_its_answer_is_codes(conn):
    """Nimish: "Have the mapping that you've created now and build the whole platform accordingly for multiplication."
    Jev chooses the case; the place, the answer and what is left over are code's."""

    def named(best, text):
        return S.name(conn, text, _saying(best)[0], version=2)

    got = named(
        "EQUAL_GROUPS", "A baker puts 6 buns on each tray. She fills 8 trays. How many buns has she baked?"
    )
    assert (got["shape"], got["case"], got["how"], got["answer"], got["remainder"]) == (
        "EQUAL_GROUPS",
        "B01",
        "jev",
        48,
        None,
    )
    assert got["placed"], "a case some level names sits on that skill set and level"
    vans = named(
        "GROUPING_ROUND_UP", "35 children go on a picnic. Each van carries 8 children. How many vans?"
    )
    assert (vans["shape"], vans["case"], vans["answer"]) == ("GROUPING", "B15", 5)
    both = named(
        "GROUPING_BOTH_ASKED", "Dadi has 40 diyas in rows of 6. How many full rows, and how many left?"
    )
    assert (both["case"], both["answer"], both["remainder"]) == ("B17", 6, 4)
    half = named(
        "HALF_AS_MANY", "Sameer has 48 marbles. His brother has half as many. How many has his brother?"
    )
    assert (half["case"], half["answer"]) == ("B27", 24)
    two = named("MULTIPLY_THEN_ADD", "Priya buys 4 packs of 6 juice boxes and 3 more. How many juice boxes?")
    assert (two["case"], two["answer"]) == ("B18", None), "a two-step answer is not code's to guess"


@DB
def test_the_numbers_hold_a_times_reading_to_account(conn):
    """A remainder the numbers do not leave is not dropped: nothing is over, and the story is grouping exactly. A case
    that says nothing is over, read for numbers that leave some, is a person's: what the story does with them is not
    code's to guess. A one-step × question over three numbers has a number it does not need."""

    def named(best, text):
        return S.name(conn, text, _saying(best)[0], version=2)

    exact = named(
        "GROUPING_ROUND_DOWN", "A shopkeeper packs 48 eggs into trays of 6. How many trays can he fill?"
    )
    assert (exact["case"], exact["how"], exact["answer"]) == ("B03", "jev+code", 8)
    assert "nothing over" in exact["why"]
    over = named("GROUPING", "Papa ties 47 sticks into bundles of 5. How many bundles does he make?")
    assert over["case"] is None and "2 over" in over["why"] and over["ranked"][0][0] == "GROUPING"
    share = named("SHARING", "Mother divides 37 grapes equally between 4 bowls. How many go in each bowl?")
    assert share["case"] is None and "1 over" in share["why"]
    extra = named("EQUAL_GROUPS", "Aman is 9 years old. He buys 3 packets of 6 stickers. How many stickers?")
    assert (extra["shape"], extra["case"], extra["how"], extra["answer"]) == (
        "EXTRA_INFORMATION",
        "B25",
        "jev+code",
        None,
    )
    plus = named(
        "JOIN_RESULT", "Aisha is 8 years old. She has 34 red beads and 27 blue beads. How many beads?"
    )
    assert plus["case"] == "W25", "the + and − story with a number it does not need is still + and −'s"


@DB
def test_the_engines_own_times_story_is_named_by_its_template_and_jev_is_not_asked(conn):
    ask, asked = _saying("GROUPING")
    got = S.name(
        conn,
        "50 laddoos are packed into boxes, 6 in each box. How many laddoos are left over?",
        ask,
        version=2,
    )
    assert asked == [] and (got["case"], got["how"], got["answer"]) == ("B16", "template", 2)


@DB
def test_the_eval_scores_the_version_it_names_on_the_stories_that_version_reads(conn):
    """A reader that names every gold story's case scores all 146 under v2 with every one-step answer right; under
    v1 the eval reads the 65 + and − stories alone, which is what v1's bar was set on."""
    gold = {g["text"]: g["case"] for g in S.gold()}

    def perfect(conn, purpose, state, options, version=None):
        label = CASES[gold[state["story"]]]["label"]
        best = next(k for k, v in options.items() if v.startswith(label + ". "))
        return {"choice": best, "ranked": [(best, 0.99)]}

    v2 = S.evaluate(conn, ask=perfect, version=2)
    assert (v2["n"], v2["right"], v2["left"], v2["wrong_answer"]) == (146, 146, 0, 0), v2["misses"]
    assert v2["keyed"] == sum(1 for g in S.gold() if "answer" in g)
    v1 = S.evaluate(conn, ask=perfect, version=1)
    assert (v1["n"], v1["right"]) == (65, 65)


def test_engine_eval_scores_the_story_reader_version_it_is_given(monkeypatch):
    seen = {}
    result = {
        "misses": [],
        "named": 1,
        "n": 1,
        "right": 1,
        "keyed": 0,
        "wrong_answer": 0,
        "left": 0,
        "unanswered": 0,
    }

    def scored(conn, **kw):
        seen.update(kw)
        return result

    monkeypatch.setattr(cli.story_shape, "evaluate", scored)
    monkeypatch.setattr(cli.db, "connect", _no_database)
    monkeypatch.setattr(cli, "_held", lambda purpose, score: None)
    CliRunner().invoke(cli.app, ["eval", "story_shape", "--version", "2"])
    assert seen == {"version": 2}


class _no_database:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def commit(self):
        pass


@DB
def test_a_case_row_whose_match_does_not_repeat_its_taxonomy_is_read_by_its_own(conn):
    """Found 2026-10-12 on live: its case rows were loaded before M1 wrote each one's taxonomy into its match as well,
    and reading the match's crashed both versions (KeyError 'taxonomy'). The row's own column says it."""
    conn.execute("update taxonomy_case set match = match - 'taxonomy' where jsonb_typeof(match) = 'object'")
    v1 = S.name(
        conn, "Kiran had 23 shells and found 17 more. How many shells now?", _saying("JOIN_RESULT")[0]
    )
    assert (v1["case"], v1["answer"]) == ("W01", 40)
    v2 = S.name(
        conn,
        "A baker puts 6 buns on each tray. She fills 8 trays. How many buns has she baked?",
        _saying("EQUAL_GROUPS")[0],
        version=2,
    )
    assert (v2["case"], v2["answer"]) == ("B01", 48)
