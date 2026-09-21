# 0027 — The validation queue settles one answer; signing a paper off stays with the paper

Date: 2026-09-21
Status: accepted (step 4 of the five, `BUILD-ORDER.md`)

## Context

The validation queue (`/capture/check`) shows one answer at a time. Two actions already existed on
the paper's own screen: "What the child wrote" (`correctRead` → `POST /capture/correct`), which
records the person's reading and lets the engine mark it, and Right / Wrong / Blank (`judgeRead` →
`resolve_result`), which sets the mark and then calls `confirm_results` for the whole capture —
every settled answer on that page becomes confirmed evidence in the person's name. On the paper's
screen that is right: the person has the whole page in front of them. In the queue they have seen
one answer.

## Decision

The queue reuses `correctRead` unchanged (it confirms nothing) and judges with `judgeOne`: one
statement that sets that answer's mark and records who judged it as a `read_correction` whose
reading is the engine's own. Nothing else on the paper changes state. Signing a paper off — the
step that turns answers into evidence on the child's ladder — stays on the paper's screen.

## Rejected

- **Reusing `judgeRead` in the queue.** A press on one answer would sign off every other answer on
  that page without the person having seen them — evidence in their name that they never checked.
- **A transaction around the two writes (`sql.begin`).** The website's driver refuses it with
  `max_pipeline: 0` (ADR 0024); one statement with a CTE is atomic without one.
