# M1-11b — the curriculum run workflow

W1, gate N1. Goal `goals/m1-11b-curriculum-run.yaml`. Nobody could run the K2 drafting commands on the box, so
`.github/workflows/curriculum-run.yml` ("curriculum run", manual) offers a choice of FIXED runs, as `engine eval` does
(`.github/eval/command.py`). Built after #378; **not dispatched; nothing spent.**

## What it does
- **Runs** (`.github/curriculum/command.py`): `key` (is ANTHROPIC_API_KEY in the engine container: prints True or False, never the
  key), `forecast` (three `--dry-run`s, no call; the page dev stage reads `dev_pages` from the `k2.drafting` row through `--dev`, so no number is typed in the workflow), `map_dev`, `draft_dev`, `map_held_out`, `draft_all`, `materials_all` (each spends),
  `review` (what waits for a person). The choice and the allowlist are one list (a test holds them together).
- **No free text reaches a shell.** The run is a choice; the person is looked up in the repository variable `CURRICULUM_STAFF`
  (`{"github login": "staff email"}`, outside git; the public repository holds no email); the email is checked and quoted, and
  masked in the log before anything runs. A spending run for anyone not on the list is refused before the server is reached.
- **The limits stay in the engine.** The cap, the margin, the stage caps and now the stage ORDER (`order` in `llm.campaigns`:
  dev_eval, held_out, draft) are config the adapter reads before every call (`llm_budget._check_order`): a stage may not start
  until the one before it has made an answered call. Whether a stage met its bars is a person's reading, not the engine's.
- `contents: read` only; one run at a time (`concurrency`, no cancel); every input and the actor go in as environment, never
  inside a script.

## Does the box's engine container have the model key? (what I know and do not)
Evidence, not proof: `deploy/compose.yml` feeds the container every variable of `../.env` ("the model keys"); the adapter reads
`ANTHROPIC_API_KEY` for every `claude-*` model; `DECISIONS-LOG.md` (27 Oct) records `english_generate` v2 (Haiku 4.5) scored "on the
school's server, run 40499077378" through the existing eval workflow, so an Anthropic call has been made there. **Not known:** that
the key's account can use Sonnet 5.5 and Opus 5.5 (v1 mapping rows), and that it still works today. The `key` run answers the first
part with no spend; a first real call answers the rest.

## Reviews (D-073)
`/code-review` medium: 7 findings; fixed with tests: `ssh` swallowed the rest of the commands (now `ssh -n`; shown 1 of 3 lines run vs 3 of 3), the person is `github.triggering_actor` (a re-run by someone else is that someone), an email cannot start with `-`, `exists` not `count`, and a flag allowlist test. Known, documented: GitHub keeps one waiting run (dispatch one at a time); the stage order is satisfied by one answered call, not by bars met (a person reads the bars).
`/simplify` (4 agents): applied one `email()` for both paths, one `-n`, shared test helpers, `--dev` instead of a typed 100. Skipped: a per-run cache of the order check (rows could be rolled back in tests), one ssh for all commands, composite action for the ssh step shared with other workflows (out of scope), deriving `spends`.

## Verified
- `pytest tests/test_curriculum_run_command.py tests/test_llm_budget.py` on a database built by `bin/testdb fresh` → 43 passed
  (the order test fails without the engine change; the workflow tests failed first on the missing files). `bin/check` → 34 passed.

## Handoff
- Next: merge; set the variable `CURRICULUM_STAFF` and have the secrets in place; dispatch `key`, then `forecast`; the orchestrator
  tells Nimish the number; `map_dev` then `draft_dev` are the first spend (stage dev_eval, $4).
