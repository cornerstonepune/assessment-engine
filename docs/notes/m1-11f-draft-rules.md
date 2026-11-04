# m1-11f: rules for drafted K2 text, steps in the school's form, every draft is check me

## Verified
- `cd packages/engine && uv run pytest -q tests/test_k2_rules.py tests/test_k2_gold.py tests/test_k2_draft.py tests/test_k2_review.py tests/test_k2_batch.py tests/test_k2_gaps.py` → passed (fresh database, local).
- `bin/check` → see the PR.
- Read from the school's own sheet (K2 tab, column J, 2026-11-04): steps are one "• " bulleted line per step, often starting
  "The educator will" / "She will"; some begin without a bullet. Drafted steps are put in that form.
- Not verified: how often a fresh draft breaks the rules (no model call was made); the phrase list's recall on real drafts.

## Found
- The checker already receives the school's objective, steps, thinking, levels and materials with each draft
  (`k2_draft._block`); the invented facts are not for want of that text. A tighter checker prompt (quote the contradicting
  words, verified by code) is a new version needing an eval against people's verdicts, which the gold sheet makes possible.
- Before this change a draft passed (`auto_passed`) when the checker agreed, the drafter's own confidence was >= 0.8 and it
  raised no flags (`k2_draft._proposal`); 19 of the 99 did. Those drafts were written untagged. Now every drafted part is
  tagged check me until a person has reviewed it; the ledger status is unchanged.

## Handoff
- New: `config k2.draft_rules`, `engine curriculum gold-sheet --out FILE`, the rules in `k2_batch`.
- Next: a person downloads the sheet (m1-11h) and marks about 30 rows; then the replay table for page parts (not built).
- The ones already drafted in dev (99 pages) were drafted before these rules: `check_me` is set on apply, so re-applying
  nothing changes them; they would need drafting again (a paid run) to get the rules. Orchestrator's call.
