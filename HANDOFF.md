# HANDOFF — for the next session

Read `STATE.md` for what is verified and how. This file is what the last session left.

## Where things stand, 2026-09-18, evening

**Live at https://cornerstone-assessment.vercel.app** behind email + password sign-in (`scrypt`
hashes in `config.app.staff`, an httpOnly cookie signed with `AUTH_SECRET`). Nimish is the only
person on the staff list.

**N3, the legacy import, ran for four Grade 2 children** (Advika, Agastya, Heian, Hridhima).
`engine legacy paper` entered four paper definitions (`supabase/seed/papers/`); `engine legacy
import` read the scans with the `legacy_extract` prompt on Haiku and marked by lookup; `engine
legacy confirm` turned 218 candidate answers into evidence. The six-state graph is SQL
(`supabase/migrations/20260918130000_graph_functions.sql`), so CLI and app run one rule.

**Child Growth is rebuilt for a teacher.** `/growth/[id]` shows one lane per skill (Addition,
Subtraction, Mental maths, Word problems, …), each step a marked node — tick, arrow, dot, bang,
dashed ring — with score, bar and the school's own rung descriptor beneath. Click a step and the
answers behind it open under the lane (`:target`, no client JS). Every name is a row —
`rung.descriptor`, `skill.name`, `skill_set.name`, `misconception.name`; no code reaches the
page. A rung shared by two skills (R9, 3-digit ±) sits in both lanes with its own state. Above
the lanes: got it / practising / same mistake repeating / not seen yet / waiting for you. Below:
the answers a person must settle, then the marked answers to confirm. Right: next papers, papers read.

## Start here — two data faults to settle before anyone reads a ladder

1. **Every paper was imported twice per child.** `import_scan` is not idempotent and the batch
   ran twice, so each child has two captures per paper and every answer counts double (43
   confirmed on a 24-question paper; "secure across two papers" is met by one paper read twice).
   Fix: a re-read of the same scan for the same child supersedes the earlier capture (a
   `superseded_by` on `capture`; the graph reads only live captures — rule 4 keeps the rows),
   then `engine graph`. Nimish decides whether the accidental duplicates are voided or deleted.
2. **13 of 28 captures errored** — `pdftoppm` returned non-zero on some WhatsApp PDFs; those
   reads hold no results. Render with `pdftocairo` or PyMuPDF and re-run.

Then: CI (`.github/workflows/ci.yml` exists, untested; the Vercel↔GitHub connection failed once —
reconnect in the Vercel dashboard), W3 for real (photos in, QR resolves the child), and the model
research in `research/2026-09-18-cheaper-models-glm-kimi.md`.

## Blocked on Nimish

- Voiding vs deleting the duplicate imports (above).
- `AUTH_SECRET` on Vercel, if not yet set; **rotate the database password** (it was typed into a
  chat and printed into a build log); re-copy or delete `SUPABASE_SERVICE_ROLE_KEY` (returns 401).
- Achal's and Neha's emails for `app.staff`.
- Consent text · parent-note channel · whether the Olympiad papers count · Kiyaan's missing Week 1.

## Traps this session fell into — do not repeat

- **Hard-coded rung and mistake names in TypeScript were wrong** (R3 labelled "adding ones"; it is
  subtraction within 20). Rule 1: names are rows. Read `rung.descriptor` and `misconception.name`.
- **`import_scan` ran twice for every paper.** Check `capture` for an existing (child, paper)
  before importing; better, make the command idempotent.
- **Routing paper reads through Sonnet 5 burned the $10 balance in one pass.** Haiku reads pages;
  a stronger model is for judging answers only, and only when asked.
- **A grid track without `minmax(0, 1fr)` grows to a table's width** and the page scrolls
  sideways on a phone even with `overflow-x-auto`. The screens test catches it.
- **A `"use client"` file must not import from `lib/queries.ts`** — it drags the Postgres driver
  into the browser bundle. Types only (`import type`), or a server component.
- Never assemble a connection string with shell substitution; never run a migration while a fill
  is writing; the e2e suite writes to the live database.
