# M1-02 — a K2 child's picture per skill, from confirmed voice notes

W3, gate N10 (the skill graph). Design note, step 1; no code or schema yet (waits on "go schema" after #362/#363).

## Where the rebuild reads evidence today

- `engine graph` → `assess/graph.py::rebuild` → SQL `rebuild_child_skill_state(child)` (last defined in
  `20261223090000_a_state_reads_recent_answers.sql`). The whole rule is in SQL: `graph_answer` view →
  `graph_level_window` → `graph_state_of` → `graph_skill_states` → `child_skill_state`. Numbers are `threshold` rows.
- `graph_answer` reads `evidence_placed`, which keeps **`kind = 'written'` only**. A K2 observation (#362 writes
  `evidence_event` kind `observed`, mark `yes/sometimes/not_yet`, `correct` null, no rung, `observation_id`) is
  invisible to it today. So the written path can stay byte-for-byte untouched.
- `child_skill_state` is keyed `(child, skill_code, rung_code)` with **`rung_code not null`**. K2 skills
  (`MOT.GMS.01` …) have no rung and span PG–K2. They cannot go in that table without changing a shared key.
- `threshold` is one value per school and key, no grade. `state.min_adults` = 2 is global (would block every K2 skill).

## What changes (proposal)

1. A **separate Ring B table** `child_observed_state` (child, skill, grade, state, level shown, named days, first named
   yes day, re-checked on, adults, last seen). Truncate-able, rebuilt by a new SQL function from Ring A only. Not
   `child_skill_state`: keeping the written table, its key and every reader untouched is what makes `engine past`
   equal by construction, not by luck. `rebuild()` calls both functions; one extra line in `graph.py`.
2. The K2 rule, in SQL beside the written one, reading confirmed `observed` evidence joined through `observation_id`
   to `activity_observation` for entry mode and the class's grade; evidence of a superseded observation is skipped;
   a school day is the date in `school.time_zone`, as `graph_answer` does. Level comes from the mark (yes 3,
   sometimes 2, not yet ≤1) through #362's `voice.level_mark` — read backwards, not re-stated.
3. States (existing `child_state` codes, no new vocabulary): no row = not observed (D-008); named `yes` on 2 school
   days, then a `yes` ≥ 14 days after the first of them → `secure`; the 2 days but no re-check → `secure_to_recheck`;
   any other named mark → `practising` (or `emerging` if the latest named mark is `not_yet`); only "the rest" lines,
   never named → `not_enough_yet`. A group line may be the re-check; it never opens secure and never moves a state down.

## Rows, not code

- `observed_rule` (school, grade): `secure_level` 3, `secure_days` 2, `recheck_days` 14, `min_adults` 1. K2 row
  only; another grade is an insert.
- `observed_weight` (school, grade, kind, entry mode): `opens_secure`, `rechecks`, `lowers`. K2: individual
  true/true/true; group_as_expected false/true/false. The weight lives here, never on an evidence row.

## The migration — `20261228090000_k2_picture.sql` (additive only)

The three tables above; K2 rows for every school, and a trigger named to fire after the vocabularies it names; the
functions; select only for both services, DELETE (and insert, update, truncate) revoked on all three; no trigger
refuses TRUNCATE; `child_observed_state` in the data register's "learning" entry; `apply_conventions()` last.
Orchestrator's answers (D-047; Nimish may overturn): group-only is a `not_enough_yet` row; a second named yes ≥ 14
days on is its own re-check; **once secure (or secure, to re-check), a later named lower mark re-opens it and resets
the clock** (proposed by the orchestrator, unverified with the school): a fresh cycle counting only marks after it;
before that, a lower mark changes only what is shown (yes, sometimes, yes stays on course, D-052). Built as a small
state machine over each child-skill's marks in time order (building → secure, to re-check → secure; re-opened).
**Ties:** two named marks at the same moment, the lower decides (and resets), so a rebuild never flips.
**The level, not the mark** (after #362 stored `activity_observation.reached_level`; orchestrator, 4 Nov): the rule
reads the level the educator's outcome showed, never works it back from a mark, so a change to `voice.level_mark`
cannot move secure. The mark decides only emerging versus practising while a skill is building.

## Verified (a local database only; never live)

- On main (#362 squashed in) plus this branch, a fresh db from every migration and the seed:
  `tests/test_k2_picture.py` → 14 passed; with the graph, voice, register, privileges, rules, roles, vocabulary and
  loader suites → 92 passed. The level test failed first on the mark-reading rule ({'secure'} == {'practising'}).
- Migration applied twice in a row: no error. `engine live rules --write --url <local>` → only the new tables' rules.
- `engine past`: a fresh db of main's migrations, the seed and the 11 GR1 ledgers as written evidence, then this
  migration and `engine graph`: before = after, evidence 154 / states 11 / scored 154, same checksums; 0 moved.
- Independent read (athena-verifier): no blocking finding; its tie-break and tenant-join points fixed and tested.
- `bin/check` → 34 passed. `bin/engine done m1-02-k2-picture`, pasted:

```
Your words, and the test that proves each (run now, on the copy):
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_secure_needs_level_3_named_on_two_days_and_a_yes_14_days_after_the_first  — 1 passed in 0.16s
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_the_rest_did_as_expected_is_never_alone_secure  — 1 passed in 0.15s
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_the_rest_did_as_expected_never_lowers_a_state  — 1 passed in 0.14s
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_a_child_not_mentioned_is_not_observed_and_has_no_row  — 1 passed in 0.10s
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_written_evidence_is_read_exactly_as_before  — 1 passed in 0.11s
  PROVED  "All parts should just function like a well-oiled machine, right?"
            packages/engine/tests/test_k2_picture.py::test_secure_reads_the_level_reached_and_never_moves_with_the_level_to_mark_setting  — 1 passed in 0.24s

Its criteria (run now):
  PASSED  the K2 rule, worked by hand, against a database built from the migrations
            $ cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_k2_picture.py  — 14 passed in 1.23s
  PASSED  the written graph's own rule is unchanged
            $ cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_graph_rule.py tests/test_graph.py  — 15 passed in 3.37s
  PASSED  the code sits where the map says; every promise has its command; lint
            $ bin/check  — 34 passed in 28.18s

Still manual:
  - The real proof: the first confirmed K2 notes, each child's state per skill worked out by hand from the notes and compared with the rebuild. Not claimed by this goal.
  - Actions, rehearse update-live, on this branch: the migration runs on a copy of live; `engine past` prints the same evidence, states, scored answers, questions and levels before and after.

Not live yet:
  - this work is not on main yet, so the live website and engine do not have it
  - the live database did not answer from here (ConnectionTimeout): its migrations are unchecked

NOT DONE
```

## Handoff

- In flight: PR #364; main merged locally, one push when the orchestrator says live has 20261227090000, then retarget
  to main and the rehearsal (`rehearse update-live`). Next: the real proof by hand on the first K2 notes.
