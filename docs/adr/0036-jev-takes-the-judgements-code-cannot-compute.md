# 0036 — Jev takes the judgements code cannot compute; what code can compute stays code

Date: 2026-09-27
Status: accepted — Nimish, 2026-09-27: *"I'm convinced with all the use cases we have mentioned, so build as many as
you can where the impact is maximized in this context."*
Goal: goals/j1-jev-mistakes.yaml

## Context

Jev (TypeSafe, `api.typesafe.ai`, model `jev-latest` = jev-1.13.0) answers questions fixed in advance — yes/no, one of
up to 255 named options, or a score — each with probabilities, from text or JSON; it writes no text and reads no image
(its own `openapi.json`). Measured here: 290–530 ms a call. `research/2026-09-27-jev-use-cases.md` maps eight uses.

Nimish's first framing was "anything deterministic, we can do it through Jev", e.g. generating each question's wrong
answers and matching a child's to them. Measured on the live API, that is the part Jev is worst at and code already
does: asked whether 45 is a right answer to 81 − 46 it said 0.47, then 0.50; the 49 named mistakes' predictors already
compute every question's wrong answers exactly, marking already matches them, and the home assessment already puts
first the questions that can show a child's repeated mistake (`focus_paper._can_show`).

## Decision

- **Computable stays code**: arithmetic, marking, the named mistakes' wrong answers, levels, the graph. Exact, free,
  microseconds, and a reason a teacher can read.
- **Jev takes judgements code cannot compute**, each a prompt row (`model: jev-latest`, text = the instructions,
  `json_schema.type` = choice / noul / score), each with an eval before it is used (rule 7), each call a `flow_run`.
  One adapter: `adapters/jev.py`. An answer outside the options is refused, never passed on.
- **First purpose, `mistake_guess`**: a wrong answer no predictor reproduces gets Jev's three likeliest named mistakes
  or NONE. It is a shortlist for a person; nothing is named without one. Measured on gold built by the predictors (two
  sets of 120): the right mistake among the three 109 and 110; every slip (60 of 60) called NONE, none given a mistake.

## What this does not prove

The gold is built from mistakes code *can* reproduce; in use Jev is asked only about the ones it cannot. The first
real measure is people's picks on Marking.

## Rejected

- Sending arithmetic or anything code computes to Jev — slower, paid, and a probability where the answer is known.
- A worked example beside each mistake's name — measured: first-choice 42/90 against 47/90, confidence less telling.
