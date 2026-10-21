# 0090 — A check is an answer a person was shown; the notebook is rebuilt by the check

Date: 2026-10-21
Status: proposed
Goal: goals/reader-learns.yaml

## Context

Nimish asked whether ADR 0032 is really happening. Measured on live, read only (docs/notes/reader-learns-audit.md):

- All 16 notebooks were older than their child's last check: a notebook was rebuilt only when that child's next paper
  was read (`profiles.current`). The 16 Oct papers' 87 typed answers had changed no notebook.
- A paper this system prints is read in its boxes by the digit reader (ADR 0035), against that reader's floor for every
  child. The child's own floor was set aside because it was measured on Textract's readings. 12 of the 16 notebooks hold
  "no level is 95% right" (floor 95), and none of it applied on a printed paper.
- An answer signed off with its paper counted as "the reader was right" even when it had never waited for a person.
  On live: 85 such answers among the checks, 8 inside one kind's trust window. Once a kind is trusted, each right
  answer of it settled alone and then signed off would join that kind's window as one more right check.

## Decision

1. **Every check rebuilds the notebooks it made stale** (`profiles.refresh`): `/capture/correct`, `/commit`, and
   `/capture/trusted`, which the website calls after every sign-off.
2. **A child's floor is measured per reader**: `floor` on readings found in a region, `box_floor` on readings made in the
   boxes of a printed paper (`answer_checked.in_boxes`). On a printed paper the reader's floor is raised to the child's
   `box_floor`. It is never lowered (ADR 0032: the floor only rises).
3. **A signed-off answer is a check only if it waited for a person**: its reading carries the reason it waited
   (`answer_checked`, migration 20261126090000). A typed answer is a check, as before. The notebook, `kind_trust`,
   `engine read report`, the reader's gold set and Marking all count from that one view.

## Rejected

- **Leaving the rebuild to the next read.** The next read got a fresh notebook either way. But the stored notebook,
  the one the report and anyone checking reads, was wrong between papers, and that is how this audit found it stale.
- **Applying the Textract floor to the digit reader.** The two readers' confidences are on different scales (ADR 0035).
- **Counting a paper sign-off as a check of every answer on it.** A sign-off (`confirm_results`) confirms only the
  answers the engine had already settled; every answer that waited is settled in the queue, which leaves the person's
  own row (`read_correction`, "typed" here), and that still counts. Growth signs off all of a child's papers in one
  click. An answer nobody was asked about can only say "right", so counting it raised the reader's score with no
  person's word behind it.
