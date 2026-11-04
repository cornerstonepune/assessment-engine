# m1-11g: judge the proposed skills one by one, in replay only

## Verified
- `cd packages/engine && uv run pytest -q tests/test_map_replay.py` → 13 passed (fresh database).
- `bin/check` → see the PR.
- Not verified: the numbers on the real run. They come from `engine curriculum map-replay` (run choice `map_replay`) after
  deploy; the tables are keys of its second output line.

## Why
The live replay of the 2026-11-04 map_dev run: 28 passed on their own, 24 right; the 4 wrong all added a skill people did
not link beside right ones. Best confidence bar: 0.75, 35 pass, 31 right (0.886). The checker's verdict carried no signal.
The brief: split each proposal into core and extra, pass only when every skill passes, offer the extras to a person.

## What it measures
- Per proposed skill: precision by its place in the list, and by whether it was among the skills of the examples the
  proposer was shown (read from the stored question, a signal code can read).
- Activity passes when every skill it names was shown (with and without the checker agreeing), by confidence bar.
- A proposal split by the examples: the skills that would pass, their precision, the skills offered to a person and how many
  of those people had linked.

## Handoff
- Nothing about how a proposal is decided has changed. Next: dispatch `map_replay`, read the split tables, then decide with
  the orchestrator whether a rule (not a prompt) goes in; any rule goes to a threshold row and an eval on the held-out set.
