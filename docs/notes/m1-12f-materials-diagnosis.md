# M1-12f: why the materials check refuses almost every draft

## Verified
- Run 17 (`draft_replay`, free, after #418): 31 replies, 0 refused, 59 pages never good. Attempt 1 (59 asked): step_word_unlisted 36,
  uses_unlisted 22, step_too_long 1; attempt 2 the same; attempt 3: 4 asked. The format rules are fine; the materials check is the blocker.
- Now: the replay also prints, for those two rules, the words that repeat (not those seen once) and how each stands to the page's own
  materials text: `page_has_no_materials`, `all_words_listed` (the matcher's order or piece rule refused it), `some_words_listed`,
  `near_spelling`, `not_related` (invented or another page's prop). Tests: `packages/engine/tests/test_k2_replay.py`.

## Handoff
- Dispatch `draft_replay` (free). If `not_related` dominates: the model invents props, the prompt changes (new version, replay-tested).
  If `page_has_no_materials`, `all_words_listed`, `some_words_listed` or `near_spelling` dominate: the matcher is too literal; fix it with tests
  and replay the kept replies for free. The locked rule (a page names no material the school's list lacks) is not loosened.
- Suspects read from `k2_format.vocabulary`: the vocabulary is the LAST word of each listed piece, so a piece ending in a non-noun
  ("markers as needed") puts that word in the vocabulary. The word list will show it if so.
