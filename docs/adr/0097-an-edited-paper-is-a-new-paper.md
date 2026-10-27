# 0097 — An edited paper is a new paper, with a new code

Goal: goals/paper_review_add_remove.yaml

Nimish, 27 Oct 2026: "When a teacher generates an assessment, they should see a page where they can look at the actual
questions, and that should have an add/remove button: one can remove a specific question and then can add another
question from the bank."

## Decided

- **An edit never changes a paper in place.** A paper's code (the QR), the boxes the reader looks for and the answer key
  are what was printed with that code. Removing or adding a question makes the paper again, by the code that first makes
  it (`focus_paper.print_paper`): a template, a new code, its page and key rendered. The earlier copy is set void and
  keeps its questions and key, so a copy of it already in a child's hands still reads and marks as itself.
- **Every edit is a `paper_edit` row**, never changed: the code before and after, the question ids removed or added, the
  position, who, when, and whether it withdrew an approval.
- **Editing an approved paper withdraws the approval.** The new copy waits (`print_status = 'new'`, no approver) and is
  approved on its review page, one paper at a time. The child is given its questions (`item_exposure`) at that approval.
- **A printed paper is not edited.** Printed means its print PDF was opened (a `printed` run the engine writes then), it
  was said given, or a copy was uploaded. The page says "This paper is already printed. Make a new one to change it."
- **The limits are rows**: `assessment.min_questions` (1) and `assessment.max_questions` (40).

## Rejected

- *Changing `sheet_template.item_ids` and the key of the same code.* A copy printed before the change, from the PDF or
  the browser's own print, would be read against questions it does not carry: the wrong boxes, the wrong key. The
  engine cannot see every print, so only a new code makes that impossible.
- *Holding every new home assessment as waiting until approved on the review page.* Approving on the child's page already
  shows every question first (goals/preview-before-print.yaml); a second click would add work and no safety. Making it
  lands on the review page instead, where it is changed and approved again.
- *A page-count limit.* The page flows questions over as many A4 sides as they need, a code on every side; no layout
  limit exists to make a row of.
