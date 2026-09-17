# HANDOFF — current session

Session: 2026-09-17 — Phase 0 complete, real data received, item generation settled.

## Done this session

- Phase 0: schema live (30 tables, RLS forced), `engine load --check` green, prototype moved into
  `packages/engine/engine/assess/`, 53 tests. All verified in `STATE.md`.
- Difficulty vocabulary corrected to the school's Easy/Medium/Hard/Advance; template-as-unit-of-
  trust restored from the workflow (no per-item review). `ARCHITECTURE.md` written: n8n boundary,
  node-by-node table, engine surface.
- `M_SMALL_FROM_LARGE` reproduces Aseem's hand diagnosis exactly (5147 for 8500 − 3647).
- Real papers inventoried: 16 children, 37 papers, 7 Olympiad booklets in `~/cornerstone/assessments/`
  (`manifest.md` there). Kiyaan's Week 1 paper is missing.
- **Item generation re-decided (ADR 0005).** Nimish: a prompt, given topic/objective/skill/philosophy,
  creates the bank — no code per topic. Spike proved it: arithmetic 20/20, distractors 77/77 vs
  predictors, verifier caught 3 malformed items. ARCHITECTURE §6.1 and §7, SPEC §5.6 rewritten
  around his four workflows W1–W4. Samplers demoted to fallback/eval, not deleted.

## Next

1. **W1 as an endpoint**: `item_generate` prompt row + eval set from the spike's 17 items;
   `POST /bank/fill` = generate → verify → tag → `approved`; adapter with retry, ordered
   fallback, batches of ~20. Schema fix from the spike: a field per format role (`shown`/`blank`).
2. `item_feedback` migration + the flag on the library screen (step 6 of §7.1 has no table).
3. N3 legacy import: 37 papers + WhatsApp images + Olympiad booklets → candidates for
   Achal/Aseem → starting graph; compare against the five G3 reports (gold).
4. Rungs/skill sets/blueprints out of `ladder.py`/`blueprints.py` into rows (rule-1 debt, open).

## Open for Nimish

Consent text · parent-note channel · whether IMO papers count · Kiyaan's missing W1 ·
"silence = approval?" (proposed yes for practice, no for assessment) · when to reset the DB
password (came through chat; alphanumeric only, then update `.env`).

## Watch

- Free Gemini tier: 503, spurious 404, and a 120 s timeout on 40 items in one session. Never a
  single pinned id; never the `-latest` alias.
- Phase 0 plan doc (`docs/superpowers/plans/2026-09-17-phase-0-foundations.md`) still says
  claude-opus-5 prompts and 24 misconceptions — both superseded; reconcile or annotate.
- `.aislop/session.jsonl` files show as modified after every scan; do not sweep them into commits.
