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
- **Tests:** `test_curriculum_versions.py` 6 passed. With C2's tests: 13 passed. `bin/check`: 30 passed. The tests were
  written after the migration was first applied locally, so their failing-first run is the CI run of a database
  without it. Not seen separately.

## Handoff

- **Live:** nothing. Waits on C1 and C2.
- **Not in this slice:** the bank and marking still read a skill's current row when they make a paper. "Takes effect
  next week" is therefore true of what a result names and of what a version holds, but a paper made mid-week from an
  edited skill uses the edit. Making papers read the version in force is a decision for Nimish (in the PR).
- **Next:** C4, validation rules per subject and kind.
