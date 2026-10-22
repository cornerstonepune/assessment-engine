# s2b-assessments-declutter: Assessments, calm and one count one meaning

Slice S2b, on S2 (#274), after Nimish reviewed the live Assessments page on 2026-10-22: "Look at the clutter", "The
current frontend is extremely confusing to me... make it much, much cleaner." W2 (N4–N7) and W3 (N8–N9) screens; no
workflow gate moves. Goal: `goals/s2b-assessments-declutter.yaml`. No migration, no new table. Children and Curriculum
(#278) and the check screen (#276, #277) are not touched.

## Verified

- `apps/web/tests/s44-assessments-declutter.spec.ts` failed first on #274's code (the four cards were still on the page:
  1 failed, 6 did not run), and passes here: 7 passed.
- The count test fails without the rule it proves: with "a paper put away" taken out of the shared definition it failed
  (3 expected, 32 received), 2026-10-22. Restored.
- Full browser suite on a database built by `bin/testdb fresh`: 329 passed, 0 failed.
- `bin/check`: 30 passed (it skips the migration-order test until `git fetch origin main`; with main fetched it runs).
- `bin/engine done s2b-assessments-declutter`: see the end of this note for its output.
- Nothing in the engine changed; the engine's tests are untouched.

## What changed, for an educator

- **Assessments opens on the one job.** The upload box first, then two buttons: **Make an assessment** (one button; for a
  class, for each child, for one child, a ready-made worksheet, inside it) and **Filter**. One line under the title.
- **Numbers only where someone must act.** No zero is drawn. The six stage chips and the topic chips are the Filter's
  Stage and Topic choices, with Class, Child, Kind and Week. "N answers to check" is a button only when N is not 0.
- **Past scans** (every scan already read, including old ones that found nothing) are behind a link at the foot, and so is
  **How the reader is doing**. A scan stays on the page only while it is being read or a page of it waits for a person.
- **A row says four things, each once:** its copies, the papers in ("2 of 3"), the answers to check, and what waits on a
  person as papers ("2 to approve", "1 to sign off"). The old row said "26 copies · 16 with the children · 10 to check"
  beside "120 waiting": a count of *papers* and a count of *answers* under the same word.

## One count, one meaning

The bug was real in the code, not only on the page. An answer "waiting for a person" was counted by five different
queries, each its own way: Assessments' list and card counted every unsettled answer, even on a paper that had been put
away; Check the answers and Today's line left those out; Marking counted by `answer_standing`; Today's weekly sentence
counted only this week's; each scan counted its own. So the same word gave different numbers on different pages.

Now `awaitingCte` (`apps/web/lib/queries-counts.ts`) is the one fragment. It takes the database's own word,
`answer_standing` = waiting, and adds the one rule a screen needs: the answer is on a paper that is not put away and
belongs to a child, so a person can be shown it. The list, the card, Check the answers, Today's line, Marking's "Answers
to check", each scan's line and Today's weekly sentence all use it. The weekly sentence now says "from this week", since
it counts only this week, and a week's line on the list says "answers to check" for answers and keeps "to approve" and
"to sign off" for papers.

- **One difference left, and why:** `engine read waiting` (the engine's command line) counts `answer_standing` as it
  stands, so it can be higher than the screens by answers on papers put away or given to no child. Making them identical
  means putting that rule into the `answer_standing` view, which is a migration; this task allows none. It is the one
  decision needed.
- Not changed, on purpose: Today's trend table ("Is the queue shrinking?") counts every answer read and where each ended
  up. That is the reader's record, not work to do, so it keeps its own meaning.
- A paper put away is no longer listed on Marking: its answers wait for no one.
- **Could not be checked from here:** the live numbers (120 on the list, 75 on the menu, 103 on Today). The live database
  does not answer from this container. The menu's and Today's totals are *sums of several lines* (answers, papers to sign
  off, class papers to approve, and so on), so they could never equal the answers alone; #278 leaves only Today with a
  red count. I found and fixed the definitions that disagreed; I cannot say they account for every one of the 120.
  Worth running `bin/engine done` against live after deploy and comparing the list's total with Check the answers.

## Menu (5b)

Left to #278, which already makes Today the only red count. This branch does not touch the menu, so the two merge in either
order; if #278 lands first, merge main in.

## Older specs that said the old layout (changed, not loosened)

`u9`, `u16`, `u22`, `u31`, `u33`, `u37`, `u47`, `m4`, `s11`, `s41`, `u3`. Each kept its title (older goals cite them); the
body now reads the Filter, the one Make button and the new row, with a dated comment. `u3` and `s41` restate the
one definition of an answer waiting. New helper: `tests/papers-page.ts`.

## Handoff

- **Live:** nothing until merged and deployed. No migration.
- **Next:** after deploy, open Assessments on the live site and on a phone; compare the list's "Answers to check" total
  with Check the answers and Today's line (they must be equal).
- **Not done here:** the dropdown of assessment kinds (waits on C5/C3, as S2 said).
