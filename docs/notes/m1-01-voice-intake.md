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

## Not verified / open

- The design documents in cornerstonepune/teacher-os could not be read from this container (the clone asks for a
  login; attaching it was refused). Asked the orchestrator for them. The spoken template and the table design are not
  guessed; the parser and the tables wait on them.
- Speech to text is Sarvam (Nimish, 3 Nov). Read its current docs (research/2026-11-03-k2-voice-transcription-spike.md): its default keeps data indefinitely until the workspace Owner sets "No retention"; whether that covers speech-to-text, and whether audio is used for training, are unverified. Nothing measured: no fixtures yet, no key here.

## Handoff

- Live: nothing changed. In flight: step 1 (#357) and step 2, the parser (its words in
  `supabase/seed/voice_template.json`, to be checked against teacher-os field/k2-shadow-capture.md). Next: the tables,
  after M0-05's people and enrolment land. Blocked: the teacher-os documents; Nimish's 8 recordings.
