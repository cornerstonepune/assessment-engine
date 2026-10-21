# B1 — a skill's levels are rows (`skill_level`), kept equal to the blob (goals/b1-levels-are-rows.yaml, ADR 0087)

## Verified

- **Built (scope locked, #234):** migration 20261123090000 makes `skill_level`, one row per skill and level, keyed
  into `skill_set`, `difficulty` and `grade`, holding the level's words (`looks_like`), its rule (everything else of
  the blob entry), its grade (named in `level_band`, else its rung's) and who approved it and when;
  `skill_level_version` files a level's earlier words and rule, only that level's, and the migration carries each
  level's history out of `skill_set_version` once. A trigger on `skill_set` (and on a rung's grade) keeps the rows
  equal to the blob whoever writes; nobody else may write them. `learning_objective` waits empty (the split is B3's).
- **Measured on the seed:** 178 levels, 178 rows · G1 16 · G2 63 · G3 55 · G4 44 · approved 0 and 0 (a fresh build has
  no approvals). `bin/engine levels check`: words, rule, grade and approval equal on every level, and 4 questions drawn
  from each of the 178 levels on seed 1 from rows and blob, identical.
- **Readers moved, before B0d:** the generator's spec (`spec.row`, `spec.read`, so `bank.fill`, `fill_native`,
  `refill`, the mistake list), `cases.holds`/`placed`, `review`, `story_shape.placed`, `week_note.options`, `audit`,
  `references`, `legacy`, the item_generate eval; after B0c, `inventory.coverage`, `rehome.shaped` and the worksheet
  library's level list; on the website the bank's totals, a question's level words, the home counts and the people
  page's "reaches".
- **Readers moved, after B0d (#231) merged into this branch:** `shelf` (a child's levels by their rows' grades, and
  which levels are approved, from `skill_level.confirmed_at`), so `focus_paper` and the papers it draws through it;
  `prescribe` and `assess/focus` read no level data at all (checked, and now guarded); the loader counts
  `skill_level` (178) with the tables it fills; on the website `queries.ts` (a skill's levels, words, rules, grades
  and approvals from the rows), `queries-children.ts` (the levels a grade uses), `queries-worksheets.ts` (a
  worksheet's level words), `queries-taxonomy.ts` (where a case is set), and the curriculum, children, worksheets,
  papers/approve and skill-set pages that read through them. `tests/test_skill_level.py`'s guard names every one.
- **The site may call `skill_levels`** (migration 20261124090000): CI's browser job on 4a19318 failed on 43 pages
  with "permission denied for function skill_levels"; 20261123090000 had granted it to the engine's role alone (our
  functions answer only whom a migration names, 20261019090000). `test_roles.py` now lists it among the site's calls:
  failed first, passes after the grant; as `app_web` on the fresh build, 46 skills' levels read.
- **CI on c728e35** (main merged in again, with #241's one-snapshot rehearsal and #237's bank fix; run
  39581630007): engine 2589 passed, 2 skipped, coverage 85.9%; browser and web green.
- **Rehearsed on a copy of live, after B0d (run 39581724538 on c728e35, green):** "copied: 64 tables, 163666 rows,
  every count equal to live's snapshot"; `applying 20261123090000_the_levels_are_rows.sql` then `applying
  20261124090000_the_site_reads_a_skills_levels_from_their_rows.sql`. `engine levels check` before and after
  update-live: "178 levels in the blob, 178 rows · grades G1 16 · G2 63 · G3 55 · G4 44", "approved: 178 in the blob,
  178 in the rows", "drawn on seed 1: 178 levels, 4 questions each, from rows and blob", "the rows and the blob agree
  on every level"; the copy after the update clean. (Two runs at 07:29 and 07:34 UTC on 4a19318 had stopped at the
  copy, because live grew between its dump and its count; #241 counts both in one snapshot.)
- **Left on the blob, by design (ADR 0087):** the writers (the site's edit, approval and move, the loader, `engine
  ratify`, `cases` bringing levels to the seed), and "who last moved a level, when" (`level_band_by`/`_at`), which is
  the skill's record and has no column on a level's row.
- **A fresh build from this branch and one from main differed by one level, by chance (before B0d):** 28,698 questions
  and 2,737 worksheets here, 28,696 and 2,736 on main, all on SUB.3D2D Advance's case S33 (9 questions here, 7 on
  main; every other case of every level equal). S33 has few questions left once Hard has taken its 44, and the bank
  looks for them with fresh randomness each build. The level's rule is the same from rows and blob (`engine levels
  check`), so this is the bank's chance, not B1.
- **Rehearsed on a copy of live, before B0d (run 39539187766 on 3a2e376, green):** "copied: 63 tables, 160215 rows,
  every count equal to live"; B0c's then B1's migration applied with no error. `engine levels check` before and after
  update-live: "178 levels in the blob, 178 rows · grades G1 16 · G2 63 · G3 55 · G4 44", "approved: 178 in the blob,
  178 in the rows", "the rows and the blob agree on every level". The copy after the update clean (`engine live
  data`, `engine audit`: every check ok). Whole suite then: 2583 passed, 2 skipped.
- **Checks:** the moved-readers test failed on the old `shelf.py` (`approved_levels` missed a level approved in its
  row alone) and passes on the new; B1's tests and the loader's: 18 passed.
- **Whole engine suite after the merge**, on a database built from every migration (`bin/testdb fresh`): 2588
  passed, 2 skipped, 1 failed — `test_focus_paper`'s level-order check, which held the blob's key order (Easy, Hard,
  Medium, Advance: Postgres sorts an object's keys by length). The shelf now gives a skill's levels in the school's
  order (`difficulty.ord`); the papers use them as a set, so no paper moves. The test now says the school's order;
  that file, the maker's, the loader's and B1's: 51 passed. `bin/check`: 28 passed. (This container's Chromium was
  older than Playwright asked for; pointed at the installed one, outside the repo.)

## Handoff

- **Live:** nothing; B1 is not deployed. Nimish merges #234, then `bin/update-live` migrates live.
- **In flight:** #234, ready for review: B0d and the notes rule merged in (merge commit), the waiting readers
  moved, the site's grant added; CI and the rehearsal green on c728e35.
- **Next:** the writers move onto the rows; then the blob is dropped one deploy after.
- **Open for Nimish:** how a level's words split into a learning objective and "what it looks like" (kept whole now).
