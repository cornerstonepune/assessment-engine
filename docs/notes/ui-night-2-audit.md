# ui-night-2-audit: the educator's site walked at 1440 px, page by page

Nimish's night orders, 2026-10-22 (`docs/notes/night-orders-2026-10-22.md` on `claude/sleepy-keller-j2ybm5`): desktop first;
a list is a table; status is icon + word + red/amber/green; every table has a filter row; nothing in a shared block names
a subject. Audit slice of UI part 2 (Curriculum, Question bank and Library, Children, a child, the class page, School,
Staff, Approvals). Web only, no migration, no new table.

## How it was walked

`bin/testdb fresh` on a local Postgres 16, the engine and a production build of the website against it, a cookie signed
as `lib/auth.ts` signs it, 1440 × 900. Fake data only: twelve children (`Test1`–`Test12`) in G3-A, G3-B, G4-A, and three
staff: the coordinator, `admin@cornerstoneschool.in` (educator, no classes: Ayush) and Achal (educator, G4-A).
English is not in the copy: E0 (#284) is not on main yet, so the English educator's seat is checked after it is green.

## Findings (screen, what is wrong, the fix, slice)

| # | Screen | What is wrong | Fix | Slice |
|---|---|---|---|---|
| 1 | Curriculum `/` | Four collapsed "Grade n" bars and "Open everything / Close everything"; nothing is visible until opened. The header line reads "grade · subject · topic · skill" but there are no columns. Subject appears only as a tag once opened. No status, no filter. | One table: Grade, Subject, Topic, Skill, Levels approved, Status chip (icon + word + red/amber/green); a FilterBar (grade, subject, topic, status, search); the setup links ("Question bank details", "Taught in each class") moved behind one details link. | CUR |
| 2 | Skill page `/skill-sets/[code]` | A 2,569 px page of five stacked cards; "approved" is a grey tag reading `bin/testdb, as live`; level cards are three unequal boxes with clipped tags; five tab-buttons at the top; the kinds table says "horizontal sum" (kind words on an educator's screen, rule 6). | A level table: one row per level (Easy / Medium / Hard / Advance), the words, one example, approved by and date, one Approve button; status chip. Kinds and mistakes under details. | CUR |
| 3 | Top bar, every page | The Class selector is cut off ("Every clas"); the student search is a strip 900 px wide. | UI part 1 owns the top bar. Not touched here; checked again once it lands. | (part 1) |
| 4 | Question bank / Library `/library` | 8,204 px, 78 rows in two tables, no filter, no status. | A table with FilterBar (skill, level, kind, status) paged at 10, the rest behind "more". | LIB |
| 5 | Worksheets by taxonomy `/worksheets/taxonomy` | 13,486 px, 90 tables on one page, "taxonomy" in the title (rule 6). | Take it off the educator's page; one table, grouped, behind details. | LIB |
| 6 | Children `/growth` | Grade cards with collapsed class rows and prose ("4 children · nothing waiting"); "Children who need you" is a card with a sentence. | A table: Class, Grade, Children, Needs you (chip), Last assessed; FilterBar (grade, class, status). Class row opens the class page. | CHI |
| 7 | Class `/growth/class/[section]` | Four nested tables; no filter. | One children table (name, topics, status chip) with FilterBar and 10-row paging. | CHI |
| 8 | A child `/growth/[id]` | Blank when the child has no results: no next step, no explanation. | EmptyState with the next step ("Give the first assessment"), then the by-topic table with status chips. | CHI |
| 9 | Approvals `/papers/approve`, `/skill-sets/approve` | `/papers/approve` is a placeholder ("What this screen will show") plus a "database today" box of zeros; `/skill-sets/approve` is empty with no way on. Both are on `ux.frozen`. | One approvals table (what, class, grade, status, Approve), empty states that say what comes next. | APP |
| 10 | School | There is no School page: `/school` is a 404. | A School page in the shared anatomy: classes, children per class, who teaches (reads the existing tables). | SCH |
| 11 | Staff | There is no Staff page: `/staff` is a 404. Who teaches which class lives only in `config.app.staff` and is edited by `engine staff classes`. Ayush's login exists with no classes, so he sees nothing. | A Staff page: a table (person, role, classes, subjects), the coordinator edits classes with checkboxes, saved the way `engine staff classes` does. **Schema follow-up:** `config.app.staff` has no `subject` field and a JSON value in `config` is not a table; subject per person needs a core-track decision. The class part is built; subject is left to the core session. | STA |
| 12 | English educator's seat | Cannot be walked yet: E0 (#284) is not on main. | Walk it when #284 is green; fix friction in a PR stacked on its branch. | ENG |

## Order of the PRs

Part 1's design system first (`claude/ui-night-1-design-system`), then CUR, STA, CHI, LIB, APP, SCH, each stacked on the one
before, ENG on #284's branch. Each: a failing check first, `bin/check`, the whole Playwright suite on a fresh copy, CI green.
