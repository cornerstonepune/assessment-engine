"""Regression test for the coverage gaps found by auditing blueprints against taxonomy §12.

Two holes existed until 2026-09-17: every regrouping rung above Grade 1 was generated in
columns only, and unequal-length operands were assessed nowhere but R9. Both are cases the
taxonomy names as distinct diagnostics. A child who can add in a column but cannot align
342 + 5 was invisible to every sheet the engine produced.

Reverting a blueprint slot would reopen the hole silently. This test is what stops that.
"""
import collections
import random

import pytest

from engine.assess import tags
from engine.assess.blueprints import BLUEPRINTS

REGROUPING_RUNGS = ["R4", "R5", "R6", "R9", "R10", "R12"]
SAMPLES = 10


@pytest.fixture(scope="module")
def observed():
    """Sample every blueprint slot and record which tag values actually appear per rung."""
    seen = collections.defaultdict(lambda: collections.defaultdict(set))
    for slots in BLUEPRINTS.values():
        rng = random.Random(42)
        for _label, fn in slots:
            for _ in range(SAMPLES):
                item = fn(rng)
                for dim, val in tags.derive(item).items():
                    if isinstance(val, list):
                        continue
                    seen[item.rung][dim].add(val)
    return seen


@pytest.mark.parametrize("rung", REGROUPING_RUNGS)
def test_rung_is_assessed_both_in_columns_and_horizontally(observed, rung):
    got = observed[rung]["presentation"]
    assert got == {"VERTICAL", "HORIZONTAL"}, (
        f"{rung} is only ever assessed as {got}. Horizontal-to-vertical conversion is a "
        f"distinct diagnostic case (taxonomy §4) with its own misconception."
    )


@pytest.mark.parametrize("rung", REGROUPING_RUNGS)
def test_rung_is_assessed_with_unequal_operand_lengths(observed, rung):
    got = observed[rung]["operand_order"]
    assert got - {"EQUAL_LENGTH"}, (
        f"{rung} only ever uses equal-length operands. Aligning a shorter number under the "
        f"ones (342 + 5) is a distinct diagnostic case (taxonomy §4)."
    )


def test_every_blueprint_slot_generates_without_error():
    rng = random.Random(7)
    for (band, level), slots in BLUEPRINTS.items():
        for label, fn in slots:
            for _ in range(SAMPLES):
                fn(rng)  # a RuntimeError here means a slot's constraints are unsatisfiable


def test_at_band_sheets_cover_more_than_one_regrouping_case(observed):
    """A sheet that only ever shows single regrouping cannot tell secure from lucky."""
    for rung in ("R9", "R10", "R12"):
        assert len(observed[rung]["regrouping"]) > 1, f"{rung} tests one regrouping case only"
