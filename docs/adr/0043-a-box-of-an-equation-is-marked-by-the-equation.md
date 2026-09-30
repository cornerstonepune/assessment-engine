# ADR 0043 — A box of an equation is marked by the equation, not by the one split its key prints

**Status:** accepted (built on Nimish's words of 2026-09-29: "this question's right answer is 19 and 19, but its
showing wrong - need to correct it"); whether the school wants any split or only the place-value one is put to Aseem
and Achal (see Open)
Goal: goals/s24-a-split-that-holds-is-right.yaml

## What happened

The live Marking page of the Grade 3 September Week 1 Level A paper showed question 5A and 5B, "638 = 600 + [19] +
[19]", both "wrong · with working". Every answer box was marked alone against its own key, and the key prints one
split: 30 and 8. 600 + 19 + 19 is 638.

Question 5 of G3-SEPW1-A, G3-SEPW1-B and G4-SEPW1 is built the same way: two expanded forms, then the two added part by
part — `638 = 600 + [ ] + [ ]`, `475 = [ ] + [ ] + [ ]`, `638 + 475 = [ ] + [ ] + [ ] = [ ]`. That is 26 boxes in eight
equations. The boxes count on Addition (NUM.OPS.01, rung R27).

## Decision

1. **A paper names the equation once** (`holds` on each of its questions: `638 = 600 + {5a} + {5b}`). When the paper is
   entered, code refuses an equation it cannot read (whole numbers, + and − only), one with no side of numbers only,
   one that names a box not on the paper or not its own, and one the paper's own key does not make true
   (`assess/equation.py`, `of`).
2. **A box is right when the side it is written on comes out at the equation's total** with what the child wrote
   (`equation.right`). The total is the side of the question's own numbers. Each other side is its own claim: in
   `638 + 475 = [ ] + [ ] + [ ] = [ ]`, 1100 + 0 + 13 is a right split beside 1112, a wrong total.
3. **What the child wrote is a person's reading, or the engine's once it settled the box** (`marking._group`). The
   engine still settles no wrong answer on its own reading (ADR 0029). So a split other than the key's always passes
   through a person, and it is marked when the person saves the last box of its side (`marking.correct`). A side not
   coming out, or with a box still waiting for a person, leaves each of its boxes to its own key, as before. A box
   already signed off is marked again only when a person saves it, with its next batch of evidence
   (`correct_signed_off`, #131); one box's save never rewrites another's evidence. What a signed-off box says still
   counts toward its side. (Amended by ADR 0044, 2026-09-30: every deploy also marks each answer a person read again by
   the rule as it now stands, so a signed-off box whose side holds is put right at the next deploy.)
4. **A paper corrected in its file is live with the deploy that carries it.** Every deploy enters each paper again
   (`deploy-engine.yml`), as `bin/update-live` did from one Mac. The loader now files a sum where `bank rehome` does:
   the rung its shape places it on first, and the rung its file names only where the ladder has none. Before this,
   nine sums (G2-CAM-A 7b, and eight in G2-WORD-SEP17) named old rungs R8 and R11 in their files, and rehome filed them
   on R22, R24 and R26. Entered again without rehome after it, they would have gone back.

`marking.py` passed its 400-line ceiling with the group's marking. Naming the mistake behind a wrong answer (Jev's
shortlist, `name_mistake`, ADR 0036) moved to its own module, `w3_read/naming.py`. Marking says whether an answer is
right; naming says why a wrong one is wrong.

## Rejected

- **The whole equation as one claim.** A child who splits 1113 right and adds it up to 1112 would have all four boxes
  marked wrong.
- **The engine settling a split other than the key's on its own reading.** Two digits read into the wrong boxes can
  make a split that adds up: 30 and 8 misread as 38 and 0 still make 638. A person checks every wrong reading
  already, so nothing is lost by marking the split when they save it.
- **Entering again only the papers whose file changed.** That would hide the defect, not remove it. The loader and
  `bank rehome` disagreed about where nine sums belong, and `update-live` only covered it by always running rehome
  last.

## Open

The first real read of this paper (STATE.md, 2026-09-17) called the same child's 600 + 19 + 19 "a wrong method reaching
a right answer … exactly the diagnostic signal the product exists to find". Marked right, that signal is not kept.
Nothing records that the child did not split by place value. Three ways are open to the school:

- any split that adds up (built);
- only the place-value split (the three papers' `holds` lines come out);
- right, and the split noted as a fourth kind of signal (a design change, not built).
