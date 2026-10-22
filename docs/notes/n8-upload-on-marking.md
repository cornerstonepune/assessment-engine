# n8-upload-on-marking: a scan put in on Marking

W3, N8 (Capture), by Nimish's instruction of 2026-10-21, while W1 gate 3 (B0–B4) stays open. Decision: ADR 0092.

## Verified

- Every one of Nimish's sentences proved by its test, and every criterion passed, run on a fresh local copy
  (`bin/testdb fresh`), 2026-10-21: `bin/engine done n8-upload-on-marking` → 7/7 PROVED; criteria 22 engine tests
  passed, 8 browser tests passed, `bin/check` 28 passed. Verdict "NOT DONE" for two reasons only: the live database did
  not answer from the session's machine (this change has no migration), and the two manual checks on live below.
- The engine refuses a token not the site's, expired, or living over an hour, and the engine's own key as a token:
  `cd packages/engine && uv run pytest -q tests/test_upload.py::test_only_the_sites_own_fresh_token_may_upload` → passed.
- On a machine without Amazon's reader (CI, this session), an uploaded file's run stops at the reader and says so
  ("the reading stopped: ProfileNotFound …"), its pages shown: seen in `u44-upload-on-marking.spec.ts` before the run's
  result is written as the reader writes it.

## Handoff

- **Live:** nothing yet; the pull request is not merged or deployed.
- **Manual, once deployed:** a 30–60 MB class scan from a phone on Marking; two HEIC photos of one paper.
- **Open for Nimish:** a page with no readable code that falls inside a child's copy still short of pages is read as
  that copy's next page (`sorting.group`, unchanged); it is now named by its page number on Marking. Whether such a page
  should instead be left unread is his call.
- **Not done here:** the n8n Drive-folder flow stays as it is; the Drive link stays on the page as the second way in.
