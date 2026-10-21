# k1: the server has the model key

## Verified
- The deploy writes the repository's secret into the server's .env, on stdin, before the engine starts; a server
  without it is a warning on the run. `cd packages/engine && uv run pytest -q tests/test_deploy.py` (output in the PR).

## Handoff
- Live: not yet; the first deploy after merge writes the key, once Nimish has added the secret.
- Next: run `engine eval read_with_examples` on #248's branch (Actions → engine eval) and report its score.
