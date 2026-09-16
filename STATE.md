# STATE — what is verified true

Each line: a claim, the command that proves it, its last output. No claim without a check.

## Design

- Spec approved in shape by Nimish (approach A); written as `SPEC.md`; awaiting his read-through.
- ADRs 0001–0003 record the stack, the skill model, and the n8n boundary.

## Inputs verified

- Registry: `window.CSMAP` from the Skill Map Review artifact — 244 skills, 849 milestones,
  14 domains, NUM = 37 skills. All seven skill ids the ladder maps to exist
  (`NUM.OPS.01/.02/.05`, `NUM.PRB.02/.03`, `NUM.PV.03`, `NUM.MEAS.04`).
  Check: `python3 -c` parse of `data.js` → counts above.
- Prototype: `~/Downloads/assessment-engine-prototype/assess/` — 8 modules; synthetic roundtrip
  report: cell geometry agreement 1.0 on 4/4 sheets, QR decoded 12/12 pages; status agreement
  0.40–0.70 with the Tesseract stub (not for handwriting, by its own docstring).
- Existing scans: 13 `ACE Scanner_20260916(N).pdf` — none carry fiducials or a QR, none have a
  text layer. Check: prototype `find_fiducials` + `cv2.QRCodeDetector` on page 1 of each → 0/13.
  Therefore every existing assessment goes through legacy import. Real Phase 1 input is
  whatever Nimish uploads to `~/cornerstone/assessments/` (layout in its README); the Downloads
  scans were evidence only.
- Team documents incorporated: `Addition_Subtraction_Assessment_Skill_Taxonomy.pdf` (13 pp;
  §12 tag matrix, §13 progression) and `Adaptive_Subtraction_Learning_Engine_…Spec.docx`
  (M001–M010 conceptual misconceptions).

## Code

- None yet. Phase 0 starts after the spec review.

## Environment

- Docker, Supabase CLI, psql, Node, Python 3.14 present; n8n not installed (Docker);
  `gh` authenticated as nimishshah1989, admin of org `cornerstonepune`.
