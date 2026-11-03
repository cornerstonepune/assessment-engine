# m0-04b-loop-test-bank: the whole-loop test chooses its mistake from the bank it actually has

Task M0-04b (workflow: W3, gate N10, the graph's window; test setup only, no engine, schema or seed change).
Follows M0-04 (PR #356). CI of PR #367, engine shard 2, 2026-11-03:
`test_the_loop_holds_when_the_graph_reads_fewer_answers_than_a_paper_has[MD.MULTIPLES-Easy]` failed with
"no next question can show M_LAST_DIGIT_RULE_MISAPPLIED". PR #367 is unrelated.

## Verified

- **Cause, by evidence.** Each build draws its bank from an unseeded generator (`w1_bank/refill.py`: `rng or random.Random()`),
  so what a level can show differs per build. Four fresh builds (`bin/testdb fresh`, local Postgres 16), MD.MULTIPLES Easy,
  questions that can show `M_LAST_DIGIT_RULE_MISAPPLIED`: **0, 1, 0, 4** (`drawable_item`; the level holds 36). The test chose
  the mistake from the paper alone. The child's next paper (`focus_paper._draw`) takes questions the child was not just given
  before any they were, so a mistake whose only questions in the bank are on the paper just signed off cannot be shown again.
  Not a fault of the paper-maker: the test asked the bank for what a build may not hold. A lure ("is 34 a multiple of 4?") is
  drawn by chance inside a case, not as a case of its own, which is why the count moves.
- **Fix** (`tests/test_the_loop.py`, tests only): `_planted_to_repeat` now also requires the bank to hold a question, not on the
  paper, made for the skill the mistake is counted on, at the level the next paper will work at. That level is asked of the
  code (`focus_paper._where_it_shows`), not copied. No assertion loosened, nothing skipped, no limit raised.
  When no mistake qualifies the test fails with "BANK DEFECT, not a test fault …", a different message from "the paper shows
  nothing twice".
- **A separate check on the bank**: `test_the_bank_holds_a_mistake_the_loop_can_plant_and_show_again`, every new skill set at
  every level (76 cases; 2 skip because the set has no such level): some mistake is shown by two or more questions.
- **The condition forced, on any build**: `test_a_mistake_the_bank_cannot_show_again_is_not_the_one_planted` takes the paper's
  mistake out of every other question of the skill set (same size bank) and asserts the choice passes over it. Measured when
  the same condition ran the whole loop (a version of that test, replaced; see "Found"): with the old choice
  `AssertionError: MD.MULTIPLES Easy: no next question can show M_REVERSES_CLAIM_TRUTH …`, the CI message; with the new one, passes.
- **Failure rate.** Old choice on 50 different banks: **0 of 50** failed; it could not be reproduced by chance on my banks, only
  forced. (CI saw it on some builds; I did not see the mistake chosen that way. Not a measured CI rate.) New tests on the same
  50 banks: **0 of 50** failed.
- **50 different banks.** `bin/testdb fresh` once, then per seed 1–50 a clone of that database with MD.MULTIPLES Easy and
  MD.EQUALITY Easy deleted and drawn again from `random.Random(seed)` (`refill.top_up`), their library worksheets rebuilt
  (`library.build`). Each seed ran `test_the_loop_holds_when_the_graph_reads_fewer_answers_than_a_paper_has` (2),
  `…_cannot_show_again_is_not_the_one_planted` (2) and the 76-case bank check. Result: **50 of 50 seeds: 78 passed (2 + 2 + 74), 2 skipped,
  0 failed**. Only those two levels vary between seeds; the rest of each bank is the one fresh build's.
- **test_calibration.py** has no bank assumption: `_a_skill` reads `skill_level` rows, not drawn questions. Unchanged.

## Found, not fixed (a decision for Nimish, not for a test)

- **One wrong answer, two true readings.** A multiples list with one wrong number swapped in is named `M_MULTIPLE_MISSED` *and*
  `M_NOT_A_MULTIPLE` by the marker; the graph then reports one of the two (here `M_MULTIPLE_MISSED`) by its own tie rule, so a
  child who always makes the swap is told the other mistake. It surfaced when a whole-loop run was forced onto
  `M_NOT_A_MULTIPLE` (seeds 3, 4, 5, 8 …, MD.MULTIPLES Easy). A natural run can hit it when the choice lands on such a
  mistake, as the old choice could.
- **Mistakes a skill set names that no question shows, any level** (`drawable_item`, four builds): MD.EQUALITY ×3
  (`M_MUL_COLUMNWISE`, `M_MUL_ONE_ROW`, `M_MUL_PLACEHOLDER`) and MD.MENTAL `M_MUL_CARRY_ONTO_ZERO_LOST`, DIV.3D1D and
  MD.ESTIMATE `M_DIV_TENS_ZERO_EXTRA` on every build; others on some builds only (`M_DIV_EXCHANGE_LOST` on one,
  `M_DIV_QUOTIENT_ZERO_DROPPED`, `M_TENS_ZERO_DROPPED`). A child who repeats one of these is given a paper that cannot
  show it. The generator (a lure is drawn by chance, not as a case) is where a guarantee belongs.
- Same pattern, named earlier and still not changed: `"CS" + uuid4().hex[:6]` in `test_child_move.py`,
  `test_learned_mistakes.py`, `test_learn.py`.
- The brief quoted "The platform's checks give the same answer every time for the same code." as Nimish's recorded sentence.
  It is in no file of this repository; M0-03 and M0-04 record "All parts should just function like a well-oiled machine, right?",
  which this goal uses.

## Handoff

- **Live:** nothing; tests only.
- **Next:** the orchestrator re-runs CI on this branch; a decision on the two "Found" items (the generator's guarantee, and
  which mistake the graph names when an answer fits two).
