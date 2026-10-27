# paper_review_add_remove

Nimish, 2026-10-27: "When a teacher generates an assessment, they should see a page where they can look at the actual
questions, and that should have an add/remove button". Goal: `goals/paper_review_add_remove.yaml`. **W2, gate N7**
(the teacher approves). Why an edit is a new paper: `docs/adr/0097-an-edited-paper-is-a-new-paper.md`.

## Verified

Outputs from this session, on a fresh `bin/testdb fresh` copy (Postgres 16).

- The edit tests failed before the code (no `edit_paper`: collection error), then
  `cd packages/engine && uv run pytest -q -p no:cacheprovider tests/test_edit_paper.py` → `8 passed`.
- The neighbours: `uv run pytest -q tests/test_focus_paper.py tests/test_seen.py tests/test_maker.py tests/test_read_back.py
  tests/test_layout.py tests/test_contract.py tests/test_ux_rules.py tests/test_retire_kind.py tests/test_given.py tests/api/`
  → `166 passed`.
- The browser: `cd apps/web && npx playwright test tests/p5-review-a-paper.spec.ts tests/s11-focus-paper.spec.ts
  tests/p4-preview-before-print.spec.ts tests/u2-children.spec.ts tests/m2-make-papers.spec.ts tests/u49-one-role.spec.ts
  tests/u62-scope-and-todo-logic.spec.ts` → `34 passed`. s11, p4, u2 and m2 changed only where a made paper now lands:
  its review page, not the child's page or the printed paper's page.
- `bin/check` → `32 passed`.
- `bin/engine done paper_review_add_remove` → all ten sentences PROVED, both criteria PASSED; NOT DONE only because the
  live database did not answer from this machine (its migrations unchecked).

## Handoff

- **Live:** nothing until merged; the migration `20261221090000_a_paper_edit_is_kept.sql` needs the rehearsal
  (`rehearse-update-live.yml`) on the branch first, and `engine load` for the two threshold rows.
- **Where a paper's questions live:** `sheet_template.item_ids` (order), `sheet_instance.key` (the rendered key and boxes),
  the PDF at `sheet_instance.pdf_path`, `item_exposure` (what the child was given). An edit writes all four anew for a new
  code; it changes nothing of the old but `print_status = 'void'`.
- **Who may edit:** one function, `mayChange` in `apps/web/app/(app)/papers/review/[qr]/actions.ts`, is the place to switch to
  OWN's shared rule. Today it is #325's `mustBeMine`, which since Nimish's 22 Oct decision reaches every class for every
  member of staff, so no refusal of an educator can be shown yet (u49 holds the opposite).
- **Not here:** English questions are not in the bank a paper draws from, so "add the passage with it" has nothing to act
  on until they are.
