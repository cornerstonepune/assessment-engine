# m0-06-growth-skill-speed — the skill page read every answer in the school (fault fix, no gate moved)

Task M0-06. Goal: `goals/m0-06-growth-skill-speed.yaml`. Test (unchanged, budget 1000 ms):
`apps/web/tests/u71-results-by-topic.spec.ts` "class results, an open topic, an open skill and a child's page each open within a second on a class of 40".

## Verified

**Cause.** `answer_placed` is a view that groups evidence by child. The class loaders in `lib/queries-results.ts` asked it
`a.child_id in (select id from child where section = …)`; Postgres cannot push a semi-join below a grouping, so it grouped every
answer in the school (28,536 rows on the measuring copy, each with its own "newest reading" lookup) and kept the class's
afterwards. The skill page paid it once; the class and topic pages paid it too (their queries use the same helper).

**Fix.** The four call sites ask `a.child_id = any(array(select …))`: an equality on a computed list, which Postgres does push
below the grouping, so the view reads the class's rows only. No migration, no index: the existing
`evidence_event_child_idx (child_id, observed_at)` is used.

**Measured** (this machine, `bin/testdb fresh` plus 41 classes of 12 children, 28,536 evidence rows, a class of 40 `U71-BIG`):

| | skill page's own query (EXPLAIN ANALYZE) | skill query in the Postgres log during the u71 test (4 loads) |
|---|---|---|
| before | 324, 424, 471 ms (798 ms on the first run) | 262-335 ms each, plus 12 + 16 slow calls from the class and topic loaders |
| after | 1.5-6 ms | none at or above 150 ms |

`pytest tests/test_db_plans.py`: 5 passed after; the new source guard fails on the old code and passes on the new.

## Handoff

- **Not visible in the page time on this machine.** Here every page of the site takes 1.0-1.4 s, because the layout's
  `topics()` (`lib/queries-people.ts`) takes 0.87 s median / 1.04 s max on every load (32 calls in the u71 run) and runs beside
  the skill query. The u71 test's page times were 1121 ms before and 1124 ms after on the skill page; they are the same
  because the larger of the two queries sets the time. CI measured the class page at ~460 ms, so there `topics()` is under
  that and the skill query was what set 1.1 s; after the fix the skill page should sit near the class and topic pages
  (460-500 ms). That is CI's to show; I could not reproduce CI's hardware.
- **Seen, not fixed (not this cause):** `topics()` itself, a topic x class x skill matrix that calls `skill_taught_in`,
  `class_band` and `grade_ord` per cell: ~0.9 s here with 42 classes. M0-03 recorded it too. It needs its own goal.
- Also seen: the `papers_raw` query is ~300 ms (4 calls in the u71 run); not on these pages' path.
