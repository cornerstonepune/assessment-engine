"""A named mistake is named for the operation it was made in (`core/mistake_names.py`). On the local copy."""

import os

import pytest

from engine.core import db, mistake_names

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def test_one_code_is_named_for_the_operation_of_its_question_or_of_its_skill():
    """2026-09-28, a live report: "763 children, 427 girls, how many boys? — wrote 1190" was called "Added instead
    of multiplying". It is a subtraction; the name is the subtraction's."""
    with db.connect() as conn:
        name_of = mistake_names.names(conn)
    assert name_of("M_WRONG_OP", op="-") == "Added instead of subtracting"
    assert name_of("M_WRONG_OP", op="-+") == "Added instead of subtracting", (
        "a two-step story: its first step"
    )
    assert name_of("M_WRONG_OP", op="*") == "Added instead of multiplying"
    assert name_of("M_WRONG_OP", skill="NUM.OPS.01") == "Subtracted instead of adding"
    assert name_of("M_FACT_PM10") == "Tens miscounted", "one name in every operation needs no operation"
    assert name_of("M_WRONG_OP") == "M_WRONG_OP", "never a guess at which one"
    assert name_of("M_NO_SUCH") == "M_NO_SUCH"


def test_what_the_school_does_about_a_mistake_is_the_one_for_its_operation():
    """Nimish, 2026-09-28: a report card "with clear actionables". The action is the school's own `repair_hint`, for
    the operation the mistake was made in — never one guessed across operations, and never written here."""
    with db.connect() as conn:
        hint_of = mistake_names.names(conn, "repair_hint")
        want = conn.execute(
            "select repair_hint from misconception where code = 'M_SMALL_FROM_LARGE' and op = '-'"
        ).fetchone()["repair_hint"]
    assert hint_of("M_SMALL_FROM_LARGE", op="-") == want and want
    assert hint_of("M_NOCARRY", skill="NUM.OPS.01").startswith("Place-value chart")
    assert hint_of("M_FACT_PM1") is None, "two operations, two hints: none is guessed"
    with pytest.raises(ValueError):
        mistake_names.names(conn, "description; drop table misconception")
