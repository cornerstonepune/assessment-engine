# assessment-engine — how this repository is built

Read `ARCHITECTURE.md` first — it settles what runs what, and where n8n is. Then `SPEC.md`.
Both implement `docs/sources/assessment-workflow-v1.md`, the twelve-node workflow agreed with
Aseem and Achal. **When any of them disagree, the workflow wins** — its decisions were taken
with the school and are not to be re-derived. Then `STATE.md` (what is verified true) and `HANDOFF.md` (what the last
session left). This file is the constitution; `SPEC.md` is the design; `docs/adr/` is why.

## The organism

One Postgres. Four rings. Every file belongs to exactly one.

| Ring | What | Where | Rule |
|---|---|---|---|
| A — truth | registry, ladder, blueprints, items, sheets, captures, results, evidence, prompts | `supabase/migrations`, written by engine and app | append or approve; a batch job never edits it |
| B — derived | child_skill_state, class_card, item_stat | rebuilt by `engine graph` | TRUNCATE-able at any time; pure function of A |
| C — adapters | Drive, Claude vision, notify | `packages/engine/adapters/` one file each | the only place an external service is named |
| D — flows | the wiring for nodes N2–N12 | `n8n/workflows/*.json` | trigger + sequence + wait + notify; nothing else. See `ARCHITECTURE.md` §2 for which node n8n touches and how |

Code where correctness is needed (arithmetic, marking, lookup, graph). A model where judgment is
needed (reading handwriting, reading a page, writing a context or a note). Never the reverse.
A model may *generate* what code then *verifies* — that is how the question bank is made
(ADR 0005) — but a number is never a model's last word.

## Structure

```
packages/engine/assess/      generation, blueprints, pick, render, mark, misconceptions — deterministic, no I/O
packages/engine/api/         FastAPI: /generate /render /ingest /mark /read /commit /graph /cards /home — thin
packages/engine/adapters/    drive.py  vision.py  notify.py — one class each, one interface each
packages/engine/cli.py       engine load | generate | legacy import | graph | eval
packages/engine/tests/       mirrors assess/ and api/
supabase/migrations/         numbered SQL; the only way the schema changes
supabase/seed/               json the loader reads: registry, rungs, levels, blueprints, misconceptions, prompts, thresholds
apps/web/app/                six routes matching the six screens; one Supabase client; server components by default
n8n/workflows/               exported JSON, reviewed in PRs like code
data/                        gitignored — scans, renders, print packs
docs/adr/                    one decision per file, numbered
docs/sources/                team documents this design incorporates
```

## Rules

1. **Nothing structural in code.** Bands, rungs, levels, blueprints, misconceptions, thresholds,
   prompts, the weekly matrix — rows in tables, seeded from `supabase/seed/`. Adding a grade or a
   rung is an insert. `BANDS = [...]` in a `.py` is a defect.
2. **Prompts are rows.** `prompt(purpose, version, text, json_schema)`. Fetched by purpose at
   runtime. A change is a new version row plus its eval score in `DECISIONS-LOG.md`. A prompt
   string inside Python, TypeScript or an n8n node is a defect.
3. **n8n never thinks.** No Code node with logic, no prompt, no marking rule. If a workflow needs
   logic, add an engine endpoint and call it.
4. **Evidence is append-only.** `evidence_event` rows are never updated or deleted; a correction
   is a new row that supersedes. The graph reads only `confirmed`.
5. **Three signals, never two.** Blank, wrong, and wrong-with-working are distinct everywhere.
   Nothing collapses them to "incorrect".
6. **Names stay in `pii`.** Application tables carry `child_id` only. Scans and photos never
   enter git or a log. Prompts receive images, not names.
7. **Every model output ships with an eval.** New prompt version → `engine eval <purpose>` →
   score recorded → only then active.
8. **Every "works" is a command.** `STATE.md` lists each claim with the command that proves it
   and its last output. No claim without a check.
9. **Migrations only.** Schema changes are numbered files in `supabase/migrations/`. No manual
   DDL, ever, on any environment.
10. **Reuse before write.** The prototype's `assess/` is the engine. Extend it; do not rewrite it.
    A helper that exists a few files over is used, not re-implemented.

## Language and naming

Python 3.12 (engine), TypeScript (app), SQL (schema). No fourth language. Table names singular
(`item`, not `items`). Ids: registry skill ids as issued (`NUM.OPS.01`); rungs `R1`–`R14`, `X1`,
`X2`; sheet instance ids are the QR string (`CS` + 6 hex). Misconception codes `M_…` (procedural)
and `M0nn` external refs kept in `misconception.external_ref`. Bands `G1`–`G4`. Difficulty is
`Easy` / `Medium` / `Hard` / `Advance`, the school's own vocabulary — never `L−/L0/L+` or
`Level A/B`, both retired. Signals: Foundational, Conceptual, Procedural, Application, Stretch.
The school's words win elsewhere too: "exchange / regroup", never "borrow"; "educator", never
"teacher", in anything a parent sees.

## Working rhythm

- Non-trivial change → plan first; a chunk starts only with 3–5 machine-checkable success criteria.
- Tests before implementation for anything with a branch, a loop, a parser, or a money/safety path.
- Commit boundary → update `STATE.md` and `HANDOFF.md`; a rejected alternative → an ADR.
- Verification before any claim of done: run it, paste the output.
- Baseline and ratchet: today's debt is frozen; no new type errors, ≥ 80 % coverage on changed
  code, RLS on every table, no PII in logs.

## Verify

```
cd packages/engine && pytest -q                       # engine
engine load --check                                    # loader idempotence, seed counts
engine eval read_cells                                 # prompt precision/recall vs gold
cd apps/web && npx playwright test                     # one screenshot per screen
```
