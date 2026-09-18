# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: W1 — build the bank. Gates passed: 0 of 6.

Nimish reset the operating rhythm on 2026-09-19: one workflow at a time, perfected before the
next, no moving ahead, the sequence written in the repo and not in chat. The three sessions before
this built pieces of W1, W3 and the service layer out of order and left each incomplete —
`STATE.md` records what is verified from that work (a question generator measured correct on + and
−; an idempotent HTTP surface with a Docker image; a first legacy reader run on 10 of 84 real
sheets). All of it is reusable inside W1 and W3; none of it counts as a gate until that gate's
command is run and its output recorded.

Where W1 actually stands, measured on 2026-09-19: 4 of 16 rungs have a skill-set spec, all four
still `draft`; 1 of those 4 has any items; 2 of the 64 skill × difficulty units have anything in
them (2-digit subtraction with exchange: 120 Medium, 80 Hard); Easy and Advance are empty
everywhere; the code verifier knows + and − only.

## Next action

1. **Get Nimish's yes on `BUILD-ORDER.md`'s six W1 gates** — he asked for the approach to be
   defined before any code, and for the ~50-items-per-unit number (the workflow document's own) to
   be confirmed. Do not write W1 code before that yes.
2. Then W1 gate 1: draft the 12 missing skill-set specs (R1–R4, R7, R8, R11–R14, X1, X2) as rows,
   for Neha and Achal to correct. Nothing else.

## Blocked on Nimish

- The W1 gate list and the 50-per-unit number.
- Budget: 64 units × 50 ≈ 3,200 items ≈ ₹1,000–1,500 on Haiku at the measured ~20k tokens per
  20-question request. `llm.daily_budget_inr` (₹150) spreads that over ~8 days or is raised.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET`
  on Vercel if unset; the n8n owner account when F1 is wired (W1 gate 5).

## Traps — do not repeat

- **Building out of order.** Each of the last three sessions opened a new area before the last
  was done. `BUILD-ORDER.md` rule 1 exists because of this.
- **Pivoting from chat.** QR was nearly built next because one sentence was misread. Restate, get
  a yes, write it into `BUILD-ORDER.md`, then build.
- **Answering "is X built?" with a mechanism instead of a number.** The bank was 2 of 64 units.
- Still true, technical: `roster` is an unused import in `engine/legacy.py` (pre-existing, left
  alone); Docker's credential helper hangs from a non-interactive session (STATE.md N3.2 has the
  workaround); an idempotency key derived from a generic request body is not private to a test.
