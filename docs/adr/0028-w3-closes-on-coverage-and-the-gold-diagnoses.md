# 0028 — W3 closes on coverage and Aseem's diagnoses, not on the reader's accuracy bar

Date: 2026-09-21
Status: accepted (Nimish's decision of 2026-09-21, night; written into the goal as step 6 of "Next: six steps")

## Context

`goals/w3-read-and-graph.yaml` was written on 2026-09-20, before the reader existed, for a vision
model reading every page: 97% of answers read exactly right, 93% on phone photographs, at most 1%
silently wrong, a gold set of 300 answers, and 36 reading scenarios. None of its scenarios ever had a
runner, so the goal could not go green whatever the engine did.

The reader that was built reads with OCR and holds at 81.9% exact on the gold, 1 answer silently
wrong. Twice on 2026-09-21 Nimish chose not to push it further: *"keep this coverage for now and move
ahead"*, and that night, that the reader stays as it is and is improved only by what people's
validations teach it, with no other manual effort. His order: every doubtful answer validated on the
approval screen; every sheet fully covered and scored; the graphs checked against Aseem's five
reports; then W3 closes and W4 starts.

## Decision

W3's goal is restated to that order. It is green when nothing waits, every paper is signed off and
scored, the graph is rebuilt from confirmed evidence, and every mistake Aseem named in the five
Grade 3 reports that the papers hold comes back out of that child's graph on the same skill by the
same name. The five reports are transcribed once into `gold_finding` rows keyed by `child_id`, and
Nimish confirms the transcription before it is used.

The 2026-09-20 bar and scenarios stay in the file under `bar` and `superseded_scenarios` as the record
of what was asked; the goal runner reads neither.

## Rejected

- **Keep the 97% bar as a gate.** It contradicts the decision that the reader stays as it is; W3
  could never close.
- **Delete the old scenarios.** Several restate rules that still hold (4, 5, 6) and the reasoning
  behind the bar is worth keeping; archive before delete.
- **Measure the graph on reading accuracy.** Aseem's reports are the target output of the whole
  system; a graph that reaches his diagnoses from validated answers is the thing W3 exists to show.
