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

## The migration (one, additive, after "go schema")

`2026122809…_k2_picture.sql`: the three tables above; K2 rows for every school + trigger for a new school; the
functions; grants to `app_engine`/`app_web` (select), **DELETE revoked explicitly** on the two rule tables and on
the state table for both services (the rebuild is `security definer`); no ledger trigger (nothing here refuses
TRUNCATE); `data_register` entry for `child_observed_state`; `internal.apply_conventions()` last. Nothing existing is
altered. Then `engine live rules --write --url <local>` and `engine past` before/after on a local db.

## Questions for the orchestrator (my defaults in brackets)

- A named lower mark on a later day after secure: does it re-open the skill? [yes, to practising: `lowers` on the
  individual row; group never]. The task's words fix "never lowers" only for group lines.
- Group-only child: `not_enough_yet` row, or no row? [a row: D-008 says a "rest" line is an observation].
- 14 days from the first named yes, even when the second named yes is itself ≥ 14 days later? [yes, it re-checks].

## Verified

- Nothing yet.

## Handoff

- In flight: this note. Next: goal file + failing tests (no schema), then the migration on "go schema".
