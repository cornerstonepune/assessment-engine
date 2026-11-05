# M1-04 — the K2 voice-note screens

W3 (read and graph), step N9 (Read, check and learn): the screens of goals/m1-01-voice-intake.yaml's step 4b, with their
own goal, `goals/m1-04-k2-screens.yaml`. Built to the design agreed on 3 Nov 2026 (relayed by the orchestrator): desktop
first at 1280 px, one column on a phone; colour first and never colour alone; work a round chip, a child a square cell
and never red; marks are icons first; nothing ticked for her; Confirm per note. All of it behind `voice.screens_enabled`
(config, false). No migration.

## What a K2 educator sees, with voice notes switched on

- **What needs doing** gains two groups at the top: *Record a note* (one row per class her role grant names today) and
  *Notes to confirm* ("3 to confirm", counted in the menu's one count). No session rows: there is no timetable yet.
- **Record a note** (`/voice/record?class=…`): Record, Stop, play back, Send. The recording goes from the phone straight
  to the engine with a signed ticket, then the note opens, "Reading your note", and the page checks again by itself.
  A refused microphone, a recording too short to hold words, or a failed send each say so, and point to the form; the
  recording stays on screen until sent, and leaving before then asks first. It takes an optional `activity` (the K2
  team's number) for when a day's sessions can open it; today she says the number in the note.
- **Confirm this note** (`/voice/notes/[id]`): what she said, line by line beside its words, on the left; the class's
  children by Sr. No. on the right, already marked from it; the red problems pinned first, each with its fix (a number
  not in the class: tap the right child, or remove it; a child in two lists: keep one; no activity: search by number or
  name; a date in the future or not read: pick it; a list with words not read: paint it, or say it is right). The
  button stays off while one remains. Her recording plays beside it; a note about an earlier day says "late".
- **Fill the form** (`/voice/form?class=…`): paint mode — pick Above, Below, Not willing or Absent, then tap the
  children; the activity by number; the level; the day; "the rest did as expected" one switch that starts off. Save,
  under the count line, is her confirmation.
- A note that could not be read, or where nothing was heard, sends her to the form.

Words: `apps/web/lib/voice-words.ts`. Icons: `apps/web/lib/icons.tsx`, the one lookup (the status chip's too): Lucide
(`lucide-react` 1.59.0, pinned, ISC licence), the set chosen with the school's designer on 3 Nov. It is the site's first
icon dependency; before it, every icon was drawn by hand. One icon per concept, under the concept names agreed that day. The rules: the pure
`apps/web/lib/voice-check.ts`, the same for Confirm and the form; the engine checks them all again on confirm.

## Verified

- `cd apps/web && npx playwright test tests/m1-04-k2-voice-notes.spec.ts --reporter=line --workers=1` → 8 passed, on
  a database built by `bin/testdb fresh`; screenshots at 1280 and 390 px in `apps/web/test-results/k2-screens/`.
- The site's rules, the menu, What needs doing and the speed test: `npx playwright test tests/u51-ux-rules.spec.ts
  tests/u62-scope-and-todo-logic.spec.ts tests/u62-assessment-steps.spec.ts tests/u64-what-needs-doing-groups.spec.ts
  tests/u64-a-file-read-again-is-one-line.spec.ts tests/u64-stop-a-kind.spec.ts tests/u53-the-menu.spec.ts
  tests/u53-staff-and-school.spec.ts tests/u53-skill-name-opens-the-skill.spec.ts tests/u71-results-by-topic.spec.ts
  tests/u71-results-numbers.spec.ts tests/u65-what-needs-doing-walk.spec.ts tests/u1-today.spec.ts
  tests/u15-menu-and-today.spec.ts tests/u33-one-count.spec.ts tests/s41-subject-class-and-today.spec.ts` → 86
  passed; u71's pages 565–792 ms. Rerun on Lucide with the chip and board icons too (and asm2-by-topic, u60, u63, which
  read every chip's icon) → 121 passed; u71 755–978 ms, and 807–898 ms with the old drawn icons put back on the same
  machine, so the icons do not slow a page. Screenshots: `docs/screens/m1-04/` (16, with `index.html`, a contact sheet). u51 now measures the four K2 pages with the switch on, and none is on `ux.frozen`.
- Engine: a note is about the day on the school's clock, not the server's (`voice_intake.school_day`; a note heard at
  03:54 in Pune was dated the day before). `tests/test_voice_intake.py::test_a_note_is_about_the_day_on_the_schools_clock_not_the_servers`
  failed before the fix and passes after; the draft also says whether anything was heard (`heard`). The voice suites →
  108 passed.
- `bin/check` → passed; `npx tsc --noEmit` and eslint on the changed files → clean.

## Recording is its own switch (branch m1-04b-voice-recording-switch, D-065)

- `voice.recording_enabled` (config, default off; a missing row is off; in `supabase/seed/config.json` as `seed_once`).
  No migration. Recording, the upload (`POST /voice/notes`), the playback (`/voice/notes/audio`, `/api/voice/[note]`),
  the Record page, its ticket and the microphone button need it AND `voice.screens_enabled`; What needs doing, the
  form and Confirm need `voice.screens_enabled` only. With recording off a class's K2 row reads "Fill the form".
- Tests written first, failing before the code: `tests/api/test_voice_routes.py::test_with_recording_off_no_route_takes_or_gives_a_recording_and_the_form_still_works`
  (no row, and the row false: the upload and the playback refuse "Recording is not switched on.", nothing is written
  to disk, the form, the class and the queue answer), `::test_with_both_switches_on_a_recording_is_taken_and_the_queue_says_so`,
  and the browser test "with recording off, the K2 educator fills the form ...". The u64 check (the group reads Fill
  the form) and u51 measuring the form-only pages were written after the code.
- The whole engine suite in 12 shards, cut by `bin/ci-shard pick` as CI cuts it, on databases built by `bin/testdb
  fresh`: 3216 passed, 2 skipped, 2 failed. The two failures are `test_spine_provenance.py` (2): it downloads
  ncert.nic.in, and this container's Python does not trust the proxy's certificate; CI reaches it. Shard 6 first gave
  one more failure (`test_question.py::test_every_kind_in_the_bank_can_be_printed_again`) only because locally it
  shared a database with shard 3 before it; on its own fresh database, as CI gives each shard, shard 6 → 252 passed.
- Browser, the parts touched: the K2 spec, u51, u64, u62, u53, u65, u1, u15, u33, s41, u71 → 70 passed. `bin/check` → 34
  passed. tsc and eslint clean.

## The switches by command, and every activity in the picker (branch m1-04c-voice-switch-command)

- `bin/engine read voice switch screens on --by <your email>` (and `off`; and `recording on|off`). Each turn writes
  the config row and an `access_log` line under the signer's staff id (`core/signer.py`, as a people load is signed);
  nothing prints an email. `recording on` is refused without `--retention-ref "<reference of Sarvam's written No
  retention>"` (D-065), and the reference is kept in the log. No raw SQL on live; no migration.
- The form's activity picker held only activities with a number; the K2 sheet leaves 321 of live's 871 without one
  (orchestrator, checked on live, 4 Nov). It now holds every activity of the grade, numbered ones first; one with no
  number is found by a word of its name and shown by its name alone.
- Tests first, each failing before the code: `tests/test_voice_switch.py` (4) and the browser test "an activity the
  K2 sheet left without a number is found by its name and saved".

## Not verified / open

- On a real phone: the browser test fakes the microphone; a real phone is the educator's week-1 test (D-064). Android Chrome records webm, iPhone Safari mp4; both are
  kinds the engine keeps (`voice_store.KINDS`), but neither phone has been tried.
- The form has no "one line" (the free sentence). Keeping it needs a migration: nothing can hold a form's free text
  today (`activity_observation` has no text; a note needs a recording, and a form entry cannot name one). Proposed to
  the orchestrator: an additive `pii.form_note`. Not built until a go.
- The class picture and the child page wait for M1-03 Part B.

## Handoff

- In flight: draft PR (base `m1-01-voice-engine` until #362 merges, then main). Live: nothing; the switch is off.
- Next: Nimish reads the screenshots; the copy and icons change in their one file each.
