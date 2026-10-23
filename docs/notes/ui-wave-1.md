# ui-wave-1: every redesigned page of the educator's week, in one merge

Nimish, 23 Oct 2026: "I don't want to see all before-after; just go ahead and build the whole flow and get it live
properly - only when I see it and interact with it on the dashboard can I suggest changes". Goal: `goals/ui-wave-1.yaml`
(`bin/engine done ui-wave-1`). Web only: no migration, no engine change.

Supersedes the stacked drafts #290 #292 #297 #299 #301 #302 #304 #306 #307 #309 #310 #311 #312.
Branch order: #290 (updated with main) → Curriculum + Staff/School (#297, #301) → main (already inside #290's update).
#314 (whose-paper checking) was not green when this was built, so it is not in; it merges into main on its own.

## Verified

Run on a database built from this repository (`bin/testdb fresh`), as CI does, at 1440 px.

- Full browser suite on the merged tree before the flow spec: `npx playwright test` → 371 passed (16.5 min).
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
