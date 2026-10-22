# uxf-today: Today moves onto the page blocks

Second page after Check answers (docs/notes/uxf-ux-foundation.md, docs/ux-rules.md): web only, no migration, no new table.
Stacked on PR #279 (it holds the blocks); the diff here is Today alone.

## Verified

- Today (`/today`) is built on `PageShell`: the first thing that waits (in Today's order) is the one main action at the top,
  every line's own button is outlined, and the page ends on "Assessments". The week-by-week table is a `DataTable`
  (ten weeks to a page, `?weeks=2` for the next; a list of labelled cards on a phone; an all-zero column is not drawn).
  `workflows.json` `ux.frozen` loses `/today`.
- `bin/check` → 30 passed (the list shrank by one, so `test_the_list_only_shrinks` holds).
- On a `bin/testdb fresh` copy of this branch: `u1-today`, `u14-the-queue-shrinks`, `u44-numbers-true`, `s41`, `u51-ux-rules`
  → all pass; `u15-menu-and-today` passes but for the known "Today lists everything…" (Today shows five class packs and
  "and N more"; a copy that has run many specs holds more than five; it also fails on #279's head, and passes in CI's fresh copy).
- One spec changed, and why: `u44` added up "Still waiting" as the fifth column of the week table. The table no longer draws an
  all-zero column (rule 4), so the column moves; the spec now finds it by its heading and asserts the same sum.

## Handoff

- **Live:** nothing until merged and deployed.
- **Next:** Papers to approve, Print and give, Children (A child), then Curriculum (`/`), in the educator's week order.
- Not held: the menu still shows a red count on every tab (rule 5 allows red on Today alone).
