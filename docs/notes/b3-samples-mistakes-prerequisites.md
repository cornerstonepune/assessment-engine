# B3 — a skill's samples, mistakes, registry links and prerequisites are rows (goals/b3-samples-mistakes-prerequisites.yaml, ADR 0092)

## Verified

- **Built:** migration 20261127090000 makes `skill_level_sample`, `skill_mistake`, `skill_registry_link` and
  `skill_prerequisite`, each code a key. Triggers keep the first three equal to the lists still written
  (`misconception_codes`, the rung's `skill_codes`, a level's words, a card kind's examples) and refuse a list naming a
  mistake or registry skill that is no row; nobody else writes them. Prerequisites are rows only, drafted by `engine
  load` from `supabase/seed/skill_prerequisites.json` while the school has none. `engine links check` compares rows and
  lists; `engine past` (byte-for-byte B2's, #240) fingerprints the evidence, children's states and scored answers.
- **Measured on a database built from main (2026-10-21), before the code:** 46 skills; MUL.FACTS lists the 8 M_DIV_…
  mistakes, every one computed by `spec.known_misconceptions` on its Advance level, only on Y09, the fact family
  ("10 × 3 = 30. Use it to finish these facts."), whose second and third boxes are divisions (e.g. `30 ÷ 10 = □`:
  M_DIV_TENS_ZERO_LEFT 30, M_DIV_SUBTRACTED 20). M_WRONG_OP is computed there on multiplications only. Rungs: 61
  registry codes, all in `skill`. `ladder_order` empty on 26 of 46 rungs.
- **Decisions, by rule (ADR 0092):** B3-1 split → 240 samples on 114 levels, 11 of 11 card examples, 58 levels keep a
  piece in words. B3-2 → no list changes: all 8 stay. A first pass removed six links on four division skills
  that the standard sample did not show; CI's `test_estimates` then showed MD.ESTIMATE naming one, and drawn more
  widely (30 × cases, seeds 1–3) each of the six came up on a division its skill asks. Reverted in 601ac42. B3-3 → 167
  prerequisites from the ladder's grades.
- **Tests:** `tests/test_skill_links.py` failed on a database from main (no tables; DIV.3D1D's list) and passes here;
  with `test_loaders`, `test_approval`, `test_estimates`: 40 passed. `bin/check`: 28 passed. On the fresh build from
  this branch (`bin/testdb fresh`): `skill_level_sample 251 · skill_mistake 717 · skill_registry_link 61 ·
  skill_prerequisite 167` (723 mistake rows after the revert); `engine links check`: "the rows and the lists agree on
  every skill and level".
- **Rehearsed on a copy of live, run 39635752234 on 6bbbf41 (green):** past results equal before the migrations, after
  them and after update-live; `engine links check` clean before and after. (That head still removed the six links;
  the rehearsal on 601ac42 is the one that counts — see the PR.)
- **CI on 6bbbf41:** two failures, both this branch's: `test_approval` added a mistake code with no row (now refused by
  design; the test writes the row first, as `spec._store` does) and an op list compared in the database's collation.
  Fixed in 601ac42, with the revert above.

## Handoff

- **Live:** nothing; B3 is not deployed. Nimish merges, then `bin/update-live` migrates live and loads the prerequisites.
- **In flight:** PR #251, CI and the rehearsal on the latest head.
- **Next:** when B2 (#240) merges, merge main in: `checks/past.py` is the same file; `cli_check.py`, `rules.json` and
  the rehearsal workflow touch neighbouring lines and need a hand merge.
- **Open for Achal (rows, not blockers):** the 58 levels' pieces left in words (`bin/engine links check --words`), and the
  167 prerequisites.
- **Not B3:** the readers move onto these rows with the writers; until then a page may show M_WRONG_OP in any of its
  five wordings.
