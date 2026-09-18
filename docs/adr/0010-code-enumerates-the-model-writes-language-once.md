# ADR 0010 — code enumerates the bank from the spec; the model writes language once per pattern

Date: 2026-09-19. Status: accepted. Supersedes the part of ADR 0005 that demoted the deterministic
samplers to "fallback and eval oracle, not the way a topic is added."

## Decision

A skill set's difficulty rule is already a machine-readable spec (`skill_set.difficulty[level]
.check`: operation, digit counts, allowed regroup counts, ceilings, zero rules). Code enumerates
every valid (a, b) pair from it, computes the answer, computes each misconception's wrong answer
with the existing predictors, and lays the item out in each allowed format — in a loop, for no
tokens. That is how every arithmetic unit of the bank is filled (`bank.fill` defaults to the
enumerator; `assess/items.py`'s generators cover the mental-strategy, estimation, multi-addend,
efficient-method, budget and find-the-mistake rungs the same way).

The model is paid **once per pattern**, not once per question: it writes a small library of
word-problem sentence templates with number slots for a skill set (a row Neha and Achal can edit),
and it judges a template's language when the template is written. Per-question model generation
(`item_generate`) remains for the item kinds whose language cannot be templated — explain a claim,
find the mistake in a worked example — and as the oracle the enumerator is evaluated against.

The validator agent follows the same rule: it checks each template once and a sample of at most
5 % of a unit's items, never every item. Code verifies every item's numbers regardless.

## Why

Nimish, 2026-09-19, on a ₹1,500 estimate for 3,200 questions: "You have not thought this through…
an infinite loop, which works as a Python script and generates questions in a loop, is how you
would do it. You won't keep on spending tokens on every single question, because the questions
are in a similar pattern only." He is right on both counts. Questions of one kind are a finite,
enumerable space; paying a model ~₹0.40 to "discover" `47 + 38` is paying for randomness code
provides for free. And the cost of the per-item design grows linearly with the bank, so the very
thing W1 is for — hundreds of items per unit, every unit — is what makes that design worst.

ADR 0005's reason for the opposite call was "no coding to add a topic." That still holds:
adding a skill set is rows, because the enumerator reads the `check` rows. The only code a new
*operation* needs is one sampler function, once (multiplication: ~15 lines), which
`ARCHITECTURE.md` §7.4 already priced in. What ADR 0005 got wrong was treating "the model
generates" as the way to avoid code, when the spec rows already were.

## Rejected

- **Per-item model generation as the default (ADR 0005).** Linear token cost in bank size for a
  patterned space; measured ~20k tokens per 20 items. Kept only as the exception above.
- **A validator model call per item.** Same flaw in the other half of the pipeline — it would put
  the whole cost back. Templates once, items sampled.
- **Per-item `word_context` calls for word problems.** A sentence template with slots is the
  pattern; the model writes the template, code fills the numbers.

## Consequences

`bank.fill`'s default flips: enumerate first, model only where a format has no generator. A
`sentence_template` row per skill set (or column on it) holds the templates; `word_context`
writes templates, not stems. `BUILD-ORDER.md` W1 gates 2, 4 and 6 state the cost bar: the whole
64-unit bank under ₹50 of model spend. `item_generate`'s eval keeps running — the model path is
now the oracle, as ADR 0005 intended the samplers to be, in the other direction.
