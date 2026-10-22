# ci1: main runs only its newest

## Verified
- ci.yml's concurrency group is per pull request or per branch ref, with cancel-in-progress always on, so a newer merge cancels main's older run. `cd packages/engine && uv run pytest -q tests/test_deploy.py`.

## Handoff
- Live: not yet. The first two quick merges after this one show the older run cancelled.
