"""The maker drafts, code checks, a stronger checker reads it against the school's words only, the maker revises once
(goals/m1-12a-page-format.yaml, task M1-12a).

Nimish, 2026-11-05: "strong maker-checker". The pure parts here, with a stand-in for each model.
"""

from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_check as chk
from engine.w1_bank import k2_format as fmt

FMT = {
    "steps_max": 8, "step_words": 14, "slips_min": 1, "slips_max": 4, "keyword_words_min": 2,
    "keyword_words_max": 4, "spot_words": 20, "idea_words": 25, "always_there": ["child", "educator"],
}  # fmt: skip
ROWS = {"A": {"materials": "Beads, Rope"}, "B": {"materials": "Beads"}}
JUDGE = fmt.judger(ROWS, fmt.vocabulary(r["materials"] for r in ROWS.values()), FMT, None)
PARTS = ["steps", "thinking"]
WANT = {"A": PARTS, "B": PARTS}


def made(key, steps=("Show the beads.",), idea="Touch each bead once."):
    return {"key": key, "steps": list(steps), "uses": ["Beads"], "idea": idea,
            "slips": [{"keyword": "counts twice", "spot": "Finger goes back."}]}  # fmt: skip


class Models:
    """A maker and a checker that answer from lists, and remember what they were asked."""

    def __init__(self, drafts, verdicts):
        self.drafts, self.verdicts = list(drafts), list(verdicts)
        self.maker_asked, self.checker_asked = [], []

    def maker(self, keys, revise):
        self.maker_asked.append((list(keys), revise))
        return [d for d in self.drafts.pop(0) if d["key"] in keys]

    def checker(self, keys, drafts):
        self.checker_asked.append((list(keys), {k: drafts[k] for k in keys}))
        return [v for v in self.verdicts.pop(0) if v["key"] in keys]


def verdict(key, *faults):
    return {"key": key, "verdict": "disagree" if faults else "agree",
            "faults": [{"part": p, "reason": r} for p, r in faults]}  # fmt: skip


def go(models, want=WANT):
    return chk.run(want, models.maker, models.checker, JUDGE, size=4, rounds=1)


def test_a_page_the_checker_agrees_with_costs_one_maker_call_and_one_check_call():
    m = Models([[made("A"), made("B")]], [[verdict("A"), verdict("B")]])
    res = go(m)
    assert len(m.maker_asked) == 1 and len(m.checker_asked) == 1
    assert {k: v[0] for k, v in res.verdicts.items()} == {"A": "agree", "B": "agree"}
    assert res.history["A"] == [{"round": 1, "verdict": "agree", "faults": []}]


def test_a_fault_goes_back_to_the_maker_once_with_the_reason_and_the_page_is_checked_again():
    m = Models(
        [[made("A"), made("B")], [made("A", steps=("Show the beads and rope.",))]],
        [[verdict("A", ("steps", "Rope is not in the materials")), verdict("B")], [verdict("A")]],
    )
    res = go(m)
    keys, revise = m.maker_asked[1]
    assert keys == ["A"], "only the page with a fault is asked again"
    assert revise["A"][1] == [{"part": "steps", "reason": "Rope is not in the materials"}]
    assert res.parts["A"]["steps"] == ["Show the beads and rope."], "the revision replaces the faulty part"
    assert res.parts["A"]["thinking"]["idea"] == "Touch each bead once.", (
        "a part with no fault is kept as it was"
    )
    assert res.verdicts["A"][0] == "agree" and [h["round"] for h in res.history["A"]] == [1, 2]
    assert m.checker_asked[1][0] == ["A"]


def test_a_second_fault_is_not_sent_back_again_the_page_stays_with_the_reason():
    m = Models(
        [[made("A")], [made("A", steps=("Show the rope.",))]],
        [[verdict("A", ("steps", "one"))], [verdict("A", ("steps", "two"))]],
    )
    res = go(m, {"A": PARTS})
    assert len(m.maker_asked) == 2 and len(m.checker_asked) == 2, "one revision, never a second"
    assert res.verdicts["A"] == ("disagree", [{"part": "steps", "reason": "two"}])
    assert [h.get("faults") for h in res.history["A"]] == [
        [{"part": "steps", "reason": "one"}],
        [{"part": "steps", "reason": "two"}],
    ]


def test_a_revision_that_breaks_the_format_leaves_the_first_draft_with_the_checkers_reason():
    too_many = tuple(f"Step {i}." for i in range(9))
    m = Models([[made("A")], [made("A", steps=too_many)]], [[verdict("A", ("steps", "bad"))]])
    res = go(m, {"A": PARTS})
    assert res.parts["A"]["steps"] == ["Show the beads."]
    assert res.verdicts["A"][0] == "disagree" and len(m.checker_asked) == 1
    assert "revision refused" in res.history["A"][-1]["note"] and "9 lines" in res.history["A"][-1]["note"]


def test_the_checker_is_shown_each_draft_and_nothing_the_maker_said_about_itself():
    m = Models([[made("A") | {"confidence": 0.9, "reason": "I relied on X"}]], [[verdict("A")]])
    go(m, {"A": PARTS})
    shown = m.checker_asked[0][1]["A"]
    assert "confidence" not in shown and "reason" not in shown and "uses" not in shown


def test_the_money_stopping_during_the_revision_keeps_what_is_good():
    def maker(keys, revise):
        if revise:
            raise batch.Stop("the campaign has no money left")
        return [made("A")]

    m = Models([], [[verdict("A", ("steps", "x"))]])
    res = chk.run({"A": PARTS}, maker, m.checker, JUDGE, size=4, rounds=1)
    assert res.stopped == "the campaign has no money left" and res.parts["A"]["steps"] == ["Show the beads."]
    assert res.verdicts["A"][0] == "disagree"


def test_what_the_checker_says_is_read_item_by_item():
    good, bad = chk.judge_checks(
        [
            verdict("A"),
            {"key": "B", "verdict": "agree", "faults": [{"part": "steps", "reason": "r"}]},
            {"key": "C", "verdict": "disagree", "faults": []},
            {"key": "D", "verdict": "maybe"},
            {
                "key": "E",
                "verdict": "disagree",
                "faults": [{"part": "colour", "reason": "r"}, "x", {"part": "steps"}],
            },
        ],
        ["A", "B", "C", "D", "E", "F"],
    )
    assert good["A"] == ("agree", [])
    assert good["B"][0] == "disagree", "an agree that names a fault is a disagree"
    assert good["C"][0] == "disagree" and good["C"][1][0]["reason"], "a disagree always says why"
    assert good["E"][0] == "disagree" and good["E"][1][0]["reason"], (
        "faults that name no page part are not kept"
    )
    assert bad == {"D": "verdict is not agree or disagree", "F": "missing from the reply"}


def test_a_page_asked_again_asks_only_for_the_parts_at_fault():
    assert chk.parts_at_fault(
        [{"part": "steps", "reason": "r"}, {"part": "level_1", "reason": "r"}], ["steps", "thinking"]
    ) == ["steps"]
    assert chk.parts_at_fault([{"part": "level_1", "reason": "r"}], ["steps", "thinking"]) == [
        "steps",
        "thinking",
    ]


def test_a_checker_reply_missing_a_key_is_asked_for_again():
    m = Models([[made("A")]], [[], [verdict("A")]])
    res = go(m, {"A": PARTS})
    assert res.verdicts["A"][0] == "agree" and len(m.checker_asked) == 2


def test_a_second_checker_reads_the_same_first_drafts_and_its_verdict_never_drives_the_revision():
    seen = []

    def shadow(keys, drafts):
        seen.append({k: drafts[k] for k in keys})
        return {"verdicts": [verdict("A"), verdict("B", ("steps", "the second checker's own fault"))]}

    m = Models(
        [[made("A"), made("B")], [made("A", steps=("Show the rope.",))]],
        [[verdict("A", ("steps", "one")), verdict("B")], [verdict("A")]],
    )
    res = chk.run(WANT, m.maker, m.checker, JUDGE, size=4, rounds=1, shadows={"b": shadow})
    assert len(seen) == 1 and seen[0]["A"]["steps"] == ["Show the beads."], (
        "the first drafts, before any revision"
    )
    assert res.shadow["b"]["A"][0] == "agree" and res.shadow["b"]["B"][0] == "disagree"
    assert m.maker_asked[1][0] == ["A"], "only the first checker's fault sends a page back"
    assert res.verdicts["B"][0] == "agree" and res.verdicts["A"][0] == "agree"


def test_the_money_stopping_during_the_second_checker_keeps_the_first_checkers_verdicts():
    def shadow(keys, drafts):
        raise batch.Stop("the campaign has no money left")

    m = Models([[made("A")]], [[verdict("A", ("steps", "x"))]])
    res = chk.run({"A": PARTS}, m.maker, m.checker, JUDGE, size=4, rounds=1, shadows={"b": shadow})
    assert res.stopped and res.verdicts["A"][0] == "disagree" and len(m.maker_asked) == 1, (
        "no revision after a stop"
    )


def test_kept_first_drafts_are_taken_once_and_the_pages_without_one_are_left_to_ask():
    reuse = {"A": made("A"), "C": made("C")}
    items, missing = chk.take_kept(reuse, ["A", "B"])
    assert [i["key"] for i in items] == ["A"] and missing == ["B"]
    assert list(reuse) == ["C"], (
        "a kept draft is used once: a page that fails the format is asked, not fed the same draft"
    )
