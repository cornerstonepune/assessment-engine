# SF2a, parked (2026-10-15)

Nimish moved UX3–UX5 ahead of SF2 (BUILD-ORDER order line). SF2a's goal and its failing tests were written before
any code and are kept here, unchanged, until SF2a starts again:

- `goal.yaml.draft` → `goals/sf2-a-format-is-approved-once.yaml`
- `test_formats.py.draft` → `packages/engine/tests/test_formats.py`

They are `.draft` so that `bin/check` neither lints the test nor holds the goal's promises to tests that do not exist
yet. The design they test is ADR 0077 "Settled in SF2's goal": `format_of(fmt, template)`, `format` (names, seed rows),
`format_approval` (append-only; the latest row decides), `drawable(item)` read by every draw path, and
`internal.formats_approved_by_levels()` for where approval starts. One change from the drafted test: approvals are
append-only, so the starting-approval test should read `internal.formats_approved_by_levels()` rather than delete rows.
