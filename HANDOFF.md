# HANDOFF — current session

Session: 2026-09-17 — Phase 0 complete, real data received, item generation settled and built.

## Done this session

- Phase 0: schema live, `engine load --check` green, prototype moved into
  `packages/engine/engine/assess/`. All verified in `STATE.md`.
- Difficulty vocabulary corrected to Easy/Medium/Hard/Advance; template-as-unit-of-trust
  restored from the workflow. `ARCHITECTURE.md` written; four workflows W1–W4 are the frame.
- `M_SMALL_FROM_LARGE` reproduces Aseem's hand diagnosis exactly (5147 for 8500 − 3647).
- Real papers inventoried: 16 children, 37 papers, 7 Olympiad booklets in `~/cornerstone/assessments/`.
- **Item generation re-decided and built (ADR 0005, ADR 0006).** A prompt generates, code
  verifies, staff retire. W1 exists as engine code: `skill_set` and `item_feedback` tables,
  four seeded skill sets, the `item_generate` prompt row, `adapters/llm.py`, `assess/verify.py`,
  `bank.py`, `engine bank fill|recheck|flag|sheet`, `engine eval`. 98 tests. First real fill
  stored 40 verified items before the free tier's limit; recheck 0 mismatches; a rendered sheet
  (`data/bank/CS289D43.pdf`) handed to Nimish.

## Next

1. Finish the SUB.2D.EXCH Hard fill to 200 in background runs (free tier allows ~4 calls per
   sitting); then `engine eval item_generate` per set × band, score into DECISIONS-LOG.
2. Ask Neha and Achal to edit `supabase/seed/skill_sets.json` words and checks; Aseem ratifies
   (`skill_set.status`, `ratified_by`).
3. N3 legacy import: 37 papers + WhatsApp images + Olympiad booklets → candidates → starting
   graph; compare against the five G3 reports (gold).
4. Rungs/blueprints out of `ladder.py`/`blueprints.py` into rows (rule-1 debt). The prompt
   path does not read them; the deterministic generators still do.
5. `flow_run` has no column for which model served; add one when the fallback matters.

## Open for Nimish

Consent text · parent-note channel · whether IMO papers count · Kiyaan's missing W1 · reset the
DB password (came through chat; alphanumeric only, then update `.env`) · whether to pay for
Gemini (the free tier is the only thing slowing W1 down).

## Watch

- Free Gemini tier: ~20k tokens and ~95 s per 20-item call; cut-off after ~4 calls; spurious
  404s; `gemini-2.5-flash` retired. Never a single pinned id; never the `-latest` alias.
- Phase 0 plan doc (`docs/superpowers/plans/2026-09-17-phase-0-foundations.md`) still says
  claude-opus-5 prompts and 24 misconceptions — both superseded; reconcile or annotate.
- `.aislop/session.jsonl` files show as modified after every scan; do not sweep them into commits.
- `item.status = 'active'` is the schema's word for what the docs call approved.
