# M1-06 part 2 — the educator's timetable: three read calls, and the school's tabs loaded as rows

W2 step N4, files only (no thirteenth step). Goal: `goals/m1-06b-educator-timetable.yaml`. Builds on #374 (the six tables).

## What it is
- `engine timetable load` (`w2_print/cli_timetable.py`): the Time table, Monthly Planner and Pre-Primary calendar tabs, each
  as CSV, become the rows of the six tables for Fortnight N to M. **Dry run unless `--apply`**; prints counts and the lists
  below, never the school's text; safe to run twice (every insert is `on conflict do nothing`).
- The inputs are **exact exports** of the three tabs, read through the sheet connector on 2026-11-04 and committed in
  `supabase/seed/k2_tabs_2026_11_04/` (`capture.json` has the spreadsheet ids, tab names, ranges and revision ids). Nothing is
  retyped. They hold curriculum text and dates only: no child, parent, phone or email (grep'd; the Observations tab and every
  child-data tab were never read).
- `--sql FILE` writes the same rows as one transaction with row counts before and after, committed under
  `supabase/seed/` (not `migrations/`, which would auto-apply), with the sha256 of each source CSV in its header.
  Needs the K2 class on live: `--section` and `--grade` name it.
- `POST /timetable/day|week|period` (`api/routes/timetable.py`, `w2_print/k2_day.py`): her day, her week, one period, each with
  `frozen: false` until the month lock (M1-12) exists. Her email as `actor`; a class she holds an open grant on in a role of config
  `educator.timetable_roles`; 403 while `educator.timetable_enabled` is off (seeded off); no child, no name.

## Fortnight 10 is in the Monthly Planner twice — a question for the school
The tab has two rows labelled "Fortnight 10" (the November block and the December block). They differ in Hindi, Music, Circle
Time and PE. I did not choose. The main SQL loads **neither** plan (302 plan lines, 920 sessions, Fortnight 10's periods have
no planner lines). `k2_timetable_fn10_fn17_fn10_row1.sql` and `…_row2.sql` each add one candidate (row 2 → 336 plan lines,
1,049 sessions); apply at most one, after the school says which. The row that sits in the local copy used for the screens'
fixtures is **row 2**, only because the screens needed some data; it is not a claim.

## Proofs (commands)
- `pytest tests/test_k2_timetable.py tests/test_k2_timetable_load.py tests/test_k2_day.py` — every planner line of Fortnights 10–17
  is a substring of its source cell (nothing invented, nothing dropped; the earlier "a_e, ay" was an invention and is gone);
  stray quotation marks stripped; "Music and Dance" is under `music`, "Routine - …" under `routines`, FN16's column titled
  "Value Education" is kept as `value_education` (it holds events text; flagged).
- Cell by cell, all of FN10–FN17 against the earlier copy: FN11–13 and FN15–17 identical; FN14 differed by one typo of mine
  ("art: Phad"); FN10 differed because the school has edited the sheet since (and the duplicate above).
- Frame merges are proven from the sheet's own merge ranges (Fruit Break / Lunch in week B, Mon–Fri, are single merged cells
  filled across; `frame_spans.json`); periods after the first of a merged activity take no planner line.
- Dropped on purpose, because they are not periods: the week-B "events" rows (e.g. Memory Drawing, No Screen Day) and the
  "Note to educators" rows of the frame tab.
- Local copy: 8 fortnights, 80 school days, 15 periods, 150 slots; second run adds 0. SQL on an emptied copy: main file
  `8|80|150|302|920`, then row 2 `8|80|150|336|1049`, main again changes nothing.

## What the sources said (and did not decide)
- The calendar says Fortnight 10 ends 6 Dec and Fortnight 11 starts 7 Dec; the Graph tab says 7 Dec and 8 Dec. **Mon 7 Dec is
  undecided**: a school day with a note and no session.
- K2 holidays in the range, from the calendar rows relied on (all in `calendar.csv`): 24 Nov (Guru Nanak), 25 Dec–1 Jan,
  15 Jan (Makar Sankranti), 19 Feb (Shivaji Jayanti), 22 Mar (Holi), 26 Mar (Good Friday); 10 Mar is Eid, loaded and marked
  tentative. 26 Jan is PG–N only: K2 attends. The 21 Nov Parent Connect is a Saturday: outside Monday–Friday, not loaded.
- A holiday takes its day's periods with it; those planner lines are listed with no period, never moved.
- Lines with no period are listed by heading. Block Room and Gross Motor have no slot in the frame; PE has one specialist slot
  a week. Not forced.
- Activity link: by exact name (letters and digits only) to exactly one K2 activity, in SQL; 30 of 336 lines link today.

## Not claimed / for a person
- `engine done m1-06b-educator-timetable`: the K2 educator's line-by-line marks do not exist yet (D-028).
- A person confirms: which Time table tab is current, which Fortnight 10 row, Mon 7 Dec, where Block Room goes, whether the
  planner is current, Working Saturdays.

## Review (D-073)
`/code-review` (medium) found 10, fixed at the cause with a failing test first (see git history: week-B default outside every
fortnight, offline SQL path needing a DB, `--apply` without a DB, Monday-less week, non-Monday fortnight, double activity
link, hard-coded afternoon rule/date format, `date.today()`, switch checked after validating). `/simplify` applied the SQL
writer's ordered appends, shared defaults, one connection, one week-letter query. Left alone on purpose: the grant query that
resembles the voice one (touching voice code is outside this brick), the A/B rule living in both generator and read SQL (a
stored column needs a migration), request models per route (a 422 would precede the switch's 403).
