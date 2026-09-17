# HANDOFF — current session

Session: 2026-09-17 to 18 — Phase 0, item generation built, the web app's first three screens.

## Done

- Phase 0: schema live, `engine load --check` green, prototype moved into `packages/engine`.
- Item generation decided and built (ADR 0005, ADR 0006): a prompt generates, code verifies,
  staff retire. `engine bank fill|recheck|flag|sheet`, `engine eval`. 80 verified items for
  SUB.2D.EXCH at Hard; recheck 0 mismatches; first sheet at `data/bank/CS289D43.pdf`.
- **The web app** (`apps/web`): Next.js 16, server components, one Postgres connection, magic-link
  sign-in with a staff allowlist. Skill Map, the skill-set editor and the question bank all read
  and write the real database; the other three screens show honest empty states. Brand from the
  Cornerstone Brand Book. 16 Playwright checks at two widths; engine suite 101. STATE has the
  commands and their output.

## Next

1. Finish the SUB.2D.EXCH Hard fill to 200 and run `engine eval item_generate`. The free tier
   allows 20 requests per model per day and resets about 12:30 IST.
2. Neha and Achal reword the four skill sets **in the app**, not the seed file — the loader is now
   insert-only for `skill_set`, so the app is the source of truth once a row exists. Aseem ratifies.
3. N3 legacy import: 37 papers + WhatsApp images + Olympiad booklets → candidates → starting
   graph; compare against the five G3 reports (gold).
4. W2 as engine code, then the Worksheets screen stops being an empty state.
5. Rungs/blueprints out of `ladder.py`/`blueprints.py` into rows (rule-1 debt, open).

## Open for Nimish

Whether to pay for Gemini (the free tier is the only thing slowing W1) · consent text · parent-note
channel · whether IMO papers count · Kiyaan's missing W1 · reset the DB password (came through
chat) · add the real staff emails to `config.app.staff` so Achal and Neha can sign in.

## Watch

- `apps/web/.env.local` holds `AUTH_DEV_BYPASS=1` for this machine. It is gitignored and refused
  outside development, but the app is not safe to deploy until the Supabase keys are set and the
  bypass is off.
- Free Gemini tier: 20 requests per model per day; `gemini-2.5-flash` retired;
  `gemini-3.5-flash-lite` is useless here (0 of 20 items passed the verifier).
- Phase 0 plan doc still says claude-opus-5 prompts and 24 misconceptions — both superseded.
- `.aislop/session.jsonl` files show as modified after every scan; do not sweep them into commits.
- A design-gate hook blocks frontend edits until `apps/web/.design-approved.json` exists (it is
  gitignored, so a fresh clone needs the artifact published and the file written again).
