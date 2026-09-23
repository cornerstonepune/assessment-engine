"""School rounding (taxonomy §9): a number exactly halfway rounds up — 665 to 670, 850 to 900 — the rule
children are taught. Python's own `round` sends a half to the even neighbour (665 → 660), so it must never
make a number a child sees."""


def half_up(n: int, to: int) -> int:
    """`n` to the nearest multiple of `to`, a half rounding up. Whole numbers, `n` ≥ 0."""
    return (n + to // 2) // to * to
