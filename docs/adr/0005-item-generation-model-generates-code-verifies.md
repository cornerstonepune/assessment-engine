# ADR 0005 — Item generation: a prompt generates, code verifies, staff retire

Date: 2026-09-17. Status: accepted; **superseded in part by ADR 0010 (2026-09-19)** — the
deterministic enumerator, not the prompt, is the default for every unit code can enumerate from
the spec; the prompt writes language once per pattern and remains the path for item kinds whose
language cannot be templated, and the eval oracle. "Code verifies, staff retire" stands unchanged.

## Decision

The question bank is produced by a **prompt**, not by per-topic generator code. The input is a
skill-set spec authored as rows — topic, learning objective, registry skill, the difficulty rule
in words (Easy/Medium/Hard/Advance), the philosophy lines, the allowed formats, and the
misconception list with descriptions. One versioned `prompt` row (`item_generate`) turns that
into candidate items, each carrying its answer and the exact wrong answer every listed
misconception would produce.

**Code then verifies every number** — recomputes the answer, checks the difficulty rule, compares
each misconception claim to a predictor where one exists, rejects duplicates and forbidden words —
and only items that pass land `approved`. Any staff member can flag any item from the library;
a flag retires it and joins the prompt's eval set.

Adding a topic is therefore rows in a form. Python changes only when the verifier meets a rule
it cannot yet check (a new operation's regroup rule, ~10 lines) or a format needs a new renderer.

## Why

- The requirement is an engine for *any* topic in a school with no engineer. "~120 lines of
  Python per operation family" is a cost the school cannot pay each time the syllabus moves.
- Measured, not assumed: on 20 Hard subtraction items the model's arithmetic was right on all
  twenty and 77/77 of its misconception distractors matched the code predictors; the three
  malformed items were caught by the verifier (`research/2026-09-17-prompt-generation-spike.md`).
- Correctness is preserved by *verification*, which is generic, rather than by *generation*,
  which is per-topic. The answer key is still never a model's last word.
- Model errors that slip past a missing predictor surface at marking: a child's wrong answer that
  matches no distractor goes to the confirm queue the teacher already works.

## Rejected

- **Code-first generators as the general path** (ARCHITECTURE §7 as first written). Exact and
  fast for addition and subtraction, but every new topic is an engineering task. They stay as the
  fallback and as the eval oracle for the prompt path; they are not the way a topic is added.
- **A model with no verifier.** One run showed a 15 % malformed rate on one format. Unverified
  items would print wrong keys.
- **Per-item human review.** Already rejected under the workflow's "template is the unit of
  trust"; the staff flag is after-the-fact retirement, not a gate before printing.

## Revisit trigger

A topic where the verifier cannot check the rule and no small checker is possible (open-ended
reasoning, explanation items) — those need an eval-scored rubric prompt instead, a different
design. Or a measured accepted-item error rate above zero on any gold set.

## Consequences

`ARCHITECTURE.md` §7 and `SPEC.md` §5.6 rewritten. `CLAUDE.md`'s "code where correctness is
needed" gains the clause "a model may generate what code then verifies". New table
`item_feedback` is required (not in the Phase 0 schema). The existing `items.py` samplers are
demoted to fallback and eval, not deleted.
