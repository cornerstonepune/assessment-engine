# ADR 0009 — a subject is a row, a prompt scope, and at most one verifier module

Date: 2026-09-19. Status: accepted.

## Decision

A second subject (science, English, …) plugs in as:

1. A `subject` row: `code`, `name`, `mark_mode` (`lookup` or `rubric`), and an optional
   `verifier` naming a module under `engine/subjects/`.
2. Its own skill/rung/skill-set rows, exactly as maths already works (rule 1).
3. A master `item_generate` prompt row scoped to it (`prompt.subject = code`) — the "one master
   prompt per subject" the founder asked for. `llm.generate()` prefers a subject-specific row over
   the shared one for the same purpose; falls back to the shared row when the subject has none.
4. `validate_item` (chunk 5) and `validate_read` (chunk 3) run for every subject unconditionally —
   a model plus a ratified first sample is the floor every subject gets.
5. **Only where a verifier module exists** does code also recompute the answer before an item is
   trusted (ADR 0005) — maths keeps its exact guarantee; a subject with no verifier relies on the
   validator prompt and a person, same as marking free-text ("rubric" mode routes every answer to
   `needs_teacher` with the rubric shown, never auto-marked).

`engine/subjects/maths.py` is where `assess/verify.py`'s rule checks, `assess/misconceptions.py`'s
predictors, and `legacy.py`'s `rung_for`/`parse_expr`/`mark` move to (chunk 5) — today they are
free functions with no subject boundary; moving them behind `subjects.verifier("NUM")` is what
makes "no code for a second subject" true rather than aspirational.

## Why

The founder's requirement, verbatim in intent: give the system a topic, a learning objective and a
skill map, and a master prompt per subject decides how questions for that subject look; the system
should not need new Python to add biology. The data model already supports this (`skill.domain`,
`tenant_id` everywhere, `item.spec` as `jsonb`); only the code path was maths-shaped. This ADR is
the seam: subjects differ in *prompt and verification strategy*, never in orchestration — n8n's
workflows call `/bank/fill {subject, skill_set, difficulty}` and never know which subject it was.

## Rejected

- **A generic auto-verifier that tries to check any subject's arithmetic-like answers.** Answer
  checking is subject-specific by nature (a science claim isn't a number); pretending otherwise
  produces a verifier that quietly does nothing for most subjects while looking like a guarantee.
- **One `item_generate` prompt with subject as a variable inside it.** Works until a subject's
  question shape diverges enough to need its own structure (options, a rubric, no operands) —
  scoping by row from the start avoids a prompt trying to serve two shapes at once.

## Consequences

`subject` table and its seed row (`NUM`) land in chunk 1; the prompt-scoping SQL and
`llm.generate(..., subject=)` land in chunk 1 alongside it; `engine/subjects/` and the second,
generic `item_generate` prompt land in chunk 5, proven by inserting a real second subject (SCI)
and filling its bank through rows only. Plan: `docs/superpowers/plans/2026-09-18-spine.md`.
