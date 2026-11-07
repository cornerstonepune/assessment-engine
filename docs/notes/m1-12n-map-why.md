# M1-12n: what the passes were like, for free

## Verified
- `engine curriculum map-why` (run choice `map_why`, free, read-only): from the kept held-out replies, one JSON line of counts
  for the proposals that passed on their own: by skills named (1, 2+), by confidence (tenth), for the proposals that added a
  skill people did not link whether people linked that skill to a same-name activity, to one in the same section, or to none
  alike, and what the precision would be if only one-skill proposals passed, or if the added skills were offered to a person
  (a ceiling: it assumes the rest of the proposal stays). Names no activity, skill or phrase.
- `map.use_checker` = 0 because on the dev run the second model (Haiku) added no signal: agree 46 of 88 right, disagree 5 of 9.
- Tests: `tests/test_map_why.py` (8), `tests/test_curriculum_run_command.py`.

## Handoff
- Dispatch `map_why` (free). Read the table before choosing a rule; the 182 activities the cap never reached stay unseen as the clean test.
