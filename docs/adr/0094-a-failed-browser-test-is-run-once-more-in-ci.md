# 0094 — a failed browser test is run once more in CI; flaky is listed, failed twice blocks

Date: 2026-10-23
Status: proposed
Goal: none (a CI chore; Nimish, 2026-10-23: "ensure that we don't run the full tests again in case of such one-off failures")

Decision: CI runs a failed browser test once more (`retries: 1`, CI only); one that then passes is listed as flaky in the job summary and the run passes; one that fails twice fails the job. Rejected: skipping or quarantining tests, which hides a real failure along with a one-off, and which `test_no_browser_test_can_skip_itself` forbids.
