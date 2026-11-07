# M1-12o: what kind of word the step hits are, for free

## Verified
- `engine curriculum draft-why --stage draft` (run choice `draft_why`, free, read-only): the latest kept draft of each page; for every
  step word that names a prop of the band the page's list does not, a class: named elsewhere on the school's page (name, objective,
  levels), a variant of a word its list has (same first four letters, or one inside the other), a prop most pages list (more than half
  of the pages that list anything), or named nowhere. It gives hits per class, the pages each class would clear (cumulatively), the plain
  words that repeat (letters only, at most 12) under their class, and how many were seen once. No school phrase.
- Found while building: the replay judged only `wanted` pages, which leaves out every page a run recorded, so `draft-replay` after a
  run saw almost none of its own pages (the dev replay showed 10 of 15 replies refused). It now asks about every page with an empty part.
- `k2_format.unlisted_step_words` lists every offending step word; the judge still reports the first, unchanged.
- Tests: `tests/test_k2_why.py` (8), `tests/test_k2_replay.py`, `tests/test_k2_format.py`.

## Handoff
- Dispatch `draft_why` (free) and `draft_replay` with `--stage draft` is not an option yet: the run choice `draft_replay` reads dev_eval. If
  wanted, a `draft_replay_draft` choice reads the tranche.
- No rule was changed. Pass 2 and later are the clean test of any rule the table suggests.
