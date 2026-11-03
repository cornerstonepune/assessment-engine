# M1-01 — K2 voice-note intake

W3 (read and graph). A new step for voice notes is proposed to `workflows.json` with the parser (step 2), not before.

## Verified

- `cd packages/engine && uv run pytest -q tests/test_voice_intake.py` → 1 passed: git refuses every kind of audio
  file and the repository holds none.
- `bin/check` → 34 passed.
- `bin/engine done m1-01-voice-intake` → the sentence PROVED, every criterion PASSED, "NOT DONE": not on main, the
  live database does not answer from the build container, three steps manual.

## Not verified / open

- The design documents in cornerstonepune/teacher-os could not be read from this container (the clone asks for a
  login; attaching it was refused). Asked the orchestrator for them. The spoken template and the table design are not
  guessed; the parser and the tables wait on them.
- Speech to text is Sarvam (Nimish, 3 Nov). Read its current docs (research/2026-11-03-k2-voice-transcription-spike.md): its default keeps data indefinitely until the workspace Owner sets "No retention"; whether that covers speech-to-text, and whether audio is used for training, are unverified. Nothing measured: no fixtures yet, no key here.

## Handoff

- Live: nothing changed. In flight: step 1 (this goal, the spike, audio kept out of git). Next: the parser, once the
  template text arrives. Blocked: the teacher-os documents; Nimish's 8 recordings.
