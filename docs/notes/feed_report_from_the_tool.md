# feed_report_from_the_tool: a note from staff becomes a GitHub issue

Goal: `goals/feed_report_from_the_tool.yaml`. No gate moves: a tool beside the four workflows (BUILD-ORDER).

## How Nimish decides

1. A member of staff presses **Report a problem** on the top bar, writes a note, and is thanked once it is saved.
2. The note becomes one issue labelled `from-the-tool` and `bug`, `feature` or `question`. It names the role and class,
   never the person.
3. Nimish reads it on GitHub. **To have it built he adds the label `scope-locked`**, as for any scope (the harness rule
   is unchanged). The person's "Your reports" then says **taken up**.
4. When the issue is closed, their report says **done**. A note he does not take up stays **received**.

An issue made by hand uses the same fields: `.github/ISSUE_TEMPLATE/from-the-tool.yml`.

## Verified

| Claim | Command | Last output (27-Oct-2026) |
|---|---|---|
| The table keeps role and class, no name or email; the website adds a note and sets only how its sending went; the words never change and no note is removed; the limits are rows; unsent notes are said in the health check with no secret | `cd packages/engine && .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts= tests/test_feedback_rules.py tests/test_roles.py` | `9 passed` |
| Phone and email refused; @mentions and #numbers neutralised; the body holds only the listed lines; title ≤ 80; the button on every page; refused, saved, thanked, exactly one issue; GitHub down then sent; received → taken up → done; hourly limit; signed out refused | `cd apps/web && npx playwright test tests/u70-feedback-rules.spec.ts tests/u70-report-a-problem.spec.ts` | `11 passed` |

## Handoff

- **Live:** nothing until merged; then every note is saved, and stays `saved` until the token is set.
- **Owner must do (manual):** create the labels `from-the-tool` and `feature` (missing on 27-Oct-2026); make the
  fine-grained token and set `GITHUB_FEEDBACK_TOKEN` in Vercel, Production (steps in the PR).
- **Open decision:** the repository is public, so anyone can read an issue made from the tool.
- **Rehearsal:** the migration `20261219150000` adds one table; run `rehearse-update-live.yml` on the branch before merge.
- **Retry:** a waiting note is tried again whenever anyone opens the form; `engine live watch` counts what still waits.
  There is no timer of its own: if nobody opens the form after the token is set, the watch line stays until someone does.
- **A name cannot be detected by code.** The warning under the boxes is the only guard against one.
