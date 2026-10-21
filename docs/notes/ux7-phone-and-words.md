# ux7-phone-and-words

Nimish, 2026-10-15: "Most of the pages just have a long list for no reason. All these things should be expandable and
collapsible. They should have the right set of columns which are important. It should be teacher-specific." He said
"go" to UX6 and UX7 on 2026-10-21. Same branch and pull request as `ux6-curriculum-for-the-educator` (#247).

## Verified

- Measured first: every page, as an educator and as the coordinator, at 400 px, on a fresh `bin/testdb fresh`:
  - every heading sat at 394–429 px (446 on a worksheet or skill page), below the whole menu;
  - dates came in three formats ("21-Oct-2026", "21 Oct", "2026-10-21");
  - weeks appeared raw as "2026-W43" on home assessments, a class's week and a paper's page;
  - grades appeared as "G2" in the bank's grade column;
  - green was "got it" in keys and "secure" in counts, grey "not enough yet" and "too few answers".
- `u43-phone-and-words.spec.ts`, one test per sentence, crawling 29 pages as each role at 400 px. It failed first
  (headings 394–429 px), and passes now: 6 passed.
- `bin/engine done ux7-phone-and-words` (2026-10-21, on a fresh database after merging main with B1): all six of
  Nimish's sentences PROVED. "Every page still holds": 282 passed (10.3 min). `bin/check`: 28 passed. NOT DONE only
  because the work is not on main or live yet.

## Handoff

- **Live:** nothing yet; #247 waits for review and merge.
- **What changed:**
  - **The menu.** On a phone it is one row of tabs, and who is signed in is a footer outside `main`. `PageHeader` is
    tighter there, with the stage on one line.
  - **Dates** go through `dateWords` in `lib/week.ts` ("21-Oct-2026"). It replaced eight local copies and the
    "21 Oct" and ISO forms. The parent letter uses it too.
  - **Weeks** go through `weekWords` everywhere, and a paper with no week says "no week".
  - **Grades:** the bank's grade column shows the grade's name.
  - **Colours** are said with `state_colour.count_words` only. A state with too few answers is said as its colour
    (`States.say`). The child's summary reads "is secure on", built from the row.
  - **Tests:** u2 and u36 now expect "is secure on" in place of "has got". u40 opens Grade 2 only when it is closed.
- **Database:** none.
- **Nimish to decide:** `state_colour.words` ("got it", "not enough yet") is now read by no page. Dropping it is a seed
  and migration change, outside this screens-only slice.
