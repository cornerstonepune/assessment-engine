# ADR 0011 — a unit's target is its whole universe when that universe is under fifty

Date: 2026-09-19. Status: accepted. Amends `BUILD-ORDER.md` W1 gate 2.

## Decision

W1 gate 2 asked for at least 50 approved items in each of the 64 skill × difficulty units. That
target becomes **50, or the whole enumerable universe of the unit, whichever is smaller.**

A unit whose universe is smaller than 50 carries its own floor as `min_items` on its band in
`supabase/seed/skill_sets.json`; `bank.coverage` reads it and defaults to 50 when it is absent.
The floor is a row, not a branch in code, so gate 2 stays a single machine-checkable command.

A floor is only legitimate with evidence: a fresh `engine bank fill` against that unit must accept
**zero** new items, proving the count is the ceiling of what the rule can ever produce rather than
the point at which a run happened to stop. The seven floors set on 2026-09-19 were each measured
that way (`ADD.1D.WITHIN10` 24/42/30/24, `ADD.1D.BRIDGE10` 43/46/35).

## Why

"Adds within 10" contains roughly 40 usable (a, b) pairs once equal addends and multiples of ten
are excluded. Four difficulty bands each holding 50 *distinct* questions needs 200. The four
sampler formats can dress those 40 pairs about four ways, so the rung's true capacity is near 120
across all four bands, not 200. No amount of engineering changes this; it is a property of the
numbers, and it is worst at exactly the foundational rungs where the numbers are smallest.

The 50 was always a proxy for the thing that matters — enough variety that a child never repeats a
question and a class never shares one. At 24 to 46 items a band, with a 21-day exposure window and
16 children, that property still holds comfortably.

## Rejected

- **Widen R1's and R2's number ranges** so more questions exist. This redefines what those rungs
  teach — "within 10" stops meaning within 10 — and blurs R1 into R2. That is the ladder's own
  definition and Aseem's call, not a decision to take for the convenience of a number.
- **Make a word problem's story part of its identity**, so the same numbers can carry several
  different stories. This would close the gap honestly and is the most attractive of the three,
  but item identity today is (template, a, b, op); changing it rewrites the key of every word
  problem already stored and needs a migration plus a backfill. Worth revisiting if a later rung
  needs far more items than its numbers allow — the cost is a migration, not a redesign.
- **Leave the gate failing and move on anyway.** A gate that is permanently red teaches every
  future session to ignore it.

## Consequences

`bank.coverage` returns a `target` per unit and `engine bank coverage` prints "N units, M under
their target". Gate 2 closed on 2026-09-19 with 64 of 64 units at or above target, 3,373 live
items, and ₹0 of model spend. Any future unit that cannot reach 50 must show the zero-accept
evidence before its floor is written, or the floor is just a lowered bar.
