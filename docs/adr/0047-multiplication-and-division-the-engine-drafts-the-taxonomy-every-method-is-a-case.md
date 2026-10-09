# ADR 0047 — Multiplication and division: the engine drafts the taxonomy, every method is a case

**Status:** accepted (Nimish, 2026-10-09: "Achal will do - but need a properly drafted taxonomy by the system itself.
Consider all of the methods for now. Make all the required assumptions on other questions and create a build plan
around this.")
Goal: none — this decides the taxonomy and the plan and builds nothing; each slice of BUILD-ORDER's "Inserted now:
multiplication and division" writes its own goal file (`md0` to `md5`) when it starts, before its code.

## What happened

Nimish asked for multiplication and division the way addition and subtraction were done: learning objectives broken
into skills, four levels each, and the whole loop. Addition and subtraction were built on a taxonomy the school's team
wrote (`docs/sources/addition-subtraction-skill-taxonomy.txt`). Nobody has written one for multiplication and
division. What exists:

- the school's own objectives, in the registry: `NUM.OPS.03` and `NUM.OPS.04`, LO-G1-0046 to 0055, LO-G2-0492 to 0498
  and 0527 to 0530, LO-G3-0942 to 0944 and 0956 to 0959, LO-G4-1339 to 1356;
- the papers the school set in July (G3-QUIZ20, G4-BASE16): facts to 12 × 5, `8 × ___ = 72`, ×10 and ×100, 20 × 40,
  56 × 3, 144 ÷ 12;
- `MUL.1D`, added on 2026-09-19 to prove W1 gate 3. It predates ADR 0034, so one skill spans three digit shapes and its
  levels' words are not read (STATE.md "Multiplication and division — measured before the build").

## Decision

1. **The engine drafts the taxonomy; Achal corrects it.** `research/md_taxonomy.py` writes
   `docs/design/multiplication-division-taxonomy.md` and its cases as data. It follows the add/sub document's shape and
   rule ("a case is distinct whenever a child can make a different kind of mistake"). Every example is computed, every
   case's defining property is measured on its own numbers, and every named mistake's wrong answer is computed by a
   predictor. The engine's existing predictors are reused, not copied. The draft is shared as a doc for Achal. His
   corrections become row changes, run through M1's command.
2. **Every method is a case.** Easy to Hard are straight calculation, as ADR 0034 set. A level prints its numbers in
   every written method the taxonomy lists for its shape, in fair shares:
   - multiplication: in a line, columns, expanded, partitioning, grid, lattice (2 × 2 digits), long multiplication;
   - division: in a line, short division, long division, partitioning the number divided, chunking, halving.

   Pictures (groups, arrays, number lines, sharing, grouping) belong to the concept skills. A level's methods are a
   row, so a grade that teaches one method narrows it without code.
3. **The remaining questions are answered by stated assumptions** (A1 to A12 in the document), each a row or a case:
   - division prints in a line by default;
   - a remainder is written "r" and is its own answer, with its own boxes;
   - tables run from 0 to 12, with ×11 and ×12 only at Advance;
   - the words are "regroup" for a multiplication carry and "exchange" for division, never "borrow";
   - grades come from the school's objectives, and shapes in no G1 to G4 objective are placed in no grade;
   - taught stays the educator's word;
   - fractions and decimals of remainders are out of scope;
   - stories carry the ranges their numbers may take;
   - both orders of the factors are asked;
   - a slip adding the partial products counts against addition;
   - lattice is included.
4. **Seventeen skills.** Each calculation skill is one operation and one digit shape (ADR 0034). The concept and
   reasoning skills follow the school's objectives. `MUL.1D` is re-homed into `MUL.2D1D`, `MUL.3D1D` and `MUL.2D2D` and
   retired, as ADR 0034 re-homed the old ladder.
5. **"Rows only" restated.** A new operation costs code once: its question makers, predictors, tag measurement and
   layouts. Every skill or level after that is rows. Printing, the graph and the reports get no operation branch; where
   they assume addition, the fix is made general. The files each slice changes are recorded per workflow.

## Rejected

- **Wait for the school to write the taxonomy.** Nimish chose to build on a drafted one that Achal corrects. Nothing
  reaches a child until a grade declares it taught, so a draft cannot mislead a child.
- **Methods only at Advance.** The school's objectives name partitioning, grid and expanded layouts as the way Grades 2
  and 3 multiply. Nimish: "consider all of the methods".
- **Keep `MUL.1D` as one skill.** A child's graph could not say whether they lack the tables or the method. That is
  ADR 0034's reason, and July's papers show it: facts and 144 ÷ 12 sit on the column rung.
- **One box for "21 r 1".** The reader reads digits per box. A wrong remainder with a right quotient is a different
  mistake from the reverse, and one box hides which.
- **Long division as the only layout.** The school's own papers write division in a line.

## Consequences

- A remainder needs a question with two answers read, marked and counted apart. Today a library worksheet's question
  with more than one answer is never read, so M0 fixes that for every kind first, add/sub included.
- Achal's corrections may move cases between levels or remove methods. Those are row changes. A changed level
  withdraws its set's approval, as any content edit does.
