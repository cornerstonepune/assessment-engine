# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Every paper entered, every scan read, the engine settles 70%.**
**The open question is the other 30%: 261 answers waiting for a person, and the next session's whole job is to cut that.**

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

## Next session: the 261, and why 70% is not the ceiling

Nimish, end of this session: "261 is a lot of teacher approvals... you sure this is the best you
can do — we gotta work deeper into this module." No, it is not the best, and the breakdown says
where the ceiling actually is. **Every one of the 261 was counted by cause, not guessed at:**

```
  39  (16%)  not a number by design — an ordering, an explanation, a tick, a comparison symbol
  20  ( 8%)  the question was never located on the page
  ~90 (37%)  the region or box count did not add up
  ~80 (33%)  read, but under the 70% confidence floor
  ~13 ( 5%)  other
```

(Counted at 261; 19 of them went away when the echo rule was corrected at the end of the session —
see STATE.md, "A rule written this morning was deleting correct answers". **The corpus now stands
at 242 waiting for a person and 625 of 867 settled, 72%.** Re-count by cause before working the
list: the query is in that STATE entry's sibling above it.)

Only the first 39 are a floor. **The other 222 are addressable, and three of the four biggest
classes are not hard handwriting at all** — they are the engine not knowing which number on the
page is the answer. Work them in this order; each one names its own measurement.

**1. The 104 that did not add up — the free-response box (biggest single win).**
`G2-CAM-A` q7/q8, `G2-DIAG-B` q11 and their like: the child works the whole method inside one box,
so the region holds five numbers where the paper asks for two, and the engine refuses rather than
guess. Two levers, in this order:
  - **A blank-page template per paper.** This is the half of the standard pipeline this session did
    NOT need and now does: one unmarked copy of each paper, ORB + RANSAC homography to align a
    child's scan to it (`cv2.findHomography` / `warpPerspective`, the PyImageSearch recipe), then
    field coordinates read from the template instead of inferred from the scan. It is the only
    thing that fixes a paper whose answer sits on a plain underline the page does not draw —
    `G3-SEPW1-A` and `G4-SEPW1`, where the flags concentrate. **There is no blank copy of any paper
    on disk: ask the school, or reconstruct one by median-averaging the aligned copies of a paper
    across the children who sat it (≥4 copies exist for 9 of 16 papers), which removes the
    handwriting and leaves the printed page.**
  - **Textract QUERIES as a second opinion on exactly these**, in plain English ("what number did
    the student write as the final answer"), accepted only above the floor or where it agrees with
    a candidate geometry already found. Measured once before: recovered 3 of 4 on this class, at
    $15/1,000 pages and only on flagged answers.

**2. The 84 under the confidence floor — re-read the crop, do not lower the bar.**
18% of all flags sit at 50–69%, one band under the floor. The standard move is not to lower the
floor (measured: 85 costs Grade 2 80.0% → 73.3%) but to **re-read just that box at a higher
resolution**: the page goes to Textract at 150 dpi, a 40×25-pixel answer within it is at the limit,
and a crop re-rendered at 400–600 dpi is a different problem. Cost is one extra call per flagged
answer, not per page. **Target: half of the 84.**

**3. The 20 never located — anchor failures on photographs.** Mostly `G3-BASE16` and `G2-DIAG-B` on
angled phone photos where the printed question line broke up. The template from (1) removes this
class entirely, which is another reason to do (1) first.

**4. The 16 "find the mistake" answers that were read perfectly and still went to a person.**
`legacy.mark` routes every `kind: text` item to a human. But the engine already reads the number
("No! 84,602" → 84602) and the key already holds the right answer — 5 of the 16 match it exactly.
The judgement ("is he correct?") is not checkable; **the number is**. Mark the number, show the
teacher the judgement. This is a marking change, ~10 lines, no reading risk.

**If all four land, 242 → roughly 60–80, of which 39 are the structural floor.** That is the 90%+
coverage you asked for, and every step of it is measurable against the gold set before it ships.

## Do not skip this: the gold set is the only thing that kept this session honest

`supabase/seed/read_gold.json` is now **82 responses over 6 sheets**, hand-read off the page,
recording what the CHILD wrote including eleven answers that are wrong. The first cut of the box
reader this session put **five silent errors** into the corpus; the gold caught all five before
they reached a child's graph, and each is now a test. The bar wants 300 responses with 100 of them
phone photographs. **Grow it by signing papers off on the approval screen** — every correction a
teacher makes is a hand-verified response — not by another typing session.

Run it before and after every single change:

```
bin/engine read eval --reader ocr --runs 2
  78.0% exact (64/82) · 100% given a row · 1.2% silently wrong (1) · spread 78.0-78.0%
```

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
