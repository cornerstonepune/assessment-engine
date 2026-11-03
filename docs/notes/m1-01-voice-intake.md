# M1-01 — K2 voice-note intake

W3 (read and graph), step N9 (Read, check and learn). Not a new step: the map holds the twelve steps agreed with the
school and `test_layout` refuses a thirteenth, so `engine/w3_read/voice_note.py` joins N9, whose loop is the same: code
reads, each line beside its words, a person confirms.

## Verified

- `cd packages/engine && uv run pytest -q tests/test_voice_intake.py` → 1 passed: git refuses every kind of audio
  file and the repository holds none.
- `bin/check` → 34 passed.
- `bin/engine done m1-01-voice-intake` → the sentence PROVED, every criterion PASSED, "NOT DONE": not on main, the
  live database does not answer from the build container, three steps manual.

- `cd packages/engine && uv run pytest -q tests/test_voice_note.py` → 61 passed (typed transcripts, placeholder
  numbers): one line per section beside its own words; Hindi number words in Latin letters and Devanagari, and
  Devanagari digits; a repeat is one child and said so; "twelve, no, thirteen" replaced and shown; "one seven" is two
  numbers; an unknown word is "could not read" and blocks Confirm; no activity, two activities, an empty heading, none
  with numbers, a dangling correction, a child in two lists all block; an incident and the free sentence keep their
  own words; every number word in the rows reads as its number and none means two; a new heading is a row.

- Reworked to the school's spoken template (relayed by the orchestrator, 3 Nov): the one sentence has no heading and
  follows the last list after a full stop (without one it is "could not read"); a note starting "Incident" is an
  incident and is never read for lists; the day's first note may start with a date or weekday (English or Hindi),
  read against the day it reached us and never later; the Google Form's levels are rows with no mapping written.
  `tests/test_voice_note.py` → 68 passed.
- `cd packages/engine && uv run pytest -q tests/test_speech.py` → 6 passed: the Sarvam adapter against a
  recorded-response stub. Only the file, model, language and the template's own headings are sent; the key is in the
  header; a refusal names its code and never what was said; no key is an error that says so.

- The level she expected ("Activity 2, level 3") is read after the activity; when she says none the default is a row
  (level 2, unverified). A level outside 0–3 blocks Confirm. The day is read in its own file, `voice_day.py`
  (`tests/test_voice_day.py`), which keeps the reader under its ceiling.

## What step 3 (the tables) needs from M0-05 (#358), to line up before writing

- The class a note is about: `school_class.id` (one campus, year, grade, section).
- Number to child: the roll number she says (Children List Sr. No). Is it on `enrolment`, dated, unique per class
  while open? Today `child.roll_no` exists on the old table. Asked M0-05 directly.
- `enrolment (child_id, school_class_id, from, to)`: exact column names, and whether an open `to` is null.
- `staff.id` for `observed_by` and `educator_note.staff_id`, and how a signed-in user is found as a staff id.
- Step 3 adds, additive only: `activity_observation` (outcome above / below / as_expected / not_willing / absent,
  entry_mode individual / group_as_expected, route voice / form, expected level, the two clocks, supersedes and reason,
  the note it came from; one confirmation id per confirm); `pii.educator_note` (audio key in private storage, transcript,
  received_at, status received / drafted / confirmed / left_unconfirmed, staff_id); `pii.note_claim` (each draft line,
  its words, and whether she accepted, changed or removed it). Each child-data table gets its `data_register` row;
  GRANTs for app_engine and app_web; `internal.apply_conventions()` last. No table M0-05 owns is touched.

## Not verified / open

- The live Sarvam call has not been run: no key here and no fixtures.
- The spoken activity numbers (up to 634, with gaps) matching the ACT-K2-nnnn codes through `activity.sheet_no` is
  unchecked: it needs the live database.
- Speech to text is Sarvam (Nimish, 3 Nov). Read its current docs (research/2026-11-03-k2-voice-transcription-spike.md): its default keeps data indefinitely until the workspace Owner sets "No retention"; whether that covers speech-to-text, and whether audio is used for training, are unverified. Nothing measured: no fixtures yet, no key here.

## Handoff

- Live: nothing changed. In flight: step 1 (#357) and step 2, the parser (its words in
  `supabase/seed/voice_template.json`, to be checked against teacher-os field/k2-shadow-capture.md). Next: the tables,
  after M0-05's people and enrolment land. Blocked: the teacher-os documents; Nimish's 8 recordings.
