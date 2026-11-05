# ci-postgres-retry: CI's database step tries a dropped download again

Task (orchestrator, 2026-11-04). Tier 3 (CI). No workflow gate moves; no engine, schema or seed change.

## Verified

- **Cause, by reading the script.** `bin/ci-postgres` downloads three times: the signing key (`curl`), `apt-get update`, and
  `apt-get install postgresql-17`. None was retried, so one dropped connection ended the job about 90 seconds in with
  `curl: (56) Failure when receiving data from the peer` (main's CI once, engine shard 4; shards on #386, #388, #389, #390),
  each cured by re-running the failed jobs at 10 to 20 minutes apiece. I cannot read those CI logs from here; the cause is
  the script's lack of any retry, which the tests below show, not a proven reading of which of the three fetches failed.
- **Fix** (`bin/ci-postgres` only): `CURL_RETRY=(--retry 6 --retry-all-errors --retry-connrefused --retry-delay 5
  --connect-timeout 20 --max-time 120)` on the key fetch (a transfer error is retried only with `--retry-all-errors`); a
  `retry` function (5 attempts, 10 s apart, then `giving up` on stderr naming the command and exit 1) around `apt-get update`
  and `install`, each also with `-o Acquire::Retries=5` for a single file. The package source is unchanged; no test or check
  weakened.
- **Proof** (`tests/test_ci_postgres.py`, reads the script's own settings and runs them):
  - a server that promises the key, sends 50 bytes and hangs up, twice: with the script's flags curl asks three times and
    writes the whole key (`test_a_key_fetch_that_drops_part_way_is_tried_again_and_succeeds`); the old command on the same
    server asked once and exited 18 with half a key.
  - a server that always drops: curl asks more than twice and exits non-zero, so the step fails; `retry false` returns 1 and
    says `giving up` with the command; a command failing twice then working passes through `retry`
    (`test_a_fetch_that_always_fails_fails_the_step_after_its_last_attempt`).
  - every `curl` in the script carries the retry flags, and every `apt-get update` / `install` goes through `retry` with its
    own `Acquire::Retries` (`test_every_download_in_the_script_goes_through_a_retry`). All three failed on the old script
    first (3 failed), pass now (3 passed).
- The delay in the test is one second (0 would mean curl's growing backoff); the test reads the script's flags and asserts the
  script's own delay is at least one second.

## Not proven here

- The script itself runs on a CI runner only (it refuses elsewhere), so the real apt path is not run here; the first CI run
  after merge is the proof, and shows any retry in the job log.

## Handoff

- **Live:** nothing; CI only.
- **Next:** the orchestrator merges, and watches the first runs for `ci-postgres: … trying again`.
