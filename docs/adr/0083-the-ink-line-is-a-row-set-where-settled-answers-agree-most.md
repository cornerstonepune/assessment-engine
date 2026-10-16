# ADR 0083 — The ink line is a row, set where the answers people settled agree most

**Status:** accepted (2026-10-16).
Goal: goals/l12b-the-ink-line-is-a-row.yaml

## What happened

A box holds a digit when enough of it is marked darker than the paper around it, down enough of its height. "Darker"
was a constant in `boxes.dark`: 28% (a line of 0.72). On the 16 Oct Grade 3 scan roll 4 wrote "862" with its 6 in
pencil whose darkest 2% is 21% darker than its paper, so that box counted as empty. The reading waited as "2 boxes hold
ink but the reader saw 862".

L12a measured the line instead of guessing it (`engine read ink`, Actions run 38909176094). It took the 328 answers a
person settled on copies read in their boxes, found each answer's boxes again as the reader found them, and counted the
boxes holding ink against the digits settled:

| line | agree | lose ink | gain ink | settled blanks given ink |
|---|---|---|---|---|
| 0.72 | 281 | 40 | 7 | 0 |
| 0.76 | **291** | 28 | 9 | 0 |
| 0.80 | 289 | 26 | 13 | 0 |
| 0.84 | 286 | 25 | 17 | 0 |
| 0.88 | 283 | 23 | 22 | 0 |

## Decision

- The line is a threshold row, `read.ink_line`, set to **0.76**: the line at which the most settled answers agree.
- The box reader reads at it (`digits.settings` carries it to `boxes.read_page`).
- Every reading records the line it was read at (`ink_line` beside `inked`), so a later measure compares a stored count
  at the line it was made.
- The measure counts at 0.74 and 0.78 as well. Those are the lines either side, and the 16 Oct 6 measured about 0.78 on
  its photograph.

## Rejected

- **0.80, the faintest line that would read the 16 Oct "862".** It is one answer that no person has settled yet,
  against 328 that have been: at 0.80, 2 fewer agree and 4 more gain ink. The next measure, run once 16 Oct is settled,
  says whether 0.78 does better than 0.76 on all of them.
- **Keep 0.72.** Ten more settled answers agree at 0.76, and no blank is given ink.
- **A line per box, from the box's own contrast.** This is not measured, and every box would be judged by a different
  rule. A row a person can see and change is one rule, measured.

## Consequences

Both kinds of miscount send an answer to a person, never past one. An answer that loses ink is held as unclear, or
blank if it loses all of it; an answer that gains ink is held as unclear. So a better line means fewer answers a person
must type. It does not mean fewer silent errors, because the line causes none. The 16 Oct "862" still waits at 0.76.
