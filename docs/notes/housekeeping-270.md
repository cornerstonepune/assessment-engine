# Housekeeping on PR #270 (R2, an unaligned page goes whole to a person)

W3 (read), slice R2, no gate moved.

## Is R2 still needed after CK2 (#281)? Yes.
CK2 decides which paper page a photograph is; it does not stop a page that cannot be lined up from being read by its words.
Evidence: R2's own tests (`tests/test_each_answer.py` from this branch) run against current main's code, on a fresh database:
`test_a_printed_page_that_did_not_line_up_goes_whole_to_a_person` fails (the reader by words is still asked for all 3
questions). So R2's goal sentence is not covered by main.

## Handoff
- Main merged into the branch (no text conflicts). Reader tests and CI are the proof of the merge; see the PR.
