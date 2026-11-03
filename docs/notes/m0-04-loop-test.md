# m0-04-loop-test: the whole-loop test stops failing by chance

Task M0-04 (workflow: W3, gate N10, the graph's window; test setup only, no engine, schema or seed change).

## Verified

- **Cause, by evidence.** Each CI shard builds its own database and its question bank is drawn from an unseeded
  generator (`w1_bank/refill.py`: `rng or random.Random()`), so no two builds hold the same papers. The graph reads a
  skill's latest `state.window_answers` (10) answers at a level, and a mistake repeats there on `state.repeat_min` (2) of them
  (migration 20261223090000). `test_the_loop` planted the mistake with most places on the paper, which are early boxes; a
  build that drew more questions for that skill than the window holds pushed them out, and the graph rightly said nothing
  repeated. The CI logs (run 41654671878 attempt 1, shards 7 and 12) show `seen == planted` passing and then `graph []`.
- **Reproduced**: on a database built by `bin/testdb fresh`, with the graph's window set to 6 inside the test's transaction,
  the old selection fails with `AssertionError: MD.EQUALITY Easy: graph []` and `MD.MULTIPLES Easy: graph []`, the two CI
  messages; the new selection passes. That is `test_the_loop_holds_when_the_graph_reads_fewer_answers_than_a_paper_has`.
- **Fix**: the test now plants the mistake the graph can see repeating inside one skill's window, computed from the same
  threshold rows the graph reads (`_planted_to_repeat`). No assertion was loosened and no limit raised.
- **QR**: `test_calibration` built a sheet code from six random hex digits (24 bits) in a column unique across the shared
  test database; it now uses the whole random id. `test_two_papers_whose_random_ids_start_alike_are_both_stored` fails on
  the old line (UniqueViolation) and passes on the new.
- Not changed, same pattern, named for a later task: `"CS" + uuid4().hex[:6]` in `test_child_move.py`,
  `test_learned_mistakes.py`, `test_learn.py` (and `hex[:6]` ids in `test_grades.py`, `tests/rows.py`).

## Handoff

- **Live:** nothing; tests only.
- **Next:** the orchestrator re-runs CI five times on this branch and counts green runs.
