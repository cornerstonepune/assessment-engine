"""School rounding: a number exactly halfway rounds up, as children are taught. Python's own `round` sends
a half to the even neighbour (665 → 660), which printed wrong rounded numbers on estimate questions."""

import pytest

from engine.assess.rounding import half_up


@pytest.mark.parametrize(
    "n,to,want",
    [
        (665, 10, 670),
        (985, 10, 990),
        (64, 10, 60),
        (450, 100, 500),
        (850, 100, 900),
        (849, 100, 800),
        (1250, 100, 1300),
        (0, 10, 0),
    ],
)
def test_half_up_rounds_a_five_up(n, to, want):
    assert half_up(n, to) == want
