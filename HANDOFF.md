# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Goal written, bar agreed, red on purpose. Gate 1 is entering the papers.**

W1 and W2 are done. Verified again at the start of this session, not assumed:

```
bin/engine goal w1-build-the-bank      10/10 scenarios · 5/5 criteria · GOAL ACHIEVED
bin/engine goal w2-assemble-and-print  12/12 scenarios · 4/4 criteria · GOAL ACHIEVED
bin/engine audit                       12 invariants · 0 violations      (suite: 301 passed)
```

`goals/w3-read-and-graph.yaml` now exists — written before a line of reader code, as ADR 0015
requires. It opens red, which is correct:

```
bin/engine goal w3-read-and-graph      2/4 criteria · 30 scenarios short of the bar   (exit 1)
```

## Where the reader stands (end of 2026-09-20)

Transcription is AWS Textract, not a vision model (ADR 0019): what reads a child's handwriting must
not know arithmetic, because a model that does fills faint pencil with the answer it can compute.
**`engine legacy import` — the real ingest path — now reads with it too**, which it did not for most
of the session while every measurement was taken against a different reader.

```
bin/engine read eval --reader ocr
  read exactly right   80.0%   (36/45)     bar 97%    NOT MET
  given a row at all   100.0%              bar 100%   met
  SILENTLY WRONG       0.0%    (0)         bar 1%     met
```

45 responses read off the page by eye, three children, two paper types, **Grade 2 only**. Against
the vision model on the same gold: 55–63% exact with about seven silent errors.

The frontier is measured, in `STATE.md`: no combination of render resolution and confidence floor
meets both bars. 250 dpi with no floor reaches 91.1% exact but 4.4% silently wrong.

**Three complements tested, results in `STATE.md`:** Textract QUERIES recovers 3 of the 4
free-response misses (at confidences 98/32/66, and one confidently wrong) and is the clearest
remaining lever **as a second opinion on already-flagged answers**; FORMS finds `Answer: → 155` but
cannot say which question it belongs to; **OpenCV preprocessing measured WORSE** (mean confidence
90.6 → 87.9) and was the lever I had predicted would help most.

## Next, in the order that removes the most risk

1. **Grade 3, before anything else is built on these numbers.** Every measurement above is Grade 2
   PDFs. Grade 3 is 38 pages of phone photographs — angled, pencil, the educator's pen over the
   child's answer — and **not one has ever been read**. Enter one G3 paper, hand-verify one sheet,
   run `read eval`. Largest unknown in the project and the cheapest way to close it.
2. **The teacher approval screen.** Nimish's own argument for putting it early: every correction a
   teacher makes IS a hand-verified response, so the gold set grows by using the system rather than
   by a data-entry project — and coverage becomes 100% immediately, because anything doubtful is
   either read confidently or confirmed by a person. It is the mechanism that makes the reader
   improve, not a reward for finishing it.
3. **Enter the remaining papers** (`docs/w3-paper-inventory.md`): 10 of 14 never entered, including
   the Grade 3 baseline all five of Aseem's gold reports are written from.
4. **Wire QUERIES as the second opinion** on flagged answers, accepted only above the confidence
   floor or where it agrees with a candidate geometry already found.
5. **Then** read all 118 pages once, score, build the graph. Not before: reading at 80% would put a
   confident wrong diagnosis on sixteen real children.
6. **Then** the rest of the frontend.

## Code quality, measured

```
pytest        340 passed          coverage 66%
ruff          format + check clean, and a goal criterion now fails if either drifts
aislop        engine package 68/100 "Needs Work"; repo-wide 35 is ONE research spike
engine audit  12 invariants, 0 violations
```

Known and named, not hidden: `engine/assess/mark.py` is 247 statements at 0% coverage that nothing
imports (built for the QR path, never wired — dead, and it will rot). Four files are over the size
ceiling (`items.py` 743, `legacy.py` 570, `loaders.py` 481, `cli.py` 462). `research/` holds 15 of
the repo's 16 lint errors and is not production.

## Carried over — Nimish's calls, not blockers

- **Grade 1**: `ADD.1D.WITHIN10` holds 22–24 questions against a class need of 216. Fewer questions
  per sheet for G1, a wider rung, or accepted sharing.
- **W2's live n8n run**: n8n Cloud cannot reach `http://engine:8000` on a laptop. `deploy/compose.yml`
  runs both together where they share a host. Hosting decision, not a workflow change.
- **The plain-English pass on the skill-set screen** is still not done — formats shown as raw codes
  (`bare_sum`), difficulties as boxes instead of a sentence plus a worked example, misconceptions
  led by `M_NOCARRY` instead of the plain sentence. Presentation only: it must not write to
  `skill_set`, or it withdraws the ratification it exists to make legible.
- **`ruff format`**: every engine `.py` trips aislop's `python-formatting` warning. Adopting it is
  536 diff lines and explodes the misconception registry from one line per mistake into five.
  Adopt, or record the exception in `.aislop/config.yaml` with the reason.
- **Three pedagogy questions** for Neha, Achal and Aseem: the reviewer's objection to format mixing
  on `SUB.2D.EXCH` Hard; the provisional gold set's revise-or-reject case; the G1 floors.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET`
  on Vercel if unset; the n8n owner account and its two credentials (`n8n/README.md`).

## Traps — do not repeat

- **Building out of order.** `BUILD-ORDER.md` rule 1 exists because three sessions did this.
- **Pivoting from chat.** QR was nearly built next because one sentence was misread. QR is
  identification only, layered on *after* the reading engine is proven. Restate, get a yes, write
  it into `BUILD-ORDER.md`, then build.
- **Answering "is X built?" with a mechanism instead of a number.**
- **Measuring on synthetic images.** The prototype's 1.0 cell-geometry agreement was synthetic.
  Every W3 number comes from the 118 real pages or it is not a number.
- **Inventing a code verifier where none exists.** R7, R11, R13, X1, X2 have a claim code cannot
  check — say so in `philosophy` and route through the validator, never a fabricated numeric check.
- **A skill set's `formats` list must be a subset the generator actually renders** — `bank._sampled`
  now refuses rather than silently rendering the wrong shape.
- Still true, technical: `roster` is an unused import in `engine/legacy.py` (pre-existing, left
  alone); Docker's credential helper hangs from a non-interactive session (STATE.md N3.2).
