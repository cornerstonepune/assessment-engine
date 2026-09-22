# assessment-engine — how this repository is built

Read `BUILD-ORDER.md` first — it says which of the four workflows we are on, what "done" means
for it, and forbids touching the next one before then. Say "W_, gate _" before doing anything.
Then `ARCHITECTURE.md` — it settles what runs what, and where n8n is. Then `SPEC.md`.
Both implement `docs/sources/assessment-workflow-v1.md`, the twelve-node workflow agreed with
Aseem and Achal. **When any of them disagree, the workflow wins** — its decisions were taken
with the school and are not to be re-derived. Then `STATE.md` (what is verified true) and `HANDOFF.md` (what the last
session left). This file is the constitution; `BUILD-ORDER.md` is the sequence; `SPEC.md` is the
design; `docs/adr/` is why.

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
  checks/                       the proofs: `engine audit`, `engine goal`, scenarios, the live site's health
  api/  cli.py                  the front doors — thin; each command or route hands straight to a workflow
packages/engine/tests/          one test file per module; test_layout.py holds the code to the map
goals/                          one yaml per goal: the sentence, its scenarios, its criteria
bin/engine                      run the engine from any directory
supabase/migrations/            numbered SQL; the only way the schema changes
supabase/seed/                  json the loader reads: registry, rungs, levels, misconceptions, prompts, thresholds
apps/web/app/                   the screens; server components by default
n8n/workflows/                  exported JSON, reviewed in PRs like code
data/                           gitignored — scans, renders, print packs
docs/adr/                       one decision per file, numbered
docs/sources/                   team documents this design incorporates
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
8. **Every "works" is a command.** `STATE.md` lists each claim with the command that proves it
   and its last output. No claim without a check.
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

12. **A task starts with a goal and ends when the goal's own command is green.** A goal is a
    sentence saying what the thing must *do*, plus the scenarios that prove it, written down before
    the work: `goals/<name>.yaml`, run by `engine goal <name>`. A scenario states a real request in
    the school's terms (this topic, this difficulty, this many questions) and the run checks the
    result independently of the code that made it — answers recomputed, every question re-measured
    against the band's own rule, every wrong answer mapped to a named mistake, no duplicates. **The
    bar is 100%: 19 of 20 is a failure, and work continues until the command passes.** Hygiene
    belongs in the same file as `criteria` (audit, coverage, recheck, load, suite), never instead of
    scenarios. Nimish, 2026-09-20: "the system should keep on working towards it till 100% accuracy
    is achieved."
13. **Read the graph before reading files, and hand over commands that run anywhere.** Exploration
    goes through `tokensave_context` / `tokensave_search` / `graft` first; `cat`, `grep` and `sed`
    are for editing and running, not for finding out how something works — a session that greps its
    way around the repository burns the context it needs later. Any command written for Nimish must
    work from whatever directory he is in: `bin/engine …` or an absolute path, never `cd x && y`.
14. **A promise is a command, and done is a report the machine writes** (ADR 0033). A goal written from
    2026-09-22 carries Nimish's own words, each with the test that proves it (`says:`), and nothing else a
    command does not run — `engine promises` refuses the rest. `bin/check` (the code against
    `workflows.json`, every promise against its command, lint) runs before every commit and before Claude
    Code may end a turn; a failure is fixed at its cause, never by raising a limit or loosening a rule.
    Work is reported done only with the output of `engine done <goal>` pasted — each of his sentences with
    its test run now, what is still manual, what is not live — never with a summary written instead.

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

- **One workflow at a time** (`BUILD-ORDER.md`). No code, prompt, migration, endpoint or screen for
  the next workflow while any gate of the current one is unchecked. A session names the gate it
  moved, or it did nothing.
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
