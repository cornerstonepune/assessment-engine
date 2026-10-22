# B4 — the rung folded into the skill; the registry's table is `registry_skill` (goals/b4-the-rung-folded-in.yaml, ADR 0084)

## Verified

- **Measured on a database built from main (fba80af), before the code:** 46 rungs, one per skill; 25 files read the
  `rung` table (18 engine, 7 website); 3 engine and 4 website files read the registry as `skill`; 14 rungs list more
  than one registry skill, the first being the skill's own (the paper catalogue, the child's map's lane).
- **Built:** migration 20261201090000 puts the rung's grade, ladder place, description and registry list on the skill
  (`grade`, `ladder_order`, `descriptor`, `registry_codes`), makes `rung_code` a unique key a question points at, moves
  the level and registry-link triggers onto the skill, drops `rung`, renames the registry's `skill` to `registry_skill`
  (keys too). For the one deploy in which the old code may still run, `rung` and `skill` answer as read-only views;
  the next deploy (B4b) drops them. It stops, naming what, if live holds a rung milestone or a question on a rung no
  skill holds. Written to run twice (applied twice locally: same result).
- **Tests:** `tests/test_rung_folded.py` (7). On a database built from main: 5 of the 6 that do not apply the
  migration fail (no `grade`, `registry_codes` or `registry_skill`; the one that passes checks only that every rung
  code on record is already a skill's); with the migration and the old code, the two file scans failed on 25 files. After the
  code, on a fresh build of this branch: 7 passed. `bin/engine links check`: "the rows and the lists agree on every skill and
  level". `engine live rules` on a fresh build: "0 rules held otherwise than the migrations make them" (rules.json
  rewritten from it).
- **Whole engine suite, this branch vs main, same machine, each on its own fresh build:** main 126 failed + 62 errors,
  this branch the same set plus 5, all five fixed since (re-run: no failure main lacks). Every failure main also has
  is a test that needs a browser, which this container lacks; CI has one.
- **Old tests changed, not loosened:** B1's and B3's tests re-ran their whole migrations, which can no longer run once
  `rung` is gone; they now re-run the migrations' data steps (`tests/rows.py::data_steps`). The l2 goal's proof that
  "a rung no skill holds is removed" became `test_no_rung_is_left_without_a_skill`: no such rung can exist now.
  The audit's "every rung has a spec" went with the table it checked.

- **Rehearsed on a copy of live, run 39745650087 on a7c389c (green):** live held 46 rungs (G1 4, G2 20, G3 13, G4 9),
  one per skill, so the migration stopped on nothing. `engine past` before the migrations, after them and after
  update-live, all three the same: `evidence 1740 rows checksum 8f69097fe762641397c33ed7f3ed8945 · states 274 rows
  checksum 8ef89d8c9d9d09d532841d7cb529d3f7 · scored 12665 rows checksum 565e33bdd7a3819f7415a7c73dbbbde1`.
  `engine links check`: "the rows and the lists agree on every skill and level"; the copy after: every check ok.
- **CI on a7c389c:** run 39745683535, success (the website's browser suite included).
- **`bin/engine done b4-the-rung-folded-in` (2026-10-22, on a fresh build of this branch):** every sentence PROVED (7
  of 7); criteria: the fold 39 passed, `links check` agree, `bin/check` 30 passed; the whole suite timed out at done's
  1800 s on this container. Run alone with a browser: `2712 passed, 2 skipped, 1 warning in 2597.05s`. CI on 5895b48
  (run 39749669201): success.

## Handoff

- **Live:** nothing; not deployed. Merge → `migrate live` runs the migration → the engine and site take the code.
- **In flight:** PR #273, CI and the rehearsal green; waiting on Nimish to merge.
- **Next:** B4b, `skill_set` → `skill` (goals/b4b-the-skill-is-called-skill.yaml), which also drops the two views.
- **Not done here (decided):** evidence, child_skill_state and class_card keep `rung_code` (B4-2); the maths library's
  word "rung" stays (B4-3); the seed keeps `rungs.json`, read onto the skill by `engine load`.
