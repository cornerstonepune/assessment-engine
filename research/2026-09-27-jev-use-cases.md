# Jev: where it earns its place (2026-09-27, measured on the live API)

Nimish, 2026-09-27: deep-dive Jev and find every use case. Supersedes the "not now" of 2026-09-21.

## What it is, from its own API (`GET /openapi.json`, `POST /v1/systemone`, model `jev-latest` = jev-1.13.0)

Text or JSON state in; answers to questions defined in advance out: `noul` (yes/no as a probability), `choice` (one of
up to 255, with probabilities), `score` (a rating on a legend). No images; nothing generated. Measured here: 290–530 ms
a call, ~400 input tokens for a small question. A request with 50 long option descriptions returned HTTP 520; short
option names worked.

## The dividing line, measured

- Asked "is 45 a right answer to 81 − 46?" Jev said 0.47, then 0.50: a coin toss. Arithmetic is code's.
- Asked which named mistake explains four wrong subtraction answers: right on 81−46→45 (smaller-from-larger, 0.49) and
  74−39→45 (exchanged but tens not reduced, 0.50); **wrong** on 63−28→45 ("none", 0.72), which the engine's predictor
  reproduces exactly and for nothing.

So: **what can be computed stays code** (exact, free, microseconds, a reason a teacher can read) — the 49 named mistakes'
predicted wrong answers, marking a wrong answer to its mistake, choosing a home paper's questions by the child's repeated
mistake (`focus_paper._can_show`), levels, the graph. **Jev takes the judgements code cannot compute** and today go to a
large model or to a person, wherever it matches or beats that on a gold set (rule 7).

## Use cases, in the order they would pay

| # | Decision | Today | With Jev |
|---|---|---|---|
| 1 | An educator's week in words ("we did exchanging in subtraction") → skills and levels (N4) | not built | a choice per skill, in under a second, as they type |
| 2 | A question's text → its skill / taxonomy case (`skill_match`) | large model, ~44 s a call | two-stage choice over 244 skills / 270 cases |
| 3 | A wrong answer no predictor reproduces → the likely named mistake, or "none" | lands unexplained | a ranked proposal for a person; "none" answers grouped as candidate new mistakes (step 7) |
| 4 | The working's text (read from the working box) → the method used, exchange shown or not | "working shown: yes/no" | a richer third signal (rule 5) |
| 5 | Language and pedagogy review of a question template → pass / fail with a score | large model, reasons and verdict | Jev's verdict; the large model writes reasons only for a fail |
| 6 | A child's standing → which sentences of an approved parent-note bank apply | large model writes free text | choices from sentences the school wrote once: no invented claims about a child |
| 7 | Near-duplicate questions; is this question right for Grade 2 | not built | yes/no and scores for the bank's upkeep |
| 8 | Is this reading right (reader's words, key, the child's history) | a person checks | only after step 2's checks measure it: a model that knows arithmetic leans to the right answer (ADR 0019) |

Children's data: only question text, numbers and codes are sent; never a name or an image (rule 6).
