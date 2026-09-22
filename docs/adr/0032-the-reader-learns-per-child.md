# 0032 — The reader keeps a notebook per child, and reads with it open

Date: 2026-09-22
Status: accepted (inserted after step 8, `BUILD-ORDER.md`)
Goal: goals/reader-learns.yaml

## Context

ADR 0007 (2026-09-19) decided how the reader learns: never by retraining a model, but by rows —
`read_correction` written from every settle, `child_reading_profile` rebuilt from them by code, the
profile carried into the next read, measured overturn rates routing doubt. Three days later the
first two children were fully checked (95 answers), 121 answers had been typed by a person, and
`child_reading_profile` held **0 rows**. A correction changed its own row and nothing after it.

The reader is Amazon Textract (ADR 0019) behind the engine's own geometry, with one confidence
floor (70) for every child. On the 121 typed answers, at 90+ confidence it was right 33 of 42; at
70–89, 7 of 17; below 70, 1 of 30. Per child it ranged from 13 of 34 to 6 of 28. When it gave up
("3 numbers in the region for 2 answers", the largest reason answers reach a person) it recorded
nothing of what it had seen, so a correction on those answers could not even be compared.

Nimish, 2026-09-22: *"do not give me any other story afterwards … the handwriting of the student
starts remaining more consistent … I want you to first tell me how you are wiring, and then only go
ahead and wire."*

## Decision

**A notebook per child, rebuilt by code from every check a person makes, and read before every read
of that child.** Concretely:

1. **Every reading records what the reader saw** (`raw_read.seen`: each number in the region with its
   confidence), including the readings it gave up on. A sign-off without a correction counts as
   "the reader was right"; today only a correction counted.
2. **The notebook** (`child_reading_profile.notes`, ring B, `engine read profile`): per child — how
   often the reader was right, by kind of question and by confidence; its **own confidence floor**
   (70, 80, 90 or 95 — the lowest level at which this child's readings were right 95% of the time
   over at least ten checks); the **kinds routed to a person** regardless of confidence (overturned
   more than `read.route_above_overturn` of the time — the threshold row that has existed unused
   since ADR 0007); **digit confusions** (read 1, the child wrote 7); and up to eight **confirmed
   handwriting samples** (a crop and what it says).
3. **The next read of that child changes.** The child's floor replaces the global one; a reading of
   a routed kind, or holding a digit this child has had confused twice, is flagged with the reading
   offered as the one-click guess. The engine learns to doubt; it never silently changes a reading
   (rule 5, `silently_wrong_at_most`).
4. **A second reader with the child's own examples, for what the first gave up on.** The crop goes
   to the vision model *with that child's confirmed samples* as labelled examples, and its reading
   is offered as the guess. It never settles an answer alone — ADR 0019's reason stands (a model that
   knows arithmetic must not be the one that settles a digit); what widens is that it may *propose*,
   because a person always decides. It ships with an eval (rule 7): its guesses against the answers
   people have already typed.
5. **Trust is earned per kind** (`marking.agreement_gate`, 0.95, also unused until now): the reader
   settles a kind of question alone only once its readings on that kind have matched people 95% of
   the time over the last fifty checks. Until then every reading of that kind goes to a person with
   the reading as a one-click guess. This is what makes the queue shrink by itself as accuracy rises.
6. **It is measured, per batch** (`engine read report`, and on Capture & Mark): reader right, silently
   wrong, gave up, and each kind's standing against the gate — so the effort can be seen to pay.
7. **The proof is a replay** (`engine read replay`): a child's signed-off paper is read again with and
   without the notebook built from that child's *other* papers, and both are scored against what
   people confirmed. A correction must change a later read, or the loop is not built.

## Rejected

- **Retraining or fine-tuning the reader.** Not available for Textract, and ADR 0007 already rejected
  it for the vision models; a school's volume would not support it.
- **Letting the second reader settle answers.** It knows arithmetic, which is the failure ADR 0019
  removed; proposing is safe because a person confirms every proposal.
- **A per-child × per-kind trust gate.** Forty answers per child per kind is too few to measure 95%
  on; the gate is per kind across children, and the per-child route rule sits on top of it.
- **Lowering the floor below 70 for a child the reader reads well.** Below 70 the reader was right 1
  of 30 times; the floor only rises.
- **A separate batch table for the flag-rate series.** It is derivable from `capture.created_at`; a
  report computes it (ring B), nothing is stored twice.
