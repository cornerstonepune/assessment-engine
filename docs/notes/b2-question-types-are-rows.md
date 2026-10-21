# B2: question types are rows, one approval each

W1, gate 3, B2. Goal: `goals/b2-question-types-are-rows.yaml`. Built on B1 (#234).

## Measured

Before the code, 2026-10-21. A type is ADR 0077's format: the printed format where the template is only the level's
numbers written as a name, else the template (decision B2-1). Command: `.github/measure/b2_types.py`, run on the seed
(`bin/testdb fresh`) and on a copy of live by the rehearsal (run 39560151627, read only, codes and counts only).

| | seed (fresh build) | copy of live, before update-live | after update-live |
|---|---|---|---|
| types in use | 74 | 74 | 74 |
| skill × type / level × type | 212 / 394 | 212 / 394 | 212 / 394 |
| levels holding questions / confirmed | 178 / 0 | 178 / 178 | 178 / 178 |
| types whose every level is confirmed | 0 | 74 | 74 |
| types on a printed or library paper | 74 (library) | 74 | 74 |
| types that would wait on the day | — | 0 | 0 |
| unconfirmed levels a paper draws today | 0 | 0 | 0 |
| evidence rows, checksum | 0 | 1740, 080698e7… | 1740, 080698e7… |

- So gating on confirmed levels and approved types refuses no paper on live today: every level is confirmed and every
  type starts approved under either starting rule.
- Labels: the bank holds 33, the skills' lists name 32, the website has words for 33. `word_budget` is on a list and is
  a level's own format but has no words (its questions print as `word_2step`, type `BUDGET`); `chunking` and
  `long_division` have words and questions but are on no list. Decision B2-3 waits on Achal; nothing here guesses it.
- How a type reaches the child: "drawn" where the maths library draws its format (`assess/pictures.py` `DRAW`, 20
  types), else "printed". Nothing is read aloud today; the column allows it.
- How a type is marked: the ways its questions are marked, as the bank holds them. Four types mix computed and judged
  questions (`FTM`, `CLAIM`, `EFFICIENT`, `bare_sum`), so `marked` is a list, not one word.
- The school's earlier papers (`legacy_*`) are not types: their questions are never drawn, and their template is the
  paper's own name.

## Verified

Phase 1 (no B1 yet):

- `bin/check` → `28 passed`.
- `uv run pytest tests/test_question_types.py` on the fresh seed → `11 failed`: no `question_type` table, no gate,
  no migration yet. The tests are written before the code.
- `bin/engine past` on the fresh seed → `evidence 0 rows checksum d41d8cd98f…` (no child there).

## Handoff

- In flight: phase 2 waits for B1 to bring in B0d, then builds on `skill_level`.
- Open: B2-3 (Achal): words for `word_budget`; whether chunking and long division are types of their own.
