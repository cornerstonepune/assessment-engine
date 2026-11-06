# u49-papers-race

## Verified

- **What failed.** `tests/u49-one-role.spec.ts`, "an educator reaches every page and every action the coordinator
  does", failed on /papers in CI browser shard 3 on two unrelated PRs (#420 run 42097568153, #424 run 42104501147).
  - The coordinator was "offered" Child, Level, Roll, `/papers/card` and two worksheet links that the educator was not.
  - It passed on a re-run.
  - It reproduced locally in about one run in five of `--shard=3/3` on a fresh database (`bin/testdb fresh`).
- **Cause, proven.** To count what a folded section would show, the test clicks every `[aria-expanded=false]` in `main`
  and then reads the page. Nothing waited for the click to take effect.
  - On /papers an assessment's row toggle is a link (`assessments-table.tsx`, `aria-expanded={open}`). It opens the
    row by loading `/papers?open=<key>`, and the open row is where the children's table (Child, Level, Roll) and their
    worksheet links are.
  - So whether a row read as open depended on whether that person's page load had landed before the read.
  - With the fix, a logged run shows both people ending on the same
    `/papers?open=earlier~U47-CLASS~~ADD.2D2D`, both with the Roll column.
  - On each of the 20 pages the two people end on the same address, with equal action counts except one page where
    the educator is offered more.
  - Nothing about who sees what differed: the two worksheets were class U48-G3's, which the educator is mapped to and
    `staff_sees` allows.
- **Fix, at the cause.** `unfold()` clicks one toggle and waits for that toggle, by its words, to say
  `aria-expanded=true`, then for the network to settle.
  - The fold marker (▸ or ▾) is left out of its words, since it is the one part that changes.
  - No sleep, no skip, no loosened assertion: the comparison is unchanged and now always compares open rows.
- **Checks run.**
  - `npx playwright test tests/u47-phone-and-one-action.spec.ts tests/u48-no-guessed-pages.spec.ts tests/u49-one-role.spec.ts --workers=1 --retries=0`
    on a fresh database → 8 passed.
  - `--shard=3/3` on a fresh database → u49 passed.

## Handoff

- Live: nothing; this changes a test only.
- Next: none.
