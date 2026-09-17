# HANDOFF — current session

Session: design and repo creation, 2026-09-16.

## Done

- Read the whole Cornerstone project (design/, research/, ops/, brain) and the prototype code.
- Reconciled three conflicting architecture documents; Nimish chose to build the assessment
  module first, in full, rather than follow the Learning OS phase order.
- Approach A approved; `SPEC.md`, `CLAUDE.md`, ADRs 0001–0003 written.
- Confirmed the thirteen existing scans need the legacy path (no QR / fiducials).
- Repo created under `cornerstonepune/assessment-engine`.

## Next

1. Nimish reads `SPEC.md`; changes if any.
2. `writing-plans` skill → implementation plan for Phase 0 and Phase 1 with chunk criteria.
3. Phase 0: migrations, loaders, seeds, move `assess/` in with tests green.
4. Phase 1: legacy import of the G2/G3 assessments Nimish uploads to `~/cornerstone/assessments/`
   (layout in its README) → first real trajectory on Child Growth. The Downloads scans are
   reference only.

## Spec change 2026-09-17

Per-child adaptive assignment is in scope (SPEC §5 "The next-sheet rule", `prescription`
table, Phase 2 gate). Nimish: with four data points per child the graph exists, so the next
set of assignments must come from it.

## Open for Nimish (from SPEC §14)

Consent text · parent-note channel · who approves word-problem items · whether IMO papers count ·
n8n hosting after pilot.

## Watch

- The registry G2/G3 milestone for `NUM.OPS.02` is identical text; rungs R9/R10 have no
  milestone row — coverage report, not a registry edit from here.
- Handwriting reading accuracy is the one unmeasured risk; Phase 1 measures it on real scans
  against Aseem's marking before anything else is built on it.
