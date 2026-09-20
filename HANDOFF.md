# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Its goal is written and red on purpose. Blocked on one yes.**

W1 and W2 are done. Verified again at the start of this session, not assumed:

```
bin/engine goal w1-build-the-bank      10/10 scenarios · 5/5 criteria · GOAL ACHIEVED
bin/engine goal w2-assemble-and-print  12/12 scenarios · 4/4 criteria · GOAL ACHIEVED
bin/engine audit                       12 invariants · 0 violations      (suite: 301 passed)
```

`goals/w3-read-and-graph.yaml` now exists — written before a line of reader code, as ADR 0015
requires. It opens red, which is correct:

```
bin/engine goal w3-read-and-graph      2/4 criteria · 17 scenarios short of the bar   (exit 1)
```

## The one thing blocking W3's reader: Nimish's yes on the bar

Proposed in the goal file, with the evidence in `STATE.md` under *W3 opens*:

| | number | why |
|---|---|---|
| responses read exactly right | **97%** | regime A measured at 100%; regime B never attempted |
| responses given a row at all | **100%** | a missing row is invisible — today it is 88.9% |
| silently wrong (not flagged) | **≤1%** | a flagged error costs a glance, a silent one corrupts a graph |
| phone-photo floor | **≥93%** | 80 easy pages must not carry 38 hard ones |
| gold set | **≥300 responses, ≥100 phone photos** | ±1.9 points at n=300 |

The unit is the **response** — one child's answer to one question-part — not the page or the sheet.

**The finding that shaped it.** Hand-checking Advika's Cambridge Level A sheet against the 24 rows
the engine stored: 24 of 24 read exactly right, but the page holds 27 responses. Q5's three boxes
became one row, Q7's estimate and total became one. All three children who sat that paper produced
exactly 24 rows. The failure mode is **not emitting a row**, not misreading digits — so "% read
correctly" would score that sheet 100% and hide the hole.

## Next action

1. **Get the yes on the five numbers above**, or the corrected ones. Change one line of
   `goals/w3-read-and-graph.yaml` per number changed.
2. **Then build the reader, in the goal file's own order** — the `kind: read` runner first
   (`engine/scenarios_read.py`), because every scenario is red behind it. The two failing criteria
   name the other two deliverables: `engine read accuracy` and `n8n/workflows/f3-read-and-graph.json`.
3. **The gold set is the long pole and it needs a person.** ≥300 hand-marked responses across ≥22
   pages. Much of the truth is already on the page in the teacher's red pen — which is also exactly
   the regime-B hazard the reader must not fall for.
4. **Two captures are stuck on a billing error, not a code fault**: `claude-sonnet-5 returned HTTP
   400: Your credit balance is too low`. Also note those two ran on Sonnet, while `STATE.md` N3.1
   records the three read prompts as pinned to Haiku — worth confirming which path sent them
   before the first real read batch.

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
