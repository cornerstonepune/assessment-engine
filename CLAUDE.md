@.claude/athena/CLAUDE.md

# cornerstone-platform — how this repository is built

Work here follows the common Athena loop above: a locked scope in `specs/<ID>/`, its proofs, `athena done`.
The design is `ARCHITECTURE.md` (what runs what, and where n8n is) and `SPEC.md`. Both implement
`docs/sources/assessment-workflow-v1.md`, the twelve-node workflow agreed with the school's staff. **When any of them
disagree, the workflow wins**: its decisions were taken with the school and are not to be re-derived. `STATE.md` and
`HANDOFF.md` were frozen on 2026-10-21; the newest files in `docs/notes/` carry both since. `docs/adr/` is why.
The old goal loop (`goals/`, its build order and its done-report) was retired on 2026-11-07 (ATH-14): its files stay
as read-only history, and goals not yet met became draft Athena scopes.

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

**`workflows.json` is the map, and the code follows it** — every step of the agreed workflow, the files
that do it, and the only connections one workflow may make to another. `packages/engine/tests/test_layout.py`
fails the day the code drifts from it (a file on no step, an undeclared connection, a file past its
ceiling, a step with no subject mark, a command or screen that does not exist). Change the map first.

```
workflows.json                  the map: 12 steps in 4 workflows, their files, hand-overs, ceilings
packages/engine/engine/
  w1_bank/                      W1 build the bank (N1–N2): skill sets, questions made and checked
  w2_print/                     W2 assemble and print (N4–N7): prescriptions, worksheets, packs
  w3_read/                      W3 read and graph (N3, N8–N10): reading, marking, the reader's notebook, evidence
  assess/                       the maths library — pure, no I/O, stands alone; W1–W3 use it
  core/                         the base: the one database connection, the seed loader, the class list
  adapters/                     the only files that call an outside service (text model, handwriting reader)
  checks/                       `engine audit`, scenarios, the live site's health, and the retired goal runner
  api/  cli.py                  the front doors — thin; each command or route hands straight to a workflow
packages/engine/tests/          one test file per module; test_layout.py holds the code to the map
goals/                          read-only history: the retired goal loop's goals (new work is scoped in specs/)
bin/engine                      run the engine from any directory
supabase/migrations/            numbered SQL; the only way the schema changes
supabase/seed/                  json the loader reads: registry, rungs, levels, misconceptions, prompts, thresholds
apps/web/app/                   the screens; server components by default
n8n/workflows/                  exported JSON, reviewed in PRs like code
data/                           gitignored — scans, renders, print packs
docs/adr/                       one decision per file, numbered
docs/sources/                   team documents this design incorporates
docs/ux-rules.md                the eight rules of the educator's site, the shared blocks, the pages still off them
```

A workflow imports only `core`, `assess`, `adapters`, and another workflow through a hand-over the map
declares. The doors (`cli.py`, `api/`, `checks/`) may import anything. No new file over 400 lines; the
files already over are frozen at their size in the map and may only shrink.

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
8. *(Retired 2026-11-07, ATH-14: proving work is the Athena loop's job.)*
9. **Migrations only.** Schema changes are numbered files in `supabase/migrations/`. No manual
   DDL, ever, on any environment.
10. **Reuse before write.** The prototype's `assess/` is the engine. Extend it; do not rewrite it.
    A helper that exists a few files over is used, not re-implemented.
11. **Root cause, in the same session, never a band-aid.** When something is found wrong — a weak
    prompt, a failing check, a lint or aislop finding on code this session wrote, a limitation named
    in a report — it is fixed at its cause before the session ends. Not noted for later, not worked
    around, not deferred to a "v3" in `HANDOFF.md`. Nimish, 2026-09-19: "do not leave for anything
    later; whenever you find an issue — don't apply a band aid; solve the root cause."
    What that means in practice: if a model is asked to produce something code can compute, the fix
    is to compute it, not to write a better prompt; if a file breaches a ceiling, it is split along
    a real responsibility, not exempted; if a claim cannot be verified, the claim is downgraded, not
    dressed up. Pre-existing debt in files this session does not touch stays frozen (baseline and
    ratchet) — it is named in `STATE.md`, never silently inherited.

12. *(Retired 2026-11-07, ATH-14: a change starts with a locked Athena scope instead.)*
13. **Read the graph before reading files, and hand over commands that run anywhere.** Exploration
    goes through `tokensave_context` / `tokensave_search` / `graft` first; `cat`, `grep` and `sed`
    are for editing and running, not for finding out how something works — a session that greps its
    way around the repository burns the context it needs later. Any command written for Nimish must
    work from whatever directory he is in: `bin/engine …` or an absolute path, never `cd x && y`.
14. *(Retired 2026-11-07, ATH-14: `bin/check` still runs as part of the fast checks; done is `athena done <ID>`.)*

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
- Commit boundary → update the branch's own note, `docs/notes/<spec ID>.md` (`docs/notes/README.md`); never
  edit `STATE.md` or `HANDOFF.md` on a branch, since two branches writing one file conflict on every merge; a
  rejected alternative → an ADR.
- Verification before any claim of done: run it, paste the output.
- Baseline and ratchet: today's debt is frozen; no new type errors, ≥ 80 % coverage on changed
  code, RLS on every table, no PII in logs.

## Verify

```
cd packages/engine && pytest -q                       # engine
engine load --check                                    # loader idempotence, seed counts
engine eval <purpose>                                  # a prompt's score against its bar (threshold rows eval.*)
cd apps/web && npx playwright test                     # one screenshot per screen
```
