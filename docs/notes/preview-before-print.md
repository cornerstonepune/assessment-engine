# preview-before-print

Nimish, 2026-10-21: "a teacher can only see the assessment when they print. They click on print just to see the
assessment, but after the printing is done, they feel like the assessment is not good." He said yes to "that preview
before printing starts". Goal: `goals/preview-before-print.yaml`.

## Verified

Each line names the command that proves it; outputs are this session's, on a fresh `bin/testdb fresh` copy.

- A preview, and every "Different questions" draw of it, writes no sheet, template, seen question or prescription; a
  print after it is exactly the questions shown, in order, for one child and for a class batch; a paper whose
  questions changed since they were shown prints nothing —
  `cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_seen.py tests/test_focus_paper.py tests/test_maker.py`
  → `39 passed`.
- The child's page, a class's home assessments, a paper chosen for one child and Make papers each show the questions
  under their skill and level, change them without making a paper, and print the ones shown —
  `cd apps/web && npx playwright test tests/p4-preview-before-print.spec.ts` → `3 passed`.
- The pages that made papers before still do — `npx playwright test tests/s11-focus-paper.spec.ts
  tests/m2-make-papers.spec.ts tests/m4-the-maker.spec.ts tests/m5-every-kind-draws.spec.ts
  tests/s7-paper-from-library.spec.ts` → `23 passed`.
- `bin/check` → `28 passed`, lint clean.
- The route tests now preview before they print; a print with no `seen` is refused (422), one with another paper's `seen`
  is refused (412) — `uv run pytest -q tests/api/` → `83 passed`.
- The class's home assessments still say the shared count once — `npx playwright test tests/u38-make-and-marking.spec.ts
  tests/u2-children.spec.ts` → `13 passed`.
- CI on `ccb3802`: engine `2609 passed, 2 skipped … in 1955.00s (0:32:35)`; browser, web green.
- `bin/engine done preview-before-print` → all seven of Nimish's sentences PROVED; criteria: the paper tests `39 passed`,
  `bin/check` `28 passed`; the whole suite "timed out after 1800s" there, because the suite takes 32 minutes on CI and
  longer here — the same criterion on every goal, not raised. CI above is the whole suite's own run. Report: NOT DONE on
  that line alone.

## Handoff

- **Live:** nothing yet; the pull request waits for review and merge.
- **What changed:** every plan the website shows carries `seen`, a code for its children and questions in order
  (`w2_print/seen.py`). "Different questions" is the same plan drawn again with the next `draw` (a seed, no rows).
  Printing sends `draw` and `seen` back; the engine re-plans that draw under the child's lock and prints only if it is
  still what was shown, else answers 412 and the page shows the questions as they are now. The three print routes
  now require `seen`, so nothing prints from the website without having been shown.
- **Draw 0 is unchanged:** the seed is the old one, so every existing plan and test draws as before.
- **Not here, on purpose:** a library worksheet's questions are fixed and its page shows it before printing for
  children; the class's weekly pack is assembled and approved on `/papers/approve`.
- **B1 (#234) and B2 (#240):** this adds a `draw` argument to `focus_paper.plan`, `make`, `_planned`, `preview` and
  `maker.plan`, `_plan`, `_for_all`, `make`, and one `seen.check` line in each `make`. Whoever merges second keeps both.
