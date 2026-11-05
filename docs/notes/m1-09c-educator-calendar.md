# M1-09c — the K2 educator's Today and This week as calendars

D-076 (5 Nov 2026): the screens are built now, in the real app, to D-075's rules, behind the staff preview (M1-09p).
This replaces the first M1-09 branch (cream ground, Jost and Cormorant, lists), which Nimish rejected. Goal:
`goals/m1-09c-educator-calendar.yaml`. No migration.

## What she sees

- **Her menu** (left sidebar on a desktop, tabs at the foot of a phone): Today; Timetable with Tomorrow, This week and
  Next week. A breadcrumb on every page.
- **Today** (`/educator`): a strip of counts (periods, lessons, breaks, activities; each opens the first it counts), the
  day as a timeline of blocks (time as time, the frame's name, the planner's line, the activity), a Now line when it is
  today, and beside it the next period with a countdown and the colour key. Breaks are plain white blocks with a cup
  icon; an empty slot says Free. No chip on a period still to come (D-075); Do now, To confirm, Done and Late only.
  Step a school day back or on (weekends skipped), or back to today.
- **This week** (`/educator/week`): the strip of counts, a column a day and a row a period start, a holiday one tall
  cell, today's column grey; a day's name opens that day. On a phone the days stand one under another.
- **A period** (`/educator/period/[id]`), opened from any block: its date and time, the school's words, the planner's
  lines for its subject this fortnight, its activity's name (its page comes with the activity PR).

## The shell (for the other areas)

`components/educator/shell.tsx`, `SchoolShell({ items, label })`: white ground, the area's menu (a sidebar with
submenus; tabs at the foot of a phone), the page in ten of twelve columns, and the school's tokens loaded for this
shell alone (`school-tokens.css`, the lowest CSS layer). An area moves in with one change: its layout renders
`<SchoolShell items={its menu} label={its name}>`; the educator's menu is `lib/educator/menu.ts`. Pages outside it keep
the site's look and font (orchestrator, 5 Nov; tested).

## Choices made without asking (D-076: the simplest reading, recorded)

- The site's top bar stays; the sidebar is the educator area's own, beside the page.
- PageShell stays (every page is held to it by `test_ux_rules.py`): its title, purpose, one action (the date steps) and
  next step; the breadcrumb sits under its action row.
- The site's font (Source Serif 4) stays.
- "Today's column is grey" is `--border` at 45%: no grey token exists besides the line colour.

## Verified

- `npx playwright test tests/m1-09-calendar.spec.ts tests/m1-09-tokens.spec.ts tests/m1-09-shared-taps.spec.ts
  --workers=1` → 14 passed, on Fortnight 10 as the school wrote it (M1-06's loader, the tests' placeholder K2 class).
  The tests were written after a first draft of the pages and seen failing against it (white ground, taps, the holiday
  span, then each D-075 rule) before each fix.
- Screenshots: `docs/screens/m1-09-built/1-today-*`, `2-week-*`, `3-period-*` (1280, 390, 1280 at 200%).

## From the code review (each fixed, the code-level ones test first)

- The site's heading rule stays as it was (moving it to the base layer changed heading spacing on old pages); only the
  phone's 24 px floor moves, so a control's own 44 px wins.
- A period with no end (the bus) lasts until the next starts (`lib/educator/period.ts` `withEnds`), so the chip and the
  Now line agree; a period's name and time are said by one helper.
- A day in the address that is not a date is not found, not a crash. A past day says "This day is over."
- The colour key shows only what the timetable can show (Do now, Coming up as the countdown's colour, Done, Late); the
  unused "To confirm" branch is gone until the engine says a part waits for her.
- The tests no longer assume 23 Nov is ahead.

## Open

- The planner list on a period shows each line twice for a subject planned in both blocks of the fortnight (M1-06's
  `_plan_lines`); reported to M1-06, not hidden here.
- Fortnight and month views; the sidebar's Activities, Materials, Children and notes: with their screens.

## Cleanup pass (/simplify)
- Done: one placement helper in the week grid; `isLesson` / `isBlank` / `blankWords` said once; `DayHead` for the row of steps;
  one `Pill` for chip, countdown and fortnight; each block's chip worked out once by its page; dead words and a dead type gone;
  the browser test loads Fortnight 10 with M1-06's own `engine timetable load` (the Python helper is deleted).
- Left, with reason:
  - `StatusChip` is not reused: D-075 gives each state a fixed colour, so the site-wide chip would change on every other page.
  - Dates stay "Monday 23 November" (D-075: time shown as time), not the site's `dateWords`.
  - The bus's missing end and the period's name were worked out on the website (`withEnds`, `nameOf`). They now come from
    the engine (M1-06e, #409) and the website's copies are deleted: this branch needs #409 merged first.
  - The site's own CSS is still unlayered; layering it all touches every page, so it is out of this PR's scope.
