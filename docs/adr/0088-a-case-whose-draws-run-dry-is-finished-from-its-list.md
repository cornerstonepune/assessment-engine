# ADR 0088 — A case whose random draws run dry is finished from the list of every question it can be

**Status:** accepted (2026-10-21).
Goal: goals/bank-fills-every-time.yaml

## What happened

CI failed now and then on "every unit meets its target" (ADD.2D1D Hard 172 of 175 on #235; SUB.3D2D Advance, case S33,
while #234 was built), with main green at the same commit. The bank is built afresh for each run, from the operating
system's randomness. ADD.2D1D Hard's three cases make 180 questions for its 175; its last few turned up roughly once in
1,600 draws, and each question is given 2000, so now and then the budget ran out first. Multiplication and division
already ended their draws on a list of every pair (2026-10-09, MUL.2D1D Easy 66 of 69); addition and subtraction did
not, nor did × 10, 100 or 1000 itself. Measured in docs/notes/bank-fills-every-time.md.

## Decision

- **Draw first, then list.** A case's random draws come first, as before, so the bank's mix of questions is what it
  was. When they run dry, the rest is taken from the list of every question the case can be (`draw._listing`), in a
  random order, so the last questions are as varied as the first. The list covers + and − up to 100,000 pairs (3
  digits by 2 is 81,000), and a case that is × 10, 100 or 1000 itself is listed as the factor beside every number of
  its digits.
- **A level that cannot fill says why** (`refill.why_short`, printed by `engine bank refill`): per case, how many it is
  short, what it can make at all, and how many of those the bank holds; or that its questions cannot be listed.
- **A build can be seeded.** Every generator takes the caller's `rng`; a real build passes none and keeps the operating
  system's randomness, so a top-up still finds new questions.

## Rejected

- **Re-run CI until green, lower a target, or raise the 2000 draws until it passes.** Each hides the cause: a level
  that is barely fillable stays one bad run from short.
- **List first, never draw.** It fills every listable case at once and builds faster, but it changes the bank's mix:
  a level that allows 2 digits by 1 and 2 by 2 would be filled about ten to one from the larger list (8,100 pairs
  against 810), where the draws pick the digit sizes evenly.
- **Make every build the same (a fixed seed).** A second fill meant to top a level up would retrace the first fill's
  questions and find nothing new (the reason the randomness exists, `bank.fill_native`).

## What it changes for a person

Nothing on a page: the bank holds the same kinds of questions in the same proportions. CI no longer fails on a level
being a few questions short by luck, and when a level truly cannot be filled the refill says exactly why.
