# M1-12h: the step check's list of props

## Verified
- Replay of run 20 (free, after #426): 12 of 59 pages pass (was 0). Still refused in the step check: point, place, small, feel, big, them, things,
  ends (ordinary words) and box, glass, pieces, blocks, shapes, picture (real props, or plural/singular mismatches); 29 uses with every word listed.
- Cause: the step check's vocabulary is the last word of every piece of every page's list, so a clause ("things to feel", "cards to point at") puts
  its last word in it. A fixed word list would be a band-aid, so the list is now derived from the school's own steps: a word they use, on at least
  `k2.format.ordinary_min_pages` (3) pages whose list does not name it, is an ordinary word and no prop (`k2_format.ordinary_words`).
- Also: one stem for singular, plural and British spelling (`boxes`/`box`, `glasses`/`glass`, `berries`/`berry`, `colours`/`colors`); a word ending in
  `ss` is not a plural. A materials list is split where the school separates things and not inside brackets (`k2_batch.pieces_of`), which is the
  likely reason "Crayons (red, blue, green)" copied whole was refused with every word listed.
- The replay now tells an all-listed use apart: `one_piece_not_contiguous` (the words are in one piece, not side by side in that order) or `spans_pieces`.

## Handoff
- After merge: `load_settings`, then the free `draft_replay`; read pages_good, the step words still refused, and the all-listed kinds.
- Not known: how many school pages have steps (the ordinary-word list is only as big as that evidence) and whether the 29 are the bracket case.

## Superseded
- The ordinary-words list (derived from the school's own steps) could not work: the school wrote no steps. See `m1-12i-props.md`.
