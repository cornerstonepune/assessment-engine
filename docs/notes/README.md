# Notes: one file per branch

Nimish, 2026-10-21: every branch wrote the top of `STATE.md` and `HANDOFF.md`, so each merge put every other open
branch in conflict, even a branch that changed no code, and he could merge nothing. So from that day on:

- **A branch writes one file of its own:** `docs/notes/<goal name>.md`, for example `b1-levels-are-rows.md`.
  No other branch touches it, so it never conflicts.
- **That file holds two sections:**
  - `## Verified`: what `STATE.md` held, each claim with the command that proves it and its last output.
  - `## Handoff`: what `HANDOFF.md` held (live, in flight, next, blocked), under 20 lines.
- **`STATE.md` and `HANDOFF.md` are frozen** as the record up to 2026-10-21. They are read, never edited on a branch.
- **Where things stand now** is the newest notes: `ls -t docs/notes/`. A goal that cites a measurement names the note
  and the heading it is under, as it once named a heading in `STATE.md`.
