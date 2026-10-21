# The bank fills every level every time (W1, gate 3)

Goal: `goals/bank-fills-every-time.yaml`, proved by `bin/engine done bank-fills-every-time`.

## The problem

CI failed now and then on `tests/test_goal.py::test_every_invariant_holds`, "every unit meets its target": ADD.2D1D
Hard 172 of 175 on #235, SUB.3D2D Advance (case S33) while #234 was built. Main passed at the same commit. The bank is
built afresh for every CI run (`bin/testdb fresh`), and its draws use the operating system's randomness on purpose (a
top-up must find new questions, not retrace the first fill's), so two builds of the same code give different banks.

## Verified

Measured on 2026-10-21, on a database built from this repository alone (every migration, `engine load`), Postgres 16.
How each was run: a build is `bin/engine bank refill` on a fresh copy, then the levels short of their target listed
from `inventory.coverage`; "simulated" is the same order of levels drawn with `draw.level` (levels of cases) and
`bank.fill_native(dry_run=True)` (the rest), stored nowhere, as `tests/test_bank_fills.py::_fresh_build` does. The
proofs now are the commands at the end of this section.

**Twenty fresh builds of today's code** (`engine bank refill`, each about 5½ minutes): none left a level short. The
failure is rarer than one build in twenty here; CI met it at least twice. I can't give an exact rate from these runs.

**The same build, simulated** (every level of cases drawn in refill's order with one shared set of keys, stored
nowhere; the 32 levels made by their own generators drawn dry), with fewer random draws per question, to show which
levels lean on luck:

| draws a question gets | today's code: levels short | with the fix: levels short |
|---|---|---|
| 2000 (a real build) | none in seeds 100, 101 | none in seeds 0, 1 (before the × 10, 100, 1000 listing) |
| 200 (a tenth) | ADD.2D1D Hard 168 and 163 of 175; MUL.TENS Medium 167 and 176 of 216 (seeds 0, 1) | none (seeds 0, 1) |
| 50 (a fortieth) | ADD.2D1D Hard 145 of 175; ADD.3D1D Hard 156 of 216; SUB.3D1D Hard 170 of 216; MUL.TENS Easy 108, Medium 99, Hard 203 of 216; ADD.MANY Easy 88 of 216 | ADD.MANY Easy 94; MUL.TENS Easy 93, Medium 113 (all before the × 10/100/1000 listing below) |

**Why: the pools.** What each case can make at all (`draw.listed`), against what a fresh build asks of it:

| level(s) | case | can make | asked for |
|---|---|---|---|
| ADD.2D1D Hard, Advance | A14 / A15 / A16 | 45 / 45 / 90 (180 in all) | 75 / 75 / 75, for a level target of 175 |
| SUB.3D2D Hard, Advance | S33, "the answer becomes 1 digit" | 72 | 55 |
| SUB.3D1D Hard, Advance | S23 | 72 | 122 |
| ADD.3D1D Hard, Advance | A35 / A36 | 90 / 90 | 69 / 69 |
| MUL.TENS Medium | TP05, "× 100 of a number with a zero inside" | 162 | 54 |

A random draw for A14 (2-digit + 1-digit, the carry makes a 3-digit answer) hits one of its 45 sums once in 18 tries
(45 of the 810 pairs); the last one of A16's 90 turns up roughly once in 1,600 (an estimate, not measured). Each question is given 2000 tries, so the level filled
almost every time, and now and then its budget ran out a few short. The draws already ended on a list of every pair for
× and ÷ cases (`draw._rest`), but not for + and −, and not for × 10, 100 or 1000 itself, where listing by digit sizes
gives a million pairs. TP05 got 51 of its 54 even at the full budget; its level filled only because its other cases
made up the gap.

Drawn alone with **one** random draw a question, ADD.2D1D Hard got 4 to 14 of its 175 on today's code, and 175 with the
fix (five seeds each).

**A fresh build with the fix** (`engine bank refill` then `engine library build`, as `bin/testdb fresh` does): 5 min 59 s
(today's code: about 5 min 40 s), and `engine audit` says "ok every unit meets its target".

**Generators' own levels** (32 levels: tallies, estimates, budgets, cards…): 20 of 20 dry draws filled each, and the
worst of 50 used at most 41% of its try budget (MENTAL.BRIDGE_EQ Easy). They are not at risk.

**The proofs, run on the fixed branch** (a database built by the fixed code):

    cd packages/engine && uv run pytest -q tests/test_bank_fills.py
    7 passed in 198.70s    (two whole-bank seeds 86 s and 81 s; ADD.2D1D Hard with one draw a question, 2.4 s)

and `bin/engine done bank-fills-every-time` (twenty seeds), pasted in the pull request.

## The fix

- `assess/draw.py`: when a case's random draws run dry, the rest is taken from the list of every question it can be
  (`_listing`), shuffled, so the last questions are as varied as the first. The list now covers + and − (pairs of a
  sum's digits, up to 100,000 pairs: 3 digits by 2 is 81,000). The random draws still come first, so the bank's mix is
  what it was; the list only finishes what they leave.
- `assess/draw_times.py`: a case that is × 10, 100 or 1000 itself is listed as the factor beside every number of its
  digits (TP05: 162 questions, not a million pairs).
- `w1_bank/refill.py`: `shortfall` is the one place a level's case shares are worked out (the top-up and the test use
  it); `why_short` says why a level is short, case by case: how many it is short, what it can make at all, and how many
  of those the bank holds. `engine bank refill` prints it above its last line.
- `tests/test_mul_levels.py` read a case's whole list through the private `draw._rest`; it reads `draw.listed` now.
- `w1_bank/bank.py`: the generators take the caller's `rng`, so a seeded build can be run again exactly. A real build
  still passes none, and keeps the operating system's randomness (the reason is unchanged).

## Cost

The new test adds about 3½ minutes to CI's engine job: two whole-bank seeds at about 85 s each, and about 20 s for the
single-draw levels. The goal runs twenty seeds as two commands of ten (about 14 minutes each here), each inside the half hour `engine done`
gives a command.

## Not done, and why

- Kinds that are not a straight calculation of two numbers (missing numbers, stories, three or more numbers, ranges
  past 100,000 pairs) still rely on their draws alone. Measured: at a tenth of the draws every level holding them
  still fills, so a real build has ten times the margin.
- `checks/audit.py` is untouched (PR #234 changes it).

## Handoff

- **Live:** nothing; the bank on live is not rebuilt by this change (a refill only tops levels up, and live's are full).
- **In flight:** PR "The bank fills every level every time: no more random CI failures", on
  `claude/bank-fills-every-time`.
- **Next:** Nimish merges; every later PR's CI builds its bank with the fix.
- **Blocked:** nothing.
