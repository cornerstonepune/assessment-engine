# ADR 0077 — A format is approved once, across skills

**Status:** accepted (2026-10-15). Revises ADR 0075, decision 5.
Goal: none — SF2's goal file is written with its tests, when SF2 starts (BUILD-ORDER); this ADR records the measurement and Nimish's choice that shape it.

## What happened

ADR 0075 made approval per skill × kind. BUILD-ORDER asked that SF2 first be measured on a copy of live, and that
what it would close be named to Nimish before it ships. The rehearsal measured it on 2026-10-15 (run 38714442140,
`.github/measure/sf2_kinds.py`), on live as it was:

- 43 skills, 20 of them approved whole; 168 levels, 76 approved.
- 314 skill × template pairs, 182 skill × format pairs.
- 38 unapproved levels reach a class's paper today: 10 skills, 10,486 questions, in G2 and G3. Nothing stops them,
  because F1g never shipped.
- Approvals needed to open those 38 levels again, counted four ways:

  | One approval covers | Approvals needed |
  |---|---|
  | a level, as today | **38** |
  | a template | **75** |
  | a skill × format | **48** |
  | a format alone | **18** |

So approving per skill × format is more work than approving level by level, not less. Most templates are only the
level's numbers written as a name (`ADD.1D2D.REG1`), so counting by template is worse still.

## Decision (Nimish, 2026-10-15, from the options put to him)

1. **One approval covers a format, across every skill and level that uses it.** It is given on samples drawn from
   each of them. A change to the format withdraws it.
2. **A level's numbers are the coordinator's own rows,** so writing them is approving them. Code checks every question
   against them (ADR 0075, decision 3).
3. **What "a format" is gets settled in SF2's goal, measured on the bank.**
   - Where the template is only the level's numbers, the format is the printed format: bare sum, column, word story.
   - Where the template names a different question, it is that template: an equation of balance, the nth multiple,
     each card kind.

## Settled in SF2's goal (2026-10-15)

Measured on a copy of live (rehearsal 38770003055, `.github/measure/sf2_formats.py`), after the coordinator had
approved every level that day (46 skills, 178 levels):

- **What a format is.** A question's format is its printed format (`item.fmt`) where its template is only the level's
  numbers written as a name: `ADD.2D2D.REG1`, `MUL.3D1D`, `DIV.4D2D`, `ADD.MULTI3`. Otherwise it is the template:
  `EQ.TRUE_FALSE`, `MULT.NTH`, each card kind. One rule, in the database (`format_of`), for the engine and the website.
  The bank holds 74 formats in 212 skill × format pairs.
- **Where approval starts.** A format starts approved where every level that uses it was approved. On live today that
  is all 74 under either rule (every level, or any level), so no paper changes on the day SF2 ships. A format no level
  approved, or a new one, waits.
- **The gate is one rule.** "A question a paper may draw" is written once, in the database: active, and of an approved
  format. Every draw reads it — a home paper, a made paper, the library's build, a week's pack, a worksheet handed out —
  and so do the counts that choose a skill and a level before drawing, so the engine never chooses what it then cannot
  fill. Until now each draw repeated its own `status = 'active'`, and a worksheet handed out by its code checked
  nothing about its questions.
- **What withdraws an approval.** A kind that is a row is changed by changing its row; that withdraws its format at once
  (SF2a). A format made in code changes only with the code; it is withdrawn when the questions it was approved on print
  differently, checked on every deploy (SF2b). A level's numbers stay the coordinator's own rows: writing them is
  approving them (decision 2), and F1d's level approvals gate nothing.
