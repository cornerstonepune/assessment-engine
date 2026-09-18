# HANDOFF — for the next session

Read `STATE.md` for what is verified and how. This file is what the last session left.

## Where things stand, 2026-09-18

**Live at https://cornerstone-assessment.vercel.app**, behind a staff sign-in. Nimish is the only
person on the staff list. Repo: `cornerstonepune/assessment-engine`, private, in sync.

Built and verified: the database and loader; W1 the question bank (a prompt generates, code
verifies, staff retire); W2 the week's papers (roster, prescription, per-child packs with QR);
and four of the six screens. 114 engine tests, 40 browser tests over two passes.

The bank holds 200 verified questions for SUB.2D.EXCH — 80 Hard from the model, 120 Medium from
the offline samplers.

## Start here

1. **Pick up the model research.** `research/2026-09-18-cheaper-models-glm-kimi.md` has prices,
   quality, the privacy split, and the exact experiment. Nimish asked for this and it is the open
   thread. Short version: try GLM 5.2 for question generation behind the existing adapter, never
   for reading children's work, and decide on cost per *accepted* question, not per token.
2. **W3, read and mark.** The next real build: photos in, QR resolves the child, marking by
   lookup, the confirm queue, the six-state graph. This makes Capture and Child Growth real.
   `assess/graph.py` is the seam already waiting for it.
3. **N3, the legacy import.** 37 real papers in `~/cornerstone/assessments/` become each child's
   starting evidence, checked against Aseem's five Grade 3 reports.

## Blocked on Nimish

- **Rotate the database password.** It was typed into a chat and then printed into a Vercel build
  log by a malformed connection string. Supabase → Settings → Database → Reset, alphanumeric only,
  then update `.env` and the Vercel variable.
- **Achal's and Neha's emails**, to add to the `app.staff` config row. Nobody else can sign in.
- **A real SMTP sender.** Supabase's built-in one allows two emails an hour and forbids custom
  templates on the free tier. This is what forces the client-side `/auth/finish` page to exist.
- **A working `ANTHROPIC_API_KEY`** — the one in `.env` returns 401.
- **An API key** for GLM or Kimi, if the experiment goes ahead.
- Consent text · parent-note channel · whether the Olympiad papers count · Kiyaan's missing Week 1.

## Traps this session fell into — do not repeat

- **Two keys in `.env` were placeholders**, not keys: `SUPABASE_ANON_KEY` was nine characters and
  `SUPABASE_SERVICE_ROLE_KEY` was too. Both are fixed. The only symptom was "the link could not be
  sent" on a healthy-looking page. Check a key authenticates before believing anything downstream.
- **Never assemble a connection string with shell substitution.** A stray backslash made the driver
  print the whole string, password included, into a build log.
- **Do not run a migration while a fill is writing** — the `ALTER TABLE` lock deadlocks it, and it
  cost a day's model quota.
- **The end-to-end suite writes to the live database.** It sweeps up after itself now and fails if
  it cannot, but a failing run once left a real question retired.
- Free Gemini tier: 20 requests per model per day, resets about 12:30 IST.
  `gemini-3.5-flash-lite` is useless here — 0 of 20 items passed the verifier.
- `apps/web/.env.local` holds `AUTH_DEV_BYPASS=1` on this machine only. It is gitignored and
  refused outside development.
- A hook blocks frontend edits until `.design-approved.json` exists at the repo root; it is
  gitignored, so a fresh clone needs it written again.
