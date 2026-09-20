# 0019 — The transcription layer is an OCR engine, because it must not know arithmetic

Date: 2026-09-20
Status: proposed — needs Nimish's choice of vendor

## Context

Nimish, after watching five rounds of prompt-tuning: *"isn't there an established technology to do
this? I am surprised we are figuring this from scratch — a normal OCR or a version of image
recognition should be able to do this much better — you aren't researching sufficiently — obviously
someone has solved this basic issue."*

He is right, and the measurements say so twice over.

**What we built scores 63%.** `engine read eval` against a page a person read by eye, worst of three
runs: `legacy_extract` v2 55.6%, v3 59.3%, v4 63.0%. The bar is 97%.

**Every stubborn error is the same one**: the reader returns the *arithmetically correct* answer
where the child wrote a wrong one. `425 − 38` read as `387` where the child wrote `397`.
`250 + ☐ = 300` read as `50` where the child wrote `150`. `763 − 427` read as `336` where the child
wrote `1190` — the child having added instead of subtracted, which is the single most valuable
observation on the page.

Four attempts to instruct it away, each measured:

| attempt | result |
|---|---|
| tell it plainly not to compute (v2, v3) | 55.6% / 59.3% |
| stop asking it for the printed question, hand it the answer slots instead (v4) | 63.0%, and missing rows fixed 81.5% → **100%** |
| cut the page into overlapping bands so each digit gets more pixels | 63.0% — better on a probe, no better overall |
| mask the digits in the slot list so the prompt carries no sums | **51.8% — worse** |

The band probe is the diagnostic one. Asked for six answers on a whole page the reader got two
right; asked for the same six on tight crops it got four, and **both it gained were cases where it
had been returning the correct answer instead of the child's.** It was never disobeying. It could
not see the pencil, and a model that knows arithmetic fills an uncertain gap with the answer it can
compute. No phrasing fixes that, because the arithmetic is not in the prompt — it is in the model.

**And the field solved this long ago.** 2026 handwriting benchmarks, word error rate:

| engine | WER |
|---|---|
| Handwriting OCR (specialist) | **0.9%** |
| Azure Document Intelligence | 8.67% |
| AWS Textract | 10.5% |
| Claude Sonnet | 11.2% |
| GPT-5 vision | 14.4% |
| Google Document AI | 23.3% |

This engine reads on **Haiku**, smaller than the Sonnet that scores 11.2%. Azure reaches roughly
95% on neat printing and block handwriting — which is exactly what a Grade 2 child's digits are —
and falls to ~45% only on cursive narrative, which these papers barely contain.

## Decision

**Transcription moves to an OCR engine. The model keeps only the judgement.**

The argument is not that OCR is more accurate, though it is. It is that **OCR cannot commit our
worst error at all.** An OCR engine has no idea that 348 + 27 = 375, so it can never write 375 where
a child wrote 374. Our principal failure mode is not reduced; it is structurally impossible.

This is CLAUDE.md's own rule, which we broke: *"Code where correctness is needed … a model where
judgment is needed. Never the reverse."* Reading a digit off a page is recognition, not judgement.
We put a mathematician on a proof-reading job, and it kept correcting the text.

The second gain is as large. OCR returns **calibrated per-word confidence**, and AWS Textract
returns per-cell confidence on form fields. That is the thing this session established a model
cannot do for itself — `skill_match` gave the same question different confidence labels on different
passes, which is why ADR 0018 forbids self-reported confidence. A confidence number from OCR is
measured, not claimed, and it routes doubt to a person, which is what `silently_wrong_at_most: 0.01`
requires and what the whole approval loop is built on.

The layers become:

| layer | who does it | why |
|---|---|---|
| find the answer regions | code, from the paper's slots | geometry, already known |
| read the marks | **OCR** | recognition, with a confidence number, and no knowledge of sums |
| mark right or wrong | **code** | already true — marking is a lookup against computed answers |
| name the mistake | **code** | already true — misconception predictors |
| judge what code cannot | a model | a written explanation, an unusual method, the Channel B reading |

## Alternatives rejected

**Keep tuning the prompt.** Five measured attempts moved it from 55.6% to 63.0% and one made it
worse. The gap to 97% is not a wording gap.

**Use a bigger vision model.** Sonnet's 11.2% WER against a specialist's 0.9% is still an order of
magnitude, it costs more per page, and it keeps the arithmetic knowledge that causes the errors.
Worth measuring as a control, not as the answer.

**Tesseract.** Already tried in the prototype and rejected for good reason — it is not a handwriting
engine and says so in its own docstring. Modern HTR is not Tesseract.

## Consequences

- A new adapter, `adapters/ocr.py`, beside `llm.py` — Ring C, the only place an external service is
  named (CLAUDE.md's organism table).
- `engine read eval` already exists and is vendor-blind: it scores whatever is reading. The
  comparison is one command per candidate, against the same hand-read page.
- Cost is not a constraint: Textract is about $15 per 1,000 pages, so the whole 118-page corpus is
  roughly ₹150 — comparable to what these prompt experiments already spent.
- **Open, and Nimish's:** which vendor. `gcloud` and `aws` are installed on this machine; there is no
  Azure CLI and no OCR credential in `.env`. Azure scores best of the three on block handwriting;
  Textract gives the best structured per-field confidence and is reachable with tooling already here.
  The honest answer is to measure two on the same page before committing, which `read eval` makes a
  one-command comparison.
