# 0034 — A calculation skill is one operation and one digit shape; its levels are the taxonomy's cases

Date: 2026-09-23
Status: accepted (Nimish, 2026-09-23)
Goal: goals/s13-levels-by-taxonomy.yaml

## Context

The calculation skill sets were the steps of the school's ladder (R1–R6, R9, R10, R12, R15). A step put
addition and subtraction in one skill (`ADDSUB.2D.NOREG`), and its levels changed the *kind* of question as
much as the numbers: Grade 2 "2-digit" Easy held seven kinds — sums across and in columns of both operations,
stories of both, and missing numbers. Nimish, 2026-09-23: *"even in a two-digit addition, an easy level should
have just included sums with horizontal and vertical two-digit additions … the rung level isn't making sense
that way"*, and *"For every skill, for different difficulties, there are dedicated worksheets … Mixed back can
also be a part of advanced only."* The taxonomy (ADR 0031) was already measured on every question; it had not
been used to define the levels.

## Decision

- **A calculation skill is one operation and one digit shape**, read from the taxonomy's sections (§2.1–2.6,
  2.8, 2.9, 3.1–3.6, 3.8): fifteen skills, `ADD.1D1D` … `SUB.4D`, each with its own rung and grade. The shape is
  a condition on measured tags (`check.within`), in the same language as a case.
- **A level is the union of its cases on its skill's own numbers** (`taxonomy.within`): Easy, Medium and Hard
  are straight calculation — no carry, one carry from the ones, carries further up or a changed answer size;
  Advance adds the operation's missing-number, one-step story, lining-up and find-the-mistake cases, mixed.
  A case the shape contradicts is refused when the level is read, not silently empty.
- **Every case has a place**: in a level, or — §5, the carry and exchange patterns — as the rule the levels
  climb (`config: taxonomy.across_levels`). `engine bank taxonomy` counts it.
- **The bank is re-homed, not rebuilt** (`engine bank rehome`): the replaced skill sets are retired, kept as
  rows so every printed paper and every answer still names them; each of their questions moves to the one
  skill whose shape it has and the hardest straight level it is a case of (Advance for any other kind). Like its
  tags (ADR 0030), where a question belongs is recomputed from what it is. A question with no place is retired
  with the reason. Levels whose numbers run out keep their ceiling (`min_items`).

## Rejected

- **Keep the ladder steps, give each four levels from its own cases.** Smaller, but addition and subtraction
  stay one skill in R4 and R12, and a child's graph cannot say which of the two they lag in.
- **Regenerate the bank for the new levels.** It would lose which questions each child has already sat, and
  the numbers are the same; only where a question belongs changes.

## Consequences

- The graph still groups answers by the old rungs until the children's graphs move to the new skills (L2).
- The fifteen skills arrive as drafts: a person approves each once on the Skill Map.
- Which grade a skill belongs to, and where one level ends, are the school's to confirm; they are rows.
