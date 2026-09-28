# ADR 0039 — Mistakes are learned from children's answers, as column rules

**Status:** accepted (Nimish, 2026-09-28)
Goal: goals/s22-learned-mistakes.yaml

## Context

Step 7 asked for "distractors nobody picks" to become proposals. Asked what approving one should do, Nimish answered
with the opposite direction: grow the mistake list rather than prune it. "Whenever there is an answer that the student
writes which is not found in the answer list, the system should create that as a mistake so that next time, when a
child does that, that is found."

A named mistake here is code: given the two numbers, it computes the exact wrong answer (`assess/misconceptions.py`).
To recognise a mistake on a question it was never seen on, a learned mistake has to be code too. A stored answer
matches only one question.

## Decision

- **The space.** A learned mistake is a column rule (`assess/learned_rules.py`): what each column writes, what it
  carries or borrows and where that lands, whether the last carry is written, how the numbers are lined up, and whether
  the answer comes out reversed or with a placeholder zero dropped. There are 540 rules for adding and 504 for taking
  away. The right method is one of them.
- **Proof that it is the right space.** Every procedural mistake people named by hand lies in it: 20,267 of 20,267
  answers on 6,000 sums of up to four digits. Slips of a fact and the other operation are left out on purpose, because
  they are slips, not ways of working (ADR 0036).
- **What counts as evidence.** A wrong answer a person confirmed, on a two-number `+` or `−` question, that no named
  mistake explains and no person named from the list.
- **Search.** Code finds every rule that reproduces each such answer. It is exhaustive and exact, so nothing is guessed.
- **Proposal.** A rule reproducing such answers on at least `mistake.learn_min_questions` (2) different questions is
  proposed once. The widest and simplest rule comes first, and a rule whose answers another already explains is not
  offered again.
- **Adoption.** A person names the rule and adopts it: it joins `misconception` with code `L_` + a hash of the rule, and
  is stored in `learned_mistake`. Or the person rejects it.
- **Recognition.** Marking recognises an adopted mistake when a wrong answer carries no named one, at reading time
  (`marking.verdicts`), on a person's correction and on re-marking.

## Rejected

- **Pruning the list** (a mistake nobody makes is dropped from a skill set). Nimish asked for the opposite, and a
  mistake unseen in 30 answers is not evidence it will never be made.
- **Storing the child's exact answer as the mistake.** It would recognise the same answer to the same question only.
- **Jev or a model to say what the child did.** Code can compute it exactly, so a model is not asked (rules 11 and 12;
  ADR 0036: arithmetic stays in code). A model could suggest a name. It is not needed: the rule's description is
  generated from its parts, and a person names it.
