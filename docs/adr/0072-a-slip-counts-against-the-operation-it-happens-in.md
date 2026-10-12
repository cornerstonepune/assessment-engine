# ADR 0072 — A slip counts against the operation it happens in, in a question of several

**Status:** accepted (2026-10-12, slice M4d2b2 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4d2b2-what-a-slip-charges.yaml

## What happened

ADR 0023 charges a mistake to the skill of the operation it happens in; ADR 0055 (A11) carried it inside a written
method, so a multiplication's rows added without a carry are addition's. Measured on the bank (STATE.md "M4d2b2 —
measured before the build"), a question that carries two operations never got there: "Check 42 ÷ 3 = 11 by multiplying"
charged a times-table slip to Division, a fact family's division slips went to the fact family's own skill, and the bar
model's "leaves the smaller one's part out", whose row names Word problems, went to Division. `skills.charges` looked a
mistake up by the question's operation only when the question had one. And `skills.operations` read a two-step story's
stored copy of its operations first, so the template's halving (`divide: 2`) never counted on Division.

## Decision

1. **In a question of several operations, a mistake with a row for exactly one of them is charged as that row says**:
   to that operation's skill, or to the skill the row names. A mistake with rows for more than one (choosing the wrong
   operation) reads as before.
2. **A two-step story's operations are its template's**, its halving among them; the stored copy is read only for a
   story no template wrote.
3. **What is a choice is a row of the table.** Choosing the wrong operation in a missing-number equation or a fact family
   is a slip reading the equation, the kind's own skill (Mental maths & missing-number equations); it landed there by
   default, and the table now says it, so the one approval of the table (A11) covers it.

## Rejected

- **A row in the table for each (kind, mistake) the rule now gets right.** 469 charges moved on the bank, all by one
  rule; listing them would make the table the rule, and a person would approve rows instead of the principle.

## Consequences

- `bin/update-live`'s `bank relabel` rewrites the stored charges; evidence already recorded keeps what it charged
  (append-only), and live has no × and ÷ answers yet.
- On the bank, 530 × and ÷ charges move and 54 + and − ones: choosing the wrong operation in a + or − equation counted
  against Addition or Subtraction and now counts against the equation's skill, as the table says for every equation.
