# M1-12g: the materials check refused ordinary words and quantities

## Verified
- Replay of run 18 (free): step check refused `the` 43, `place` 15, `draw` 10, `colours` 2, `open` 2 (all not related to the page's list);
  of 45 refused `uses`, 38 had every word listed and 7 some. Read: the matcher, not the model.
- Causes, in `k2_format`: (1) the vocabulary was the last word of every list piece, so pieces ending in "the", "as needed", a verb put
  those words in it; (2) a step's first word (the verb the prompt asks for) was checked as a prop; (3) `uses` was compared with the digits
  dropped on one side and kept on the other, so "Beads (10 per child)" never matched its own piece.
- Fixes: trailing function words dropped before the head word is taken (row `k2.format.function_words`); the first word of a step is not a
  prop; both sides of a `uses` comparison are words only. The locked rule is unchanged (tests: a prop named later in a step is still refused;
  words not side by side in one piece are still refused).
- The replay printed whole `uses` phrases (the school's own material text) to a public log in run 18: it now prints only plain words of at
  most 12 letters seen twice or more, and only for the step rule; a use is counted by kind only. The run-18 logs were deleted by the orchestrator.

## Handoff
- After merge: dispatch `load_settings`, then the free `draft_replay`; its `pages_good` is how many of the 59 kept replies pass now.
- Still refused after this (by design): a use whose words are not all in one piece of the list (7 of 45 had some words only), and a step that
  names a prop of another page's list that this page lacks.
