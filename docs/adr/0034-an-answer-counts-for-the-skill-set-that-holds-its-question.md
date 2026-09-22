# 0034 — An answer counts for the skill set that holds its question, not the one that shares its rung

Date: 2026-09-22
Status: accepted (Nimish, "Fix the rule.")
Goal: goals/next-paper-per-skill.yaml

## Context

N5 decides each child's next level in a skill set from their confirmed answers (`next_difficulty`). It found
a skill set's answers by joining evidence to the skill set on `rung_code`. A rung is the old ladder's step and
can hold two operations — R9 is "3-digit ± with regrouping" — while its one skill set, ADD.3D.REG, practises
addition; since step 8h the taxonomy's 3-digit subtraction cases sit in SUB.2D.EXCH (Hard, Advance) and
SUB.3D.ZERO. On the live data Dhanvi's next ADD.3D.REG paper targeted `M_NO_DECREMENT` (a subtraction
mistake), and her 3-digit subtraction, a repeating mistake, led to no paper.

A generated question names its skill set and level (`item.skill_set_code`, `item.difficulty`). An old paper's
question (330, `source = 'legacy'`) names only the rung and skill a person gave it — and every confirmed
answer today is on an old paper.

## Decision

1. **An answer counts for every skill set whose level holds its question.** For a generated question, the
   one it was made for. For an old one, `engine legacy place` measures its numbers (`assess/tags.py`) against
   the team's taxonomy cases (`assess/taxonomy.py`) and writes each skill set and level whose cases it is one
   of to `item_placement`. A question two levels both hold is evidence for both — the same rule step 8 took
   for skills (ADR 0023).
2. **No case → its rung's skill set, only if that skill set's questions use the question's skill.** "342 + 268"
   told as a story on R9 counts for ADD.3D.REG; "862 − 268" told the same way does not.
3. **Neither → listed, never dropped.** `engine legacy place` names each one (12 on 2026-09-22: place value,
   comparison, fractions, division, number words — skills no skill set practises yet, one of the four
   pedagogy questions for Neha, Achal and Aseem).
4. **The join is written once**, `skill_set_evidence(child, skill set)`, and `next_difficulty` reads it for
   both the share of right answers and the mistakes it aims at.
5. `item_placement` is derived: rewritten whole by `engine legacy place`, by `engine legacy paper` when a
   paper is entered, and by `engine graph`. How an old kind is measured is a config row (`legacy.kind_as`).

## Rejected

- **Setting `item.skill_set_code` on old questions.** One value cannot hold a question two levels share, and
  the worksheet library deals every active question with a skill set — old papers' questions would have been
  printed on new worksheets.
- **Keying evidence by (rung, skill) instead of rung.** R9 subtraction would count for no skill set at all:
  no skill set on R9 practises it. The rung is the old ladder; the skill set's levels are the school's.
- **Matching cases in SQL.** The matcher is Python and already the bank's (`assess/taxonomy.py`); a second
  copy in SQL would drift from it.
- **A person placing every old question.** 318 of 330 are placed by their own numbers; a person places only
  the 12 the code cannot.

## Consequences

- Dhanvi (copy of live, 2026-09-22): ADD.3D.REG Medium with no targets; SUB.3D.ZERO Easy aimed at
  `M_FACT_PM10`, `M_NO_DECREMENT`.
- `child_skill_state` is still keyed by (skill, rung); the graph per skill set and level is the next step
  (`goals/two-child-loop.yaml`), and reads `skill_set_evidence` and `item_placement`.
- A level rewritten later changes placements only when `engine graph` or `engine legacy place` runs.
