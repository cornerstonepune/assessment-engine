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
bin/engine goal w3-read-and-graph      2/4 criteria · 21 scenarios short of the bar   (exit 1)
```

## The bar — agreed by Nimish 2026-09-20

In the goal file, with the evidence in `STATE.md` under *W3 opens*:

| | number | why |
|---|---|---|
| responses read exactly right | **97%** | regime A measured at 100%; regime B never attempted |
| responses given a row at all | **100%** | a missing row is invisible — today it is 88.9% |
| silently wrong (not flagged) | **≤1%** | a flagged error costs a glance, a silent one corrupts a graph |
| phone-photo floor | **≥93%** | 80 easy pages must not carry 38 hard ones |
| gold set | **≥300 responses, ≥100 phone photos** | ±1.9 points at n=300 |

The unit is the **response** — one child's answer to one question-part — not the page or the sheet.
Plus the correction loop he asked for: doubt goes to a person, their answer is stored, and it feeds
later reads. Stated plainly in the goal — the model does not learn and nothing is retrained; what
falls is the flag rate, because corrections accumulate as context. So a correction only counts if it
changes a **later** read.

**The finding that shaped it.** Hand-checking Advika's Cambridge Level A sheet against the 24 rows
the engine stored: 24 of 24 read exactly right, but the page holds 27 responses. Q5's three boxes
became one row, Q7's estimate and total became one. All three children who sat that paper produced
exactly 24 rows. The failure mode is **not emitting a row**, not misreading digits — so "% read
correctly" would score that sheet 100% and hide the hole.

## Next action

W3's gate 1 is **entering the papers**, and it is bigger than it looked. `docs/w3-paper-inventory.md`
is the work list: **14 distinct papers, 4 entered (1 proven wrong, 2 unchecked), 10 never entered.**

1. **Fix `G2-CAM-A`**: 24 slots for a 27-answer page. Q5's three boxes need three slots, Q7's
   estimate and total need two. Then re-read the 10 captures. Nimish's call, 2026-09-20: re-check
   all four entered papers now, not later.
2. **Check `G2-SEPW2-S1` (12 slots) and `G2-WORD-SEP17` (6 slots)** against their real pages.
   `G2-CAM-B` page 1 is already verified correct; its page 2 is not.
3. **Enter the 10 missing papers**, engine-proposes/person-approves. Order by what unblocks most:
   the **G3 16-question baseline** first — it is the gold paper, all five of Aseem's reports are
   written from it, and `8500 - 3647 = 5147` lives there.
4. **Then** build the `kind: read` runner (`engine/scenarios_read.py`), `engine read accuracy`, and
   `n8n/workflows/f3-read-and-graph.json` — the three things W3's goal names as missing.

**Fixed this session, not carried:** the two test children left active in the roster. Nimish ran
the deactivation (`UPDATE 2`); the roster now reads `G2|11`, `G3|5` — 16 active, matching disk. The
cause was a cleanup keyed on a section name that drifted, so the concurrency test now cleans up by
the ids it created and asserts none survives. Suite `301 passed`, `engine audit` `0 violations`.

**Still open, Nimish's call:** `child.section` is free text with no section table, which is what let
a test invent a section and leave it live. No audit invariant was added, because with sections as
free text it could only pattern-match on a test's name — a fabricated check, which the traps below
forbid. The real fix is a `section` table and a migration. Now, or after W3's gate 1?

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
