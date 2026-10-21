# ux8d-phone-and-one-action

Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now for math, making sure that every screen and
every other representation is thought through well: it's clear, it's accurate, clickability is fine." Slice UX8d of the
audit in `docs/notes/ux8-every-screen.md` (#253): its findings 18 and 23–25.

## Verified

- Measured first: `u47-phone-and-one-action.spec.ts` on main's code, all four failed. More than one terracotta action
  on 13 page-and-role pairs (198 on the coordinator's Curriculum); 520 actions under size on a phone; the stage and the
  "Why" off a phone's screen; "How m"; "Grade 1–Grade 4".
- After the change: u47, u43, u13, m4, screens and the maker's tests: all passed but u15, which fails only on a database
  the suite has already filled (its own class pack falls past Today's first five). On a fresh one it passes.
- `bin/engine done ux8d-phone-and-one-action` (2026-10-21, on a fresh database): all four of Nimish's sentences PROVED;
  "every page still holds": 290 passed (11.7 min); `bin/check`: 28 passed. NOT DONE only because the work is not on
  main or live yet. A first run failed u22: a second copy of the stage, hidden on a wide screen, was still the name
  cell's text. On a phone the columns a row's copies repeat now fold away instead, and nothing is shown twice.

## Handoff

- **Live:** nothing yet; this pull request waits for review.
- **What changed:**
  - One loud action per page. Today's first waiting line keeps terracotta and the rest are outlined. Outlined too: the
    topic switches, "Say it is taught", Show, Read it, "Change this child", and a child's "Sign off" (that page's main
    action is approving the home assessment).
  - On a phone (under 768 px wide): buttons and chips at least 44 px tall; toggles, fields, tick boxes and a table's
    one link at least 24 px. One rule in `globals.css`, not page by page.
  - On a phone, Assessments folds Kind, Class, Copies and Score so where an assessment stands sits beside its name, and a class's home assessments show the
    reason under what each child works on.
  - The one-child paper's number field is wide enough for "How many"; the menu says "Grade 1 to Grade 4".
- **Database:** none.
