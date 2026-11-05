"""M1-17: a K2 child's growth (levels by month, first seen, last seen, a trend) and what is ready next (from confirmed
links only). Pure functions: no database. Every table below is worked out by hand."""

import datetime as dt

from engine.w3_read.k2_growth import growth, ready_next

D = dt.date


def test_growth_of_nothing_is_nothing():
    assert growth([], min_months=2) is None


def test_one_month_shows_its_level_and_days_and_no_trend():
    g = growth([(D(2026, 10, 5), 1), (D(2026, 10, 19), 2), (D(2026, 10, 19), 1)], min_months=2)
    assert g["first_seen"] == D(2026, 10, 5) and g["last_seen"] == D(2026, 10, 19)
    # the highest level reached in the month; days = different days seen, not marks
    assert g["by_month"] == [{"month": "2026-10", "level": 2, "days": 2}]
    assert g["trend"] == "too_few"


def test_trend_compares_the_latest_two_months_seen_and_a_gap_month_is_a_gap_not_a_zero():
    seen = [(D(2026, 8, 3), 1), (D(2026, 10, 7), 3)]  # nothing in September
    g = growth(seen, min_months=2)
    assert [m["month"] for m in g["by_month"]] == ["2026-08", "2026-10"]
    assert g["trend"] == "up"


def test_steady_and_down():
    assert growth([(D(2026, 9, 1), 2), (D(2026, 10, 1), 2)], min_months=2)["trend"] == "steady"
    assert growth([(D(2026, 9, 1), 3), (D(2026, 10, 1), 1)], min_months=2)["trend"] == "down"


def test_only_the_latest_two_months_decide_the_trend():
    seen = [(D(2026, 7, 1), 0), (D(2026, 8, 1), 3), (D(2026, 9, 1), 2), (D(2026, 10, 1), 2)]
    assert growth(seen, min_months=2)["trend"] == "steady"


def test_months_needed_is_a_parameter_not_a_constant():
    seen = [(D(2026, 9, 1), 1), (D(2026, 10, 1), 2)]
    assert growth(seen, min_months=3)["trend"] == "too_few"


def test_input_order_does_not_matter():
    a = [(D(2026, 9, 1), 1), (D(2026, 10, 1), 3), (D(2026, 8, 1), 0)]
    assert growth(a, min_months=2) == growth(list(reversed(a)), min_months=2)


# ---- ready next: confirmed links only; a missing observation is never "not ready" ----

DONE = {"secure"}


def link(skill, before, strength="hard"):
    return {"skill": skill, "before": before, "strength": strength}


def test_a_skill_is_ready_when_every_hard_link_before_it_is_done():
    out = ready_next([link("B", "A")], {"A": "secure"}, DONE)
    assert [r["skill"] for r in out] == ["B"]
    assert out[0]["because"] == [{"before": "A", "strength": "hard"}]


def test_secure_to_recheck_is_not_done():
    assert ready_next([link("B", "A")], {"A": "secure_to_recheck"}, DONE) == []


def test_a_before_skill_not_seen_means_not_listed_and_nothing_says_not_ready():
    # absent from the answer is all it is: the function has no "not ready" output at all
    assert ready_next([link("B", "A")], {}, DONE) == []


def test_all_hard_links_must_be_done_soft_ones_need_not_be():
    links = [link("C", "A"), link("C", "B"), link("C", "S", "soft")]
    assert ready_next(links, {"A": "secure"}, DONE) == []
    out = ready_next(links, {"A": "secure", "B": "secure"}, DONE)
    assert [r["skill"] for r in out] == ["C"]
    assert [b["before"] for b in out[0]["because"]] == ["A", "B"]  # only what is done is cited


def test_only_soft_links_need_one_done_before_to_be_ready():
    assert ready_next([link("B", "A", "soft")], {}, DONE) == []
    assert [r["skill"] for r in ready_next([link("B", "A", "soft")], {"A": "secure"}, DONE)] == ["B"]


def test_a_skill_already_done_is_not_next_and_one_in_progress_still_is():
    links = [link("B", "A")]
    assert ready_next(links, {"A": "secure", "B": "secure"}, DONE) == []
    assert [r["skill"] for r in ready_next(links, {"A": "secure", "B": "practising"}, DONE)] == ["B"]


def test_a_skill_with_no_link_is_never_listed():
    assert ready_next([], {"A": "secure"}, DONE) == []


def test_answer_is_in_a_stable_order():
    links = [link("Z", "A"), link("M", "A")]
    assert [r["skill"] for r in ready_next(links, {"A": "secure"}, DONE)] == ["M", "Z"]
