# 0029 — The engine settles only a right answer on its own; a wrong or a blank waits for a person

Date: 2026-09-21
Status: accepted (Nimish, 2026-09-21 night: "yes, let's build that part"). Supersedes the reader hold of
the same day for this one rule: the reader itself is unchanged.

## Context

Checking Aseem's five Grade 3 reports against the engine's own marks, three children's "strong" skills
showed more wrong answers than right. The crops showed why: 600 − 245 = 355, ticked by the teacher, read
as 921 (the next question's answer); 204 + 48 = 252, ticked, read as 204 (the top line of the working).
Both were marked wrong at 89–95% confidence and never reached a person.

A random sample of 40 answers the engine had settled with no person touching them, looked at crop by crop
(`STATE.md`, 2026-09-21 night):

| engine said | what the handwriting shows |
|---|---|
| correct (10) | 10 right |
| wrong (20) | 11 read and marked right · **4 right answers** (61 read as 6, 158 as 15, 252 as 204) · 2 read from the wrong place · 3 illegible |
| blank (10) | 3 truly blank · **5 right answers** written where the reader did not look (beside the `=`, in a box) |

The asymmetry is structural, not a quirk of the sample. A misread almost never lands on the exact key, so
when the reader's number equals the answer, the child wrote it. Every misread — a truncation, a working
line, the wrong question, an answer written off the line — comes out as `wrong` or `blank`. The 1.2%
silent-error figure the reader hold rested on was measured on 83 answers that did not look like these
photographs.

## Decision

`legacy.mark_read` is the one place the engine's own reading becomes a mark. It settles `correct` and
holds `wrong` and `blank`: status `needs_teacher`, the reading kept unchanged, the reading offered as
`raw_read.guess`, and `raw_read.why` saying which rule held it (`legacy.HELD`). A person's reading —
typed, confirmed in one click, or "Nothing is written here" — still goes through `mark`, so what a person
says was written stands and the engine does the arithmetic and names the mistake.

- `legacy.remark` holds rows the old rule settled; `engine legacy remark --every-child` runs it for every
  child in one transaction.
- `engine audit` gains "no wrong or blank answer stands on the engine's reading alone".
- The queue asks a held answer the way it asks a guess ("Yes, the child wrote 75"), not as a Right/Wrong
  judgement, and says why it is there; the paper's own screen offers "What the child wrote" filled with the
  reading and no Right/Wrong, because a judgement would drop the named mistake.
- Signing a paper off (`confirm_results`) already skips waiting answers, so a held answer cannot reach a
  child's graph until a person has said what the child wrote.

## Rejected

- **Keeping the hold and trusting the 1.2%.** The sample puts roughly 1 in 3 engine-settled wrongs and
  blanks on the reader, not the child (9 of 30; about 1 in 6 to 1 in 2 at this size).
- **Holding only readings that equal a number printed on the page** (23 of 185 wrongs on live). It catches
  one kind of misread; the sample's truncations (61 → 6) and off-line answers (272 beside the `=`) carry
  no such signature.
- **A second, independent reader whose agreement settles a wrong.** The right way to cut the clicking
  later, but it is a new reader and needs its own measurement first. Until then a person is the second
  reader.
- **A config row for the rule.** The only change it will ever take — letting agreed wrongs settle — needs
  code (the second reader), not a flag.

## Consequences

The queue grows by every engine-settled wrong and blank: 274 on the local copy (184 wrong, 90 blank),
about 280 on live, on top of the answers already waiting. Most settle in one click because the reading is
offered. The engine still settles right answers alone (332 on the copy), and the one spot-check per paper
keeps measuring whether that holds.

Revisit when a second reader exists and has been measured on the gold set with silently-wrong beside
exact, or when the engine's own printed papers, with one box per answer, have been measured the same way.
