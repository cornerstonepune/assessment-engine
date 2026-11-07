# M1-12p: style rules are notes, not gatekeepers

## Verified
- Nimish (7 Nov, via the orchestrator): pages are editable by teachers, so loosen the checks and stop spending on gatekeeping.
- `k2.format.advisory_rules` (config row): step_word_unlisted, uses_unlisted, keyword_length, spot_length, step_too_long,
  steps_too_many, idea_too_long. A page that breaks only these is good: no retry, no revision, no third ask; the rules it broke
  are on the proposal (`notes`) and its reason (`| notes: ...`). Status and confidence do not change.
- Still hold a page back: steps/idea empty or not the right shape, the wrong number of slips, a part empty, missing or answered
  twice, levels alike, he or she, comparing children. (Levels alike and the slips count are my reading of "pure style"; say so if a
  teacher would rather have them as notes too.)
- `engine curriculum draft-record --stage S --by` (run choice `draft_record`, free): reads every kept maker reply of the stage, takes
  for each page still wanted the first draft the judge accepts now, records it as `needs_person` "recorded from a kept draft; the
  checker has not read it" plus the notes. No model call.
- `engine curriculum apply --kind page_part --apply --by` (run choice `curriculum_apply`, free): writes the recorded and standing pages
  to the activity page as drafted, check_me, editable, revertible. `apply` takes `--kind`; without it, it is as before.
- A free run that writes rows now names its dispatcher like one that spends (`command.py`: the email is looked up when a command carries it).
- Tests: `tests/test_k2_advisory.py`, `tests/test_k2_record.py`, `tests/test_k2_format.py`, run-command tests.

## Handoff
- Order after merge: `load_settings`, `draft_record`, `curriculum_apply`. Pass 2 then runs under the new rule.
- Screens: open to the head and the coordinator (`curriculum.review_roles`) without the educator switch; the educator switch is a separate gate.
