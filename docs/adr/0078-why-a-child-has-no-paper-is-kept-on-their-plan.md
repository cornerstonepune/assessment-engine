# ADR 0078 — Why a child has no paper is kept on their plan

**Status:** accepted (2026-10-15).
Goal: goals/ux5-papers-grouped.yaml

## What happened

The week's assembly (`w2_print/assemble.for_week`) never gives a child a short paper or a repeat. When it cannot dress
a child it names them, with the reason: the library holds no worksheet at their level, they have sat every one, or every
one left shares a question with another child's paper or holds one they saw in the last three weeks. It returned that
reason to whoever ran it, and nothing kept it. The class's papers to approve, where an educator approves the week, showed
such a child nowhere (UI audit, 2026-10-15).

## Decision

The reason is kept on the child's plan for the week: `prescription.no_paper` (migration 20261118090000). The assembly
writes it when it cannot dress the child, and clears it when it hands them a paper. The page reads it and says it beside
the child's name. A child of the class with no plan at all is named too, said from the roll: "joined the class after this
week was planned" when they were added after the plan, else "not on this week's plan".

## Rejected

- **The website works the reason out again.** It would repeat `_why_short`'s three cases in SQL, and the two would drift.
  A rule has one owner.
- **The page asks the engine to explain each child.** The answer would describe the library as it is when the page is
  read, not as it was when the assembly ran, and a worksheet added since would make the reason wrong.
- **The reason stays only in the stored API result** (`run_idempotent`). That is kept to replay one call, and is not
  where a page reads a child's week; a week assembled from the command line stores nothing there.

## Also decided here

A class assessment made in the maker is drawn for each child on a worksheet of its own, so it had no skill set to be
grouped by, and Assessments showed it as one row a child, titled by a QR code. It is one assessment by the skills and
levels every copy names (`sheet_instance.key -> 'areas'`), titled by them. The rejected alternative, a batch id written
when the papers are made, would leave every paper made before it ungrouped.
