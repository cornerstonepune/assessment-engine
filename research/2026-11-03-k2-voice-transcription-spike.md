# K2 voice notes: the recording turned into words (task M1-01, step 1)

W3 (read and graph). A new step for voice notes is proposed to `workflows.json` in the parser's pull request.

**Decision, Nimish, 2026-11-03 (relayed by the orchestrator): Sarvam AI, which the school already has.** No
comparison of tools. The earlier draft of this file compared it with faster-whisper on our own server; that is
dropped, with one fact kept for the record: our engine's server has 2 GB of RAM, too little for a speech model.

Nothing in this repository calls Sarvam yet (searched: `adapters/`, `.env.example`, ADRs, goals). Background
research already here: `research/research_notes/School operating system council/4-observation-documentation.md`
and `8-india-context.md` (third-party benchmarks; not re-checked).

## What I read, 3 Nov 2026, and what it says

From [the speech-to-text API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe.md):
- `POST https://api.sarvam.ai/speech-to-text`, multipart form, key in header `api-subscription-key`.
- `model`: `saaras:v4` (the default) or `saaras:v3`. `mode` (`transcribe`, `translate`, `verbatim`, `translit`,
  `codemix`) is read only by `saaras:v3`. `transcribe` mode does "number normalization"; `verbatim` keeps spoken
  numbers as spoken.
- `language_code`: `hi-IN`, `en-IN`, `unknown` (detect) and 21 more.
- `keyterms`: up to 50 terms, 64 characters each, `saaras:v4` only, to bias recognition. They don't guarantee a term.
  We would put the template's own words here ("above", "below", "not willing", "absent", "incident", "activity"),
  never a name.
- Formats: WAV, MP3, AAC, OGG, OPUS, FLAC, MP4/M4A, WebM and others; works best at 16 kHz.
- **Length:** the REST call is meant for audio "under 30 seconds"; longer goes to the Batch API. No hard limit or file
  size is stated. **A note longer than 30 seconds is a real risk:** the Record screen will show a timer, and the
  fixtures will tell us whether 30 seconds is enough.
- The REST call does not separate speakers.

From [pricing](https://docs.sarvam.ai/api-reference-docs/pricing.md): speech to text ₹0.49 a minute pay-as-you-go
(₹0.45 Pro, ₹0.41 Growth), excluding GST, billed per second. 20 notes of 30 seconds a day is about ₹5 a day.
Approximately; **verify against the school's own plan.**

From [data retention](https://docs.sarvam.ai/api/platform/data-retention.md):
- **The default is to keep everything, indefinitely, until an Owner sets a period.** This is the one thing the school
  must change before the first real note.
- Only the workspace's org Owner can set it: Settings → Workspace → Data retention. The options include "No
  retention" (0 days). It is supported for "Model APIs" and not yet for Voice Agents. **The page does not name
  speech-to-text**, so whether "No retention" covers it is unverified. Ask Sarvam to confirm in writing.
- A change applies only to data created after it.
- **Not found:** whether Sarvam trains on customer audio, its terms of service and its data-processing terms. Sarvam's
  marketing pages say audio is processed in India and never used for training, but that is marketing, not a contract.
  Unverified until the school's agreement with Sarvam is read.

## What can't be known until measured (S-M1-01-fixtures)

- **Hindi number words.** Whether "unnees" comes back as "19", as "उन्नीस", or as a wrong word. The API reference
  says `transcribe` mode normalises numbers, but it doesn't say it handles Hindi numbers inside English speech.
  The parser will read all three forms (digits, English words, Hindi words in Latin script and in Devanagari) so
  either output works. The fixtures decide which `model` and `mode` we use.
- The measure on each fixture: every template word and every number the reader said, found or not, from
  Sarvam's transcript read by our parser. The bar is every number on every fixture (rule 12). A miss is reported,
  not tuned away, because the educator confirms every line anyway.

## Privacy, as built

- Children are said only as numbers (O-13 open). The audio is kept on our private side; Sarvam receives the audio
  and nothing else (no roll, no name, no class). Retention on our side is a setting, and nothing is deleted yet (O-14).
- The key is the environment variable `SARVAM_API_KEY`, never in git or a log. Only the adapter
  `packages/engine/engine/adapters/speech.py` calls Sarvam (rule 10).
- `.gitignore` refuses audio files, and a test holds it.

## Recording instructions (the fixtures)

Nimish will not record these for now (orchestrator, 3 Nov). Synthetic recordings of an adult voice with placeholder
numbers are allowed for this spike only, never as proof (D-056). None could be made from the build container, which has
no voice and no Sarvam key, so the live check is manual and not run. The adapter is tested against a recorded-response
stub (`tests/test_speech.py`).

1. Use any phone's voice recorder. One adult, in a normal room. A little background noise is good. **No children,
   no real class, no real child's number.** Use numbers 1 to 30 as placeholders.
2. Record **8 notes**, each 10 to 30 seconds, each reading the spoken template (teacher-os
   `field/k2-shadow-capture.md`) with made-up numbers. Vary them:
   - 1 and 2: plain English, slowly, then quickly.
   - 3 and 4: the numbers in Hindi ("teen, saat, unnees"), the rest in English.
   - 5: one number said twice ("seven, seven"), and one corrected ("twelve, no, thirteen").
   - 6: a pause and an "umm" in the middle, and one list empty ("none below").
   - 7: one free sentence at the end, and the word "incident" with a made-up line.
   - 8: fast, with Hindi and English mixed throughout.
3. After each recording, write down exactly what you said, the numbers especially, in a text file of the same name.
4. Name them `fx-01-english-slow.m4a` to `fx-08-mixed-fast.m4a`, with `fx-01-english-slow.txt` beside each.
5. Put them in one Google Drive folder and share it with the build. Never put them in GitHub.

## Asked of the school

- The Sarvam workspace Owner sets Data retention to "No retention" for Model APIs, before the first real note.
- Someone confirms with Sarvam (support@sarvam.ai, per its pricing page) that this covers speech-to-text, and that
  audio is not used for training.
- `SARVAM_API_KEY` goes into the server's environment, not into any file in git.
