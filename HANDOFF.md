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

## Where the reader stands (2026-09-20, end of session)

Transcription moved from a vision model to AWS Textract (ADR 0019): what reads a child's
handwriting must not know arithmetic, because a model that does fills faint pencil with the answer
it can compute. Measured against 45 responses read off the page by eye, across three children:

```
bin/engine read eval --reader ocr
  read exactly right   80.0%   (36/45)      bar 97%   NOT MET
  given a row at all   100.0%              bar 100%  met
  SILENTLY WRONG       0.0%    (0)         bar 1%    met
```

| | model (all day's prompt work) | Textract + geometry |
|---|---|---|
| exactly right | 55–63% | **80.0%** |
| silently wrong | ~7 in 27 | **0** |

The frontier is measured and in `STATE.md`: no combination of render resolution and confidence
floor meets both bars. 250 dpi with no floor reaches 91.1% exact but 4.4% silently wrong. The
shipped setting is the one that protects the child's graph.

## Next, in the order that removes the most risk

1. **Test Grade 3 before anything else is built on this.** Every number above comes from Grade 2
   PDFs. Grade 3 is 38 pages of phone photographs — angled, pencil, with the educator's pen over
   the child's answer — and **not one has ever been read**. Enter one G3 paper, hand-verify one
   sheet, run `read eval`. If the approach does not survive a photograph, everything below is
   premature. This is the cheapest way to find that out and the largest unknown in the project.
2. **Enter the remaining papers** (`docs/w3-paper-inventory.md`): 10 of 14 have never been entered,
   including the Grade 3 baseline that all five of Aseem's gold reports are written from.
3. **Grow the gold set to ~300 responses.** `1/45 = 2.2%` is the smallest non-zero rate this gold
   can express, so the 1% bar is currently finer than the ruler. `gold_responses_min: 300` in the
   goal file is that arithmetic, not bureaucracy.
4. **The two named causes of the nine remaining misses**, both in `STATE.md`: free-response boxes
   where nothing marks which number is final, and faint pencil at low confidence. For the first,
   the clean option is a model that never reads digits and only CHOOSES among the numbers Textract
   already read — it cannot hallucinate an answer because it is picking from a list. For the second,
   image preparation before Textract (contrast, deskew, binarise) is completely untried.
5. **Then** read all 118 pages once, score, and build the graph. Not before: reading the corpus at
   80% would put a confident wrong diagnosis on sixteen real children.
6. **Then** the frontend, which is where Nimish wants to see the output.

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
