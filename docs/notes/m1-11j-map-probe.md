# m1-11j: the one-call probe of proposer v3 (W1, gate N1)

## Verified
- `su postgres -c "cd packages/engine && DATABASE_URL=… TEST_DATABASE_URL=… .venv/bin/pytest -q tests/test_map_probe.py tests/test_map_replay.py tests/test_curriculum_run_command.py"` → 51 passed (local copy `m115`).
- Not run against the vendor: no model call has been made. Whether the vendor accepts the v3 request is unknown until `map_probe` is dispatched.

## What it is
`engine curriculum map-probe --version 3` asks the proposer once, about the first dev-set activity, links hidden as in the
eval, stage `dev_eval`. It prints one line: `HTTP 200; the reply passed the local check`, `HTTP 200; the reply broke the
local check`, `HTTP <status>; no reply`, or `no HTTP status; …`. Neither the reply nor the vendor's message is printed (the
log is public). Run choice `map_probe`, ahead of `map_dev`.

## Handoff
- Needs Nimish's yes to spend about INR 1 (an estimate: one proposer call) before dispatching `map_probe`.
- The line cannot say anything about the roughly 3% refusal rate; only the full `map_dev` can.
- The probe's flow_run row is labelled `probe:`; `map-replay` skips it, so it can be dispatched before `map_dev` at any gap.
- The review screen for offered skills is the next brick; not started, waits for the orchestrator to confirm it.
