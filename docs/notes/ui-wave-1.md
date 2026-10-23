# ui-wave-1: every redesigned page of the educator's week, in one merge

Nimish, 23 Oct 2026: "I don't want to see all before-after; just go ahead and build the whole flow and get it live
properly - only when I see it and interact with it on the dashboard can I suggest changes". Goal: `goals/ui-wave-1.yaml`
(`bin/engine done ui-wave-1`). Web only: no migration, no engine change.

Main moved while this was built: #290 itself merged (with #317, CI retry, and #318, a skill's name opens the skill), so
main was merged in at the end (one conflict, `topics.tsx`, both sides kept).

Supersedes the stacked drafts #290 #292 #297 #299 #301 #302 #304 #306 #307 #309 #310 #311 #312.
Branch order: #290 (updated with main) → Curriculum + Staff/School (#297, #301) → main (already inside #290's update).
#314 (whose-paper checking) was not green when this was built, so it is not in; it merges into main on its own.

## Verified

Run on databases built from this repository (`bin/testdb fresh`), as CI does, at 1440 px.

- Full browser suite, run from nothing on a database built by `bin/testdb fresh` (as CI does) on the finished page code:
  `npx playwright test` → 379 passed, 1 failed (my own flow spec's Curriculum step, a read made before the filtered table had
  drawn; fixed, `u60` → 9 passed). An earlier full run on a database already used by a first run failed 6 older specs
  (`s2`, `s43`, `u15`, `u26`, `u43` and the flow spec): they leave rows behind and are written to run once on a fresh
  copy. They all pass on a fresh one. After the last merge of main: `s2`, `s43`, `u15`, `u26`, `e2e`, `u13`, `u30`, `u52`,
  `u53`, `u60` pass on a fresh copy; `u51`'s "Check answers lists what is left" reads a column that needs the other specs'
  papers, as on main.
- `bin/engine done ui-wave-1` → both of Nimish's sentences PROVED, 3 of 3 criteria PASSED; it ends "NOT DONE" only for "not on
  main yet" and "the live database did not answer from here". `bin/engine done uxn1-design-system` → 3 sentences PROVED,
  3 of 4 criteria PASSED; its fourth is the whole browser suite, which failed there because it ran on a used database (see
  above). The other twelve UI goals each carry that same whole-suite criterion (about 20 minutes each, and a rerun on a used
  database fails the same way), so they were not run through `engine done`; the one clean full run above covers their specs.
- `tests/u60-ui-wave-1-flow.spec.ts` (new): Today → Assessments (upload box above the table, one row per assessment, the class
  filter and its clear) → Papers to approve → Print and give → Upload papers → Check answers → Marking → Class results (a
  class, a child) → the Assessment card → Curriculum (the Subject filter, then the top bar's subject, Maths and English) →
  Staff → School, and each page's next step opens the next page. On every page: each table's head sits over its columns
  (position and width), no heading overflows its column, a status is an icon plus a word, a filter row is there, every row
  has a way in, and "This page could not load" never shows. → 9 passed.
- `bin/check` → passed. `npx tsc --noEmit`, `npx eslint --max-warnings 0` → clean.
- Engine tests the merge touches (`test_same_page`, `test_e0_english`, `test_question_registry_skills`, `test_ux_rules`,
  `test_layout`, `test_ratchet`) → 42 passed.

## Found and fixed while walking the flow

- Papers to approve, with no week planned, was an old panel with no next step (a dead end): now on the page shell with a way on.
- Its rows and Today's week-by-week rows opened nothing: a child's name opens the child; a week opens that week's Assessments.
- Class results headings broke inside words ("ROL L", "PRACTIS ING"): headings never split a word now (`globals.css`), the
  squeezed columns are wider, and the flow spec fails if a heading ever overflows its column.
- Curriculum listed English skills first under "Maths" with no way to choose: the filter row has a Subject dropdown (built from
  the data's own subject names).
- Taught this week printed 84 class codes under every topic: more than eight classes fold behind "Not taught yet in N classes".
- "1 papers" on a class's home assessments.

## Handoff

- gstack could not be installed in this session (the permission layer refused the clone-and-setup command), so
  /design-review, /qa and /review did not run; the same checks were done with Playwright and the Superpowers skills.
- The spec is named `u60-ui-wave-1-flow.spec.ts`, not `ui-wave-1-flow.spec.ts`: the Playwright config only runs files named
  `[sump]<digits>-…`, and it was not to be touched.
- When #314 merges into main, `capture/check` and `capture/[id]/card.tsx` will need main merged in; the Yes button moves into
  the answer box there.
- Left alone on purpose: Today's list of counts is still a list, not a table (its own slice); the four "Make an assessment"
  tiles under the upload box on Assessments push the table down the page (a decision for Nimish once he has used it).
