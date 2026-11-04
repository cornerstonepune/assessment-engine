# M1-03 — the K2 screens' read calls

W3, step N9 (the voice notes' reader). No migration: queries in code. Part A (to-do, coordinator) and Part B (class
picture, child page, reading `child_observed_state` from #364) are built.

## Verified

- `cd packages/engine && uv run pytest -q tests/test_k2_reads.py tests/api/test_k2_routes.py` → 13 passed, on a local
  database built from every migration (`bin/testdb fresh`), placeholder rows only.
- `bin/engine done m1-03-k2-reads` → both of Nimish's sentences PROVED, all three criteria PASSED, "NOT DONE": not on
  main; Part B manual; the live database does not answer from the build container.
- `bin/check` → 33 passed. Neighbouring suites (voice intake, confirm, tables, cli, routes, loaders) → 56 passed.
- Routes `POST /k2/todo` and `POST /k2/coordinator` (JSON, engine key, `actor` = her email), 403 while
  `voice.screens_enabled` is off. `apps/web/lib/engine-routes.ts` regenerated with `bin/engine contract`.
- Query counts: todo 5, coordinator 8, the same for 3 notes or 43. Both well under 1 s (asserted, not loosened).

## Decisions made without an answer (the orchestrator was asked)

- **Late** = confirmations (not children) made on a later school day than the activity, since the week began.
- **Unplanned** = null with the reason in words. No plan or session table exists and no migration is allowed.
- **No notes this week** = two counts: children with no observation, and weekday class-days with no note received.
  School holidays are not known, so a holiday counts as a day with no note. Needs a calendar to be exact.
- Who may ask for the coordinator's list, which grades, how far back rows reach, week start: one config row `k2.reads`
  (seed only). It reaches live by itself: `.github/workflows/deploy-engine.yml` runs `engine load --settings` on every
  engine deploy, so nobody runs a command. Not yet seen on live (the deploy has not happened).
- A note older than 48 hours is "left unconfirmed" by time, whether or not the hourly job has run yet.
- `voice_intake.resolve` takes optional lookups so a list uses the Confirm page's one rule without a query per note.

## Part B

- `POST /k2/picture` (`actor`, `class_id`): the class's children by Sr. No. against the skills anyone was seen on; a cell
  `{state, words, colour, level, last_seen}` only where the child was seen. `POST /k2/child` (`actor`, `class_id`,
  `roll_no`): her skills newest first, each with the free sentence of the note it came from, or null.
- State words and colour are the `child_state` rows (a test changes a colour and the answer follows). The level is the
  level reached by the latest *named* observation; "the rest did as expected" shows no level. "Not willing" shows
  nothing at all. A child not seen has no cell: not seen is not "not secure".
- Who may ask: a current grant on that class, or a role in config `k2.reads` on its campus; else 403.
- Tested on a class of 22 and 20 skills of real observations, graph rebuilt by the engine, every cell held to a table
  worked out by hand from the scenario and to counts read straight from `child_observed_state`; 6 queries (picture)
  and 7 (page) whether the class has 2 skills or 20; under a second; the query planned below the JIT line.
- **The free sentence is guarded** (orchestrator's decision, 4 Nov; D-021: names stay off the website). It is read from
  the note's transcript, and before it is returned the engine compares its words, case-insensitively and on word
  boundaries (letters, marks and digits, so a Devanagari vowel sign belongs to its word), with every word of the given
  and family names of the children enrolled in that class, read through the logged `pii.read_child` (22 logged reads,
  one query). On any match, or if the names cannot be read, the sentence is withheld and the flag
  `sentence_note` reads "sentence held back: it may name a child". A name inside a longer word is not a match ("Zorbakian"
  for "Zorbak"; "आरवी" for "आरव"): the rule is whole words, as asked. A one-letter word is never a name.
- **What the guard cannot catch:** a child of another class; a nickname; a name written in the other script from the one
  the child's name is held in; a misspelling. So the sentence goes only to the educator who recorded the note and to
  coordinator roles; any other staff of the class gets the skills without it and a `sentence_note` saying so.
- The child page lists skills **newest first** (decided).

## Not verified / open

- On live: nothing run; the `k2.reads` row arrives with the first engine deploy after merge.
- Test fixtures: two K2 classes must have different activity numbers (a number names one activity on the school's list).

## Handoff

- In flight: Part A in review. Next: Part B contract tests on fixture rows, then the real table after #364.
