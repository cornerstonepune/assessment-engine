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

- `observed_rule` (school, grade): `secure_mark` yes, `secure_days` 2, `recheck_days` 14, `min_adults` 1. K2 row
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

## Verified (a local database only; never live)

- `tests/test_k2_picture.py` → 13 passed (the reset, a sometimes between, the tie: a test each; one through #362's
  confirm step); with the graph, voice, register, privileges, rules, roles, vocabulary, loader suites → 86 passed.
- Migration applied twice in a row: no error. `engine live rules --write --url <local>` → only the new tables' rules.
- `engine past` on a fresh db (every migration but this one, seed, the 11 GR1 ledgers as written evidence), then this
  migration and `engine graph`: before = after, evidence 154 / states 11 / scored 154, same checksums; no state or
  next level moved.
- Independent read (athena-verifier): no blocking finding; its tie-break and tenant-join points fixed and tested.
- `bin/check` → 34 passed. `bin/engine done m1-02-k2-picture` → every sentence PROVED, every criterion PASSED,
  "NOT DONE": not on main, live unreachable from here, two steps manual.

## Handoff

- In flight: PR #364, based on #362's branch; retarget to main once #362 lands. Rehearsal (`rehearse update-live`)
  only on a head containing #363 on main (orchestrator). Next: the real proof by hand on the first K2 notes.
