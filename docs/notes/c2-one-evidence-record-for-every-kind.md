# C2: one evidence record for every kind (goals/c2-one-evidence-record-for-every-kind.yaml)

## Verified

- **Before the code (fresh build, C1 applied):** `tests/test_evidence_every_kind.py` failed 6 of 7: no `evidence_kind`, no
  `mark`, `seen_by`, `place` or `source` on a record. The seventh runs the migration itself. Every question's skills and
  every mistake's skill are registry keys (0 of 125,786 mistake skills and 0 question skills are not), so a written
  answer's `skill_code` already names a registry skill.
- **Built:** migration 20261205090000.
  - `evidence_kind`, `evidence_scale` and `evidence_mark` are rows, the same for every school and seeded from
    `vocabulary.json`.
  - `evidence_event` gains `kind` (default written), `mark`, `seen_by`, `place` and `source`. A new record must name a
    registry skill (a key, `not valid` for past rows).
  - A written answer's mark follows `correct` (right, wrong, blank). Any other kind is refused without who, where,
    source, or a mark on its own scale.
  - `evidence_placed`, which the graph reads, keeps its columns and reads written answers alone.
- **`engine past`:** the evidence is fingerprinted on the columns a record held before C2. That is the same text as
  `e::text` was, so its checksum is unchanged on a database without C2. Adding a column would otherwise move every past
  row's text without moving any of its values.
- **Tests:** `test_evidence_every_kind.py` 7 passed. With `test_live_data.py` and `test_rules.py`: 17 passed. `bin/check`:
  30 passed. `test_live_data`'s self-made school now holds the registry skill its evidence names (`rows.a_registry_skill`).

## Assembled onto main (#305, 2026-10-23)

C2 to C6 were merged each into the branch below it, so none reached main; #305 merges main with all five, in order
(every commit of every slice branch contained: `git rev-list origin/claude/<branch> ^HEAD | wc -l` → 0 for each).
- Rehearsal on a copy of live (Actions → rehearse update-live, run 39886818396, head abd0b7c): migrations 1203 to 1210
  applied on live's rows; `engine past` before, after the migrations and after update-live, identical:
  evidence 1748 `f8e77132…`, states 276 `a70d7cfe…`, scored 12665 `13bf1849…`, questions 51634 `e11078c5…`, levels 178
  `3f13044d…`.
- `bin/testdb fresh` builds; this slice's migration applied a second time on it: OK.
- `bin/engine done c2-one-evidence-record-for-every-kind` on the assembled branch (2026-10-23): 7 of 7 sentences PROVED; the slice's own criteria
  and `bin/check` PASSED; the whole-suite criterion timed out on the session's box (1800 s), and is proved instead
  by CI on 72548b8: all 12 engine shards and the browser suite green. NOT DONE only because it is not on main/live.

## Handoff

- **Live:** nothing. Waits on C1.
- **In flight:** CI and the rehearsal on a copy of live (it now also prints evidence by kind and mark, and how many past
  rows name no registry skill).
- **Next:** C3, the curriculum as numbered versions.
- **Later (out of scope):** the observation engine writes `observed`, `voice`, `project` and `performance` records. Past
  written rows keep `mark` empty; their mark is read from `correct`.
