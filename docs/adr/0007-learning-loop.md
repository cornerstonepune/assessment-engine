# ADR 0007 — the learning loop is rows, retrieval and eval gating, not model training

Date: 2026-09-19. Status: accepted.

## Decision

The reading models (Claude, Gemini) are never fine-tuned — we cannot retrain a frontier vision
model on one child's handwriting, and would not want to if we could (ADR 0006: no harness, no
hidden state). What learns instead:

1. Every settle where a person edits what the model read writes a `read_correction` row
   (child, capture, item_result, model's read, the true read, by whom).
2. `child_reading_profile` is rebuilt from those rows by code — digit-confusion tallies, a
   habit, the last few corrected crops — never by a model, and truncatable at any time (ring B).
3. A read for a child whose profile has notes carries them, plus a few corrected examples, in
   the prompt (`{{child_notes}}`, few-shot images) — this is retrieval, not weight change.
4. Every correction is also a `gold` row. `engine eval <purpose>` scores a prompt version
   against the accumulated gold set; a new version activates only if it matches or beats the one
   it replaces (rule 7).
5. Confidence and queue routing read from measured overturn rates (`read.route_above_overturn`),
   not a fixed guess.

## Why

Think of a new teacher marking a class's books: by the second week she knows whose 7 looks like a
1 and who writes the answer in the margin. She has not rewired her brain; she keeps a note and
reads with it next time. That is the only kind of "getting better" available to us, and it is
enough — the model is frozen, the context around it is not.

## Rejected

- **Fine-tuning a vision model on corrected crops.** Not offered for the frontier models this
  system uses, and the volume of corrections from one small school would not support it even if
  it were.
- **A vector-search "memory" layer.** The correction volume per child is a few dozen rows at
  most; a `jsonb` profile rebuilt by a SQL/Python pass is simpler and stays inside rule 1 (nothing
  structural is a model's guess) — no new infrastructure for a problem this size.

## Consequences

`read_correction` and `child_reading_profile` (migration `20260919090000_service_foundations`)
exist from chunk 1; chunk 3 writes `read_correction` from the settle flow and grows `gold`; chunk 6
builds `rebuild_profiles` and wires the profile into the prompt. Plan:
`docs/superpowers/plans/2026-09-18-spine.md`.
