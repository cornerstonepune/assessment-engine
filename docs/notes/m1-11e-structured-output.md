# m1-11e: the vendor holds the mapping proposer's reply to its schema

## Verified
- `cd packages/engine && uv run pytest -q tests/test_llm.py tests/test_llm_budget.py tests/test_map_schema.py tests/test_curriculum_run_command.py` → passed (local, fresh database).
- Read off the request that leaves for Anthropic through the SDK itself (mock transport): `output_config.format` =
  `{type: json_schema, schema}` with `minimum`/`maximum`/`maxItems` taken out (the SDK's `anthropic.transform_schema`),
  every object closed; effort kept beside it; a call not asked for in this form sends what it sent before.
- A reply that breaks a bound the vendor was not told (four skills where three is the most) is still refused here.
- `bin/check` → see the PR.
- Not verified: any live call. The shape is from the claude-api reference of 2026-10-06 and the installed SDK's types
  (anthropic 1.6.0); that Sonnet 5.5 takes it is the docs' word. A vendor 400 on the schema would cost nothing.

## Found on the way
- The proposer's `levels` (v2) is a free-form map (`additionalProperties: {type: string}`). The SDK's transform turns that
  into an object with no properties and `additionalProperties: false`: the vendor would then force `levels` to `{}`,
  silently, and the level words the proposer is asked for would never come. So proposer v3 names `level_0`..`level_3`
  (an empty string for each not asked for), and `config llm.structured` names versions, not purposes; v2 is never held.

## Handoff
- New: `config llm.structured` = {curriculum_map_propose: [3]}; `curriculum_map_propose` v3 (inactive); `map_dev` and
  `map_held_out` now run proposer v3 with checker v2.
- Next: dispatch `map_dev` (the eval; the orchestrator says when). Rule 7: v3 is not active until its score is recorded.
- The three batched K2 rows (v3) have description-only properties (no types) and are not held: untested with the vendor.
