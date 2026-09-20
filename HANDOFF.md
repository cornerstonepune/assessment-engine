# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Gate 1 closed: every paper entered, every scan read. The queue is now 368 answers deep.**

W1 and W2 were verified at the start of this session and at the end of it, not assumed:

```
bin/engine goal w1-build-the-bank      6/6 criteria · GOAL ACHIEVED
bin/engine goal w2-assemble-and-print  5/5 criteria · GOAL ACHIEVED
bin/engine audit                       12 invariants · 0 violations
cd packages/engine && .venv/bin/python -m pytest        356 passed
cd apps/web && npm run test:e2e                         35 passed (1 skipped) · 8 passed
bin/engine read eval --reader ocr --runs 2              76.2% exact · 1.6% silently wrong
```

## What moved

**The paper's own printed boxes are now the answer fields** — the standard form-processing move
(align to a template, read each field at its coordinates), with the boxes found on the child's own
scan so no alignment step is needed. Nine of sixteen papers declare `fields: boxes` as a row.

```
                answers   settled by the engine   waiting for a person
before              869        501  (58%)              368
after               867        606  (70%)              261   of which 39 are structural
```

Structural means an ordering, an explanation, a tick or a comparison symbol — answers that are not
numbers, which this transcriber cannot read by design and which always reach a person.

**`bin/engine read eval --reader ocr --runs 2` → 78.0% exact (64/82), 100% given a row, 1.2%
silently wrong, spread 78.0–78.0%.** The gold grew from 63 to 82: Kabir's Grade 3–4 quiz, a phone
photograph under heavy red marking, hand-verified.

Two findings worth carrying: **red ink is the educator's and is inpainted out before reading** (a
red circle over 5147 read back as 147 at 95%), and **a number the question prints is never the
answer unless the child declared it**. Both are rows, both are tested, both measured on the gold.

**A sixteenth paper was hiding**: the Grade 4 child's baseline is not the Grade 3 one — same
header, different questions. `G4-BASE16` is entered and his misfiled reading superseded.

## Next, in the order that removes the most risk

1. **Sign off the corpus on the approval screen.** 606 answers are marked and waiting for a
   signature; 261 need a person, 39 of them structurally. Nothing reaches a child's ladder until
   that happens, and every correction is a hand-verified response that grows the gold set.
2. **A real template for the two underline papers.** `G3-SEPW1-A` and `G4-SEPW1` print their
   answers on plain rules with no box, and they are where the remaining flags concentrate. One
   blank page per paper plus an ORB/RANSAC homography — the PyImageSearch pipeline in full — gives
   field coordinates for papers whose fields the page does not draw. That is the next real lever,
   and it is the half of the standard approach this session did not need.
3. **Split `adapters/ocr.py`** along the transcriber/geometry seam: 859 lines against a 400 ceiling.
   An attempt this session was abandoned rather than half-landed; the seam is real and the tests
   already cover both sides.
4. **Textract QUERIES as a second opinion** on answers already flagged, accepted only above the
   confidence floor or where it agrees with a candidate already found.
5. **Then** the graph, the five gold reports, and the two W3 criteria still red.

## Carried over — Nimish's calls, not blockers

- **Grade 1**: `ADD.1D.WITHIN10` holds 22–24 questions against a class need of 216.
- **W2's live n8n run**: n8n Cloud cannot reach the engine on a laptop. Hosting decision.
- **The plain-English pass on the skill-set screen** is still not done (formats as raw codes,
  difficulties as boxes rather than a sentence plus a worked example).
- **`ENGINE_URL`** is `http://localhost:8931` on this machine — 8000 and 8011 are held by other
  projects of yours. The engine's own default is 8000; `deploy/compose.yml` is unaffected.
- **Four pedagogy questions** for Neha, Achal and Aseem — the fourth is new:
  format mixing on `SUB.2D.EXCH` Hard; the provisional gold set's revise-or-reject case; the G1
  floors; and **which rung place value, comparison and rounding belong on**. The Grade 3 baseline
  tests all three, the ladder is addition and subtraction only, and R11 ("estimate first, judge
  reasonableness") is the only rung that carries any of their skills. Their skills are named
  correctly (`NUM.PV.01/02/03`) so the screens read right; the rung is a guess and is marked as one.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET`
  on Vercel if unset; the n8n owner account and its two credentials (`n8n/README.md`).

## Traps — do not repeat

- **Building out of order.** `BUILD-ORDER.md` rule 1 exists because three sessions did this.
- **Pivoting from chat.** Restate, get a yes, write it into `BUILD-ORDER.md`, then build.
- **Answering "is X built?" with a mechanism instead of a number.**
- **Measuring on synthetic images.** Every W3 number comes from the 118 real pages or it is not a
  number.
- **A `blank` is a claim, not a flag.** It says the child did not attempt the skill and it lands in
  the graph as exactly that. Anything the engine stands behind — `written` or `blank` — counts
  against `silently_wrong`; only `illegible` and `not_found` reach a person.
- **Running `npm run test:e2e` used to leave `engine audit` red.** Fixed, and the cause was worth
  the hour: a restore that changed content withdrew the ratification it was restoring.
- **Inventing a code verifier where none exists.** R7, R11, R13, X1, X2 have a claim code cannot
  check — say so in `philosophy` and route through a person, never a fabricated numeric check.
- **The ingest map is outside the repository on purpose.** `ingest.py`, `classify.py` and
  `classify3.py` in the session scratchpad hold the file-to-child-to-paper mapping; they name
  children, and names stay in `pii` (rule 6). Everything they established is in
  `docs/w3-paper-inventory.md` as counts, and in the database as rows. A future re-read of the
  corpus rebuilds them from the papers themselves the same way — by reading the page, never the
  file name.
- Still true, technical: `engine/assess/mark.py` is 247 statements at 0% coverage that nothing
  imports; `legacy.PAPERS` is an unused constant; `roster` is an unused import in `engine/legacy.py`;
  `apps/web/lib/queries.ts` has one `regexp_replace(c.roll_no, '\D', …)` whose backslash is eaten by
  the template literal, so it strips the letter D rather than non-digits (harmless on today's roll
  numbers, wrong in principle); five `react-hooks/static-components` errors in
  `apps/web/app/(app)/library/page.tsx`, all pre-existing.
