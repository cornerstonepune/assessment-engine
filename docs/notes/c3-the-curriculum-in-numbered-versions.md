# C3: the curriculum in numbered versions (goals/c3-the-curriculum-in-numbered-versions.yaml)

## Verified

- **Built:** migration 20261206090000.
  - `curriculum_version`: numbered per school, with who published it, when, and the Monday it takes effect.
  - `curriculum_version_skill`: every skill at its version. Both tables are records that are never edited.
  - `publish_curriculum(school, by, note)` publishes. `curriculum_in_force(school, at)` returns the newest version
    whose Monday has come, by the school's own clock (`config` school.time_zone, Asia/Kolkata, seeded).
  - Version 1 is the curriculum as it stood, in force from this week's Monday.
  - `item_result` and `evidence_event` name `curriculum_version` by themselves on insert. Past rows name none.
- **Applied twice locally:** one version 1 holding 46 skills.
- **A fresh build had an empty version 1.** The whole suite on a fresh build found that the migrations run before any
  skill exists. Version 1 now begins once a school has skills: in the migration where they exist (live), else at the
  end of `engine load` (`curriculum_begins`). Rebuilt fresh: version 1 holds 46 skills, and the C1–C3 tests with
  `test_rules` and `test_layout` pass (80).
- **Tests:** `test_curriculum_versions.py` 6 passed. With C2's tests: 13 passed. `bin/check`: 30 passed. The tests were
  written after the migration was first applied locally, so their failing-first run is the CI run of a database
  without it. Not seen separately.

## Assembled onto main (#305, 2026-10-23)

C2 to C6 were merged each into the branch below it, so none reached main; #305 merges main with all five, in order
(every commit of every slice branch contained: `git rev-list origin/claude/<branch> ^HEAD | wc -l` → 0 for each).
- Rehearsal on a copy of live (Actions → rehearse update-live, run 39886818396, head abd0b7c): migrations 1203 to 1210
  applied on live's rows; `engine past` before, after the migrations and after update-live, identical:
  evidence 1748 `f8e77132…`, states 276 `a70d7cfe…`, scored 12665 `13bf1849…`, questions 51634 `e11078c5…`, levels 178
  `3f13044d…`.
- `bin/testdb fresh` builds; this slice's migration applied a second time on it: OK.
- `bin/engine done c3-the-curriculum-in-numbered-versions` on the assembled branch (2026-10-23): 6 of 6 sentences PROVED; the slice's own criteria
  and `bin/check` PASSED; the whole-suite criterion timed out on the session's box (1800 s), and is proved instead
  by CI on 72548b8: all 12 engine shards and the browser suite green. NOT DONE only because it is not on main/live.

## Handoff

- **Live:** nothing. Waits on C1 and C2.
- **Not in this slice:** the bank and marking still read a skill's current row when they make a paper. "Takes effect
  next week" is therefore true of what a result names and of what a version holds, but a paper made mid-week from an
  edited skill uses the edit. Making papers read the version in force is a decision for Nimish (in the PR).
- **Next:** C4, validation rules per subject and kind.
