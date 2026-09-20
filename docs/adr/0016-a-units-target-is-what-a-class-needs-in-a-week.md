# 0016 — A unit's target is what a class needs in a week

Date: 2026-09-20
Status: accepted

## Context

W1 gate 2 asked for 50 approved items per skill set × difficulty, "or the unit's whole enumerable
universe, whichever is smaller" (ADR 0011). 50 was a proxy for "enough variety that no child repeats
a question and no two children share one".

W2's first scenario run measured the proxy against the real thing. `assemble.for_week` draws without
replacement across a whole class, so one week needs
`(children + spares_per_difficulty) × items_per_sheet` questions from a single unit. For the school's
class of 16 at 12 questions a sheet with 2 spares that is **216**. `SUB.2D.EXCH Medium` — one of the
richest units in the bank — held **159**, and three of sixteen children got no paper:

```
FAIL  a real class of sixteen gets sixteen different papers, not ten
      children=16  papers=13  questions_needed=216  questions_held=159  short=3
```

A dry fill of that same unit accepted 80 more items immediately, so 159 was not its ceiling. The
bank stopped at a round number that had nothing to do with what a classroom needs.

## Decision

A unit's target is `(bank.class_size + assemble.spares_per_difficulty) × assemble.items_per_sheet`,
from config rows — 216 today — and a unit whose band declares `min_items` keeps that floor, because
that number is its measured universe (ADR 0011). The three inputs are rows, so a school with 24
children in a class changes one row and the gate moves with it.

Where a unit's universe is smaller than a class needs, the class *cannot* have entirely different
papers from that unit in one week. That is arithmetic, not an engineering failure, and it is stated
rather than hidden: those units are named in `STATE.md`, and the choices are to widen the rung (a
pedagogy call, Aseem's) or to accept that some children in that band share questions for that week.

## Alternatives rejected

- **Leave the target at 50 and let `assemble` overlap children.** It breaks the property the school
  asked for first — a child's neighbour has different questions — and it breaks it silently.
- **Compute the target inside `assemble` at draw time.** The shortage would then surface as a teacher
  holding 13 papers for 16 children on a Friday morning. The bank is the place to be early.
- **A bigger round number (200, 500).** Same mistake with a larger constant: it would still have no
  relationship to a class register, and the next school with a different class size would inherit it.

## Consequences

- W1's gate 2 and the audit invariant "every unit meets its target" go red until the bank is filled
  to the new target. This is correct: the definition of done changed when W2 measured the need.
  Filling is free — the enumerator, no model — and runs as a background job.
- `engine bank coverage` now prints the target each unit is actually held to, and the goal for W1
  fails until every unit reaches it.

## Measured, after the fill (2026-09-20)

`bank.class_size = 16` seeded, every short unit filled by the enumerator — no model, no cost:
**12,633 live questions, 68 of 68 units at target.** Four of them could not reach 216 and recorded
their measured ceiling as `min_items`, which ADR 0011's evidence rule requires: a second fill that
accepts nothing new is the proof the number is the universe rather than where a run stopped.

Thirteen units now sit below what a class of sixteen needs, and every one of them is a Grade 1 rung
whose numbers genuinely run out:

| unit | holds | a class of 16 needs |
|---|---|---|
| `ADD.1D.WITHIN10` all four bands | 22–24 | 216 |
| `ADD.1D.BRIDGE10` Easy / Medium / Hard / Advance | 80 / 43 / 45 / 35 | 216 |
| `SUB.1D.WITHIN20` Easy / Medium / Hard / Advance | 107 / 54 / 44 / 40 | 216 |
| `MENTAL.BRIDGE_EQ` Easy | 145 | 216 |

"Adds within 10" has about two dozen distinct questions in the whole of arithmetic; no code makes
more. So for a Grade 1 class the engine **cannot** give sixteen children entirely different papers in
one week, and it must say so rather than print short ones. That is now a scenario of its own — *a
Grade 1 class is told the rung is too small, never handed short papers* — so the limitation is
machine-checked instead of discovered on a Friday morning.

The ways out are all the school's to choose, not the engine's: fewer questions per sheet for Grade 1
(`assemble.items_per_sheet` is a row and could be per band), a wider rung (Aseem's call), or accepting
that children in that band share some questions in a week. Until one is chosen, the shortfall is
reported by name.
