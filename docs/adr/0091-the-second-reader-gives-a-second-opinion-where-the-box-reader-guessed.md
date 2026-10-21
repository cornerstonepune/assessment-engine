# 0091 — The second reader gives a second opinion where the box reader guessed (amends ADR 0032 §4)

Date: 2026-10-21
Status: proposed
Goal: goals/second-reader-every-guess.yaml

## Context

ADR 0032 §4 sent the second reader only what the first reader gave up on: a doubted reading with no guess. The box
reader of a printed paper (ADR 0035) almost always offers its best reading as the guess when it doubts one ("under the
confidence floor", "the reader's readings disagree", "2 boxes hold ink but the reader saw 4"). So on printed papers,
which are now every paper, the second reader was never asked: since 1 Oct, 8 doubted readings, 8 with the box reader's
own guess, 0 second-reader calls (docs/notes/reader-learns-audit.md). PR #244 asked Nimish whether it should give a
second opinion there too. Nimish, 2026-10-21 11:45 UTC: "yes".

## Decision

§4 now reads: **a second reader with the child's own examples, for what the first gave up on, and a second opinion on
what the box reader guessed.**

1. A reading read in the boxes of a printed paper that the box reader did not stand behind (`profiles.doubted`) and
   guessed is read again by the second reader: the same crop, shown up to eight of that child's confirmed answers.
   Notebook flags (a routed kind, a confused digit) are doubted readings with a guess, so they are included.
2. **Agreed** (the same digits, `profiles._norm`): the reading is returned exactly as it was. It waits for a person as
   before, the box reader's guess the one-click answer.
3. **Not agreed**: it waits for a person with both readings. The guess is still the box reader's; `second_read` holds
   the second reader's ("" for nothing), and the reason adds "the second reader, shown k of the child's answers, read
   …". The queue and the paper page say "Two readers disagree" and show both.
4. Unchanged from ADR 0032 and ADR 0019: the second reader never settles an answer, and it is shown no question and no
   right answer: only the child's samples, the crop and how many answers it holds. A reading the box reader stood
   behind is never sent to it, so no answer that settles alone today waits because of it.
5. **Off until it is measured** (rule 7): the threshold row `read.second_opinion` is 0. It is scored by
   `engine read guess --eval --second-opinion`, and on live by Actions → engine eval → read_with_examples
   (`.github/measure/second_opinion.py`), which scores this branch's code on every checked answer the box reader
   guessed. A call that fails is counted apart (`failed`), never as a wrong reading.

## Measured on live, 21 Oct (engine eval runs 39603709261, 39605855114)

- 34 printed papers read in boxes (26 Sep–16 Oct), 421 answers. The box reader guessed on 116 of them: about 3.4 per
  paper, one model call each. All 116 already waited for a person; none was settled without a person's word. **A second
  opinion sends no more answers to a person**: it changes what the person is shown.
- The box reader's guess was right on 82 of the 116 and wrong on 34. The 34 are the most a second opinion could catch.
- The second reader could not be scored: the live engine has no model key ("ANTHROPIC_API_KEY is not set"; the
  fallback models failed too), so all 116 calls failed and Rs 0 was spent. Its last guess on live was 29 Sep. Until a
  key is set, the second reader does nothing on live, for what the first reader gave up on as much as for this.
- Cost, approximate: its 49 calls that worked cost Rs 0.28 on average (Rs 0.73 at most), about 3,000 tokens in. At
  3.4 calls a paper that is roughly Rs 1 a paper.

## Rejected

- **Letting agreement settle the answer.** Two readers agreeing is still a model's word on a digit, which ADR 0019
  forbids; and it would let an answer skip the queue on the strength of a reader that knows arithmetic.
- **A second opinion on readings the box reader stood behind** (a kind not yet trusted, a spot check). Those wait
  for a person already or are trusted; asking about them would add a call per answer for no change in who decides.
- **A second opinion on Textract's guesses on papers read by region.** Not what was asked, and not measured; old
  papers only.
- **Showing the second reader's reading as the one-click guess when they disagree.** Its eval on what the first reader
  gave up on was 9 of 16; the box reader's own guess stays the default until the second reader is measured better.
- **Running the backfill (`engine read guess`) as a second opinion too.** It exists to turn typing into clicking on
  answers with no guess; asking it again on every run about answers already guessed would spend for nothing.
