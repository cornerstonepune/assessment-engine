# reader-learns-audit — is ADR 0032 really happening?

Nimish, 2026-10-21: "if what you are mentioning, ADR, is at least happening, that's something we need to ensure from a
codebase point of view." Goal: `goals/reader-learns.yaml` (five `says` lines added). ADR 0090.

## Verified

**On live, read only**: `.github/measure/reader_learns.py`, run by Actions → engine logs on this branch (runs
39571745907, 39572107800, 39573658534, 21 Oct 08:46–09:01 UTC). It ran in a read-only transaction and printed counts
and dates only.

| ADR 0032 promise | on live, 21 Oct | verdict before this branch |
|---|---|---|
| every check rebuilds the child's notebook | 16 notebooks, 16 checked children; all 16 older than their child's last check. Newest rebuild 16 Oct 16:18, last check 16 Oct 18:46. The 16 Oct papers (5 papers, 5 children, 87 typed, 0 signed off): no notebook rebuilt after them. | partly: rebuilt only when the child's next paper is read |
| the next read uses it: own floor | floors 70 ×2, 80 ×1, 90 ×1, 95 ×12. Checks: 907 by region (21–28 Sep), 415 in boxes (26 Sep–16 Oct). A printed paper was read against the digit reader's 90 for every child. | not on printed papers |
| routed kinds | bare_sum ×2, word_2step ×3, legacy_bare ×7, legacy_missing ×5, legacy_word ×4 notebooks. 27 notebook flags in the week of 28 Sep. | working |
| confused digits flagged | 12 notebooks hold confusions; no reading since 1 Oct held a digit confused twice (0 flagged, 0 missed) | in code; nothing to flag yet on live |
| second reader with the child's samples | `read_with_examples` v1 active; eval 9 of 16 (DECISIONS-LOG, 22 Sep). 86 guesses, the last on a paper read 29 Sep. Since 1 Oct, 8 doubted readings, all 8 already carrying the box reader's own guess, so it was asked about none. | wired; dormant on printed papers |
| trust per kind at 95% | bare_sum trusted (48 of 50). column_grid 47/50, needs 5 more; grid_method 38/39, needs 11; the rest 35–48 more. | working; but 85 checks were answers no person was shown, 8 in legacy_word's window |
| measured per batch, proven by replay | `engine read report` per batch, printed by engine logs; replay is a CLI (`engine read replay`) | working (report); replay not rerun here |

Answers per paper, week by week, since September (papers read that week; "to a person" is every answer except
auto-accepted and never-read):

| week of | papers | children | read | auto-accepted | kind not trusted | wrong held | blank held | reader unsure | notebook flag | spot check | to a person per paper |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 21 Sep | 87 | 16 | 1029 | 143 | 319 | 217 | 110 | 240 | 0 | 0 | 10.2 |
| 28 Sep | 20 | 10 | 228 | 0 | 86 | 18 | 25 | 72 | 27 | 0 | 11.4 |
| 12 Oct | 5 | 5 | 93 | 7 | 67 | 11 | 0 | 8 | 0 | 0 | 17.2 |

It is not falling. The 12 Oct week's papers are printed papers of kinds that have not earned trust yet: 67 of the 93
answers waited only for that.

**The silent-error gap**: a trusted kind's right answers go to a person at `marking.spot_check_rate` (0.15,
`marking.spot_checked`, `test_legacy.py::test_a_trusted_kinds_right_answers_are_spot_checked_at_the_rows_rate`). On live,
7 answers have been auto-accepted since trust was earned, and 0 were spot-checked. At 15%, finding none in 7 happens
about a third of the time (0.85^7 ≈ 0.32), so 7 answers cannot show whether it fires on live. No proposal needed:
the sample already exists as a threshold row.

**Fixed on this branch** (ADR 0090), each with a test that fails on main and passes here:
- `profiles.refresh` after `/capture/correct`, `/commit`, `/capture/trusted`. Tests:
  `test_profiles.py::test_a_check_rebuilds_the_notebook_of_the_child_checked_and_no_other`, and
  `api/test_capture_routes.py::test_every_check_rebuilds_the_notebooks_it_made_stale_correction_and_sign_off_alike`.
- `box_floor`, measured on readings made in boxes, raises the digit reader's floor on a printed paper. Tests:
  `test_profiles.py::test_a_childs_floor_on_the_box_reader_is_measured_on_that_readers_readings_alone`, and
  `test_copies.py::test_a_printed_copy_is_read_against_the_childs_own_floor_on_the_box_reader_never_below_the_readers`.
- `answer_checked` counts a signed-off answer only if it waited for a person (migration 20261126090000). Test:
  `test_profiles.py::test_an_answer_signed_off_that_no_person_was_shown_is_not_a_check`. `tests/rows.a_read_paper` now
  gives a confirmed answer the hold it waited with, as marking does.

## Handoff

- **Live:** nothing changed. Not migrated, not deployed. The measure runs read only, from engine logs.
- **On merge:** run migrate, then deploy the engine. Notebooks become current at the next check, or the next read.
  A printed paper is then read against each child's own floor in boxes (`box_floor`, from their 415 checks in boxes
  so far). A child whose readings in boxes were never 95% right at any level has every reading of it sent to a person.
  I have not counted how many children that will be.
- **Decision for Nimish:** the second reader is never asked on printed papers, because the box reader always offers
  its own guess. Ask it there too, as a second opinion? That is a change to ADR 0032 §4, not built.
- **Not certain:** the confused-digit flag has had no reading to act on since 1 Oct, so it has not been seen working
  on live. The tests prove it in code.
