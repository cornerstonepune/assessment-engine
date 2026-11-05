# m1-12e: draft_tranche and load_settings (W1, gate N1)

## Verified
- tests/test_curriculum_run_command.py and test_k2_draft.py pass on a local copy. No call made.

## What changed
- `engine curriculum draft --tranche` drafts the next `k2.drafting.tranche_pages` (250) pages not yet drafted by the current maker, and stops. Run choice `draft_tranche` (spends, stage `draft`, needs a person). Not combinable with `--dev` or `--limit`.
- Run choice `load_settings` = `engine load --settings` (spends nothing): loads the reviewed settings, prompts and thresholds from the deployed repository. The only way to do it on the server.

## Handoff
- Between tranches: dispatch `forecast` (now measured) and `checkers`; the cap ($25, stop at $23) and the stage order are the engine's and cannot be changed from a run choice.
