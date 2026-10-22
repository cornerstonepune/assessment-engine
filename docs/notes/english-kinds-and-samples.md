# English kinds and samples, Grades 3 and 4 (goals/english-kinds-and-samples.yaml)

Content only, as Nimish's locked scope of 22 Oct allows beside the build ("the English content (skills, kinds of
question, samples for the English educator to approve) is prepared now, content only"). No migration, engine code,
endpoint or screen. Grade 3 = Cambridge Stage 3, Grade 4 = Stage 4. "Stage 5" in the task is the fifth step of the
scope's order, not Cambridge Stage 5.

**The educator's document:** https://claude.ai/artifact/MZwtoA6Vav2uvu4NWdDpBg — an Overview (how to review, what
is here, questions for the educator), a tab per grade and topic with one section per skill, and a tab of observed
skills. Rebuilt from the rows by `packages/engine/.venv/bin/python research/english_doc.py` (writes
`data/english_doc/`, gitignored; Cambridge's words are quoted at build time, never committed).

## What changed

- The English rows moved from `docs/drafts/english/` to `supabase/seed/english/` (seed-ready, **not loaded**: no
  loader reads the folder; a loader comes with the build). `research/english_check.py` reads them there.
- `skill_level_sample.json`: 1,308 → **2,499** samples, three for every (skill, level, kind) a level uses (833
  of them), numbered within the kind. Every sample has likely wrong answers (4,366 in all), each naming one of the
  340 mistakes linked to its skill (`skill_mistake.json`, 390 → 405 links; no new mistake). 253 passages.
- `question_type.json`: each kind says `answer` = `one` (code checks the one right answer) or `open` (a person
  reads every answer, `first_answers`: "every answer seen by a person"); the three open kinds are now marked by
  the educator, not a model (Nimish, 22 Oct: "a new one shows a person every answer").
- `observed_skill.json` (new): the 56 objectives not on a paper, each one milestone with the scale yes /
  sometimes / not yet, for the observation engine to come.
- Checks added: `research/english_wrong.py` (a wrong answer fits its kind of question — a printed option, a real
  reorder, a pair or group the key does not make, words in the text — and, where the mistake is a rule, is the
  wrong answer that rule gives); `research/english_spelling.py` (every word against the en_GB Hunspell dictionary,
  pinned by commit and sha256; Indian English words listed with meanings in `research/english_words.txt`; words
  shown on purpose that are not words declared per sample in `not_words` and confirmed unknown); the right answer
  of a choice spread across positions (it was option 1 in about half of them; reordered by a seeded rule).
- The words rule (`tests/test_school_words.py`: never carry or borrow) caught ~70 everyday uses in the English
  rows; they were reworded (take, lift, hold, take home) rather than exempting English from the rule.
- Facts: real places checked (sources below) or made vaguer; invented library shelf codes replaced by plain names.

## Verified

- `packages/engine/.venv/bin/python research/english_check.py` → last line `0 faults`. Counts: G3 102 objectives
  (73 on paper, 29 observed), 52 skills, 1,167 samples (933 code / 234 open), 128 passages; G4 106 (79 / 27), 57
  skills, 1,332 samples (1,074 / 258), 125 passages. Code ran: 4,366 "wrong answer names a mistake of its skill",
  every wrong answer fits its kind (CHOOSE 1,231 · GAP 412 · SHORT_ANSWER 421 · SORT 371 · SHORT_WRITE 306 ·
  WRITE_WORD 236 · MATCH 220 · MARK_WORDS 209 · COPY 168 · REWRITE 157 · TABLE 156 · CORRECT 153 · ORDER 133 ·
  DICTATION 97 · PUNCTUATE 96), **235 wrong answers rebuilt from their mistake's rule**, **382 right answers
  worked out again** (affix 60, sort_pattern 61, add_ending 42, compound 29, passage_order 29, alphabetical 24, …).
- `uv run -q --no-project --with spylls==0.1.7 python research/english_spelling.py` → `135494 words read against
  en_GB (67032ee); 6823 different` · `151 words shown on purpose that are not words …, each unknown to it` ·
  `0 faults`.
- `cd packages/engine && .venv/bin/python -m pytest -q tests/test_english_kinds_and_samples.py
  tests/test_english_foundation.py tests/test_school_words.py` → `25 passed, 1 skipped` (the skip needs a database).
- `bin/check` → `30 passed`, lint clean. `bin/engine done english-kinds-and-samples` → every sentence PROVED, every criterion PASSED; "NOT DONE" only because the work is not on main and the live database did not answer from this machine (content only, nothing to deploy).

Fact sources (opened 2026-10-22): [Sinhagad](https://en.wikipedia.org/wiki/Sinhagad) (about 1,317 m, 28 km
south-west of Pune, once Kondhana, Tanaji Malusare 1670, "Lion's Fort"); [Shaniwar Wada](https://en.wikipedia.org/wiki/Shaniwar_Wada)
(Delhi Gate spikes against elephants, Hazari Karanje lotus fountain, seat of the Peshwas); [Dabbawala](https://en.wikipedia.org/wiki/Dabbawala)
(since 1890; "4,500 to 5,000" is a 2002 figure, so the passage says no number); [Living root bridge](https://en.wikipedia.org/wiki/Living_root_bridge)
(rubber fig, Khasi, up to 15 years, Nongriat double decker); [Kabaddi](https://en.wikipedia.org/wiki/Kabaddi)
(seven a side, the chant, a tackled raider gives the defenders a point); Velas olive ridleys
([The Week, 2025](https://www.theweek.in/magazine/theweek/leisure/2025/05/10/how-villagers-near-a-konkan-beach-went-from-eating-olive-ridley-turtle-eggs-to-protecting-and-building-an-economy-around-them.amp.html),
[Tata](https://tata.com/newsroom/saving-olive-ridley-tcs): conservation from 2002–03, about 100 eggs, 45–60 days,
basket release). Passages that state a fact list it in their `facts` field.

## Handoff

- **Live:** nothing; rows not loaded.
- **In flight:** the English educator reviews the document above: approve, edit or comment per skill. Edits come
  back into `supabase/seed/english/`; `research/english_check.py` and `research/english_spelling.py` re-check them;
  `research/english_doc.py` rebuilds the document.
- **For the educator, flagged:** listed under "Questions for you" in the document (facts, shelf names, sounds by
  ear, order of strength, hard words, the nearest mistake where a skill has few, open-answer drafts).
- **Next:** when the build reaches English, the `ENG` subject row and a loader for `supabase/seed/english/`; the
  observed skills feed the observation engine (C2's evidence record carries their yes / sometimes / not yet scale).
- **Blocked:** nothing.
