# gr1-state-from-recent-evidence — a state reads recent answers at the child's level

Nimish, 3 Nov 2026, from the learning-science review (teacher-os `research/council-2026-11-03/learning-scientist.md`
§1). W3, gate N10, reopened. Rules and rejected alternatives: ADR 0098. Goal: `goals/gr1-state-from-recent-evidence.yaml`.

## Verified

On databases built by `bin/testdb fresh` (Postgres 16, this container), 3 Nov 2026:

- `pytest tests/test_graph_rule.py`: 14 passed. These are the goal's 11 hand-computed ledgers, run as real papers,
  plus the rule as rows and the new state row.
- `pytest` over graph, levels, calibration, states, parent report, class card, focus, focus paper, loaders, legacy,
  every-skill, roles, live data, week, past: all passed (198 in the last run).
- `bin/check`: 34 passed.
- `npx playwright test` on the specs that read the graph: 175 of 187 passed on the first run. The 12 failures were
  fixtures that made "secure" from one day's answers, plus one real wording bug: practising said "not yet four in five
  right" to a child with 10 of 10 on one day. Every failing spec passed on the re-runs (40 of 40, then 22 of 22).

On a copy of live, `rehearse update-live` with `states_may_change`, run 120 (head eee431b):

- Evidence 1838 rows and scored answers 13425 rows: checksums equal before and after (rule 4).
- `engine past --states-since`: 20 children have a state. Of them, **14** change state, on 53 skills:
  - ready to move up → secure, to re-check: 25
  - ready to move up → practising: 11
  - secure → practising: 11
  - ready to move up → secure: 5
  - emerging → practising: 1

  11 of the 53 are 10 of 10 (or near) on a single day. 24 are on answers from papers that name no level.
- Next level: **19** children change, on 69 skills.
  - 48 are Hard/Easy → Medium. Those are skills whose only answers are on the historical papers (no level) with no
    prescription, so the current level is `level.usual`.
  - 21 move up after the child's last 2 papers at their level.
- Run 119, on the first draft, had sent 60 next levels to the grade's start for the same papers. That draft was
  changed (commit eee431b).

## Handoff

**Live**: nothing. It needs Nimish's merge, then `bin/update-live` (the migration, then `engine graph`).

**Decision for Nimish before merge**: 18 children, 48 skills, whose answers are only on the historical papers. Today
their next level is Medium (the school's usual) until a paper with a level is sat. The old engine moved them ±1 on
all their answers pooled. Treating those papers as sat at the usual level would restore that, read over the last 2
papers only.

**Open, not built**:
- The paper-maker does not schedule the 14–21-day re-check.
- `state.min_adults` applies only to evidence naming who saw it, which no written answer does yet.
- The review's "no demote-level result at any easier level" before secure is not built.
