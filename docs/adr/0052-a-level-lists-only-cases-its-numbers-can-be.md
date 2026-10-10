# ADR 0052 — A level lists only cases its numbers can be, and a kind fails aloud on a rule it cannot read

**Status:** accepted (2026-10-10, slice AS1 of BUILD-ORDER "Inserted now: multiplication and division")
Goal: goals/as1-every-listed-case-draws.yaml

## What happened

Proving M2b, a database built as CI builds it held no question of some cases addition's and subtraction's levels list.
Measured (STATE.md "AS1 — measured before the build"): drawn alone on its level, 35 of the 605 (case, level) pairs the
seed lists gave nothing, for four causes. A level hands a dry case's share to its other cases, so every level still
filled, and nothing said so.

## Decision

1. **A level made of cases lets its case decide what its rule does not name.** An estimate read its level's `regroups`,
   which a level of cases never has, and every draw of R01 and R02 failed on it. Its numbers are now any regrouping
   their sizes allow, and the case's own match keeps what it asks for.
2. **A worked answer for + and − is drawn at the level's two sizes**, as a multiplication's already was. Both numbers
   were drawn the first number's length, so a 2 by 1, 3 by 1 or 3 by 2 level never held its mistakes to find (X03,
   X06 to X09). A level whose two numbers are one length is drawn exactly as before.
3. **A level lists a case only where its numbers can be that case.** M01 to M05, M24 and M25 leave the 20 levels whose
   numbers cannot hold their box (a 1-digit box on ADD.2D2D), and stay where they fit. SZ6 (1000 − 476) and SZ9
   (1000 − 999) start at 1000, a 4-digit number: they move from SUB.3D3D (Grade 3) to SUB.4D (Grade 4), after its own
   straight cases at Hard and Advance.
4. **The drawer counts only a `RuntimeError` as an unlucky draw**, as `operations.CannotMake` says the bank does. A
   `KeyError` or a `ValueError` is a rule the kind cannot read, and it is raised. Measured over every listed pair, the
   only ones swallowed were R01's and R02's missing `regroups`, 6,000 times each.
5. **A test draws every case every level lists** (`tests/test_every_listed_case.py`), with the multiplication levels.

## Rejected

- **`regroups` written into those levels' rows.** A story and a missing digit on the same level read it too, and
  would change.
- **SUB.3D3D's numbers widened to hold 1000.** Its numbers would then hold every 4-digit by 3-digit subtraction, and
  those are SUB.4D's: a question lives in one level.
- **A check by key in `taxonomy.within` alone.** It would catch a box of the wrong size, but not SZ6, whose
  3-digit numbers can never pass an exchange through two zeros. Only drawing finds that.
- **The stories W02, W03 and W06 here.** They draw on their own, and go missing only when a 1-digit level is filled
  whole, since a story's key is its numbers alone. That is ADR 0011's rejected option, and its trigger is met: AS2.

## Consequences

- On live, `bin/update-live` brings the new questions (`engine load`, `bank refill`); nothing stored is retired.
- Achal is asked whether the school teaches subtraction from 1000 in Grade 3. If it does, SUB.3D3D's numbers need a
  rule of their own for it.
