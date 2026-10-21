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

On a database built fresh from this branch (`bin/testdb fresh`, 2026-10-21) unless said otherwise.

- `bin/engine done b2-question-types-are-rows` → every one of Nimish's 11 sentences `PROVED`; criteria: the types,
  links, seed and migration `23 passed`; every path that makes a paper `83 passed`; `bin/check` `28 passed`; the whole
  suite `timed out after 1800s` here (this container takes 52 min), so it is proved by the next line and CI. `NOT DONE`
  only for what is not live: the branch is not on main, the live database was not asked.
- `uv run pytest -q` (whole engine suite) → `5 failed, 2595 passed`; the 5 then fixed and `27 passed`
  (tests/test_approval.py, test_rules.py, test_spec.py, test_level_approval.py, test_provenance.py). Here the browser is
  the container's own (`PLAYWRIGHT_BROWSERS_PATH` pointed at /opt/pw-browsers' headless shell); without it every page
  render errors, which is this container, not the code. CI `engine` on PR #240 → success.
- `bin/check` → `28 passed`.
- Rehearse update-live on this branch (run 39564332907, success, the copy clean):
  - `engine past` before the migrations, after them and after update-live, all three equal: evidence 1740 rows
    `8f69097f…`, states 274 `8ef89d8c…`, scored answers 12545 `4e36e878…`.
  - after B2: types 74, approved 74, level × type links 394; active questions 43840, a paper may draw 43512. The 328
    between are the earlier papers' questions (the seed's 17 papers hold exactly 328), which no paper draws; the next
    rehearsal counts the bank's own questions alone.
- CI `browser` on PR #240 failed on `permission denied for function skill_levels` — B1's, fixed on B1 (eb2c132) and
  merged here; re-run on the new head.

## Handoff

- Live: nothing. In flight: PR #240 (draft), built on B1 (#234), which merges first; then main merges here.
- Next: once #234 merges, merge main, CI green, mark #240 ready.
- Decision for Nimish: the skills' `formats` list stays only as the generator's input (146 of 178 levels); move it
  into each level's rule with B3/B4, or leave it (ADR 0088).
- Open: B2-3 (Achal): words for `word_budget`; whether chunking and long division are types of their own.
- Visible on the day: the library page's kind chips sort by their words and include chunking and long division.
