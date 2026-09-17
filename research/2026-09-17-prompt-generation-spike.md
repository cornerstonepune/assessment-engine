# Prompt-driven item generation — first measurement

Date: 2026-09-17. Script: `research/spike_prompt_gen.py`. Model that served: `gemini-3.6-flash`
(`gemini-3.5-flash` returned 503 then a spurious 404; the ordered fallback in the script took over).

## Question

Nimish's requirement: *given a topic, a learning objective, a skill and the philosophy of the
assessment — through a prompt — an agent creates the bank. No code to make questions.* The
engineering worry was correctness: can a model be trusted to write the answer key and the
misconception distractors? This run measures it.

## What the model was given

Only data a teacher could type into a form: topic, skill code, learning objective, the Hard rule
in words ("3-digit minus 3-digit, exactly one exchange, no zero in the top number"), four
philosophy lines ("say exchange, never borrow" …), three formats, and the eleven subtraction
misconceptions from `supabase/seed/misconceptions.json` with their descriptions.

## What code checked afterwards

Answer recomputed · rule checked (digit count, regroup count via `_regroup_count_sub`, no zero,
positive) · every claimed misconception answer compared to the existing predictor · duplicates.

## Result — one call, 20 items asked

```
model returned 20 items (asked 20)
answers correct:        17/20
constraint met:         20/20  (3-digit, no zero on top, exactly one exchange)
duplicate (a,b) pairs:  0
misconception claims:   89; with a code predictor: 89; matched predictor: 77
formats: {'column': 7, 'missing_number': 7, 'word_1step': 6}

failures:
   ('answer', 582, 236, 236)
   ('misconception', 582, 236, 'M_SMALL_FROM_LARGE', 244, 354)
   ...
   ('answer', 643, 281, 281)
   ('answer', 864, 391, 391)

sample word item: A mango orchard in Pune harvested 483 mangoes and sold 237 of them,
                  so how many mangoes are left?
```

## Reading the three failures

All three are `missing_number` items of the shape `582 − □ = 236`. The model put the *shown*
difference (236) into both the `b` and `answer` fields; the true `b` is 346. Its misconception
claims for that item — 244, 246, 235, 928 — are exactly what the predictors return for
582 − 346, so the model's arithmetic was right on all twenty; on three it filled the JSON wrongly.
The verifier rejected all three. The twelve "misconception" mismatches are those same three items
× four claims each; on the seventeen well-formed items every one of the 77 claims matched the
code predictor.

## What this settles

- **Model generates, code verifies** works: the prompt path produced a usable Hard subtraction
  bank with correct keys and correct diagnostic distractors, and the verifier caught every
  malformed item. Design in `ARCHITECTURE.md` §7, decision in ADR 0005.
- The schema needs a field per format role (`shown`, `blank`) rather than asking the model to
  reinterpret `a`/`b`/`answer` for missing-number items — the one error class seen was a
  field-fill error, not an arithmetic one.
- The free tier is slow and flaky at this size: a 40-item request timed out at 120 s. Generate in
  batches of ~20 with retry and fallback; this is the adapter's job, not the prompt's.

## Not measured

One call, one topic, one difficulty. Multiplication and word-problem quality (reading load,
context, vocabulary) are unmeasured. This becomes the first eval set for the `item_generate`
prompt row: the 17 accepted items are its seed, and every staff flag adds to it.
