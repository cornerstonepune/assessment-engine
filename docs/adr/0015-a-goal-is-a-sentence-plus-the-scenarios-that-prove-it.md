# 0015 — A goal is a sentence plus the scenarios that prove it

Date: 2026-09-20
Status: accepted

## Context

`BUILD-ORDER.md` holds W1–W4 and six gates each, in prose, with the proving commands written into
`STATE.md` after the fact. That is a document, not a mechanism: the commands only run when somebody
remembers them, and "done" survives as an opinion between sessions.

Worse, the tests were being written the wrong way round. Every defect this repository has found
recently was found *by accident* — a test touching a neighbouring property, a scan of a file that
happened to be open. Nimish, 2026-09-20, twice: "with every test you are finding an error — how do
we know that we don't have any more errors", and then "we need to start having a very specific goal
for every task/milestone and have very specific tests to prove that goal … If the assessment
engine's goal is to build the set of questions for given difficulties for a given task, with a set
of conditions for a subject, the system should be able to test that across a couple of scenarios
(which also should be defined when the development is happening). The system should keep on working
towards it till 100% accuracy is achieved."

## Decision

A goal is a file: `goals/<name>.yaml`, run by `engine goal <name>`. It has three parts.

1. **The sentence** — what the thing must *do*, in the school's terms, not the code's.
2. **`scenarios`** — real requests, each checked independently of the code that answered it. W1's
   ten scenarios name a skill set, a difficulty and a count; the runner asks the engine for them and
   then, without trusting anything the engine said: recomputes every answer from the numbers,
   re-measures every question against that band's own rule, checks every wrong answer maps to a
   mistake the vocabulary names, and checks no two questions are the same. Nothing is stored.
3. **`criteria`** — the whole-repository checks, as commands: `engine audit`, `bank coverage`,
   `bank recheck`, `load --check`, the suite.

**The bar is 100%.** A scenario that produces 19 of 20 asked-for questions has not met the goal, and
the command exits non-zero until it does. The scenarios are written when the work is planned, not
after it passes.

Beside it, `engine audit` answers the other half of the question — what is wrong that nothing is
looking at? — as twelve named invariants over every row: every rung has a ratified spec, every code
resolves, one active prompt version per purpose, every band can produce a question, no spec claims a
mistake its own numbers cannot produce, every misconception a stored item names exists, every
answer-lookup code is computed somewhere, every unit meets its target, every stored item still
satisfies its band. A new class of bug becomes a new invariant here, never another test that happens
to notice it.

## Alternatives rejected

- **Leave the gates as prose in `BUILD-ORDER.md`.** It is what we had. Three sessions drifted
  because nothing failed loudly when a gate quietly stopped being true.
- **Treat the unit suite as the definition of done.** 294 tests pass and did not notice that
  multiplication questions had no diagnosable wrong answers: the suite checks the parts, the
  scenarios check the promise.
- **A hygiene checklist only** (lint, coverage, tests green). That is `criteria`, and on its own it
  says nothing about whether the engine does its job.
- **Scenarios that call a model.** They would cost money per run and wobble. The scenarios use the
  enumerator path, which is free and deterministic; the model's own quality has its own eval
  (`engine eval`), scored separately.

## Consequences

- W2, W3 and W4 each need a goal file written *before* their work starts — for W3 that means the
  reading accuracy bar against the 84 real sheets, stated as a number, before any reader is built.
- `engine goal` is the single answer to "is it done?", and `bin/engine` makes it runnable from any
  directory, including by Nimish.
- What the audit and the scenarios do not cover is now the explicit list of what we do not know.
  `STATE.md` carries it.
