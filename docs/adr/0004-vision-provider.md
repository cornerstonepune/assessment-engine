# ADR 0004 — Gemini Flash for vision in the pilot, behind a masking adapter

Date: 2026-09-17. Status: accepted.

## Decision

The pilot reads worksheets with Google's Gemini Flash on the free tier. `adapters/vision.py`
is the only module that talks to a vision model, and it **masks the child's name region before
any image leaves the machine** — known cell geometry on generated sheets, the top band of page 1
on legacy scans. The five prompts keep their JSON schemas; Gemini's `response_schema` carries
them unchanged.

## Why

- Free, no card, no billing setup — the pilot can start today.
- Gemini Flash reads handwriting well, and the school already chose it for transcription
  (`cornerstone-brain` decisions log, 2026-09-08).
- The masking requirement is what makes the free tier acceptable: Google's free tier permits
  submitted content to be used for product improvement, including human review. Masked pages
  carry no name, so what is exposed is anonymous arithmetic, not a named child's record.

## Rejected

- **Anthropic Claude (paid) from day one.** Recommended on data grounds — paid APIs do not train
  on submissions — and the cost was small (~$12 for the whole back catalogue, ~$25/month at full
  pilot). The founder chose free for the pilot; the masking adapter closes most of the gap.
- **Free tier without masking.** Sends named children's work to a tier that may train on it. Not
  acceptable under DPDP or under the school's own duty, at any price.

## Revisit trigger

Any of: the first non-founder class run; parent consent text being finalised; a measured accuracy
gap against Claude on the `gold` set; or going to production. Swapping is a one-file change
because the adapter is the seam.

## Consequences

`prompt.model` rows carry a Gemini model id. The exact id is confirmed against the live model
list when the adapter is wired — Google renames these often, and a stale id is a silent failure.
Masking is enforced in the adapter, not by discipline, so no caller can bypass it.
