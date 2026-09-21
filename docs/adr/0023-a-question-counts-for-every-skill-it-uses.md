# 0023 — A question counts for every skill it uses: all of them when right, the broken one when wrong

Date: 2026-09-21
Status: accepted by Nimish; built after the current system is live on the server

## Context

The founder asked how questions that cover more than one concept are handled. About 5,200 of the
bank's 12,567 questions combine concepts: two-step and budget problems (1,296), estimate-then-work-out,
find-the-mistake, explain and quickest-method (864 each), number walls and balance scales (216 each).

Today a child's answer to any of them reaches the graph as one `evidence_event` for one skill —
`coalesce(spec ->> 'skill', skill_codes[1])`, the first label — so a two-step problem that needs
adding and subtracting counts for "word problems" alone. And the labels are copied from the rung, not
read from the question: `bank.fill` gives every item its rung's `skill_codes`, so the 864 questions
of "3-digit addition with regrouping" also carry subtraction.

## Decision

Nimish, 2026-09-21: *"A question can have attribution to multiple skills. When a student gets that
kind of a question wrong, there is a part of that skill that the child has got wrong. That can be
attributed. If he gets it right, then all three skills get attribution. It should be simpler in that
sense."*

1. **A question's skills are the concepts it actually uses**, decided by code from the question
   itself — never copied from its rung.
2. **Right answer:** one confirmed piece of evidence for every skill the question uses.
3. **Wrong answer:** evidence against the skill whose part broke, named by the answer's own mistake —
   on a budget problem, 4463 is "added the costs but never took them from the budget". Every named
   mistake therefore has to say which skill it belongs to.

Two things that are not the same, in his words:

- **A multi-skill question** is two or three concepts coming together in one question. It is defined
  as its own skill set — a complexity level — wherever concepts sensibly combine (addition and
  subtraction inside a budget problem; later, the precursors of a topic like permutations).
- **A mixed bag** is a paper: individual questions from two or three skill sets put in one bag.

## Rejected

- **One skill per answer** (today): a two-step problem cannot tell adding from subtracting, and the
  graph loses the diagnosis the question was built to make.
- **Every skill charged for any wrong answer:** a child who adds perfectly and forgets the second step
  would be marked down on addition too.

## Open, to settle when this is built

- A wrong answer no named mistake explains: which skill it counts against.
- Where a named mistake's skill is recorded: a row per mistake (`misconception`), not a table in code.
