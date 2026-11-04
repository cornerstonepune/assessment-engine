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

## Step 3, the tables — `20261226090000_k2_voice_notes.sql` (additive only)

- New: `activity_observation` (one row per child per activity per confirmation; append-only by trigger and by grant;
  a correction is a new row with `supersedes` and `reason`; `stored_at` is the database's clock; `observed_at` never
  later; the curriculum version named by the existing trigger), `pii.educator_note` (audio key, transcript,
  `received_at` set by the server and never moved, status), `pii.note_claim` (each line, its words and her decision;
  written once). Five vocabulary tables (`observation_outcome`, `observation_entry_mode`, `observation_route`,
  `note_status`, `claim_decision`) and two config rows (`voice.confirm_within_hours` 48; `voice.audio_retention_days`
  null, O-14), also in `supabase/seed/config.json`.
- Not touched: `evidence_event`, `activity`, `enrolment`, `staff`, any M0-05 table, any existing row. No DELETE for
  either service on any new table; the website reads the observations and the words, and never a note or a claim.
- `cd packages/engine && uv run pytest -q tests/test_voice_tables.py` → 9 passed (after the orchestrator's review: a correction is of the same school, child and activity, once, never itself; a confirmed note keeps its words and class and no note goes back); with `test_roles`,
  `test_db_privileges`, `test_data_register`, `test_people`, `test_rules`, `test_evidence_every_kind`,
  `test_vocabulary`, `test_loaders` → 62 passed, on a local database built from every migration and the seed.
- The migration applied twice in a row locally: no error, nothing changed the second time.
- `engine live rules --write --url <local>` → 35 rules added, every one on the new tables.
- Data register: a new "observations" entry names the three tables, in a parent's words.

## Step 4a, the engine — `20261227090000_k2_voice_evidence.sql` (additive) and `w3_read/voice_*`

- A recording is kept on the engine box's disk under `data/voice/<year>/<note id>.<ext>` (gitignored, as scans are);
  only its key is in the row. Retention is O-14: `bin/engine read voice retention` deletes nothing while
  `voice.audio_retention_days` is null.
- Transcribed through `adapters/speech.py` after the upload answers, only when `SARVAM_API_KEY` is set; otherwise the
  note waits as received. Read by `voice_note.read`; the activity's spoken number found by `activity.sheet_no` in the
  class's grade; every number in the class's enrolment open that day. A stranger or an unknown activity is a problem.
- Confirm (or the form's Save) writes, in one transaction: an observation per child (named, or "the rest" as a group),
  evidence on each activity skill for above / as expected / below with the mark from config rows
  (`voice.outcome_moves_level`, `voice.level_mark`, unverified for every activity), none for not willing or absent,
  her decision on each line (`pii.note_claim`), the note confirmed. An incident is never confirmed. `observed_at` is
  the note's own time on its own day, else the start of the day she said, never later than now.
- `bin/engine read voice expire`: notes older than `voice.confirm_within_hours` are left unconfirmed, never evidence.
- Every route refuses while `voice.screens_enabled` (config, false) is off.
- `uv run pytest -q tests/test_voice_intake.py tests/test_voice_confirm.py tests/test_cli_voice.py
  tests/api/test_voice_routes.py` → 21 passed (after an independent review: a note past 48 hours is refused at confirm, not only by the job; only her own observation is corrected, and once; a refused upload keeps no recording; an id that is not one is refused in words); with every neighbouring database suite 241 passed locally.

## Step 4a, after the architecture council (3 Nov)

- The database refuses evidence of an observation from a voice note unless that note is confirmed
  (`internal.evidence_of_a_confirmed_note`); confirm marks the note confirmed first, in the same transaction.
- Only an educator with an open grant on the class, in a role `voice.roles_that_record` names (class teacher, cover
  educator; a campus role does not record unless added), records, confirms or corrects for it.
- The level each outcome showed is kept (`activity_observation.reached_level`), and its mark comes from the two config
  rows; a test changes both rows and the result follows.
- `uv run pytest -q tests/test_voice_confirm.py tests/test_voice_intake.py tests/api/test_voice_routes.py
  tests/test_voice_tables.py tests/test_cli_voice.py` → 33 passed; neighbouring suites 212 passed (three runs; one
  earlier run, right after re-applying the migration locally, had one failure not seen again and not identified).

## Step 4a, observed evidence and the rung rule (3 Nov, found by the 4b worker)

- Found: `tests/test_rung_folded.py::test_every_rung_code_on_record_is_a_skills_second_code` failed on any database
  holding a confirmed voice note (`('evidence_event', [{'rung_code': None}])`). CI's clean database never held one.
- Cause: the test (22 Oct) is older than C2's rule (`20261205100000`, 23 Oct), which lets every kind but a written answer
  carry no rung (`evidence_event_written_has_rung`); nothing wrote another kind until voice notes. A rung cannot be set:
  an activity's skills are registry skills, and none of the 3711 `activity_skill` rows is a school skill with a second
  code (local database, `select count(*) ... from activity_skill a where exists (select 1 from skill s where s.code =
  a.skill_code)` → 0).
- Fix: the test confirms a voice note first, so it fails before the fix, and then excuses only an unrunged record that is
  not written, in `evidence_event` alone; every other table and every non-null rung is held as before. A written answer
  with no rung stays refused by the database (`tests/test_evidence_every_kind.py`, line 141).
- `pytest tests/test_rung_folded.py -k every_rung_code` before the fix → `1 failed` (the row above); after →
  with the evidence, voice, roles, privileges, register and past suites `136 passed`; `bin/check` → 34 passed.

## Step 5 groundwork — scoring the reader, replay, retention

- `bin/engine read voice check <expected.json>`: each drafted note scored against what the educator says it said
  (activity, above, below, not willing, absent, the rest), field by field; prints note ids, field names and counts,
  never a transcript or a name. For the first 20 real notes.
- `bin/engine read voice replay --class <id> <transcript.txt>`: a typed transcript read against a class as a recording's
  would be; writes nothing and calls no service. A free sentence or incident is shown by its length only.
- `voice_store.retention`: null keeps every recording; a number deletes finished notes' recordings older than it and
  reports a count; the row and its key stay.
- `uv run pytest -q tests/test_voice_check.py tests/test_cli_voice.py` → 8 passed.

## To set up on the engine box, after Nimish approves the pilot (not built: no scheduler here)

The engine runs on the box as the container `deploy-engine-1`. The deploy runs its commands as
`sudo docker exec deploy-engine-1 engine …` (`.github/workflows/deploy-engine.yml`), so the timer does the same. On the box,
`sudo crontab -e`, then add these two lines exactly (the box's clock is UTC):

    17 * * * * docker exec deploy-engine-1 engine read voice expire >> /var/log/voice-expire.log 2>&1
    43 21 * * * docker exec deploy-engine-1 engine read voice retention >> /var/log/voice-retention.log 2>&1

- **The first line, hourly:** a note past `voice.confirm_within_hours` (48) is left unconfirmed and never becomes
  evidence. Confirm already refuses a late note by itself, so this keeps the queue and the coordinator's count honest.
  It is safe to run at any time and changes nothing the second time.
- **The second line, daily at 03:13 in Pune:** it deletes nothing while `voice.audio_retention_days` is null (O-14,
  open). It prints "kept: … nothing deleted" until Nimish sets a number. It is safe to add now.
- Both print counts only, never a transcript, a name or which note. `tests/test_cli_voice.py` holds these two lines to
  commands the engine has.

## Step 4a extras, what any front end needs from the engine (branch m1-01-voice-engine-extras)

- `/voice/queue` also returns `classes`: the classes her `staff_role_grant` names today whose grade has activities
  (`voice_intake.classes_of`); the website never looks staff up by email, so this is how it learns her class.
- `/voice/notes/draft` also returns `level` (the level she said, else the template's default row) and `day_problems`
  (the problems about the date she said, `Draft.day_problems`), so picking a date can clear exactly those.
- `/voice/notes/audio` serves the recording with its own audio type (from its file's ending), so a phone can play it.
- `uv run pytest -q tests/test_voice_day.py tests/test_voice_note.py tests/test_voice_intake.py tests/test_voice_confirm.py
  tests/test_cli_voice.py tests/api/test_voice_routes.py tests/test_voice_tables.py tests/test_speech.py` → 107 passed,
  on a local database built by `bin/testdb fresh`.
- The screens (step 4b) are stopped until the design is agreed (orchestrator, 3 Nov); no site code on this branch.

## What step 3 (the tables) needed from M0-05 (#358)

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

## Lesson (3 Nov, #363)

- A ledger table's guard trigger must not refuse TRUNCATE, because the rehearsal's copy of live empties every table
  before loading live's rows (`engine live copy`). Follow `evidence_event`: the trigger refuses update and delete only,
  and emptying is refused to both services by grant (`internal.apply_conventions()`). #361's triggers refused TRUNCATE
  too, and every rehearsal failed once they were on live; `20261226100000_voice_ledgers_like_evidence.sql` fixes them.

## Not verified / open

- The live Sarvam call has not been run: no key here and no fixtures.
- The spoken activity numbers (up to 634, with gaps) matching the ACT-K2-nnnn codes through `activity.sheet_no` is
  unchecked: it needs the live database.
- Speech to text is Sarvam (Nimish, 3 Nov). Read its current docs (research/2026-11-03-k2-voice-transcription-spike.md): its default keeps data indefinitely until the workspace Owner sets "No retention"; whether that covers speech-to-text, and whether audio is used for training, are unverified. Nothing measured: no fixtures yet, no key here.

## Handoff

- Live: nothing changed. In flight: step 1 (#357) and step 2, the parser (its words in
  `supabase/seed/voice_template.json`, to be checked against teacher-os field/k2-shadow-capture.md). Next: the tables,
  after M0-05's people and enrolment land. Blocked: the teacher-os documents; Nimish's 8 recordings.
