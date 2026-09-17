# STATE — what is verified true

Each line: a claim, the command that proves it, its last output. No claim without a check.

## Design

- Spec approved in shape by Nimish (approach A); written as `SPEC.md`; awaiting his read-through.
- ADRs 0001–0003 record the stack, the skill model, and the n8n boundary.

## Inputs verified

- Registry: `window.CSMAP` from the Skill Map Review artifact — 244 skills, 849 milestones,
  14 domains, NUM = 37 skills. All seven skill ids the ladder maps to exist
  (`NUM.OPS.01/.02/.05`, `NUM.PRB.02/.03`, `NUM.PV.03`, `NUM.MEAS.04`).
  Check: `python3 -c` parse of `data.js` → counts above.
- Prototype: `~/Downloads/assessment-engine-prototype/assess/` — 8 modules; synthetic roundtrip
  report: cell geometry agreement 1.0 on 4/4 sheets, QR decoded 12/12 pages; status agreement
  0.40–0.70 with the Tesseract stub (not for handwriting, by its own docstring).
- Existing scans: 13 `ACE Scanner_20260916(N).pdf` — none carry fiducials or a QR, none have a
  text layer. Check: prototype `find_fiducials` + `cv2.QRCodeDetector` on page 1 of each → 0/13.
  Therefore every existing assessment goes through legacy import. Real Phase 1 input is
  whatever Nimish uploads to `~/cornerstone/assessments/` (layout in its README); the Downloads
  scans were evidence only.
- Team documents incorporated: `Addition_Subtraction_Assessment_Skill_Taxonomy.pdf` (13 pp;
  §12 tag matrix, §13 progression) and `Adaptive_Subtraction_Learning_Engine_…Spec.docx`
  (M001–M010 conceptual misconceptions).

## Handwriting reading — first real measurement (2026-09-17)

One real Grade 3 paper (`ACE Scanner_20260916(2).pdf` p1, Sep Week 1), name band masked before
sending, `legacy_extract` prompt v1, `gemini-3.5-flash`, 1,237 in / 695 out tokens.

Read correctly, checked against the page: Q1 a=53 b=612 c=1250 d=36 (all four arithmetically
consistent); Q2 balance = 600; Q3 blank and circled, correctly reported as not attempted;
Q4 number line landing 78, answer 83; Q6 column 675+589 = 1264. It also caught the teacher's
circles on Q1 b/d, and on Q5 read the child's partition of 638 as 600+19+19 — a wrong method
reaching a right answer (1113), which is exactly the diagnostic signal the product exists to find.

**Status: promising signal, not a measurement.** One page, one child. The real figure comes from
the Phase 1 `gold` set against Aseem's own marking.

Three things this spike changed:
1. `legacy_extract` needs a `part` field — Q1's four lettered sub-answers arrived crammed into one
   string. Marking needs one row per response.
2. Teacher annotations are legible to the model. Useful for Channel B; Channel A must be told not
   to read a teacher's circle as the child's answer.
3. Free tier returns 503 and intermittent 404 under load. The adapter needs retry with backoff
   and an ordered model fallback list, not a single pinned id.

Model availability (checked live, `models.list`): flash line runs to `gemini-3.8-flash`;
`gemini-3.8-flash` was overloaded, `gemini-3.5-flash` served. `gemini-2.5-flash` — the brain's
2026-09-08 choice — is now three generations back. Never use the `gemini-flash-latest` alias:
a silent model change would invalidate every accuracy measurement taken against it.

## Phase 0 — schema

Two migrations applied to the hosted project `ruznbyngtfjsaymuylhm` (ap-south-1) with
`supabase db push --db-url "$DATABASE_URL"`: `20260917090000_ring_a.sql` (Ring A, the `pii`
schema, `internal.apply_conventions()`) and `20260917090100_ring_b.sql` (the three derived
tables). The full schema exists now, so Phases 1–4 add rows, never DDL. Every check below is
run after `cd ~/cornerstone/assessment-engine && set -a && . ./.env && set +a`.

- Both migrations are recorded as applied, and nothing else is.
  Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from supabase_migrations.schema_migrations order by version"` →
  ```
  20260917090000 ring_a
  20260917090100 ring_b
  ```

- 30 tables exist across `public` and `pii` — the 26 Ring A tables, `pii.child`, and the 3 Ring B
  tables. Check: `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii')"` → `30`

  The list, with `relrowsecurity` and `relforcerowsecurity`. Check:
  `psql "$DATABASE_URL" -c "select n.nspname as schema, c.relname as table, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') order by 1,2"` →
  ```
   schema |         table         | rls_enabled | rls_forced
  --------+-----------------------+-------------+------------
   pii    | child                 | t           | t
   public | access_log            | t           | t
   public | blueprint             | t           | t
   public | capture               | t           | t
   public | case_dimension        | t           | t
   public | child                 | t           | t
   public | child_skill_state     | t           | t
   public | class_card            | t           | t
   public | config                | t           | t
   public | coverage_target       | t           | t
   public | evidence_event        | t           | t
   public | flow_run              | t           | t
   public | gold                  | t           | t
   public | home_sheet            | t           | t
   public | item                  | t           | t
   public | item_result           | t           | t
   public | item_stat             | t           | t
   public | level_rule            | t           | t
   public | milestone             | t           | t
   public | misconception         | t           | t
   public | narrative_observation | t           | t
   public | parent_note           | t           | t
   public | prescription          | t           | t
   public | prompt                | t           | t
   public | rung                  | t           | t
   public | sheet_instance        | t           | t
   public | sheet_template        | t           | t
   public | skill                 | t           | t
   public | tenant                | t           | t
   public | threshold             | t           | t
  (30 rows)
  ```

- Not one table is missing RLS, and none is missing the forced flag — so the owning role is
  subject to the policies too. Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not (c.relrowsecurity and c.relforcerowsecurity)"` → `0`

- Every one of the 30 tables carries the `service_role_all` policy. Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not exists (select 1 from pg_policies p where p.schemaname=n.nspname and p.tablename=c.relname and p.policyname='service_role_all')"` → `0`

- `tenant` is the only table without a `tenant_id` — it is the tenant. Check:
  `psql "$DATABASE_URL" -Atc "select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not exists (select 1 from information_schema.columns k where k.table_schema=n.nspname and k.table_name=c.relname and k.column_name='tenant_id') order by 1"` →
  ```
  public.tenant
  ```

- `evidence_event` is append-only, enforced by a statement-level trigger, so it refuses the write
  even when no row matches. Check:
  `psql "$DATABASE_URL" -Atc "update evidence_event set correct = true where false"` and the same
  with `delete from evidence_event where false` →
  ```
  ERROR:  evidence_event is append-only: UPDATE is not allowed
  ERROR:  evidence_event is append-only: DELETE is not allowed
  ```

- No foreign key column is left without a covering index — the query returns every FK constraint
  whose columns are not the leading columns of some index, and returns none. Check:
  `psql "$DATABASE_URL" -Atc "select c.conrelid::regclass::text||' ('||c.conname||')' from pg_constraint c where c.contype='f' and c.connamespace in ('public'::regnamespace,'pii'::regnamespace) and not exists (select 1 from pg_index i where i.indrelid=c.conrelid and (string_to_array(i.indkey::text,' ')::smallint[])[1:array_length(c.conkey,1)] @> c.conkey) order by 1"` →
  (no rows)

- No column anywhere is `double precision` or `real`; every measured value is `numeric`
  (`threshold.value` and `flow_run.cost_inr` at `numeric(20,4)`, `p_correct` and
  `read_confidence` at `numeric(5,4)`). Check:
  `psql "$DATABASE_URL" -Atc "select table_schema||'.'||table_name||'.'||column_name||' '||data_type from information_schema.columns where table_schema in ('public','pii') and data_type in ('double precision','real') order by 1"` →
  (no rows)

- Names are reachable only through the logging accessor: `pii.read_child(child_id, actor)` writes
  `access_log` before returning, and `anon` / `authenticated` are revoked from the schema.
  Check: `psql "$DATABASE_URL" -Atc "select proname from pg_proc where pronamespace='pii'::regnamespace"` →
  ```
  read_child
  ```

- Only one prompt version per purpose can be active, enforced by a partial unique index. Check:
  `psql "$DATABASE_URL" -Atc "select indexdef from pg_indexes where tablename='prompt' and indexname='prompt_one_active_idx'"` →
  ```
  CREATE UNIQUE INDEX prompt_one_active_idx ON public.prompt USING btree (tenant_id, purpose) WHERE active
  ```

Empty by design, each with a comment at its definition saying so: `blueprint`, `threshold`,
`config`, `case_dimension`, `coverage_target` (first read by Phase 2), and every operational
table (`child`, `item`, `sheet_*`, `capture`, `item_result`, `evidence_event`, `gold`,
`home_sheet`, `parent_note`, the three Ring B tables). `tenant` and the registry, ladder,
misconception and prompt tables are filled by `engine load`.

## Phase 0 — seeds and loader (complete 2026-09-17)

`engine load --check` fills the hosted project from `supabase/seed/`, checks every code
resolves, then loads again and fails if any count moved.
Check: `cd packages/engine && uv run engine load --check` →
```
  tenant               1
  skill               37
  milestone          162
  rung                16
  level_rule          12
  misconception       27
  case_dimension      18
  coverage_target     46
  prompt               5
  threshold           10
  every code referenced resolves
  unchanged on a second run
```

Test suite: 53 tests, all passing, including the live loader tests against Supabase.
Check: `cd packages/engine && uv run pytest -q` → `53 passed`

Three misconceptions were seeded as `answer_lookup` — a promise that the engine can compute
the number the mistake produces — with no predictor behind them. `test_every_seeded_answer_lookup_code_has_a_predictor`
caught it. Now written: `align_left` (342 + 5 with the 5 under the 3 → 842, the error the
unequal-length blueprint slots exist to catch), `zero_dropped` (495 + 505 → 100), and
`carry_always_one`, which needed its own `MULTI_PREDICTORS` registry because it takes a list of
addends — two operands can never make a column total of 20, so the error is invisible until a
sheet asks for three. Verified live: `7489 + 8845 + 3539 = 19873`, a child always carrying 1
writes `19863`.

## The misconception vocabulary matches an expert's independent diagnosis (2026-09-17)

Aseem's written report on a real Grade 3 child names the error — "subtracts the smaller digit
from the larger digit in each column" — and gives the example `8500 − 3647 = 5147`. The report
was written by hand, months before this engine existed.

`M_SMALL_FROM_LARGE` given those operands returns **5147**. The six other subtraction predictors
return 4852, 4863, 4953, 4863, 5963 and 12147 — so the match is unambiguous, not a coincidence
of a crowded answer space.
Check: `cd packages/engine && uv run python -c "from engine.assess import misconceptions as M; print(M.predict('-', 8500, 3647))"`

This is the strongest evidence so far that marking by lookup produces the same diagnosis a good
teacher reaches, and it is why the five Grade 3 reports become the `gold` set for the whole
pipeline rather than only for digit reading.

Not covered: Aseem's second finding, `56 × 3 = 1518` (partial products written side by side), is
multiplication. Off the ladder, no predictor — the `M_MULT_CONCAT` the Kabir POC proposed.

## Prompt-driven item generation — first measurement (2026-09-17)

The bank generated the way the founder specified: the skill-set spec as plain text (topic,
objective, skill, Hard rule in words, philosophy lines, formats, the eleven seeded subtraction
misconceptions with descriptions), one prompt, no per-topic code; then every number checked by
code. Full reading in `research/2026-09-17-prompt-generation-spike.md`; decision in ADR 0005.
Check: `cd packages/engine && uv run python ../../research/spike_prompt_gen.py 20` →
```
model used: gemini-3.6-flash
model returned 20 items (asked 20)
answers correct:        17/20
constraint met:         20/20  (3-digit, no zero on top, exactly one exchange)
duplicate (a,b) pairs:  0
misconception claims:   89; with a code predictor: 89; matched predictor: 77
formats: {'column': 7, 'missing_number': 7, 'word_1step': 6}
```
The three rejected items were `582 − □ = 236`-shaped: the model wrote the shown difference into
both `b` and `answer`. Its distractors for that item (244, 246, 235, 928) equal the predictors'
output for 582 − 346, so the arithmetic was right on all twenty and the verifier caught the field
error. 77/77 distractors on the seventeen accepted items matched code. A 40-item request timed
out at 120 s on the free tier — batch at ~20. `gemini-3.5-flash` returned 503 then a spurious
404 on this run; the ordered fallback served.

**Status: one call, one topic, one difficulty.** Enough to choose the architecture, not a quality
measurement. The seventeen accepted items seed the `item_generate` eval set.

## W1 — the question bank as engine code (2026-09-17)

Plan: `docs/superpowers/plans/2026-09-17-w1-bank.md`. Design: ARCHITECTURE §7, ADR 0005.

- Migration `20260917120000_skill_set_and_feedback` applied and recorded (the `supabase db push`
  output shows a pg-delta certificate error from a Supabase helper, then finishes; the check is
  what counts). Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from supabase_migrations.schema_migrations order by version"` →
  ```
  20260917090000 ring_a
  20260917090100 ring_b
  20260917120000 skill_set_and_feedback
  ```
  `skill_set` and `item_feedback` exist; `item` has `skill_set_code` and `difficulty`. 32 tables.

- Seeds: four skill sets at Easy/Medium/Hard/Advance (drafts for Neha and Achal), two config
  rows (school philosophy, model fallback list), the `item_generate` prompt.
  Check: `cd packages/engine && uv run engine load --check` → the Phase 0 counts plus
  ```
  prompt               6
  config               2
  skill_set            4
  every code referenced resolves
  unchanged on a second run
  ```

- Tests: 98, including live bank tests that run inside a rolled-back transaction against the
  hosted project. Check: `cd packages/engine && uv run pytest -q` → `98 passed`.

- **The real fill, three runs, each of which taught something now in a test:**
  1. Died on the first batch: the model wrote U+2212 for minus and the schema's enum refused the
     reply. Now `verify.normalise` folds symbols; schema takes any single character.
  2. Eight successful calls, 162k tokens, **zero items stored**: every item carried a claim our
     predictor cannot check ("aligns from the left" on 243 − 27 gives a negative) and an
     off-by-one written +1 where the predictor says −1. Both were verifier strictness, not model
     error — the six candidates inspected by hand all had correct numbers. Now: unverifiable
     claims are dropped and the item survives; "plus-or-minus" codes accept either sign.
  3. `uv run engine bank fill SUB.2D.EXCH Hard --n 200` → 40 items in four batches, ten per
     format, then the free tier rate-limited every model. Check:
     `psql "$DATABASE_URL" -c "select fmt, count(*) from item where source='generated' and status='active' and skill_set_code='SUB.2D.EXCH' group by fmt"` →
     ```
     bare_sum       10
     column_grid    10
     missing_number 10
     word_1step     10
     ```
     A word problem from the bank: "Aarav saved 472 rupees for the mela and spent 38 rupees on
     rides, how many rupees does he have left?"

- Independent audit of everything stored. Check: `uv run engine bank recheck` → `0 mismatches`.

- A sheet from the bank, through the existing renderer unchanged.
  Check: `uv run engine bank sheet SUB.2D.EXCH Hard --n 12 --out data/bank` →
  `CS289D43  2 pages  12 responses  -> data/bank/CS289D43.pdf`. Looked at both pages: QR,
  fiducials, column grids, digit cells, working boxes, key JSON beside it.

- Free-tier numbers to plan around (`flow_run` rows): ~20k tokens and ~95 s per 20-item call;
  the limit closes after roughly four calls in a row; `gemini-2.5-flash` is retired for new
  users (404 with that message). The adapter now waits 5/10/20/40/60 s per model and 60 s on a
  429; a 200-item fill is a background job of ten to fifteen minutes.

- A fourth fill with the patient policy got **no call through in 886 s**: every attempt on all
  three models returned 503 "This model is currently experiencing high demand". That is
  Google's capacity for free-tier traffic at that hour, not our quota. Check: the `flow_run`
  row at 12:27:53 UTC, status `error`, 886 s.

- **The binding limit is 20 requests per day per model** on the free tier
  (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 20, read from the 429 body).
  Tokens are not the constraint; requests are. The adapter now skips a model whose daily quota
  is gone instead of waiting on it. The lever is more items per request, to be measured when
  the quota resets.

- `gemini-3.5-flash-lite` is not a usable fallback: one real call at n=20 returned 20 items and
  the verifier accepted **0** — every item had two exchanges where the rule asks one, and its
  distractor arithmetic was wrong. The verifier earned its keep; the model is out of the list.
  Turning thinking off (`thinkingBudget: 0`) is rejected with 400 on these models; the
  reasoning is what makes the exchange count hold, so it stays on.

- Not yet run: `engine eval item_generate` across all four sets × four bands — it needs sixteen
  calls the free tier will not grant in one sitting. The 40 stored items are the first eval seed.

## Real assessment data received (2026-09-17)

16 children in `~/cornerstone/assessments/` — 11 in G2, 5 in G3, of whom Rudraksh is confirmed
Grade 4 and the only one. 37 usable papers plus 7 Olympiad booklets. Twelve scans carried no name
in the filename and were attributed by reading their printed headers; the manifest records who
each belongs to. Nothing was moved.

Two filename assumptions were wrong and were corrected by looking: in G3 the PDF is Aseem's
report and the WhatsApp images are the papers; in G2 the PDF is the paper and the WhatsApp images
are further pages in a different format. Both directions matter for the importer.

Confirmed by Nimish: Level B is above Level A, so B maps to L+ and A to L0.

## Code

- `engine/db.py` — the only module that opens a connection.
- `engine/loaders.py` — seed JSON to tables, upsert on the natural code, plus `orphans()` for the
  referential checks the schema cannot express (codes live in arrays).
- `engine/cli.py` — `engine load`, `engine load --check`.
- `engine/assess/tags.py` — taxonomy §12 case tags derived from generator parameters.
- macOS python.org build has no CA bundle; the engine venv must include `certifi`.

## Environment

- Docker, Supabase CLI, psql, Node, Python 3.14 present; n8n not installed (Docker);
  `gh` authenticated as nimishshah1989, admin of org `cornerstonepune`.
