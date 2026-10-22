# s1-subject-class-and-today: the bar at the top, Today's five lines, a phone

Slice S1 of the scope Nimish locked on 2026-10-22 (`BUILD-ORDER.md` on #269, "the locked scope of 22 Oct"), built beside
the C slices because it needs no new table. Goal: `goals/s1-subject-class-and-today.yaml`.

## Verified

- `s41-subject-class-and-today.spec.ts` failed on main's code first (the bar not found), 2026-10-22, on a fresh local
  copy (`bin/testdb fresh`); passes on this branch: 5 passed.
- Neighbouring specs the bar and the class choice touch (u1, u13, u15, u18, u25, u26, u32, u33, u43, u46, u47, u49,
  screens): 69 passed.
- `bin/engine done s1-subject-class-and-today` (2026-10-22): all five of Nimish's sentences PROVED; `bin/check` 30 passed;
  "every page still holds" 310 passed, 1 failed: `e2e.spec.ts` "every kind of question in the bank is drawn with its own
  numbers" timed out at 30 s on `/library?fmt=missing_digit`, and passes run alone (26 s). This copy's bank was filled
  twice (33,042 questions, not about 28,700), which makes that page slow; S1 does not change it beyond the shared bar.
  CI's fresh copy decides. NOT DONE also because the live database did not answer from this machine.

## Handoff

- **Live:** nothing until merged and deployed. No migration.
- **What changed:**
  - **The bar** (`components/top-bar.tsx`) above every page: Subject (rows of `subject`; Maths only today), Class (your
    classes, every class, or one class) and a search box. The choice is a cookie (`choose`), a view, never a permission.
    "See every class" in the menu is replaced by the bar's Class; u26, u32 and u49 now choose there.
  - **Search** (`lib/search.ts`): a child by part of a name or a roll number, an assessment by its skill or title, a paper
    by its code; posted, never in an address.
  - **Today's five lines** (`lib/queries-week-note.ts`): papers back and answers read this week, checked and waiting,
    where the children stand, the mistake seen most, children needing help on two or more skills — for the class and
    subject chosen.
  - **Phone:** the menu is a row of tabs at the foot of the screen, so the bar and the heading sit at the top.
- **Open for Nimish:** the subject chosen counts in Today's five lines; with one subject the other pages are unchanged.
  Filtering every page by subject comes with a second subject's rows (S4, a tab per subject).
