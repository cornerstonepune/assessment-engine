# M1-12i: what the step check may call a prop

## Verified
- Run 22 (free, after #428): still 12 of 59 pass. The live check by the orchestrator: `activity.steps` is empty in 0 of 2497 rows (thinking 0, steps_list 0),
  materials non-empty in 646. M1-12h derived "ordinary words" from the school's own steps; there are none, so that list was empty and nothing changed.
  It was my mistake to build on steps I had not checked existed; `ordinary_words` and its row `ordinary_min_pages` are removed.
- Now (`k2_format`): a piece of a materials list names a prop only if it is a short name (no word of the language inside: a clause like "cards to point at" or
  "place the blocks" names none); the head noun is its last word after trailing function words and generic words (thing, piece, small) are dropped; a noun counts
  as a prop only when it names a material on at least `k2.format.prop_min_pages` (3) pages. A `uses` entry passes when each run of its words stands in one piece
  of the list, in order (function words ignored); a word the list lacks is still refused. A page with no list is judged by its `uses` alone (must be empty).
  Its steps are read by the checker, which is also shown "materials: the school wrote none" for such a page (before, the line was left out).
- The checker prompt (k2_page_check v1) already lists "a step uses a thing the school's materials text does not name" as its first fault, so no v2 was written;
  whether it catches what the code no longer refuses is unmeasured until the first paid run (checkers report).

## Handoff
- After merge: `load_settings` (prop_min_pages, function_words, not_props), then the free `draft_replay`; read pages_good and the step words still refused.
- Not known: how many of the 59 pass now; how often the checker catches an invented prop.
