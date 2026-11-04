# M1-06 part 2 — the educator's timetable: three read calls, and the school's tabs loaded as rows

W2 step N4, files only (no thirteenth step). Goal: `goals/m1-06b-educator-timetable.yaml`. Builds on #374 (the six tables).

## What it is
- `engine timetable load` (`w2_print/cli_timetable.py`): the Time table, Monthly Planner and Pre-Primary calendar tabs, each
  as CSV, become the rows of the six tables for Fortnight N to M. **Dry run unless `--apply`**; prints counts and the lists
  below, never the school's text; safe to run twice (every insert is `on conflict do nothing`).
- `--sql FILE` writes the same rows as one transaction with row counts before and after, for a person to run where this code
  cannot reach (live). Committed as `supabase/seed/k2_timetable_fn10_fn17.sql` (not `migrations/`, which would auto-apply),
  with the sha256 of each source CSV in its header. Needs the K2 class on live: `--section` must name it (2026-27).
- `POST /timetable/day|week|period` (`api/routes/timetable.py`, `w2_print/k2_day.py`): her day, her week, one period with its
  activity, each with `frozen: false` until the month lock (M1-12) exists. Her email as `actor`; a class she holds an open grant on in a role of config `educator.timetable_roles`; 403 while
  `educator.timetable_enabled` is off (seeded off); no child, no name; one query per call for the days asked for.

## Proof (commands)
- `pytest tests/test_k2_timetable.py tests/test_k2_timetable_load.py tests/test_k2_day.py`: 41 passed.
- Fortnight 10 to 17 on a local copy: 8 fortnights, 80 school days, 15 periods, 150 slots, 313 plan lines, 1,013 sessions;
  second run adds 0. The SQL file on an emptied copy: counts 0 to the same numbers; second run changes nothing.

## What the sources said (and did not decide)
- The calendar says Fortnight 10 ends 6 Dec and Fortnight 11 starts 7 Dec; the Graph tab says 7 Dec and 8 Dec. **Mon 7 Dec is
  undecided**: loaded as a school day with that note and no session. Pass `--undecided DATE=REASON` for any other.
- K2 holidays in the range, from the calendar: 24 Nov, 25 Dec to 1 Jan, 15 Jan, 19 Feb, 22 Mar, 26 Mar; 10 Mar is Eid (loaded,
  marked tentative). 26 Jan is a holiday for PG–N only: K2 attends. Mahashivratri is a Saturday.
- A holiday takes its day's periods with it: week A of Fortnight 10 has no Tuesday, so its one Hindi period and one Art
  period are gone and those planner lines are listed with no period, never moved to another day.
- Lines with no period (by heading): hindi 5, block_room 8, art 2, gross_motor 8, pe 29, music 3, fine_motor 5, clay 3,
  practical_life 1. Block Room and Gross Motor have no slot in the `F.N` frame; PE has one specialist-led slot a week for
  about seven planner lines. Not forced.
- Activity link: by exact name (letters and digits only) to exactly one K2 activity, in SQL; 30 of 313 lines link today
  (6 of 34 for Fortnight 10). The period call says only who the activity is; its text is the activity page's (`/activity`,
  M1-09), so activity columns land in one place. The activity list has no lesson-plan text.

## Not claimed / for a person
- `engine done m1-06b-educator-timetable`: the K2 educator's line-by-line marks do not exist yet (D-028).
- I copied the Planner rows and the calendar's holiday column into the CSVs by hand from what the connector returned
  (`data/k2/`, git-ignored; checksums in the SQL header). A person should spot-check them against the tabs before live.
- Which timetable tab is current, where Block Room goes, whether planner Fortnights 10 to 17 are current, Saturdays.

## Review (D-073)
`/code-review` (medium) found 10: fixed at the cause with a failing test first: a day outside every fortnight returned week B's
periods; the offline SQL-file path needed a database; `--apply` with no database looked like a dry run; a week with no Monday
row lost its fortnight; a fortnight not starting on a Monday is now a conflict; the activity link was written twice (now SQL
only); the afternoon-hour rule and the date format are vocabulary words; "today" is the school's clock; the period call checked
the switch after validating. `/simplify` (four reviewers): applied the SQL writer's ordered appends, the loader's shared
default day and fortnight-on-session, one connection in the command, one place for the week letter in SQL, the route's single
switch check. Left alone, on purpose: the grant query that resembles the voice one (different filters; touching voice code is
outside this brick), the A/B rule living in both the generator and the read SQL (a stored column needs a migration), a 14-day
fortnight and Monday-to-Friday as config rows (they are the definition of the words and a check on the table), request
models per route (a 422 would come before the switch's 403).
