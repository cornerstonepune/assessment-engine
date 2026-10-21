# ux8-every-screen

Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now for math, making sure that every screen and
every other representation is thought through well: it's clear, it's accurate, clickability is fine."

Phase 1 is the audit below; the report with its screenshots is claude.ai/artifact/3SML11631m2kGzGDfrCCf3 (private). No
screen changed on this branch. Phase 2 is four slices, UX8a to UX8d, each its own goal and pull request from main.

Note on the build order: `BUILD-ORDER.md` (2026-10-20) puts B0–B4 before any UX slice. Nimish's sentence above is newer,
so the slices follow it. None of them touches a migration, a seed or the bank's queries; B2 and B3 own those tables.
There is no "admin" role: the staff list knows `educator` and `coordinator` only, so the audit covers those two.

## Verified

- Built on a fresh test database, then the whole browser suite run once as the baseline and to make its test classes:
  `bin/testdb fresh postgresql://postgres:postgres@127.0.0.1:5432/postgres` (applied every migration, loaded the seed,
  28,700 questions, 2,737 worksheets), then `cd apps/web && npx playwright test`: **286 passed (11.2 min)**.
- A test educator teaching U38-CLASS and U37-CLASS (fake names: Asha, Bina, Chetan, Dev, Esha) and the coordinator.
- A crawler opened 35 screens as each role, at 1280 px and 390 px: **138 full-page screenshots**. Then it opened every
  link found on them: **2,884 links. 2,881 opened; 3 crashed** (parent reports, below).
- Things the crawl measured that hold: no page scrolls sideways at 390 px; no page errors on load; an educator opening
  another class gets "Not one of your classes", not the class.
- Counts recomputed with SQL that agree with the pages: Today's 3 answers to check (`answer_standing` = waiting, in
  U37/U38), 3 papers to sign off, Marking's 6 settled by the engine; the menu's 40 = 3 + 3 + 1 + 3 + 30; the
  coordinator's 162 = 83 + 76 + 3.

## Findings, ranked

Severity: wrong number > dead end or broken > unclear > inconsistent > polish. "Educator" and "coordinator" are the
roles; D is 1280 px, P is 390 px.

### Wrong numbers and wrong statements
1. **Today and Marking show school-wide reader numbers to an educator.** Today: "3 answers to check", then "Still
   waiting 27" in "Is the queue shrinking?" (every class). Marking: "0 checked by a person", then "Checked by a person:
   12 answers" in "How the reader is doing". `queueByWeek()` and the reader panel take no scope. Fix: count both in the
   person's classes (the coordinator's are every class). Educator, D and P.
2. **A paper that came back says it is waiting for approval.** `worksheets/[qr]` says "Waiting for a teacher to approve
   the pack" for every status but `printed`, so every read paper (`returned`) says it. Fix: one sentence per status
   (new, printed, with the children, came back and read). Also "teacher" → "educator". Both roles, D and P.
3. **A paper's "For" line prints "null".** `Roll 1 · U38-CLASS · null`: the kind is printed raw, and an older paper has
   none; a newer one says "focus" where every other page says "home assessment". Fix: the kind's words, or nothing.
4. **Curriculum counts children under a grade they never answered in.** Grade 1 shows "4 children assessed, 2 of 8"
   for an educator whose classes are Grade 2: ADD.2D2D and SUB.2D2D have their Easy level filed under Grade 1, and
   "assessed" counts the skill, not the level answered. Fix: count a child under a grade by answers on that grade's
   levels (the answered question's level). Both roles, D.
5. **A link to a class's week that is not on the list opens another class's week, silently.**
   `/papers/approve?section=U37-CLASS&week=2026-W30&kind=practice` (no plan was made for that week) shows U37's
   week-of-19-Oct assessment instead, with no word; an educator following a link to another educator's class sees the
   first of their own. (Corrected after the audit: I first wrote that week was already approved; nothing was planned.)
   Fix: say "no papers have been made for it" or "not one of your classes", then what is shown instead.
6. To verify on live, not fixed: a child's page says "12 answers signed off over 1 paper" and the report card "2
   answers on 1 paper" above "12 right of 12". Both come from 10 answers the tests wrote with no paper. Every engine
   path ties an answer to a paper, so live should have none: `select count(*) from evidence_event where
   item_result_id is null` on live settles it.

### Dead ends and broken
7. **3 of 2,884 links crash:** three parent reports from Today. All three are rows the tests wrote by hand
   (`{"facts": {}, "draft": {}}`, weeks "U35" and "U8"), which the engine never writes, so not a live defect. The
   tests should write a real report's shape (u8, u35, u43).
8. **`/home`, "Home Assignments", is a placeholder still reachable** from "How it works": "Arrives with W4", "home
   sheets 0" while 3 home assessments wait under Assessments. It is a screen in `workflows.json` (step N11), so removing
   it is a map change: listed for Nimish below.

### Unclear
9. **Papers and worksheets are named by codes.** "Paper CS38A001", "Asha · R16-A01", Marking's paper column, the
   approve page's "CS370A01 · R21-H01", a child's papers "R16-A03", the check page's "R16-A01 · sat —", the skill
   page's footer "ADD.1D1D · R19", and worksheet lists "R7-E01". Fix: name a paper by its skill and level ("Equality,
   inverse and checking · Advance"), with the printed code as small text where a person matches a page in hand.
10. **One skill, two names.** Worksheet R16-A01 is "Equality, inverse and checking" on its page and "Mental maths &
    missing-number equations" (its rung's strand) on the paper's marking page. Fix: the skill's name everywhere.
11. **Curriculum uses "taught" two ways.** The top panel lists Multiplication as taught (a Grade 1 skill is); Grade 2's
    row says "not taught yet" with a "Mark taught" button. The same action is "Say it is taught" in the panel and "Mark
    taught" in the table. Fix: the panel for the person's own grades, one label for one action.
12. **Parent reports: "waiting" means two things.** The reports page lists 4 "to write" under "Waiting on a person";
    Today says "Nothing waits here" under Children and the Children table's Parent report column is blank. Fix: one rule.
13. **Grade 2 has two question totals.** Curriculum: 8,572 (6,671 in Addition & subtraction); question bank: "5,807
    ready". Each is explained in small print (every skill of the grade's levels; skills taught in your classes), but
    nothing on screen says why they differ. Fix: one line under each naming what it counts.
14. **The reader's trust in engineer's words.** "The reader is trusted on 0 of 4 kinds of question; the nearest, sum
    (earlier paper), needs 44 more right checks" on Today. Fix: plain words, or the coordinator's only.
15. **Questions the engine drafted:** 30 in one flat list titled "A1: Every method is a case.", "(SZ6, SZ9)". The titles
    are rows (`ask`), so changing them is content: listed below.
16. **Taxonomy page** for an educator: case codes "§2.1", "A01", worksheet code lists, 14,900 px long. Fix: open on the
    person's grade; codes as small text.
17. Home assessments page: a class with 5 children and "0 proposed" gives no reason. The make page's button "This week's
    declaration" opens a page titled "this week", whose back link says "U38-CLASS's papers".

### Inconsistent
18. **Terracotta, the one loud colour, is on 5 buttons on the educator's Today, 6 on the coordinator's and 47 on
    Approve the skills.** `design-system/PRINCIPLES.md`: "if two things on a screen are terracotta, one of them is
    wrong." Fix: one primary action per page, the rest secondary.
19. Child names are dark on Children, terracotta links on Marking, Reports and a class page.
20. "1 papers" (Home assessments), "1 questions on 1 worksheets" (taxonomy); Today says "1 paper".
21. The report card says "skill set"; every other page says "skill". Its "2 of 13 skill sets assessed" counts three
    grades; the child's page counts the grade's 8.
22. Children's footnote says "red" and "amber"; its key says "needs help" and "practising".

### Polish, phone
23. **Tap targets at 390 px:** "Approve" on a class's home assessments is 53 × 20 px; "Change level" 19 px tall; "Open"
    33 × 17; the worksheet library's counts 14 × 17; a worksheet's print-list boxes 13 × 13. Fix: 44 px tall for every
    action outside running text.
24. On a phone, Assessments' table shows Assessment, Kind, Class; what waits is off to the side. Home assessments drops
    the "Why" column, which is what an educator approves on. Fix: on a phone, the next step and the reason on the row.
25. "How m" (placeholder cut short) on a one-child home assessment; the menu's "GRADE 1–GRADE 4" for "Grades 1–4".

### Backend or content, listed and not fixed here (B2/B3 own these, or they are rows)
- A mistake's words are the mistake's, not the question's: "If the child writes 8 (answer 7): Fact off by one — the
  answer is one less than the correct difference: 62 − 27 written as 34."
- Mistake names with "->" and "mod 10" ("Drops the final carry-out (76+54 -> 30)", "Writes each column sum mod 10").
- The 30 drafted questions' titles.

### For Nimish to decide
- D1. Addition's skills say "carrying"; subtraction's say "exchanging". The school's rule names "exchange / regroup".
  Is "carry" right for addition, or should it read "regroup"? (Achal's words, rows, not code.)
- D2. Should an educator see the 30 drafted questions and the taxonomy page, or only the coordinator?
- D3. Remove the `/home` placeholder and point step N11's screen at Home assessments (`/make`)?

## Handoff

- **Live:** nothing; this branch carries the audit only.
- **Next:** UX8a (numbers true and the person's own: 1–5), UX8b (a paper named by what it tests: 9, 10, 17), UX8c (one
  meaning per word: 11–14, 19–22), UX8d (phone and one primary action: 18, 23–25). Each a goal file, a failing
  Playwright test per finding first, its own pull request from main.
- **Blocked:** D1–D3 above; finding 6 needs one query on live.
