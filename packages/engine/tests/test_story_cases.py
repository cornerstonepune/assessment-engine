"""Which of two story cases a story is, where its print tells them apart (`w1_bank/story_cases.py`,
goals/md4d2b5-story-told-apart.yaml). No database: the cases are given as the reader holds them."""

from engine.w1_bank import story_cases as SC

KNOWN = {
    "GROUPING": {
        "code": "B03",
        "match": {"taxonomy": "MUL_DIV", "structure": "GROUPING", "remainder": "NONE"},
    },
    "GROUPING_ROUND_UP": {
        "code": "B15",
        "match": {"taxonomy": "MUL_DIV", "structure": "GROUPING", "remainder_use": "ROUND_UP"},
    },
    "GROUPING_BY_EACH": {"code": "B24", "match": {"taxonomy": "MUL_DIV", "structure": "GROUPING_BY_EACH"}},
    "RATE_TOTAL": {"code": "B06", "match": {"taxonomy": "MUL_DIV", "structure": "RATE_TOTAL"}},
    "RATE_TOTAL_TABLE_OR_CHART": {
        "code": "B26",
        "match": {"taxonomy": "MUL_DIV", "structure": "RATE_TOTAL", "context": "TABLE_OR_CHART"},
    },
    "JOIN_RESULT": {"code": "W01", "match": {"taxonomy": "ADD_SUB", "structure": "JOIN_RESULT"}},
}
TOLD = {"GROUPING_BY_EACH": {"instead_of": "GROUPING", "words": ["each", "every"]}}


def test_a_list_is_a_colon_then_two_numbers_or_more_in_that_sentence():
    assert SC.listed("Price list: apple ₹20, banana ₹5. How much do 6 apples cost?")
    assert SC.listed(
        "Price list: Pen (₹) 6, Eraser (₹) 4. Use the price list. What do 48 pens cost, in rupees?"
    )
    assert not SC.listed(
        "At the stationery shop a ruler costs ₹12 and a sharpener ₹8. What do 4 sharpeners cost?"
    )
    assert not SC.listed("Note: a pen costs ₹15. What do 3 pens cost?"), (
        "one number after a colon is not a list"
    )


def test_each_or_every_names_the_grouping_that_means_divide_and_its_absence_the_other():
    every = "Every plant needs 5 litres of water. The gardener uses 40 litres. How many plants does he water?"
    bundles = "Papa ties 45 sticks into bundles of 5. How many bundles does he make?"
    assert SC.resolved(TOLD, KNOWN, "GROUPING", every) == "GROUPING_BY_EACH"
    assert SC.resolved(TOLD, KNOWN, "GROUPING_BY_EACH", bundles) == "GROUPING"
    assert SC.resolved(TOLD, KNOWN, "GROUPING_ROUND_UP", every) == "GROUPING_ROUND_UP", (
        "a remainder's case keeps it"
    )
    assert SC.resolved(TOLD, KNOWN, "JOIN_RESULT", every) == "JOIN_RESULT"


def test_the_pair_jev_split_is_summed_into_the_case_code_settles():
    every = "Every plant needs 5 litres of water. The gardener uses 40 litres. How many plants does he water?"
    got = SC.merged(TOLD, KNOWN, [("GROUPING", 0.54), ("GROUPING_BY_EACH", 0.46)], every)
    assert got == [("GROUPING_BY_EACH", 1.0)]
    canteen = "Canteen prices: idli ₹10 a plate, dosa ₹30 a plate. What do 3 plates of dosa cost?"
    got = SC.merged(TOLD, KNOWN, [("RATE_TOTAL", 0.71), ("RATE_TOTAL_TABLE_OR_CHART", 0.23)], canteen)
    assert got[0][0] == "RATE_TOTAL_TABLE_OR_CHART" and round(got[0][1], 2) == 0.94
