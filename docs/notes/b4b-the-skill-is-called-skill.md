# B4b — the school's skills are the table `skill` (goals/b4b-the-skill-is-called-skill.yaml, decision B4-1, ADR 0084)

## Verified

- **Before the code (on B4's build):** `tests/test_skill_is_called_skill.py` 4 of 4 failed — `skill` was B4's view of
  the registry, `skill_set` was read as a table, `rung` still answered, the migration did not exist.
- **Built:** migration 20261202090000 drops B4's two views (`rung`, the registry's old `skill`), renames `skill_set` to
  `skill` with its keys (`skill_pkey`, `skill_rung_code_key`, …), and writes again, with the new name, the 11 database
  functions that read the table by name. `skill_set` answers as a view, read and write, for the one deploy in which
  B4's code may still run; the next schema slice drops it. Columns keep their names (`skill_set_code`,
  `skill_set_version`): the decision names the table. Written to run twice (applied twice locally).
- **Code:** 425 places in 138 files name the table in a query (after from, join, into, update, table, references,
  truncate, or `'skill_set'::regclass`); the rest of the word's uses (a field `skill_set` in the engine's answers, a
  form field, columns) are not the table and stay.
- **Found and fixed:** B4's migration checked for the `rung` table with an `and` that Postgres evaluates whole, so it
  failed once the table was gone; its guard now asks `relkind` of `to_regclass(...)`, the same answer wherever the
  table exists (live applied it with the table there). Three more tests re-ran old migrations whole (B0a's vocabulary,
  the level-by-level approval, B2's types); they now run those migrations' data steps, which `tests/rows.py::data_steps`
  reads to include a migration's top-level update, insert and delete statements. The rehearsal no longer reads `rung`:
  a skill's grade and a level's grade are keys since B4 and B0b, and a rung no skill holds cannot exist.
- **Tests:** fresh build of this branch (`bin/testdb fresh`): applied 91 migrations, load and bank clean;
  `test_skill_is_called_skill`, `test_rung_folded`, `test_skill_links`, `test_skill_level`, `test_level_approval`,
  `test_question_types`, `test_vocabulary`, `test_roster`: 45 passed. `engine live rules --write`: 317 rules.
  `bin/check`: 30 passed.

- **Whole suite with a browser, fresh build of this branch:** first run `2 failed, 2727 passed` — the roles test named
  `public.skill_set` as the table the website may update, and the school's-words test read `rung` by a table name in a
  list (an f-string, which the file scan cannot see). Both fixed; those two files: 10 passed.

## Handoff

- **Live:** nothing; B4 is merged and waits for `migrate live` (after main's CI), this waits on B4 being there.
- **In flight:** the whole suite with a browser, then the PR, CI and the rehearsal.
- **Next:** C1 — every question names its registry skills.
