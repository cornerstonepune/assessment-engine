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
multiplication. Off the ladder, no predictor — the `M_MULT_CONCAT` the Child A POC proposed.

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

- Fifth fill, with quota skipping: the two exhausted models were passed over at once, the third
  was tried through all five waits and returned 503 "high demand" every time; the run ended in
  226 s with one reason per model. Check: the `flow_run` row at 12:48:23 UTC. **The bank stands
  at 40 verified items until the daily quota resets** (midnight Pacific, about 12:30 IST).

- Not yet run: `engine eval item_generate` across all four sets × four bands — it needs sixteen
  calls the free tier will not grant in one sitting. The 40 stored items are the first eval seed.

## The web app — shell and the W1 screens (2026-09-18)

Plan: `docs/superpowers/plans/2026-09-18-web-shell-and-w1-screens.md`. Brand:
`apps/web/design-system/PRINCIPLES.md`, from the Cornerstone Brand Book Edition 02 (it overrides
the Atlas house language for this product, and says why). Screens published for review:
claude.ai/artifact/D1zoM7ZZX8nSfWswvH2mQR

- Builds clean, no type errors, eight routes.
  Check: `cd apps/web && npm run build` → `✓ Compiled successfully`, routes `/ /_not-found
  /capture /growth /home /library /login /skill-sets/[code] /worksheets`. No Proxy: the
  middleware existed only to refresh a Supabase session and went with it.

- Every screen renders its heading, scrolls sideways nowhere, and logs no console error, at
  1440 px and at 400 px. Check: `cd apps/web && AUTH_DEV_BYPASS=1 npx playwright test` →
  `16 passed (5.4s)`.

- The Skill Map shows the real per-difficulty counts: `SUB.2D.EXCH` reads 80 at Hard and 0
  elsewhere, matching `select count(*) from item where skill_set_code='SUB.2D.EXCH'`.

- **Editing a difficulty in the app writes to the database, through plain fields — no JSON.**
  Verified end to end in the browser: changed the Easy band's words and ticked a second exchange,
  pressed Save, then
  `psql "$DATABASE_URL" -Atc "select difficulty->'Easy' from skill_set where code='SUB.2D.EXCH'"` →
  ```
  {"check": {"op": "-", "digits": [2, 1], "regroups": [1, 2]}, "words": "… EDITED BY TEST."}
  ```
  and `updated_at` moved. The test edit was then restored to the seeded values.

- **Bug found and fixed by that test:** `engine load` used to upsert `skill_set`, so the next
  load would silently overwrite whatever Neha and Achal had authored in the app. The loader is
  now insert-only for that table, with `test_load_does_not_overwrite_a_skill_set_edited_in_the_app`
  as the regression. Engine suite: 101 passing.

- Sign-in is email and password against the staff allowlist in `config.app.staff`, which holds a
  `scrypt$salt$hash` per person; the session is an httpOnly cookie signed with `AUTH_SECRET`
  (HMAC-SHA256, 30 days). Every route in the app group is behind it and both server actions check
  again on their own. A development bypass exists, is refused outside development, and shows a
  "dev bypass" pill in the sidebar when on.
  Check: `cd apps/web && npm run test:gate` → `8 passed`, seven routes redirecting and a wrong
  password refused. `npm run test:screens` → `32 passed`.

  It replaced the magic link on 2026-09-18, after the live site returned `over_email_send_rate_limit`:
  Supabase's built-in mail sender allows two emails an hour, and there is no other sender on the
  project. Check: `curl -s -X POST "$SUPABASE_URL/auth/v1/otp" …` →
  `{"code":429,"error_code":"over_email_send_rate_limit"}`; and the project's auth config reads
  `rate_limit_email_sent = 2`, `smtp_host = None`.
  Check: `curl -s "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/config/auth" -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN"`.

- `SUPABASE_SERVICE_ROLE_KEY` in the repo `.env` does not authenticate — the project rejects it on
  both the auth admin API and PostgREST. Nothing in the engine uses it (data goes through
  `DATABASE_URL`), so it is dead rather than breaking, but it is wrong and should be re-copied or
  deleted. Check: `curl -s -o /dev/null -w "%{http_code}" "$SUPABASE_URL/rest/v1/config?select=key&limit=1" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"` → `401`.

- Not built: the Generate form (needs W2), paper previews (the Python renderer owns those), and
  Capture, Child Growth and Home Assignments beyond their honest empty states, which name the
  workflow that fills them and show the real table counts.

## W2 — the week's papers, and the dashboard tested end to end (2026-09-18)

Migration `20260918100000_prescription_difficulty` applied: a prescription now names a skill set
and a difficulty (the retired `level` stays, nullable), plus `item_exposure` so a child is never
shown the same question twice. Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from
supabase_migrations.schema_migrations order by version"` → four rows ending
`20260918100000 prescription_difficulty`.

- **The real roster is loaded.** 16 children, names in `pii` only.
  Check: `uv run engine week roster ~/cornerstone/assessments/roster.json` → `added 16`.

- **The week is prescribed with a reason per child.**
  Check: `uv run engine week prescribe G3 T2W1 --set SUB.2D.EXCH` →
  ```
  1   G3  Medium   not enough of their own work yet, so this is the starting level for their grade
  …
  5   G4  Hard     not enough of their own work yet, so this is the starting level for their grade
  1 at Hard · 4 at Medium
  ```
  Rudraksh is banded G4 and is the only child at Hard, from rows, not a special case in code.

- **The pack builds.** Check: `uv run engine week assemble G3 T2W1 --actor nimish` →
  `5 named · 4 spare · 17 pages`, at `data/packs/G3-T2W1-practice/T2W1_pack.pdf`. Looked at two
  pages: each child's own name, their own QR, Medium is 2-digit and Hard is 3-digit.

- **No two children share a question.** Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from sheet_template a join sheet_template b on a.id < b.id and a.item_ids && b.item_ids where a.week='T2W1' and b.week='T2W1' and a.child_id is not null and b.child_id is not null"` → `0`

- **The offline fallback works**, which is the only reason the pack exists today — the free tier's
  20 requests per model were spent. Check: `uv run engine bank fill SUB.2D.EXCH Medium --n 120
  --offline` → `accepted 120, rejected 0`, through the same verifier as the model path.

- **Bug found and fixed:** `bank recheck` compared missing-number questions against whole-equation
  predictors and wrongly flagged 30 of them. It now rebuilds each item through the same
  `verify.to_item` that made it, so the audit cannot drift from generation. Two regression tests,
  one of which edits a stored answer behind the engine's back and expects it caught.
  Check: `uv run engine bank recheck` → `0 mismatches` over the whole live bank.

- **Engine: 114 tests.** Check: `cd packages/engine && uv run pytest -q` → all pass.

- **The dashboard, driven end to end in a browser against the real database: 40 tests, two passes.**
  Check: `cd apps/web && npm run test:e2e` → `32 passed` then `8 passed`. Every action is asserted
  in the database, not just on screen: editing a difficulty changes the stored rule; a difficulty
  with no exchange ticked saves nothing; ratifying records who; removing a question writes the
  flag and the trigger retires it; changing a child's level stores the reason; approving marks the
  papers printed. The second pass runs with the sign-in bypass **off** and proves all seven routes
  redirect to sign-in — a gate only ever tested with the bypass on is not tested.

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

## N3 — legacy import and Child Growth, as a teacher reads it (2026-09-18)

Migration `20260918130000_graph_functions` applied: the six-state graph rule is SQL
(`rebuild_child_skill_state`, `next_difficulty`, `confirm_results`, `resolve_result`), so the CLI
and the app run one rule. Thresholds are rows (`state.min_events` 3, `state.min_observers` 2,
`next_sheet.promote_at` 0.8, `next_sheet.demote_below` 0.5).

- **Four Grade 2 children have ladders built from confirmed evidence.** Check:
  `psql "$DATABASE_URL" -Atc "select count(*), count(distinct child_id) from evidence_event where confirmed_by is not null"`
  → `218|4`. Blank answers carry `correct = null` and never count as attempts (rule 5):
  `select status, correct, count(*) from evidence_event e join item_result r on r.id = e.item_result_id group by 1,2`
  → `blank||7`, `correct|t|178`, `wrong|f|33`.

- **A rung can carry two skills and keeps a state per skill.** R9 (3-digit ±) holds Addition and
  Subtraction separately; for one child they differ (`stretch_ready` / `patterned_error`, mistake
  `M_FACT_PM10`). Check: `select child_id, rung_code, skill_code, state from child_skill_state
  where rung_code = 'R9'` → six rows, two per child.

- **`/growth/[id]` is one lane per skill, in the school's words, with the answers behind each
  step.** Names come from `rung.descriptor`, `skill.name`, `skill_set.name` and
  `misconception.name`; no code reaches the page. Check: `cd apps/web && AUTH_DEV_BYPASS=1 npx
  playwright test --project=screens` → `17 passed (8.1s)`, including *a child's ladder is in
  words, with the answers behind each rung*, which asserts no `R\d`, `X\d`, `M_…` or
  `AAA.BBB.CCC` token appears in the ladder and that clicking a step reveals a table with a
  *Child wrote* column. No sideways scroll at 400 px on `/growth` or a child page.

- **The double-import fault above is fixed, not just described.** `engine legacy dedupe` (chunk 1
  of `docs/superpowers/plans/2026-09-18-spine.md`) backfilled every capture's content hash and
  superseded every live capture but the best one per (sheet, file) pair, never deleting a row
  (rule 4). Check: `uv run engine legacy dedupe` → `28 captures given a content hash, 16
  superseded`; then `uv run engine graph` → `26 states`; then
  `psql -Atc "select count(*) from evidence_event e join item_result r on r.id=e.item_result_id
  join capture c on c.id=r.capture_id where c.superseded_by is null and e.confirmed_by is not
  null"` → `133` (was 218); and `select si.child_id, t.key->>'title', count(*) from capture c
  join sheet_instance si on si.id=c.sheet_instance_id join sheet_template t on t.id=si.sheet_template_id
  where c.superseded_by is null and exists (select 1 from item_result r where r.capture_id=c.id)
  group by 1,2 having count(*)>1` → zero rows. `import_scan` is idempotent on the file's content
  going forward (`file_sha256`, a partial unique index), so this cannot recur by re-running the
  same command twice.

## N3.1 — the spine, chunk 1: idempotent capture, Haiku reads, a budget the adapter refuses past (2026-09-19)

Plan: `docs/superpowers/plans/2026-09-18-spine.md`. ADR 0007 (learning loop), 0008 (engine as a
service; n8n moves to F3 now, not N7), 0009 (subject plugins). Migration
`20260919090000_service_foundations`: `capture.file_sha256`/`superseded_by`, `flow_run.model`/
`tokens_in`/`tokens_out`/`idempotency_key`/`request`, `prompt.subject`, and three new tables —
`subject`, `read_correction`, `child_reading_profile`. `rebuild_child_skill_state` and
`confirm_results` re-defined to read only live (non-superseded) captures.

- **The three active read prompts run on Haiku, not Sonnet** — the $10 burn's cause (HANDOFF.md,
  earlier session). Check: `psql -Atc "select purpose, model from prompt where active and purpose
  in ('read_cells','read_page','legacy_extract')"` → all three `claude-haiku-4-5`.

- **The adapter refuses a call before it is made once today's spend reaches the
  `llm.daily_budget_inr` threshold row (₹150 default), and prefers a subject-scoped prompt row
  over the shared one for the same purpose.** Check: `cd packages/engine && uv run pytest -q
  tests/test_llm.py` → `20 passed`, including a budget-refusal test that asserts zero `flow_run`
  rows are written for a refusal, and a real-database test of the subject-selection SQL itself.

- **A PDF renders in-process; `pdftoppm` is gone.** The September batch's transient subprocess
  failures (13 of 28 captures once held `status = 'error'`) cannot recur because there is no
  subprocess. Check: `uv run pytest -q tests/test_render_pdf.py` → `2 passed`; every previously
  `error` capture now renders and reads under `engine legacy import` (or, more precisely,
  already-imported ones are superseded correctly by `engine legacy dedupe` above).

- **`engine load` is unchanged in kind, larger by one table.** Check: `uv run engine load --check`
  → 13 rows printed including `subject 1`, `threshold 12`, `config 7`, `every code referenced
  resolves`, `unchanged on a second run`.

- **Full engine suite, including everything above.** Check: `cd packages/engine && uv run pytest -q`
  → `146 passed`.

- **Not yet built** (chunks 3–7 of the same plan): n8n is not installed; `read_correction` and
  `child_reading_profile` are empty tables, waiting on chunk 3's settle-flow write and chunk 6's
  rebuild; `engine/subjects/` does not exist yet — `subject.verifier = 'maths'` names a module chunk
  5 has not written; `/prescribe` `/assemble` `/render` are deliberately not built (below).

## N3.2 — the spine, chunk 2: the engine as a service (2026-09-19)

Plan: `docs/superpowers/plans/2026-09-18-spine.md` (chunk 2's own section there records two
deliberate departures from its original text and everything below in more detail). ADR 0008.
`packages/engine/engine/api/`: `app.py`, `deps.py`, `idempotency.py`, `models.py`,
`routes/{capture,children,graph,bank,runs}.py`. Migration `20260920090000_flow_run_result.sql`
(`flow_run.result jsonb`). `Dockerfile`, `.dockerignore`, `deploy/compose.yml`.

- **Every route sits behind `X-Engine-Key`, and an unconfigured key refuses everything rather
  than accepting anything.** Check: `cd packages/engine && uv run pytest -q tests/api/test_deps.py`
  → `6 passed`, including the case where `ENGINE_KEY` itself is unset or empty (500, not a silent
  401-that-could-have-been-200).

- **`run_idempotent` runs a route's function at most once per (tenant, flow, key); a call still
  `running` (a genuine concurrent duplicate) is refused, never double-run; a call that previously
  failed is retried, not permanently stuck.** Tested against the real partial unique index
  (`flow_run_idempotency_idx`), not a fake connection — a fake cannot reproduce
  `ON CONFLICT … WHERE … DO NOTHING`'s actual semantics. Check: `uv run pytest -q
  tests/api/test_idempotency.py` → `8 passed`. The `InProgress` exception is also proven to reach
  an HTTP caller as a 409, not an unhandled 500 — a distinct claim from "the Python exception is
  raised", caught only because both were tested (`test_capture_routes.py::…already_in_flight…`).

- **Verified for real, against the deployed container and the real database, not only in
  pytest.** `docker compose -f deploy/compose.yml build engine` → built; the running container's
  own `/health` → `{"ok": true}`, Docker's healthcheck → `healthy`; `POST /graph/rebuild` with the
  real `X-Engine-Key` → `{"states": 26, "already": false}` and a `flow_run` row with `flow =
  'graph_rebuild', trigger = 'http', status = 'ok'`; the same call repeated with the same
  `Idempotency-Key` → `{"states": 26, "already": true}`, and exactly one `flow_run` row exists for
  that key, not two.

- **A real bug this verification caught, that no unit test could have:** `db.py`'s `REPO_ROOT =
  Path(__file__).resolve().parents[3]` assumed the monorepo's directory depth and raised
  `IndexError` at import time inside the container, where the Dockerfile copies only `engine/`
  (`/app/engine/db.py` has nothing four levels above it) — every route imports `engine.db`
  transitively, so the whole process died before serving a request. Fixed (`_repo_root_for`, a
  pure function now unit-tested — `uv run pytest -q tests/test_db.py` → `3 passed`) and only found
  because chunk 2's own criteria insisted on a real `docker build` + a real container, not a mock.

- **`bank.fill` is not naturally idempotent** (unlike `import_scan`, chunk 1) — a fresh model call
  returns different items each time, so a retried `/bank/fill` HTTP call without the wrapper would
  silently double-spend model tokens. Check: `uv run pytest -q tests/api/test_bank_routes.py` →
  `5 passed`, including a test that a retried call asks the model exactly once.

- **Full API and engine suites.** Check: `cd packages/engine && uv run pytest -q tests/api` →
  `41 passed`; `uv run pytest -q` (the whole engine suite) → `182` collected, all green.

- **Deferred, not built: `/prescribe`, `/assemble`, `/render`.** They need an answer to "where
  does a rendered PDF live when the engine runs in a container" that nothing in chunks 1–4 needs
  yet (F3 read-and-respond never calls them) — building them without that answer is how a route
  ships with the wrong assumption baked into its shape. A later chunk states the storage answer
  first (a volume, or served back as bytes) and builds them against it.

- **Environment note, not a code defect:** this machine's Docker Desktop credential helper
  (`credsStore: "desktop"`) hangs indefinitely on a registry pull from a non-interactive session —
  it waits on a Keychain-mediated lookup with no UI to approve it. Worked around per-session via
  `DOCKER_CONFIG`/`DOCKER_HOST` pointed at a credential-helper-free config and the real socket
  (`~/.docker/run/docker.sock`); the user's own interactive terminal is unaffected. Recorded in
  case a future session hits the same silent hang and burns time on the wrong theory (network
  block) before checking `docker pull` directly.

## W1 gate 1 — every rung has a ratifiable skill-set spec (2026-09-19)

Nimish gave the yes on `BUILD-ORDER.md`'s six W1 gates in chat on 2026-09-19, including the
50-per-unit number and ADR 0010's design, clearing the block `HANDOFF.md` had recorded. Gate 1
scope: draft the 12 missing skill-set specs — R1–R4, R7, R8, R11–R14, X1, X2 — as rows in
`supabase/seed/skill_sets.json`, each with name, learning objective, philosophy, formats,
misconception codes, and a words rule plus a checkable rule for Easy/Medium/Hard/Advance.

- **All 16 rungs now have a skill-set row; the four already-drafted ones (R5, R6, R9, R10) are
  untouched.** For R7, R11, R13, X1 and X2 — where the substantive claim (mental strategy,
  rounding reasoning, "most efficient" method, an explanation, a diagnosis) is not something code
  can check — the row says so in its `philosophy` and names the validator route (a template-level
  check plus a ≤5 % item sample, never a per-item model call), per ADR 0009 and ADR 0010, rather
  than inventing a code verifier for it. Every `check` block still states what code *can* verify
  (the numeric or tick answer). All 16 rows load at `status = 'draft'`, awaiting Neha's and
  Achal's correction and Aseem's ratification (N1) — not yet ratified, so gate 1's fuller text
  ("every row `ratified`") is open; the count gate itself is closed.

  Check (the gate exactly as stated): `psql "$DATABASE_URL" -Atc "select count(*) from rung r
  where not exists (select 1 from skill_set s where s.rung_code = r.code)"` → `0`.

- **The loader accepts all 16 rows with no orphaned reference.** Every `misconception_codes` entry
  across the 12 new rows was checked by hand against `misconceptions.json` before writing, since
  `skill_set` is insert-only (Neha's and Achal's edits must never be overwritten) and a bad code
  would otherwise sit silently orphaned. Check: `cd packages/engine && uv run engine load --check`
  → `skill_set 16`, `every code referenced resolves`, `unchanged on a second run`.

- **A real regression this caught:** `tests/test_loaders.py`'s `EXPECTED` dict hardcoded
  `"skill_set": 4`; `test_every_table_has_the_expected_number_of_rows` would have failed the
  moment the loader ran with 16 rows in the seed. Fixed to `16` — the only code change gate 1
  needed. Check: `cd packages/engine && uv run pytest -q` → 186 passed, 0 failed (up from the
  182 recorded at N3.2; no other test assumed a skill_set count).

- **Not done:** gate 1's own fuller sentence — "every row `ratified`" — needs Neha and Achal to
  correct the 12 drafts and Aseem to ratify all 16, in the app; that is a human step, not a
  command. Gates 2–6 (the enumerator itself, the any-topic proof, per-template validation, the n8n
  flow, and the cost figure) are untouched, per `BUILD-ORDER.md` rule 1.

## W1 gate 2, chunk A — the arithmetic enumerator, zero model spend (2026-09-19)

Nimish chose "chunk A first" when gate 2 turned out to be two differently-sized jobs: (a) the
+/- units, which already had a working offline sampler ("the coin slot already exists"), needed
only a fix for a rung that mixes both operations; (b) 8 new question shapes (mental strategies,
word problems, budget, estimation, "most efficient method", explain, find-the-mistake) that need
their own generator wiring plus the sentence-template feature ADR 0010 promises — not built at
all yet. Chunk A is (a) only; (b) is deliberately not started.

- **A real, dangerous bug the new rungs exposed, fixed before it could fire:** `bank._sampled`
  silently fell back to rendering plain column arithmetic whenever a skill set's `formats` didn't
  overlap the sampler's four known shapes — which never happened with the original 4 skill sets
  (their formats always did overlap) but would have on R11 or X2 the moment anyone ran
  `--offline` on them: an "estimate first" or "find the mistake" unit would have silently filled
  with ordinary sums. It now refuses with a clear error instead. Check:
  `cd packages/engine && uv run pytest -q tests/test_bank.py -k sampled` → 2 passed (op-list
  candidates come back as real "+"/"-" pairs; a formats list with no sampler match raises).

- **`_sampled` and `verify.problems` accept `check.op` as a list**, needed because ADR 0010's own
  rungs are one skill_set per rung, not one per operation — R4 (2-digit ± without regrouping)
  mixes + and − in a single unit. Check: `uv run pytest -q tests/test_verify.py -k op_list` →
  2 passed.

- **`engine bank coverage`** (`bank.coverage()` + the CLI command gate 2 names) prints every one
  of the 64 skill_set x difficulty cells, zero cells included — the number gate 2's own text asks
  for, not a description. Check: `cd packages/engine && uv run engine bank coverage` → 64 units
  printed, 39 under 50 (the exact table is below).

- **25 of the 32 arithmetic-shaped units (the ones whose `check` is a plain op/digits/regroups
  rule reachable by the sampler) now hold >=50 active items, filled by
  `engine bank fill <code> <difficulty> --offline --n 50` — zero model calls. 7 fell short.**
  Check: `psql "$DATABASE_URL" -Atc "select coalesce(sum(cost_inr),0), count(*) from flow_run
  where flow = 'bank_fill' and created_at > now() - interval '20 minutes'"` → `0|0` — no flow_run
  row exists for this run because `--offline` never calls the model, a stronger proof than a cost
  of zero. Then `uv run engine bank recheck` → `0 mismatches` over the whole bank, old and new.
  Full table (Advance columns marked "native" were never attempted this chunk — R1's and R2's
  Advance bands use `missing_number`/`number_line_jumps` with no `digits`/`op` key, correctly
  routed to chunk B, not a shortfall):

  ```
  ADD.1D.WITHIN10   Easy 16  Medium 42  Hard  6                    — all three short
  ADD.1D.BRIDGE10   Easy 38  Medium 43  Hard  1   Advance  native  — all three attempted, short
  SUB.1D.WITHIN20   Easy 50  Medium 50  Hard 50   Advance 46       — one short
  ADD.2D.REG / SUB.2D.EXCH / ADD.3D.REG / SUB.3D.ZERO / ADDSUB.2D.NOREG: every band >=50
  ADDSUB.4D.ADV: Hard 50, Advance 50 (Easy/Medium are multi_add — native, chunk B, not attempted)
  ```

- **Two different causes behind the 7 short bands, both spec problems, not enumerator bugs:**
  (1) `ADD.1D.WITHIN10` Easy's own ceiling is only 16: at "sums to 5, both addends 1-9, no repeat
  digit" there are exactly 8 distinct (a, b) pairs, times the 2 formats the row declares
  (bare_sum, missing_number) = 16 — 16 is not a partial run, it is every item that rule can ever
  produce; Medium's ceiling is likewise well under 50. (2) `ADD.1D.WITHIN10` Medium/Hard and
  `ADD.1D.BRIDGE10` Medium/Hard share an *identical* effective rule (an unused `allow_zero_addend`
  flag doesn't change what the sampler draws), so the two bands compete for the same pool and
  whichever filled first — Medium, both times — took most of it, starving Hard (6 and 1). Item
  identity is the (template, a, b, op) tuple, not the skill_set/difficulty asking for it, so a
  pair generated under one band can never be generated again under a sibling. Neha, Achal and
  Aseem need to widen R1's number range (not just its band signatures) and give R1/R2's Medium and
  Hard bands genuinely distinct rules during ratification — a wording fix, not a code fix.

  `SUB.2D.EXCH` Medium/Hard now read 159/130 — the old per-item model path's rows (120/80, from
  the Sep 17 session, STATE.md above) plus this run's new enumerator items on top; the two paths
  cannot collide because they insert through the same dedup constraint.

- **A real regression this run caused, found by the full suite, fixed the same session:**
  `test_it_says_which_child_it_could_not_fill_rather_than_printing_a_short_paper` asserted
  `SUB.2D.EXCH` Advance was empty — true when the test was written, false now that chunk A filled
  every SUB.2D.EXCH band. Fixed by having the test retire those items inside its own rolled-back
  transaction rather than relying on a part of the shared bank staying empty forever. Check:
  `cd packages/engine && uv run pytest -q` → 191 passed, 0 failed (up from 186 at gate 1).

## W1 gate 2, chunk B — the native-generator units, still zero model spend (2026-09-19)

Nimish said "finish that" for chunk B. It split further once the code was actually read: 8 of the
9 remaining rungs (R1/R2's Advance bands, R7, R8, R11, R12's Easy/Medium, R13, R14, X2) already
had a hand-written generator function in `assess/items.py` needing only to be wired to a
skill_set row; X1 does not — its generator can only ever write one fixed, always-true claim about
two specific numbers, which ADR 0010 itself names as the reason explain-a-claim stays on the
per-item model path. X1 is therefore genuinely not part of this chunk's zero-cost story; it is
still 0 of 4 bands, honestly, not force-fit.

- **`bank.fill_native` (`engine bank fill <code> <difficulty> --native`) dispatches nine formats
  to their existing `assess/items.py` generator by `check['format']`, no model call, no
  verify.problems detour** (these generators are trusted code, the same guarantee the arithmetic
  sampler gets from its own round trip through `check`). Check:
  `cd packages/engine && uv run pytest -q tests/test_bank.py -k fill_native` → 27 passed.

- **Three real bugs found and fixed before they could ship, each with its own test:**
  1. `number_line_jumps(hi=20)` (tried for R2's Advance band) computed an impossible random
     range and crashed with a raw Python `ValueError` — its second jump is hard-coded to an
     11-39 two-digit number, a different scale than R2's "within 20." It now refuses clearly
     (`RuntimeError: … needs hi >= 54 …`) instead of crashing obscurely; R2 Advance stays
     unfilled rather than fed a nonsensical hi. Not a rewrite of the generator's number range —
     that would be inventing pedagogical content that is Aseem's call, not mine.
  2. `efficient_method` and `find_mistake` ignored the very parameter (`kind`, `digits`) that
     distinguishes STRATEGY.EFFICIENT's and REASON.FIND_MISTAKE's own difficulty bands — every
     band would have drawn from the same mixed pool. Both now take an optional parameter
     (default preserves the old random-choice behaviour for any other caller). Check:
     `uv run pytest -q tests/test_items.py -k "efficient_method or find_mistake"` → 6 passed.
  3. `fill_native`'s RNG was seeded from `(code, difficulty, attempt_number)` alone, so a second
     call for the same unit retraced the exact same sequence from attempt 1 — it could never top
     up a unit, only rediscover what a previous call had already inserted (this is what my own
     first test run collided with, against the real bank chunk B-1 had just filled). Fixed to a
     real per-call RNG. Check: `uv run pytest -q tests/test_bank.py -k produces_no_flow_run_row`
     plus the full `fill_native` suite above, both green against the real, now-fuller bank.

- **22 of the 23 units reachable this way, plus all 4 of REASON.FIND_MISTAKE (X2, filled
  separately after its `check` needed a `format`/`digits` fix — see below), now hold >=50 active
  items — 0₹ model spend for all of it.** Check: `psql "$DATABASE_URL" -Atc "select
  coalesce(sum(cost_inr),0), count(*) from flow_run where created_at > now() - interval '30
  minutes'"` → `0|0` — no flow_run row exists for any of chunk B's fills. Then
  `uv run engine bank recheck` → `0 mismatches` over the whole bank, chunk A and B and the
  original 4 together.

- **`ESTIMATE.ROUND10`, `ADDSUB.4D.ADV` (its multi-addend Easy/Medium bands) and
  `STRATEGY.EFFICIENT`'s `check` blocks needed a `format` key added** (they had `op`/`digits`/
  `kind` but nothing saying which generator to use — `_sampled`'s empty-intersection guard from
  chunk A would otherwise have refused them, correctly, rather than guess). `REASON.FIND_MISTAKE`
  needed the same plus its new `digits` key. Since none of these four rows had any items yet and
  `skill_set` is insert-only, the rows were deleted and `engine load` re-inserted the corrected
  version — the seed file stays the single source of truth. Check: `cd packages/engine && uv run
  engine load --check` → `skill_set 16`, `every code referenced resolves`.

- **`engine bank coverage` now reads 50 of 64 units at >=50 — 14 short.** Full remaining list:
  `ADD.1D.WITHIN10` (16, 42, 6, 24 — its own tiny "sums to 10" ceiling, not a bug, see chunk A),
  `ADD.1D.BRIDGE10` (38, 43, 1, and Advance still 0 — `number_line_jumps` needs a proper
  small-range generator, not built), `MENTAL.BRIDGE_EQ` Hard (48, one short of its own ceiling),
  `SUB.1D.WITHIN20` Advance (46, one short), and `REASON.EXPLAIN` (X1, all four bands still 0 —
  needs either new claim-template content or the real per-item model path, whichever Nimish
  chooses; not started).

- **Full engine suite: 227 passed, 0 failed** (up from 191 at gate 1, and including a fix to
  `tests/test_bank.py::test_coverage_…` whose "this cell is always empty" fixture cell was itself
  a casualty of chunk B filling `ADD.1D.WITHIN10` Advance).

## W1 gate 2, chunk C — closing out: 57 of 64, and the seven that arithmetic forbids (2026-09-19)

Nimish: "finish this and finalize so that we can move to the next workflow." Everything that
could be closed by engineering is closed. Seven units cannot be, for a reason no amount of code
changes, and that needs one decision from him (below).

- **X1 (`REASON.EXPLAIN`) is no longer stuck at zero: all four bands hold 50.** `explain_claim`
  had exactly one hardcoded claim (always true, always a 120-480 compensation pair). It now takes
  `a_range`, `claim_is_true` and `claim_topic`, giving it the four shapes its bands actually ask
  for — a true compensation claim, the same at 2-digit scale, a *false* claim the child must
  catch, and a claim about regrouping itself. Defaults reproduce the old behaviour exactly, which
  `blueprints.py`'s three callers depend on. Check: `uv run pytest -q tests/test_items.py -k
  explain_claim` → 5 passed, including that the true and false variants are distinct items.
  This keeps X1 on the zero-cost template path rather than the per-item model path ADR 0010
  allowed for it — the claim wording is a template with number slots, which is exactly what that
  ADR asks the model to write once; here it is written once in code instead, for ₹0.

- **R2's Advance band (`number_line_jumps` at hi=20) now works** — a `_bridge_jump` path draws
  the jump that crosses one ten (the strategy that rung teaches) instead of the 11-39 two-digit
  jump the full-scale version uses, which is what made hi=20 impossible before. Below hi=12 it
  still refuses with a sentence rather than a raw `randrange` error. Check:
  `uv run pytest -q tests/test_items.py -k number_line` → 3 passed (the small-range jump always
  lands on a ten and stays in range; the full-scale split is unchanged).

- **A band can now pin itself to one format** (`check.format` on the arithmetic path, mirroring
  what the native path already did). This is what stopped R1's and R2's Medium and Hard bands
  competing for one pool of sums: Medium is now the bare sum, Hard the same sums told as a story.
  Together with the seeding fix, this moved `ADD.1D.BRIDGE10` Easy 38 → 75, its Hard 1 → 45,
  `ADD.1D.WITHIN10` Hard 6 → 30, and `SUB.1D.WITHIN20` Advance 46 → 68.

- **`MENTAL.BRIDGE_EQ` Hard reached 50** by raising its balance-scale ceiling from 100 to 150:
  `balance_scale` draws its terms in tens below hi/2, so hi=100 allowed only {10,20,30,40} and
  capped the unit at exactly 48. A number in a draft row, not a code change.

- **Where gate 2 now stands: 57 of 64 units at >=50.** Check: `uv run engine bank coverage` →
  `64 units, 7 under 50`; `uv run engine bank recheck` → `0 mismatches`;
  `cd packages/engine && uv run pytest -q` → 235 passed, 0 failed.

- **The seven that could not reach 50 are capped by arithmetic, not engineering — and Nimish
  amended the gate rather than the ladder (ADR 0011).** "Adds within 10" has about 40 usable
  (a, b) pairs in total; four bands each wanting 50 distinct items need 200, which the numbers
  cannot supply however the code is written. The target is now "50, or the unit's whole
  enumerable universe, whichever is smaller", with the floor written as `min_items` on the band's
  own row so the gate stays one machine-checkable command. He rejected widening R1/R2's ranges
  (that redefines what the rung teaches — Aseem's call) and re-identifying word problems by their
  story (honest, but rewrites the key of every stored word problem and needs a migration).

- **Each floor was measured, not assumed.** A fill against each of the seven was re-run and
  accepted zero new items — the evidence that the count is the ceiling of what the rule can ever
  produce, not the point a run stopped at. Check: the run's output, `new=0` on six and `new=1` on
  the seventh (`ADD.1D.BRIDGE10` Hard, 45 → 46). Floors recorded: `ADD.1D.WITHIN10` 24/42/30/24,
  `ADD.1D.BRIDGE10` 43/46/35. ADR 0011 requires this evidence before any future floor is written,
  so the rule cannot decay into "the bar is whatever we got".

- **W1 GATE 2 IS CLOSED.** Check: `cd packages/engine && uv run engine bank coverage` →
  `64 units, 0 under their target`; `uv run engine bank recheck` → `0 mismatches`;
  `uv run pytest -q` → 236 passed, 0 failed.

- **Gate 6 is already satisfied, well inside its bar: the whole bank cost ₹0.** Check:
  `psql "$DATABASE_URL" -Atc "select coalesce(sum(cost_inr),0), count(*) from flow_run"` → `0|62`,
  against 3,373 live questions (`select count(*) from item where status='active' and
  skill_set_code is not null`). The bar was ₹50 for the whole 64-unit bank; every item in it was
  enumerated by code. The only model spend this design ever calls for is template judging
  (gate 4), which has not been run yet.

## W1 gate 3 — a new topic added as rows: multiplication (2026-09-19)

`BUILD-ORDER.md` names multiplication as this gate's own test case. `NUM.OPS.03 Multiplication &
times tables` already existed in the registry, so the topic needed a rung row, a skill-set row,
and the one sampler ADR 0010 prices in per *operation* (not per topic).

- **What the new topic actually cost in code**, against the gate's hope of "only `verify.py`,
  if anything": `verify.py` needed **nothing** — `problems()` reads the op generically,
  `REGROUPS` has no `×` so the regroup rule is skipped, and `_template` already emitted `MUL.*`.
  What it did need: `sample_mul` (~18 lines) and a `CONTEXTS_MUL` story list in
  `assess/items.py`, and a two-line `elif op == "×"` in `bank._sampled`. Everything else —
  the rung, the skill set, all four difficulty rules — is rows. A *second* multiplication topic
  now costs rows alone, which is what the gate is really testing.

- **A silent-corruption bug caught before it could fire.** `word_1step` picks a story first and
  then samples numbers in an if-plus/else-minus branch, so a `×` story added to `CONTEXTS_1STEP`
  would have been handed *subtraction* numbers — a multiplication word problem with a
  subtraction answer, which nothing downstream would have flagged. The `×` stories live in their
  own `CONTEXTS_MUL` list instead, and the word-problem path now raises a sentence naming the
  missing story list rather than an `IndexError` from inside `random.choice`.

- **All four multiplication bands hold 50 items, zero model spend.** Check:
  `uv run engine bank fill MUL.1D <band> --offline --n 50` → `accepted 50` ×4; a sample reads
  `59 × 8 = 472`, `12 × 7 = 84`, and "A shelf holds 84 books. How many books are there on 31
  shelves?" (2604). Then `uv run engine bank recheck` → `0 mismatches`, and
  `uv run engine bank coverage` → `68 units, 0 under their target`. Suite: 240 passed.

- **Known thinness, stated not hidden:** multiplication has no misconception predictors yet, so
  its items carry no wrong-answer diagnosis — `M.predict("×", …)` returns `{}` and the verifier
  drops unverifiable claims by design. `tags.derive` also returns early for any op that is not
  `+`/`-`, so × items carry the format-level tags but none of the regrouping dimensions. Both
  are additions for whenever multiplication is actually taught, not blockers for this gate.

- **Debt taken on knowingly, recorded not hidden:** `assess/items.py` is now over the 400-line
  limit aislop enforces (it gained six generators' worth of parameters and the bridge jump).
  Splitting it touches every import of `I.*` across the engine; not done mid-task, and it is the
  first thing to clean up before more generators land there.

## The whole skill map, and what kind of thing each question is (2026-09-19)

Nimish, after finding the registry held 37 of 244 skills: "Stop doing incomplete work. If you
are loading a table and if you are making the backend, build the whole thing for now with all
the information that we have." And: every question should carry a classification, with the
evaluation triggered off it.

- **The registry now holds the whole map, not the maths slice.** `supabase/seed/registry.json`
  is generated from the Skill Map Review artifact (built 2026-09-15) and never hand-edited.
  Migration `20260921090000_full_registry`. Check: `cd packages/engine && uv run engine load
  --check` →
  ```
  domain 14 · skill 244 · milestone 849 · learning_objective 1750 ·
  learning_objective_skill 2012 · activity 2216 · activity_skill 3711 ·
  report_item 885 · trait 56
  every code referenced resolves · unchanged on a second run
  ```
  Those counts match the source's own `counts` block exactly. `registry-num.json` is deleted —
  two sources of truth for the registry is how a third of a map got loaded in the first place.

- **Four kinds of material that had nowhere to live before, now tables**: the school's own
  learning objectives (with the same five-word `signal` vocabulary our items use), its activity
  plans (each with the teachers' own three-level mastery descriptors, `level_1/2/3`), its
  report-card lines, and the trait/pillar framework. `skill` also gained `skill_type`
  (`academic` 127 / `non_academic` 94 / `trait_behaviour` 23), `pillar`, `ncf`, `cg`.
  `skill_type` is load-bearing: a trait or value-education skill must never be handed to the
  question bank and auto-scored — the council review is explicit that scoring honesty is the
  kind of measurement the school's founding principle rejects.

- **A performance bug I introduced and fixed in the same pass:** the first full load took
  **2 min 46 s** — 11,000 single inserts, each a round trip to a remote database, and the test
  suite loads three times. Rewritten with `executemany`: **13 seconds for two full loads**
  (`engine load --check` runs it twice), same output, still idempotent.

- **Every question now says what kind of thing it is, and marking dispatches on that**
  (ADR 0012, migration `20260921093000_eval_type`). A Postgres enum with four values —
  `computable`, `closed_set`, `rule_governed`, `open_response` — declared on the skill set as a
  row and stamped onto each item at generation. `assess/evaluate.judge()` routes to the
  evaluator. Only two are built; `closed_set` and `rule_governed` raise rather than fall through
  to the arithmetic evaluator, because a question the engine cannot judge must never be quietly
  marked. Check: `uv run pytest -q tests/test_evaluate.py` → 9 passed, including that an unbuilt
  kind refuses and that an unrecognised wrong answer stays `wrong` with no diagnosis rather than
  being forced into the nearest known mistake.

- **Current split, from the database rather than from intent:** 14 skill sets `computable`
  (3,040 items), 3 `open_response` (600 items — explain-a-claim, find-the-mistake and
  choose-the-efficient-method, the three that ask for a sentence as well as a number). The three
  were identified by querying which items actually carry a free-text response, not by guessing.
  Check: `select eval_type, count(*) from item where status='active' group by 1`.

- **Suite: 249 passed, 0 failed; `engine bank recheck` → 0 mismatches.**

## W1 gates 4 and 5 — the reviewers, versioning, dimensional difficulty, and F1 in n8n (2026-09-19)

Nimish read an external "Assessment Engine — Technical Architecture" proposal and asked for three
of its points to be folded into gate 4 before n8n hardened anything: two narrow reviewers instead
of one blended validator (§8.2/8.3), difficulty as measured dimensions rather than a label (§7),
and immutable versioning with provenance (§15). All three are in, written into `BUILD-ORDER.md`
first (rule 5).

- **Two advisory reviewers, each a prompt row.** `pedagogy_review` (does this test the claimed
  skill, rung and signal?) and `language_review` (can a child of this grade read it?). Each judges
  the band's *rule* once plus a ≤5 % sample of its items — ADR 0010's economics, applied to
  review. Verdicts land in `item_review` with `acted_on_by` null: advice until a person acts.
  Check: `uv run pytest -q tests/test_review.py` → 6 passed, including that a reject never
  retires anything and that reviewing every item (the cost enumeration removed) is refused.

- **Scored against a hand-judged gold set, and the first real money spent.** Check:
  `uv run engine eval language_review` → `agreed 6/6 = 1.0 · right reason 6/6 · ₹0.1855`;
  `uv run engine eval pedagogy_review` → `agreed 5/6 = 0.83 · right reason 5/6 · ₹0.3815`.
  The single disagreement is a real judgment difference, not an error: on a 2-digit sum filed in
  a 3-digit band, I said *revise* (right skill, wrong band) and the reviewer said *reject*.
  Neha and Achal should settle it; `supabase/seed/validator_gold.json` is provisional until they do.

- **A bug in my own eval harness, found by disbelieving a bad score.** The first run scored
  pedagogy 4/6. Both disagreements were the harness's fault: it sent one skill set's context for
  gold cases spanning three, and blanked the band rule — then scored the reviewer for not knowing
  the rule it had been denied. Now one call per (skill set, band), each carrying its own rule.
  A harness that withholds the rule measures the harness.

- **Difficulty is checked as measured dimensions, not asserted.** `verify.dimension_problems`
  compares an item's own `tags` against its band's region, in `fill` and across the whole bank in
  `recheck`. `engine load --check` additionally refuses two bands of one skill set that declare
  the same region — the starvation that emptied R1's Hard band, now impossible to reintroduce.

- **It immediately found real drift, and the bank was wrong, not the check.** 93 items sat in
  bands whose rule they did not satisfy: when R1/R2/R3's bands were pinned to one format each,
  the items already in them had been generated under the old unpinned rule —
  `SUB.1D.WITHIN20` Hard says "a comparison word problem" and held 36 bare sums and missing-number
  equations. All 93 retired (not deleted), the units re-filled under the pinned rules, and the
  floors re-measured with fresh zero-accept evidence (ADR 0011): pinning makes each band correct
  but smaller, because it draws on one format's pool instead of three. New floors:
  `ADD.1D.WITHIN10` 24/22/24/24, `ADD.1D.BRIDGE10` —/43/45/35, `SUB.1D.WITHIN20` —/—/44/40.
  `ADD.1D.BRIDGE10` Easy cleared 50 outright and lost its floor.

- **Versioned rules and provenance.** Editing a skill-set rule files the old one in
  `skill_set_version`, bumps `version`, and withdraws its ratification — Aseem approved the rule
  he read, not the one that replaced it. Ratifying is not an edit and bumps nothing. Every item
  records `skill_set_version`, `generator`, `prompt_id` and `model`; the 3,574 items that predate
  this carry `generator = 'pre-provenance'` rather than a reconstructed story. Check:
  `uv run pytest -q tests/test_provenance.py` → 5 passed;
  `select count(*) from item where skill_set_version is null and skill_set_code is not null` → 0.

- **The misconception analyst (ADR 0012, external proposal §8.5): `engine bank unclassified`.**
  Wrong answers no named mistake explains, commonest first, with how many children wrote each.
  Empty until W3 reads real papers — the instrument exists before the data. For any subject
  beyond arithmetic it is the only way the mistake vocabulary grows. Check:
  `uv run pytest -q tests/test_unclassified.py` → 3 passed, against seeded results.

- **GATE 5: F1 lives in Nimish's own n8n.** `https://cornerstoneschool.app.n8n.cloud/workflow/F0i4ylZkD8zpOfH0`,
  exported to `n8n/workflows/f1-build-the-bank.json`. Schedule + webhook → `GET
  /bank/coverage?short_only=true` → per unit: `POST /bank/fill` (idempotency-keyed per unit per
  day) → language reviewer → pedagogy reviewer → email a person only if something was flagged.
  Two new endpoints carry it (`/bank/coverage`, `/bank/review`) so the *engine* decides what
  "short" means and n8n only forwards the answer.

- **`n8n/lint.py` enforces rule 3, and it has been seen to fail.** Check:
  `python n8n/lint.py n8n/workflows/*.json` → `ok — 10 nodes, no thinking, no prompt text, no
  secrets`; `uv run pytest -q tests/test_n8n_lint.py` → 9 passed, each breaking the real workflow
  one way (Code node, langchain node, prompt in a body, literal credential in an auth header, no
  trigger) and expecting it caught — plus that a sticky note may hold long prose and that every
  HTTP call goes to the engine and nowhere else.

- **The flow's routing proven by running it** with pinned data (execution 1, status success): the
  loop took both short units one at a time, the IF sent the one with `not_passed = 2` down the
  "ask a person" branch, and the loop closed with `noItemsLeft`.

- **Not done, and it is the honest gap in gate 5:** the live end-to-end run — "change a skill-set
  row and watch items appear with nobody typing a command" — has not happened, because n8n Cloud
  cannot reach `http://engine:8000` on this laptop. That needs the engine deployed or tunnelled;
  it is a hosting decision, not a workflow change, and `deploy/compose.yml` already runs both
  together for the case where they share a host.

- **Suite: 281 passed, 0 failed.** Total model spend for everything so far: see gate 6 below —
  the reviewers are the first real cost, and they are pennies.

## Environment

- Docker, Supabase CLI, psql, Node, Python 3.14 present; n8n not installed (Docker);
  `gh` authenticated as nimishshah1989, admin of org `cornerstonepune`.

## W1 gate 1 closed — all 17 specs ratified by name (2026-09-19)

Gate 1's fuller sentence ("every row `ratified`") was the last open line in W1. It is closed by
Nimish's own signature rather than Aseem's, by his instruction in chat and ADR 0013.

- **`engine ratify --by "Nimish Shah"` → `17 ratified, 0 still draft`.** New: `bank.ratify` (one
  `update … where status = 'draft' … returning code, version`) behind `engine ratify`, which also
  takes `--code` for a single set. The per-set button in the app is unchanged and stays the normal
  path; this is the bulk command a gate can quote.
  Check: `select status, count(*) from skill_set group by status` → `ratified 17`;
  `select distinct ratified_by from skill_set` → `Nimish Shah`.
- **The gate exactly as `BUILD-ORDER.md` states it:** `select count(*) from rung r where not
  exists (select 1 from skill_set s where s.rung_code = r.code)` → `0`, and no row is `draft`.
- **Ratification is per-version, and that is enforced by the database, not by discipline.** The
  trigger `internal.skill_set_version_on_change` withdraws it the moment any content column moves,
  so the 17 signatures refer to the exact words live today (`SUB.2D.EXCH` is at v15, R1–R3 at v2,
  the rest at v1). Check: `uv run pytest tests/test_provenance.py` → 6 passed, including the new
  `test_ratify_records_the_person_and_only_touches_drafts` (ratifies one set, then the rest, and
  proves an already-ratified row is not signed twice).
- **Suite: 282 passed, 0 failed** (up from 281). Check: `cd packages/engine && .venv/bin/python -m
  pytest` → `282 passed, 6 warnings in 80.55s`.
- **Stale counts corrected in `BUILD-ORDER.md`:** it said 16 rungs and 64 units, written before
  multiplication was added as the gate-3 proof. The ladder holds 17 rungs and 68 units, which is
  what `engine bank coverage` has been printing since gate 2.
- **A real defect this closed gate exposed, now fixed.** Running the full suite used to un-ratify
  `SUB.2D.EXCH` in the live database: `tests/test_loaders.py`'s
  `test_load_does_not_overwrite_a_skill_set_edited_in_the_app` commits a real edit to that row and
  restores it, and the versioning trigger withdrew the signature on both writes. Measured before the
  fix: `v33 ratified` → suite → `v35 draft, ratified_by null`. The restore now puts status and
  `ratified_by` back in a second statement that touches no content column (the trigger only fires on
  content). Measured after: `v35 ratified` → suite → `v37 ratified`, `0 drafts`. The version still
  advances by two per run, which is correct — the test really does write two versions of that rule.
- **Not resolved by this.** Ratification is a signature, not an answer to the three pedagogy
  questions `HANDOFF.md` carries: the pedagogy reviewer's objection to missing-number and
  word-problem items inside an exchange band (verdicts still in `item_review`), the gold set's
  band-vs-reject disagreement, and the G1 floors. Those still need Neha, Achal and Aseem.

## The mistake list becomes an engine output (2026-09-19, ADR 0014)

Nimish's instruction: the list of everything a child can get wrong on a learning objective is the
engine's job, not a teacher's checkbox column. Built in two halves, which is the whole point.

- **Code owns what code can compute.** `engine bank misconceptions SUB.2D.EXCH` →
  `computed  Easy 6 · Hard 7 · Medium 5 · Advance 6`, then the model's additions. The computed half
  comes from `assess/bands.py`: sample the numbers a band's own rule allows, build items with the
  same generators the bank uses, and read the misconception codes off them. No model, no cost, and
  it cannot drift from what the bank actually computes for a real item because it is the same code.
- **The model owns what code cannot** — how a child misreads a story, a method nobody has written a
  predictor for, a reasoning slip. It is told what code has already covered and asked only for the
  rest. On a pure-arithmetic set it now correctly finds almost nothing to add; on `WORD.1_2STEP` it
  added 4 (`engine bank misconceptions WORD.1_2STEP` → `11 computed by code, 4 added by the model,
  1 thrown away · ₹0.6053`).
- **The prompt's eval measures the job the prompt actually has** (rule 7). `engine eval
  misconception_list` → `0.75 of the model's proposals survived as additions over 3 skill sets ·
  claude-haiku-4-5 · ₹1.5877`, one set per kind chosen by a row (arithmetic / word / open-response),
  not by a list in code. Recall against the curated lists is **no longer an eval**: it became a
  property of arithmetic, so it is a test.
- **Version history, kept because it is the record of the loop.** v1 scored recall 0.40 against the
  curated lists, v2 0.53 — and then the design changed, because asking a model to rediscover what
  predictors can enumerate was the wrong question (CLAUDE.md rule 11). v3 asks only for the
  uncovered families; v4 makes the worked example optional (a reasoning mistake has no wrong number;
  v3 threw away 3 of 5 proposals on `REASON.EXPLAIN` for arithmetic that was never the point) and
  lets an example carry three or four addends (a multi-addend band could not state its own example
  and the whole reply was rejected by the schema). v1–v3 are inactive rows, not deleted.
- **Every check a proposal passes, in code:** its own stated correct answer must be right, or the
  entry is dropped; a wrong answer an existing predictor reproduces means the proposal *is* that
  misconception, not a new name for it; a claim of "you can see it in the answer alone" that no
  predictor reproduces is **downgraded** to the written working (or to an explanation when there is
  no number at all) rather than stored as if a marker could act on it. Check:
  `uv run pytest tests/test_spec.py` → 11 passed, all offline.
- **Three real defects the code half found in the specs themselves**, each fixed at its cause:
  - `ADDSUB.2D.NOREG` claimed `M_SMALL_FROM_LARGE`. Its four bands forbid exchange, where that
    method produces the *right* answer — unmarkable by definition. Removed from seed and row.
  - `SUB.3D.ZERO` claimed `M_ALIGN_LEFT`. All four of its bands are equal-length (3−3, 4−4), so
    misaligning unequal operands cannot occur. Removed. If the school wants that mistake tested here,
    the fix is a band with unequal-length operands — Aseem's call, and the list then regenerates
    itself.
  - `ADDSUB.4D.ADV` claimed `M_CONCAT` and its multi-addend bands had no predictor for it, and
    `WORD.BUDGET` claimed `M_WRONG_OP` with nothing computing it. Both are real mistakes, so the
    predictors were written: `misconceptions.multi_concat` (column totals written out side by side
    with three or more addends) and the wrong-operation answer in `items.word_budget`.
  - The test that finds this class of defect is `test_code_finds_every_computable_mistake_a_curated_list_names`:
    for every skill set with numbers, what code reaches must include every curated code a predictor
    can produce at all. It is the guard against a spec claiming more than the engine can mark.
  - **`ADDSUB.2D.NOREG` and `SUB.3D.ZERO` went back to `draft`** when their lists changed — the
    trigger working — and were re-signed on 2026-09-20. Check: `engine ratify --by "Nimish Shah"` →
    `2 ratified, 0 still draft`; `select status, count(*) from skill_set group by status` →
    `ratified 17`.
- **Modules split along real responsibilities** (CLAUDE.md rule 11, aislop's 400-line ceiling):
  `engine/spec.py` (the spec a person approves, its ratification, its mistake list — 197 lines),
  `engine/assess/bands.py` (a band's rule → its numbers, its items, its reachable mistakes),
  `engine/cli_legacy.py` (N3's commands). `bank.py` 520 → 309, `cli.py` 454 → 367, both under the
  ceiling. `tests/test_spec.py` mirrors the new module.
- **Nothing has been applied to any skill set.** `--apply` unions the proposals into the set (it can
  never remove a curated code) and withdraws its ratification, so it waits for Nimish's word. Check:
  `select count(*) from misconception where source like 'misconception_list%'` → `0`.
- **Suite: 291 passed, 0 failed.** `engine load --check` → `unchanged on a second run`;
  `engine bank recheck` → `0 mismatches`. Model spend for the whole day's work on this: ₹11.
- **Still open, and it is a style decision, not a defect:** every Python file in the engine trips
  aislop's `python-formatting` warning, because the repo has never adopted `ruff format`. Measured
  before deciding: on two files the reformat is 536 diff lines, and it explodes the misconception
  registry from one readable line per mistake into five, which is the layout the vocabulary is read
  from. It needs Nimish's call — adopt the formatter and accept that, or record the exception in
  `.aislop/config.yaml` with the reason. `assess/items.py` carries the engine's oldest debt, now measured
  exactly: 49 ruff E701/E702 errors (the prototype's one-line style), 3 functions over the 6-parameter
  ceiling and 490 lines against a 400-line ceiling. Fixed there this session: an unused import, two
  f-strings with no placeholders, and the missing wrong-operation predictor. The rest is frozen and
  named, not inherited silently — `ruff format` would clear the 49 but grow the file past 700, so the
  honest order is split first, format second: a warning aislop itself marks unfixable, surfaced here per `AISLOP.md`'s ladder. Its real
  cause is that per-format generators and their story text belong in rows (rule 1, ADR 0010), which
  is a design thread with its own ADR, not a line-count shuffle.

## A goal is now runnable, and it found four more defects (2026-09-20, ADR 0015)

Nimish: "with every test you are finding an error — how do we know that we don't have any more
errors", then "we need to start having a very specific goal for every task/milestone … till 100%
accuracy is achieved." Two commands answer those two questions.

- **`bin/engine goal w1-build-the-bank` → `10/10 scenarios met the bar completely`,
  `5/5 criteria met · GOAL ACHIEVED`.** The goal file (`goals/w1-build-the-bank.yaml`) states in one
  sentence what W1 must do, then proves it on ten real requests — two-digit exchange at Hard and at
  Easy, three-digit across a zero, two-digit regrouping, a foundational rung with a small universe,
  multiplication (a topic added as rows only), four addends, a word problem, a budget, find-the-
  mistake. Each is checked *independently of the code that answered it*: every answer recomputed from
  the numbers, every question re-measured against its band's rule, every wrong answer mapped to a
  named mistake, no duplicates, nothing stored. Every scenario reported
  `produced=asked  answers_recomputed=asked  off_rule=0  undiagnosed=0  distinct=asked`.
- **`bin/engine audit` → `12 invariants checked, 0 violations`.** Twelve named properties of every
  row, in one sweep, so a new class of bug becomes an invariant rather than a test that trips over it
  by luck. It runs from any directory (`bin/engine`, CLAUDE.md rule 13) — the `cd packages/engine`
  form was giving Nimish shell errors.

**Four defects found by running them, each fixed at its cause:**

1. **Multiplication questions could not be diagnosed at all.** `MUL.1D` produced 20 correct, on-rule,
   distinct questions of which **14 had no named mistake to mark against**: `M.predict` had tables for
   `+` and `-` only, so every multiplication distractor was empty and a child's wrong answer could
   only ever be "wrong". Fixed by writing the predictors — `M_MUL_NO_CARRY`, `M_MUL_CONCAT`,
   `M_MUL_CARRY_FIRST`, `M_MUL_ONES_ONLY`, `M_MUL_ROW_OUT`, `M_WRONG_OP` — with their vocabulary rows.
   Check: `M.predict("×", 56, 3)` → `{M_MUL_CONCAT: 1518, M_MUL_ONES_ONLY: 18, M_MUL_ROW_OUT: 112, …}`,
   and the scenario now reports `undiagnosed=0`.
2. **The `misconception.op` constraint had no `×`** (it predated the multiplication rung), so the
   vocabulary had nowhere to put those rows. Migration `20260922090000_misconception_multiply.sql`.
3. **1,172 live items named six mistakes that were not in the vocabulary** — `M_ADD_INSTEAD` (476),
   `M_ONE_STEP_ONLY` (300), `M_SUM_ONLY` (200), `M_ADD_ALL` (148), `M_EQUALS_MEANS_ANSWER` (148),
   `M_FACT_PM100` (100). The generators had invented them inline and nothing checked. All six now have
   rows with names, examples and repair hints, and **an unknown code can no longer reach an item**:
   `bank._strip_unnamed` drops it at insert and counts it as `unnamed_distractor_dropped`, because the
   marker, the graph and the teacher's screen all read the vocabulary by code.
4. **The skill-set screen asked for `op = 'both'`**, a value the data has never used (it is `'any'`),
   so every operation-independent mistake was invisible in the app. One-word fix in
   `apps/web/lib/queries.ts`.

**And one test was hiding a defect rather than catching it:**
`test_every_seeded_answer_lookup_code_has_a_predictor` re-typed the union of predictor tables inside
itself, so it could not see that `MUL_PREDICTORS` did not exist. Replaced by one registry
(`M.PREDICTED`) plus the audit invariant *every answer-lookup code is computed somewhere*, which also
covers the codes the generators compute inline — the case the old test could never have caught.

**Suite: 294 passed** (up from 291). `tests/test_goal.py` runs the ten scenarios and the twelve
invariants, so the goal is defended in CI and not only by someone remembering to type it.

**What these two commands do NOT cover — the honest list of what we still do not know:**
- **W3's reading accuracy.** Nothing yet measures how well a scanned paper is read; 10 of the 84 real
  sheets have been through a first reader and no number was recorded. W3 needs its own goal file with
  an accuracy bar *before* the reader is built (ADR 0015).
- **W2 and W4 have no goal file**, so "assemble and print" and "close the loop" have no functional
  bar yet.
- **The app.** `apps/web` has Playwright screenshot tests; no scenario checks that what a teacher
  sees matches what the engine knows. The `op = 'both'` bug lived there for exactly that reason.
- **Pedagogy.** Whether a band's rule is the right thing to teach, and the three open questions in
  `HANDOFF.md`, are Neha's, Achal's and Aseem's. No command can close them.
- **Prompt quality beyond its own eval.** `misconception_list` scores 0.75 on additions and the two
  reviewers 6/6 and 5/6 against a provisional gold set; those numbers bound what the model is
  trusted for, they do not prove it right.

## Style is machine-enforced, and three "flaky" failures had one cause (2026-09-20)

- **`ruff format` adopted, `ruff check` pinned to the classes that are defects.** `line-length = 110`
  (the width this engine was written at; 88 would rewrap every line and call it formatting), the
  predictor registries wrapped in `# fmt: off` because one line per misconception is the point, and
  `select = ["E", "W", "F", "I"]` with `E501` left to the formatter. That cleared 49 real E701/E702
  errors in `assess/items.py`, three unused imports, two ambiguous `l` variables and a lambda
  assignment. CI now runs `ruff format --check` and `ruff check` before the suite, so the style
  cannot drift back. Check: `uv run ruff check engine tests` → `All checks passed!`;
  `uv run ruff format --check engine tests` → `72 files already formatted`.
- **`assess/words.py` split out of `items.py`** — the stories, the names and the three word-problem
  generators, whose real home is a row (ADR 0010) and which are now one visible file rather than a
  tail on a catalogue. `items.py` is still 741 lines against aislop's 400 because formatting expanded
  its dense one-line style; the remaining fix is rows, not another split, and it is named here rather
  than gamed.
- **Three intermittent failures — `test_legacy`, `test_loaders`, and a scenario — had one cause
  between them: a test that committed to a live spec row, plus me running two suites at once.**
  `test_load_does_not_overwrite_a_skill_set_edited_in_the_app` edited `SUB.2D.EXCH`, committed so
  that `load_all()`'s own connection could see it, and restored it in a `finally`. Two runs at once
  left the row edited and unratified, and every other test that read it failed in ways that looked
  like their own bugs. It now calls `loaders._skill_sets(conn, tenant)` on its own connection and
  rolls back: same clause proved, nothing written. Check: three consecutive full runs →
  `294 passed` each, and `engine audit` → `0 violations` after.
- **A real gap that flake exposed: `fill_native` had no in-batch duplicate guard.** Its only defence
  was the insert's conflict clause, so a dry run — a scenario, an eval — could hand back a set with a
  repeat in it. It now keeps the same `seen` set `fill` does. Check: six consecutive dry runs of
  `WORD.1_2STEP Easy` → `produced 20  distinct 20` every time; before, one in roughly five had 19
  distinct.
- **`bin/engine goal w1-build-the-bank` → `10/10 scenarios`, `5/5 criteria`, `GOAL ACHIEVED`** after
  all of the above. Suite 294 passed, audit 12/12 clean.

## The mistake lists applied to all 17 specs (2026-09-20)

Nimish ran `bank misconceptions WORD.1_2STEP --apply` himself, which exposed two defects in the
apply path before the rest were touched. Both fixed, then the whole ladder was applied.

- **The generated codes were unusable.** `_code_for` slugged the model's whole sentence and produced
  `M_MISCONCEPTION_S_DEMAND_ANSWERED_THE_Q` — a join key the graph, prescriptions and every screen
  would have carried forever. It now takes the first three words that mean something, never cutting
  mid-word: `M_USES_WRONG_OPERATION`, `M_PICKS_EXTRA_NUMBER`, `M_READS_TWO_STEP`. The five rows from
  that first apply were deleted and re-proposed; two later codes cut at the 30-character cap were
  renamed in the vocabulary and in every spec that referenced them.
- **Prompt v5: the name is a label, not a sentence** (six words, 60 characters), and the model is now
  shown **every name in the vocabulary**, not only the codes this band computes — because a mistake in
  reading a story has no wrong number to match on, so the only way to stop a second name for it is to
  show the first. Measured on `WORD.1_2STEP`: 5 proposals of which several duplicated existing
  mistakes, down to 1 genuinely new.
- **`--computed-only`: the free half, applied to all 17 specs.** `engine bank misconceptions <set>
  --computed-only` unions what code can already mark against, with no model call. **58 codes added
  across 12 specs at ₹0** — mistakes the marker has been diagnosing while the spec a person approves
  never mentioned them.
- **The model half applied to the seven sets arithmetic cannot reach** (reasoning, strategy, mental,
  estimate, budget, word problems): **26 engine-proposed mistakes now in the vocabulary**, every one
  `working`, `explanation` or `teacher` — none claims to be markable from the answer alone, because
  none has a reproducible number. Total spend ₹4.1.
- **A defect the dropped counter caught in my own checker:** `WORD.BUDGET` threw away 5 of 5
  proposals as "its own arithmetic is wrong" — and the arithmetic was mine. A budget question is a
  chain (`8000 − 25 − 40 − …`) and the checker read only its first two numbers. `M.chain` now folds
  left over however many numbers a question has. After the fix: 3 added, 3 dropped. The 3 that remain
  dropped mix operations in one example (per-child multiplication inside a subtraction chain), which a
  single `op` field cannot express — named here, not hidden.
- **All 17 ratified as `Nimish Shah (engine-derived list, applied 2026-09-20)`** — his instruction to
  finish, with the full list in front of him, and the attribution says the list was derived rather
  than read line by line. Editing any spec withdraws it as usual.
- **The vocabulary is now a table the seed does not own outright** (65 rows: 39 seeded, 26 proposed),
  so `test_every_table_has_the_expected_number_of_rows` no longer asserts an exact count for it. The
  seeded rows are a floor and each must be present — which is the stronger claim, and it will hold
  when `engine bank unclassified` starts adding what children actually write.
- **Green after all of it:** `bin/engine goal w1-build-the-bank` → `10/10 scenarios`, `5/5 criteria`,
  `GOAL ACHIEVED`; `bin/engine audit` → `12 invariants, 0 violations`; **295 passed**;
  `uv run ruff check engine tests` → `All checks passed!`.

## W2 — assemble and print: the week runner, the endpoints, F2 (2026-09-20)

W2's goal was written before its code (ADR 0015). Building against it, in the order the goal named.

- **`scenarios_week.py` — eleven scenarios that build a real week** for a throwaway section
  (`GOALSEC`), inside the caller's transaction, rolled back: prescribe, assemble, store, then read the
  properties off the rows the real path wrote. **Eight of nine passed on the first run**, which is
  what the parts' own tests had earned; the two failures were both real and both mine to fix.
- **The one product failure was the class register.** `a real class of sixteen gets sixteen different
  papers` → `children=16  papers=13  questions_needed=216  questions_held=159  short=3`. A week draws
  without replacement across a class, so one unit must hold `(children + spares) × items_per_sheet`.
  The bank's target was 50 — a round number with no relationship to a class list. **ADR 0016: a unit's
  target is what a class needs in a week**, every term a config row (`bank.class_size = 16`). Then the
  enumerator filled every short unit: **12,633 live questions, 68 of 68 units at target, ₹0**.
  Check: `engine bank coverage` → `68 units, 0 under their target`.
- **Thirteen units cannot reach it, and all thirteen are Grade 1 rungs** whose numbers genuinely run
  out — `ADD.1D.WITHIN10` holds 22–24 questions in total against a class need of 216. Four recorded a
  fresh measured ceiling as `min_items` (ADR 0011's evidence rule: a second fill that accepts nothing).
  So a Grade 1 class **cannot** have sixteen different papers in one week, and the engine must say so
  rather than print short ones. That is now its own scenario — *a Grade 1 class is told the rung is too
  small, never handed short papers* — so the limit is checked, not discovered in a classroom. The ways
  out are the school's: fewer questions per sheet for Grade 1, a wider rung, or accepted sharing.
- **The other failure was in my own check**: the exposure-window scenario cleared the first week's
  sheets so it could rebuild, which a prescription's foreign key rightly refused. It now builds **two
  consecutive weeks** for three children — the real thing a school does — and asserts nothing from
  week one comes back in week two. `children_checked_across_two_weeks=3  window_days=21`.
- **Three engine endpoints, because n8n never thinks** (rule 3): `POST /week/prescribe`,
  `/week/assemble`, `/week/render`, each thin, idempotency-keyed, calling the same functions the CLI
  calls. Check: `uv run pytest tests/api/test_week_routes.py` → 2 passed, including *the same week
  assembled twice is one week* (`already: true`, identical QR codes — a retry must never print a
  second set).
- **F2 exists and lints:** `n8n/workflows/f2-assemble-and-print.json` — Wednesday's declaration or a
  webhook → prescribe → assemble → **if any child was left without a paper, email a person and print
  nothing for them** → otherwise render the pack and ask the teacher to approve. Check:
  `python n8n/lint.py n8n/workflows/*.json` → `f2-assemble-and-print.json: ok — 10 nodes, no thinking,
  no prompt text, no secrets`.
- **The teacher's approval is now a guarantee, not a label.** `print_status = 'printed'` was a string
  any code could set; migration `20260923090000_print_needs_an_approver.sql` adds `approved_by` /
  `approved_at` and a check constraint, so **the database refuses a printed sheet that cannot say who
  allowed it**. `assemble.approve` is one tap for a class (N7 — a teacher's attention is the scarcest
  thing in the school), exposed as `POST /week/approve` so the screen and the flow use one
  implementation, and the Worksheets screen's one-tap action now writes the signed-in staff member's
  email with it. Checks: `uv run pytest tests/api/test_week_routes.py` → 4 passed, including *a sheet
  cannot be printed without someone approving it* (a `CheckViolation` is the assertion) and *approving
  the week names the person on every sheet*; plus W2's own scenario *nothing prints until a person
  approves* → `sheets=6  approved=6  by='a test'`.
- **The Grade 1 limit is proved rather than promised:** *a Grade 1 class is told the rung is too small,
  never handed short papers* → `children=16  papers=2  named_short=14  skill_set=ADD.1D.WITHIN10`.
  Fourteen of sixteen children are named with what was missing, and nothing is printed for them.
- **A flake that had cost three sessions' confusion is closed.** `test_legacy`'s evidence assertion
  compared a *sequence* against a query ordered only by `rung_code`, where every row was `R5` — so
  Postgres was free to hand them back in any order, and it failed about one run in three. It asserts
  the tally now. The app's own evidence read is properly ordered (`order by date, item_key`), so there
  was no product bug behind it. Three consecutive full runs clean.

- **Two things the new target broke in the suite, both corrected at the cause.**
  `test_fill_native_produces_items_for_every_native_unit` demanded five new questions from every
  native unit unconditionally — but `MENTAL.BRIDGE_EQ Easy` is now at its measured ceiling of 145, so
  a further fill *must* accept nothing. It asserts "five, or nothing and the band says why
  (`min_items`)". And `test_coverage_targets_50_by_default…` asserted the round number the decision
  replaced; it now reads the class need from the rows and checks a ceiling unit keeps its own.
- **My own migration was too strict and history caught it.** The approval constraint gated every
  status, so a legacy paper (N3) — entered after a child had already done it, on paper nobody printed
  here, landing as `returned` with no one to name — was refused. Narrowed to `print_status <>
  'printed' or approved_by is not null`: the gate is about printing, not about history. Three legacy
  tests were the ones that said so.
- **Suite: 300 passed** (up from 295: the week routes, the approval gate both ways, and the eleventh
  W2 scenario).

## A derived counter in the hot path deadlocked two classes (2026-09-20)

Found by timing W2's scenarios while a goal run was building weeks in another connection — two real
week builders at once, which is what a school does when two teachers declare on the same Wednesday,
or when F2 fires for two sections.

- **`assemble._store` incremented `item.times_used` for every question it handed out.** Two builders
  touching the same unit deadlocked on those rows. Ordering the update by id did not fix it —
  Postgres takes `FOR UPDATE` locks in *scan* order, not in the order of the `ORDER BY` — and once the
  update was ordered the deadlock simply moved to `item_exposure`'s index.
- **The counter is derived, so it moved to Ring B.** `graph.refresh_item_usage` computes it from
  `item_exposure`, which already records every handout row by row, and `engine graph` calls it. The
  hot path now takes no row locks at all. What the counter feeds is the pool's ordering — spreading
  the load across a unit — so being one rebuild behind costs nothing. This is what CLAUDE.md's Ring B
  already said: a derived number is a pure function of Ring A, rebuildable at any time, and it had no
  business being written by a concurrent path in Ring A.
- **Checked by a test that fails against the old code:**
  `tests/test_week.py::test_two_classes_assembled_at_the_same_moment_both_finish` builds two weeks in
  two threads on two connections. Against the previous query it raised `DeadlockDetected` (seen on the
  first of three attempts, then intermittently — a deadlock needs the interleaving); with the counter
  derived it passed **five runs out of five**. It is the one test here that commits, so it uses a
  section of its own per run and deactivates its children afterwards rather than deleting them —
  `evidence_event` is append-only and refuses a cascading delete (rule 4), which is also what a school
  does when a child leaves.
- **Suite: 301 passed.** `engine audit` → `12 invariants, 0 violations`.

## W3 opens: its goal written before its reader, and red on purpose (2026-09-20)

BUILD-ORDER rule "W2, W3 and W4 must have their goal files written before their work starts"
(ADR 0015). `goals/w3-read-and-graph.yaml` states W3's sentence, 17 scenarios and 4 criteria.
Nothing of the reader is built: the bar's numbers are proposed and wait on Nimish's yes.

- **W1, W2 and the audit were all green before any of this was written.** Check:
  `bin/engine goal w1-build-the-bank` → `10/10 scenarios · 5/5 criteria · GOAL ACHIEVED`;
  `bin/engine goal w2-assemble-and-print` → `12/12 scenarios · 4/4 criteria · GOAL ACHIEVED`;
  `bin/engine audit` → `12 invariants checked, 0 violations`. Suite `301 passed`.

- **The corpus, counted rather than described.** `~/cornerstone/assessments` holds 84 files /
  194 pages. In scope for reading: **118 pages across 72 files**. Out: 66 pages of SOF Olympiad
  booklets across 7 files (multiple-choice across the whole syllabus — `manifest.md` says only
  their add/sub items map to a rung) and 10 pages of Aseem's five typed Grade 3 reports, which are
  the gold and not the input. Check: a `pymupdf` page count over the tree →
  `files: 84   total pages: 194`, then classified → `paper 72/118, olympiad 7/66, report 5/10`,
  and `paper pages whose PDF already has a text layer: 0`. Every response must come through vision.

- **Two reading regimes, not one.** 80 pages are flat scans of a printed paper answered in pen
  (regime A); 38 are phone photos — angled, page curved, answers in pencil, with the teacher's own
  tick and cross in pen beside the child's answer (regime B). Confirmed by eye on
  `G3/<child folder>/Assessment 0/WhatsApp Image 2026-08-16 at 18.02.42.jpeg`.

- **What has actually been read so far: 10 captures, all regime A, 138 responses.** Check:
  `psql -Atc "select c.status, count(*) from capture c where c.superseded_by is null group by 1"`
  → `processed 10`, `error 2`. Both errors are one cause — `claude-sonnet-5 returned HTTP 400:
  Your credit balance is too low`. No regime-B page has ever been read.
  `select count(*) from item_result r join capture c on c.id=r.capture_id where c.superseded_by is
  null` → `138`, and `select round(read_confidence,2), count(*) …` → `null|138`: the reader does
  not report its own confidence, so "the reader flagged it" does not yet exist as a distinction.

- **The first hand-check of a read against the page it came from (Advika, Cambridge Level A,
  2 pages).** Rendered at 150 dpi and compared response by response against the 24 rows in
  `item_result`:
  - **24 of 24 responses the engine emitted were read exactly right** — every digit and both
    blanks. 148+7→155, 236+9→245, 357+8→365, 425+6→431, 348+27→374, 476+58→534, 285+96→281,
    165−7→158, 243−8→235, 352−6→346, 471−9→462, 425−38→397, 563−47→516, 342−58→384, 250+[150],
    45+[5], [80]−20, 100−[30], estimate 282, 763+427→1190, 1190+38→1228, Q9 blank, Q10 blank.
    Two of those are diagnostic gold: 763+427 is the child adding where the question subtracts.
  - **But the page holds 27 responses.** Q5's three filled boxes (`0`, `52`, `72`) became one row
    reading `72`; Q7's estimate and total became one. **Three responses never got a row at all.**
  - **Systematic, not a one-off.** All three children who sat that paper produced exactly 24 rows:
    `select c.path, count(*) … where c.path like '%sept. 1st%'` → Advika 24, Heian 24, Hridhima 24.
  - So the failure mode is not misreading digits — it is not emitting a row. A bar phrased as
    "% of responses read correctly" scores this sheet 100% and hides the hole. This is why the goal
    file carries two separate numbers and a recall bar of 100 rather than 97.
  - It is the same defect class STATE.md recorded on 2026-09-17 ("`legacy_extract` needs a `part`
    field — Q1's four lettered sub-answers arrived crammed into one string"): fixed for lettered
    parts, still open for in-line boxes and for two-part questions like estimate-then-total.

- **The goal is declared and red, which is the state it is supposed to open in.** Check:
  `bin/engine goal w3-read-and-graph` → exit 1,
  `2/4 criteria met · … · 17 scenarios short of the bar`; every scenario reports
  `no runner for a 'read' scenario yet — this goal is declared, not met`, and the two failing
  criteria are the two things W3 has to build (`n8n/workflows/f3-read-and-graph.json`,
  `engine read accuracy`).

## W3 gate 1 found: the papers themselves are the defect, not the reader (2026-09-20)

Nimish: "for every grade 2 and grade 3 student in that drive we have, at least 3 to 4 assignments,
so make sure that you are not missing out on anything." Counting from disk rather than from
`manifest.md` proved him right and the manifest wrong.

- **52 sittings across 16 children, not the manifest's 37.** Check: a per-child inventory over
  `~/cornerstone/assessments`, attributing every loose file by the manifest's own table →
  `sittings-per-child distribution: {1: 2, 2: 3, 3: 4, 4: 3, 5: 4}`, `children: 16`,
  `total sittings: 52`, `unattributed files: none`. The manifest omits the WhatsApp images
  entirely — 20 Grade 3 baseline pages and 15 Grade 2 extra pages. It is data documentation kept
  outside git, so it is flagged here rather than rewritten.

- **The Grade 2 Cambridge paper runs at four levels, not two.** Check: a contact sheet of the
  printed header band of all ten `sept. 1st` PDFs → **Level A** ×4, **Level B** ×4, **Level D** ×1,
  and one whose header is cropped but whose Q1 (`62 + 5`, `71 + 6`) matches neither `G2-CAM-A`
  (`148 + 7`) nor `G2-CAM-B` (`48 + 7`), so a fourth form exists. Only A and B are in the database.
  Seven of the ten Grade 2 children who sat it are therefore unreadable today.

- **`G2-CAM-B` is correctly entered, as far as its first page.** Check: Q1–Q5 on a real Level B page
  are `48+7, 36+9, 27+8, 55+6 / 154+8, 267+5, 348+9, 236+7 / 63−8, 72−5, 84−6, 91−7 / 52−27, 74−38,
  61−45, 83−59 / 165−7, 243−8, 276−9, 354−6` — 20 answers, all single-box, matching the 20 slots the
  row holds for that page. Page 2 (`6a, 6b, 7, 8`) is not yet checked.

- **Why a wrong slot count loses answers silently.** `legacy.import_scan` looks each read up by
  `n`+`part` in `paper_rows`' `by_key`; a key with no slot appends to `summary["unmatched"]` and
  `continue`s. So the model may well have read all 27 of `G2-CAM-A`'s answers — the code had
  nowhere to put three of them. The root cause is the paper's entry, not the prompt or the model.

- **The full paper inventory is `docs/w3-paper-inventory.md`**: 14 distinct papers, of which 4 are
  entered (1 proven wrong, 2 unchecked) and **10 have never been entered** — including the Grade 3
  16-question baseline that all five of Aseem's gold reports are written from, and where
  `8500 − 3647 = 5147` lives. The gold set for the whole pipeline is behind this gate.

- **The child with the fewest papers is on the paper nobody entered.** One child has a single
  sitting, on Level D, and wrote `4+3=55`, `6+2=45`, `5+4=35`, `3+5=61`, `9+4=49` with no working
  anywhere on the page. The answers bear no relation to the operands: that child is not computing
  at all. It is the sharpest diagnostic signal in the corpus and the engine cannot currently see it.

- **Two test children were left active in the live roster.** `select count(*) from child where
  active` → `18`, but only 16 children exist on disk. The extra two are `Concurrent 1` and
  `Concurrent 2` in a bare `CONCURSEC` section, created 2026-09-20 05:26:04 by an **earlier version**
  of `test_two_classes_assembled_at_the_same_moment_both_finish`. The current test is correct — it
  uses a per-run `CONCURSEC-<hex>` section and deactivates it in a `finally`, and every one of the
  ~25 hex sections is `active = false`. The two orphans predate that design and the section-scoped
  cleanup can never match them. They sit in their own section, so they would never join a real class
  assembly. **Not yet fixed: the one-line deactivation was refused by this session's sandbox**
  (`Modify Shared Resources`), and `psql` was blocked for the rest of the session afterwards.
  The fix, for a session that can write: `update child set active = false where section =
  'CONCURSEC' and active` → expect `UPDATE 2`, then `select count(*) from child where active` → `16`.
  **Fixed 2026-09-20.** Nimish ran the deactivation; `select section, count(*) from child where
  active group by section` → `G2|11`, `G3|5` — 16 active children, matching the 16 folders on disk.

- **And the test can no longer leave orphans, whatever its section is called.** The band-aid was
  deactivating two rows; the cause was a cleanup keyed on a name that can drift. It now cleans up by
  the ids the run created — which are known at insert time and cannot drift — and asserts none is
  left active, so the test fails rather than silently leaking. Check: `pytest
  tests/test_week.py::test_two_classes_assembled_at_the_same_moment_both_finish` → `1 passed`, then
  the roster query again → still `G2|11`, `G3|5`. Suite `301 passed`, `engine audit` → `12
  invariants checked, 0 violations`.

- **The structural gap underneath is still open, and deliberately not papered over.** `child.section`
  is free text (`ring_a.sql:247`) with no section table, which is what let a test invent `CONCURSEC`
  and leave it live. CLAUDE.md rule 1 says structure is rows, so sections should be rows too. No
  invariant was added to `engine audit`, because with sections as free text any such check would
  have to pattern-match on a test's name — a fabricated check standing in for a real one, which is
  the trap `HANDOFF.md` already names. The honest fix is a `section` table and a migration; it is
  Nimish's call whether that happens now or after W3's gate 1.

## The Olympiad mapping rate, measured instead of guessed (2026-09-20)

Nimish: "the nature of the question will map itself to a skill 70%, 80%, or 90% of the time. If it
doesn't, we need to have an engine that builds a skill out of it." `engine read map` replaces the
guess with a count. Two prompts as rows (rule 2): `question_extract` (vision, a printed page → its
questions and what each tests, no child's answer and no educator's mark) and `skill_match` (text,
a described question → a registry code, `clear` / `arguable` / `none`). Split in two so the match
re-runs for a fraction of a rupee when the registry grows, with no page read again — which is
ADR 0017's requirement that naming a skill later places evidence already held.

- **Seven booklets are two forms, not seven.** Check: the printed footers — all four Grade 2
  booklets read `Class-2 | Level-1 | Set-7`, all three Grade 3 read `IMO | Class-3 | Set-C | Level 1`.
  Identical questions, different children's marks. So the mapping is measured on **~70 distinct
  questions over 16 pages, not 245 over 66** — the children's answers differ, the paper does not.

- **The registry already covers 94–95% of an Olympiad paper.** Check:
  `bin/engine read map "…/ACE Scanner_20260916(13).pdf"` → `clear 22, arguable 13, no match 2, of 37`
  → **`MAPPED 95%` (clear alone 60%)**, `Rs 6.48`; and
  `bin/engine read map "…/Advika SOF (olympiad).pdf"` → `clear 18, arguable 15, no match 2, of 35`
  → **`MAPPED 94%` (clear alone 51%)**, `Rs 6.21`. Nimish's guess was right at the top of its range.
  **Corrected 2026-09-20, same session.** "About 95, not below 89" was written from three runs and
  is wrong. Nimish ran it himself and got **84%** with 6 no-matches. Across four full runs the rate
  went **84 / 89 / 89 / 95**, and a further five runs of the matcher alone against one saved
  extraction gave **84–97%, a 14-point spread**, with the no-match count at 4, 2, 3, 1, 6.
  The honest statement is ~90% with a ±7-point swing, and a single run's number means little.

- **What the registry is missing is four questions, and one of them appears on both forms**:
  letter-sequence and odd-one-out reasoning (Grade 3 q2 and Grade 2 q1), embedded figures within a
  composite figure, and arithmetic-operation verification. That cross-form repeat is exactly the
  cluster signal a new skill should need — one stray is not a skill, the same thing on two papers is
  a candidate.

- **A cover page invents a question, reproducibly, on both forms.** The Grade 3 cover returned
  `n=18 "Sonia had 80 sweets…"`; the Grade 2 cover returned an `n=16`. Neither page prints any
  question — both are a title, a logo and a name band. The prompt said in v1 to return an empty list
  for such a page and it fabricated anyway. **This is the `silently_wrong_at_most: 0.01` bar's
  failure mode, found on the first real run**, and no reader that trusts a page's output can catch
  it. What catches it: the same `n` read from two pages is a conflict, and the page that yields a
  *run* of questions is the one that prints it — measured, the cover yields exactly 1 while every
  question page yields 3 to 9. Keeping the *first* occurrence, which is the obvious thing, kept the
  invention and threw away the real question 18. `external.resolve` and `tests/test_external.py`.

- **Two defects of my own making, fixed at the cause in the same session (rule 11):**
  - `question_extract` v1 had no `part` field, so Grade 3's `35 (p)` and `35 (q)` collided into one
    question — the identical defect to the Cambridge paper's Q5, rebuilt hours after diagnosing it.
    **v2 adds `part`, v1 is inactive.** Check: the run now reports `33p, 33q, 35p, 35q` separately.
  - **The first run sent an unmasked cover to a model, with a child's handwritten name on it** —
    a rule 6 violation, caused by `--mask` defaulting to 0. Masking is now a default rather than a
    flag (`external.FIRST_PAGE_MASK = 0.34`, applied to page 1, where the name band is and where no
    printed question sits), and a caller wanting the raw page passes `--mask 0` and says so.

- **Suite `307 passed`** (6 new in `tests/test_external.py`), `engine audit` → `12 invariants, 0
  violations`. `select round(sum(cost_inr),2) from flow_run` → **Rs 49.05** all-time, of which this
  measurement is about Rs 19 across five runs.


## The matcher is unstable, and that matters more than its average (2026-09-20)

Found because Nimish re-ran `engine read map` himself and got a materially different number from the
one this file claimed. Isolated with `engine read stability`, which re-matches a **saved** extraction
so the expensive vision half is held fixed and only the cheap text half varies.

- **Check:** `bin/engine read stability <saved.json> --runs 5` →
  ```
  37 questions, 5 runs of the matcher alone
  MAPPED  min 84%   max 97%   spread 14%
  no-match count per run: 4, 2, 3, 1, 6
  22 of 37 questions gave the SAME skill every run   (59% stable)
  ```
  **The variance is in the matcher, not the reading**: the questions were identical across all five.

- **41% of questions move between runs**, and the moves are not random noise — they are real
  ambiguity the model resolves differently each time. A money-and-change question (q34) landed on
  four different codes in five runs (`NUM.PRB.02`, `NUM.OPS.02`, `NUM.MEAS.04`, `NUM.OPS.01`); a
  mirror-image question (q10) was `NUM.GEO.03` twice and *no match at all* three times; a word
  analogy (q8) went to `ICT.CT.01` — Computing — on three of five runs.

- **This kills unsupervised skill creation, with a measurement rather than an argument.** q10 would
  propose a new "Mirror image identification" skill on three runs out of five and map to an existing
  registry skill on the other two. Run the pipeline twice and the registry gains a duplicate that
  shadows a skill already there — the exact near-duplicate proliferation that splits a child's
  evidence until nothing reaches `state.min_events` (3). The case for a person approving a *cluster*
  rather than the engine creating per question is now evidence, not caution.

- **The model's self-reported confidence is not usable and should be replaced by measured
  agreement.** `clear` / `arguable` / `none` is what the model says about itself on one pass, and
  the same question earns different labels on different passes. Agreement across N runs is a real
  measure of the same thing: 5 of 5 is clear, 3 of 5 is genuinely arguable, all-different means a
  person must look. At Rs 2.65 a run this costs about Rs 13 a paper, which is nothing against the
  cost of filing a child's evidence under the wrong skill.

- **This is rule 7 catching me.** "Every model output ships with an eval." I wrote two prompts and
  ran them without one; an eval would have surfaced the instability immediately, because an eval is
  run repeatedly against a gold set and a single run is not. The eval for `skill_match` is owed.

- **It carries straight into W3's own bar.** `read_exactly_right: 0.97` is currently written as
  though one measurement settles it. On this evidence a single run can be 7 points off, so the
  goal now requires the accuracy number to be the **worst of repeated runs**, not one run's luck.
  Digit transcription should be far more stable than 244-way classification — but that is a
  prediction, and the bar must not rest on it.

## The cache made the stability command lie, and four patches turned out to be one defect (2026-09-20)

Nimish re-ran `engine read stability` and got `100% stable, spread 0%, Rs 6.22` where the same
command minutes earlier had given `59% stable, spread 14%, Rs 13.26`.

- **His run was one response served five times, not five samples.** Check:
  `select to_char(started_at,'HH24:MI:SS'), model, tokens_in, tokens_out, cost_inr from flow_run …`
  → both runs served by `claude-haiku-4-5`, but the earlier run billed `in=7326` / `in=8116` with
  output moving every pass (`986, 932, 1049, 1032, 1038`), while the later billed **`in=3`** with
  output **exactly `1895, 933` five times over**. Independent samples of a ~1,900-token generation do
  not repeat their token count five times running. The provider served a cached reply; the adapter
  sets no `cache_control`, so this is upstream and outside our control.
- **So the 59% stands and the 100% measured nothing** — and the command reported perfect stability
  having made one distinct call, which is a confident false negative and worse than no command.
  Fixed at the cause: `external.fingerprint` hashes each run's answer, and `read stability` refuses
  with exit 2 when every run is byte-identical rather than calling it agreement. Re-verified:
  `bin/engine read stability … --runs 3` → `3 distinct responses across 3 runs`, 11 questions moving.
- **Noted, not fixed:** `flow_run.tokens_in` records only uncached input, so a cached call
  under-reports both tokens and cost. Any cost claim drawn from `flow_run` is a floor, not a total.

**Nimish, on seeing the fourth fix in a row:** *"none of this is patchwork … let's figure out a very
core solution … The prompts need to then consider this kind of use case. When the system is not able
to comprehend the prompt, it should exactly tell the system what to do."*

He is right, and the four fixes are one defect. `question_extract` gaining a `part` field, masking
becoming a default, conflict resolution preferring the page that holds a run of questions, and
fingerprinting responses are four symptoms of: **the engine treats the shape of a model's reply as
evidence of its substance.** An empty list and an unreadable page are indistinguishable to the
caller — which is exactly the collapse rule 5 forbids for a child's answer ("blank, wrong and
wrong-with-working are distinct everywhere") and which the engine never applied to itself.

**ADR 0018** is the core solution: every prompt returns a `resolution` alongside its payload —
`status`, what it `saw`, and an `unresolved` list whose `needs` field is a closed vocabulary the
code branches on (`a_person`, `more_of_the_input`, `a_new_row`, `nothing`). "This page holds no
questions" becomes an assertion the model makes rather than an absence the caller interprets, so
inventing a question means contradicting its own `saw`. It also forbids a prompt reporting its own
confidence — measured agreement replaces it — and requires every gold set to contain an input whose
right answer is a refusal. All 17 prompts migrate; `engine audit` gains an invariant that an active
prompt without `resolution` does not ship. `question_extract` v2 and `skill_match` v1, both written
today, are the first two to migrate.

- `bin/engine goal w3-read-and-graph` → `2/4 criteria · 36 scenarios short of the bar`
- `bin/engine audit` → `12 invariants checked, 0 violations`; `pytest` → `307 passed`

## The reader is at ~60%, not ~100%. The bar is 97%. (2026-09-20)

Nimish asked to extract all the papers and score them. Before spending ~118 pages of model calls,
`legacy_extract` was measured against a page a person had actually read. It should have been
measured months ago; rule 7 says every model output ships with an eval and this one never had one.

- **The gold**: `supabase/seed/read_gold.json` — all 27 answers on `Advika sept. 1st assessment.pdf`,
  read off the rendered page by eye and checked twice. It deliberately records what the CHILD wrote,
  which for eleven of the 27 is NOT the right answer. A reader that computes instead of transcribing
  scores perfectly against a gold set of right answers and catastrophically against this one.

- **The measurement**, `bin/engine read eval --runs 3`, worst of three runs:

  | prompt | read exactly right | spread over 3 runs | given a row |
  |---|---|---|---|
  | `legacy_extract` v2 | **55.6%** (15/27) | 55.6 – 63.0% | 81.5% (5 missing) |
  | `legacy_extract` v3 | **59.3%** (16/27) | 59.3 – 63.0% | 81.5% (5 missing) |

- **Two claims made earlier in this session are wrong and are withdrawn.**
  1. *"24 of 24 responses read exactly right."* That was the stored rows from an earlier import,
     hand-checked once. A fresh run of the same prompt reads 15–17 of 27. **The perfect score was
     one lucky run of a noisy process** — exactly the trap the `runs:` guard was added to the goal
     to prevent, and I fell into it myself while writing that guard.
  2. *"v3 regressed the reader from 24/24 to 17/24."* Not established and probably false: measured
     head to head over three runs each, v3 is marginally **better** than v2, not worse. The seven
     "wrong" values in the v3 run that prompted the alarm are within v2's own error rate.

- **What the errors actually are.** The reader supplies the *correct* answer in place of the child's
  wrong one: `425 − 38` read as `387` when the child wrote `397`; `342 − 58` read as `284` when the
  child wrote `384`; `250 + [ ] = 300` read as `50` when the child wrote `150`. Every one of those
  turns a diagnosable mistake into a silent "correct", which is the `silently_wrong_at_most: 0.01`
  bar's exact failure mode — currently running at roughly 22%, not 1%.

- **Five of 27 responses still get no row at all** (81.5%, bar 100%), and they are the same five:
  Q5's three boxes and Q7's estimate-and-total. Correcting the paper from 24 slots to 27 was
  necessary and did not fix this — the slots now exist and the reader does not see those as separate
  answers. The paper was one half of that defect; the prompt is the other.

- **A design fault in ADR 0018 itself, found by its own schema limit.** v3's `resolution.why` came
  back holding arithmetic: *"the child's working shows 763 + 427 = 1140, but this is arithmetically
  incorrect … requiring 763 − 427 = 336"*. Asking a model what it could not do invites it to judge
  whether the answer is **right**, and judging correctness is precisely what pulls a transcriber
  into computing. The contract stands, but `resolution` must be about legibility and completeness
  only, and must forbid reasoning about correctness in as many words. That is v4's job.

- **The consequence for the plan.** Reading all 118 pages at ~60% would put a confidently wrong
  diagnosis on sixteen children and fill the graph with answers no child gave. The reader is fixed
  to the bar first, then the corpus is read once. `engine read eval` is now the command that says
  whether it is ready, and it runs in about a minute for Rs 1.40.

## The reader was the wrong kind of tool, and the measurements say so (2026-09-20)

Nimish: *"isn't there an established technology to do this? … obviously someone has solved this
basic issue."* He was right. Five measured attempts at prompt-tuning, and then the research that
should have come first.

- **Every configuration measured against the hand-read page** (`bin/engine read eval`, worst run):

  | configuration | read exactly right | given a row |
  |---|---|---|
  | `legacy_extract` v2 | 55.6% | 81.5% |
  | v3 (ADR 0018 contract) | 59.3% | 81.5% |
  | **v4: stop asking for the printed question, hand it the answer slots** | **63.0%** | **100%** |
  | v4 + overlapping bands for resolution | 63.0% | 100% |
  | v4 + digits masked in the slot list | **51.8% — worse** | 100% |

  The slot list is a keeper regardless of what reads the page: **missing rows went 81.5% → 100%**,
  because a slot the reader cannot find must now come back `not_found` rather than never appearing.

- **The diagnostic experiment.** Asked for six answers on a whole page the reader got 2 right; asked
  for the same six on tight crops it got 4 — and both it gained (`381→281`, `387→397`) were cases
  where it had returned the arithmetically correct answer instead of the child's wrong one. **It was
  not disobeying the instruction to transcribe. It could not see the pencil, and a model that knows
  arithmetic fills an uncertain gap with the answer it can compute.** No phrasing fixes that: the
  arithmetic is not in the prompt, it is in the model.

- **The field's own numbers**, 2026 handwriting word error rate: specialist handwriting OCR 0.9%,
  Azure Document Intelligence 8.67%, AWS Textract 10.5%, Claude Sonnet 11.2%, GPT-5 vision 14.4%,
  Google Document AI 23.3%. **This engine reads on Haiku, smaller than the Sonnet that scores
  11.2%.** Azure reaches ~95% on neat printing and block handwriting, which is what a Grade 2
  child's digits are.

- **ADR 0019**: transcription moves to an OCR engine; the model keeps only the judgement. Not
  because OCR is more accurate, though it is, but because **OCR cannot make our worst error at all**
  — it does not know that 348 + 27 = 375, so it can never write 375 where a child wrote 374. And it
  returns calibrated per-word confidence, which is the thing ADR 0018 established a model cannot
  report about itself. This is CLAUDE.md's own rule, broken: *code where correctness is needed, a
  model where judgment is needed, never the reverse.* Reading a digit is recognition, not judgement.

- **Open and Nimish's:** which vendor. `gcloud` and `aws` are on this machine, no Azure CLI, no OCR
  credential in `.env`. Cost is not a constraint — Textract is ~$15/1,000 pages, so the whole
  118-page corpus is about ₹150.

## Textract reads the page the model could not (2026-09-20)

ADR 0019 built: `adapters/ocr.py`, Ring C, one external service in one file. Nimish created an IAM
user `cornerstone-reader` with a two-action read-only Textract policy, on the existing JSL account
(389517402998, ap-south-1 — the same region as the database), configured locally as the `cornerstone`
profile. No secret is in the repo or in git.

- **Same page, same 17 answers, scored against what a person read by eye:**

  | reader | exactly right | silently wrong | sent to a person |
  |---|---|---|---|
  | `legacy_extract` (Haiku vision), whole sheet | 63.0% | ~7 | 0 |
  | **Textract + geometry** | **82.4%** (14/17) | **0** | 3 |

  **Every one of the 14 ordinary answer boxes is exactly right.** The three that are not are Q5's
  inline fill-in boxes, and all three come back flagged rather than guessed.

- **`silently_wrong_at_most: 0.01` is met — at zero.** That is the bar that protects a child's graph,
  and it is met for the reason ADR 0019 predicted: Textract does not know that 425 − 38 = 387, so it
  cannot write 387 where the child wrote 397. The model's single worst failure is now impossible
  rather than merely rarer. `read_exactly_right: 0.97` is not met (0.824) and the whole gap is one
  question shape.

- **The confidence is real.** `2a` — the `374` that v2 read as `375` and a crop read as `874` — came
  back correct at 99.7%, and the genuinely hard `3b` at 61.0%. Calibrated, per word, from the engine
  rather than claimed by it: exactly what ADR 0018 says a model cannot do about itself, and what the
  approval queue needs.

- **The geometry, and what each rule cost to learn** (`tests/test_ocr.py`, seven cases, no network):
  - *Handwriting only.* Textract tags every word `HANDWRITING` or `PRINTED` — 91 and 157 on this
    page. Without it the printed `452` inside "452 = 400 + [ ] + 12" was returned as a child's answer.
  - *The region is as wide as its question.* A grid question sits in one of four boxes ~0.19 apart,
    so a fixed 0.13 column reached the neighbour and 1a's `155` beat 1b's `245` on a rounding tie;
    narrowing it to 0.085 then made Q5's boxes — 0.12 right of where their question starts —
    unreachable. The printed line's own width says which kind it is.
  - *A labelled "Answer:" box beats a number left in the working.* On 4c the working shows `284` and
    the answer line `384`; the paper's own label says which the child stands behind.
  - *A region that does not add up goes to a person.* Three printed boxes and two numbers found
    means the region was not understood, and assigning positionally would hand a graph an answer
    chosen by an off-by-one. This is why the silently-wrong count is 0 and not 1.

- Suite: **315 passed** — and the previous commit's message claimed 314 while three tests were
  failing, which was written before the run finished rather than after it. The three were stale
  expectations of my own making: the seeded prompt count (17 → 19, for `legacy_extract` v3/v4), and
  two tests whose fake reader still spoke v2's `n`+`part` shape instead of v4's `slot`. One of them
  asserted the reader is handed a COUNT of answers; it now asserts it is handed the slot list, which
  is the thing ADR 0019 actually changed.
- Cost of the whole exercise: **Rs 0.18** of Textract (~$1.50/1,000 pages).

## 63% → 85.2% exact, 100% on the page a person verified, 0 silently wrong (2026-09-20)

Nimish: "lets get that 82.4 to as close to 100 as possible." Four rules found, each one paid for by
a measured regression. `bin/engine read eval --reader ocr` — vendor-blind, so the model and Textract
are scored by one command against the same hand-read page.

| reader | exactly right | to a person | **silently wrong** |
|---|---|---|---|
| `legacy_extract` v2/v3/v4 (Haiku vision) | 55.6 – 63.0% | 0 | ~7 |
| Textract + geometry | **85.2%** (23/27) | 4 | **0** |
| — of which **page 1, the page hand-verified** | **100%** (17/17) | 0 | 0 |

- **A line mixing print and handwriting is an answer; a line of pure handwriting is working.** Q5
  prints "452 = 400 + [ ] + [ ]" and the region also holds the child's scribbles — including a
  second `52` and a second `72`. Textract's per-word `HANDWRITING`/`PRINTED` flag plus its own
  word→line relationships separate the two exactly. It ranks rather than filters: a free-response
  box has no printed text on the answer's line at all.
- **A question's answers lie between that question and the next one.** Matching each part to its own
  line put 5a and 5c on the same anchor, because "452 − 236 = [ ]" matches the line beginning
  "452 − 236 Regroup…" as well as its own. Grouping by question number needs no per-paper
  configuration and is true of every paper ever printed.
- **The region is a box spanning every part, not a column under one.** A grid prints four boxes
  side by side; anchoring on one found a quarter of the answers and flagged the rest.
- **Rows are clustered, never rounded.** The scans sit a degree or two off square, so four answers
  on one printed line came back at y = 0.302, 0.306, 0.310, 0.313. Rounding to two decimals split
  them across two "rows" and put the rightmost first — **every child in that row got their
  neighbour's answer, silently, at 99% confidence.** Caught only because the gold set records what
  the child wrote rather than what was correct.
- **A question is matched on its tokens appearing in order, not as a string.** "250 + [ ] = 300" is
  printed on the page as "250 + 150 = 300" once a child fills the box, and never matched at all.

- **The four that remain are one identifiable class and all four are flagged, not guessed**: Q7 and
  Q8's free-response boxes, where the child's whole column method fills the box and nothing marks
  which number is the final answer. `answer_state = illegible` → a person, never `blank`, which
  would be a claim that the child wrote nothing.

- `silently_wrong_at_most: 0.01` → **met at 0.000**. `read_exactly_right: 0.97` → **0.852, not met**,
  and the whole remaining gap is that one question shape on one sheet.
- Suite **319 passed** (11 in `tests/test_ocr.py`, no network — the skew case and the mixed-line
  case are both pinned). `engine audit` → 12 invariants, 0 violations. Textract spend: **Rs 0.9**.

## Three children, four sheets, 45 hand-verified responses (2026-09-20)

Nimish: "do this over 2-3 full student profiles." One sheet proved nothing — the four rules of the
previous section could all have been tuned to one paper. Three children who each sat the same papers,
every answer read off the page by eye and recorded as what the CHILD wrote.

`bin/engine read eval --reader ocr`, per sheet:

| sheet | exact | silently wrong | the child's style |
|---|---|---|---|
| `G2-CAM-A` | 23/27 (85.2%) | **0** | grid boxes with printed `Answer:` labels |
| `G2-WORD-SEP17` child A | 4/6 (66.7%) | **0** | writes `ans=43` beside the working |
| `G2-WORD-SEP17` child B | 5/6 (83.3%) | 1 | writes `Answer=43` |
| `G2-WORD-SEP17` child C | 3/6 (50.0%) | **0** | **full sentences, no label at all** |
| **total** | **35/45 (77.8%)** | **1 (2.2%)** | 100% given a row |

- **Generalising cost three more rules, and each was a real defect the single sheet had hidden.**
  - *A label is a label, whoever wrote it.* The paper prints `Answer:` beside a box; a child writes
    `ans=43` beside their working. Rejecting anything not purely numeric threw away every
    child-written label and fell back to the column arithmetic above it. Child A and B: 0/6 → 4/6
    and 5/6.
  - *A number in a sentence is a declared answer.* Child C answers every question in prose —
    "Simran took 43 total apples." — with no label anywhere. A handwritten line with words on it is
    a child stating an answer; digits stacked in a column are working, and the page says which by
    whether the line has words.
  - *A question's region must not reach up into the one before it.* The region started a full
    line-height above its anchor, and a word problem wraps, so its bounding box is two lines tall.
    Every region therefore held the previous question's answer as well as its own. Child C, who
    writes her sentences in the gap between questions, scored **0/6** until this was fixed: every
    region held two answers and neither could be told from the other. 0/6 → 3/6.

- **`silently_wrong` is now what the eval leads with**, because it is the bar that protects a child:
  a reading the engine stands behind and got wrong corrupts a graph invisibly; one it flagged costs
  a teacher a glance. **1 of 45 = 2.2%, against a 1% bar** — close, and not met.
  `read_exactly_right` is 77.8% against 97%. Both numbers are honest and both have room.

- **What the remaining 9 flagged responses are**: Q7/Q8's free-response boxes on the Cambridge sheet
  (4), and word problems where the child's sentence and their working were merged by the OCR into
  one line holding two different numbers (5). None is a new class; all reach a person.

- Suite **319 passed**, `engine audit` → 12 invariants, 0 violations. Spend to date **Rs 117.59**
  all-in, of which Textract is a few rupees; the rest was the model experiments this replaced.

## What it would take to reach 97%, measured rather than hoped (2026-09-20)

Nimish: "so do we have clarity on how we get the read exactly right answer to the threshold we
need." Yes, and the clarity is that **tuning will not get there.**

- **Two fixes moved the frontier, and both were real defects rather than knob-turning:**
  - *No minus sign.* A child's `64` came back `-64` — a stray mark read as an operator — and it was
    the only reading in the set that was wrong while claiming to be right. Every answer on these
    papers is a count and primary arithmetic is set so none is negative, so a leading `-` is a mark,
    not a value. That is a property of the PAPER, not of the sum, so reading it off smuggles no
    arithmetic back into the transcriber. 77.8% → 80.0%, and the silent error gone.
  - *The child's final answer comes after their working.* Where a question asks for one answer and
    the region holds several numbers, the last in reading order is the one they stood behind. Only
    for single-answer questions: where a paper prints several boxes, position decides and guessing
    is not allowed. Children A and B went to **6/6**. 80.0% → 88.9%.

- **Then the frontier, measured as a grid of render resolution against the confidence floor:**

  | render | floor | exact | silently wrong |
  |---|---|---|---|
  | 150 dpi | off | 88.9% | 2.2% |
  | **150 dpi** | **70** | **80.0%** | **0.0%** ← shipped |
  | 150 dpi | 85 | 73.3% | 0.0% |
  | 250 dpi | off | **91.1%** | 4.4% |
  | 250 dpi | 70 | 80.0% | 2.2% |
  | 250 dpi | 85 | 73.3% | 0.0% |

  A higher render finds more numbers, which raises exact reads **and** hands the single-answer
  tie-break more wrong numbers to choose confidently. The two bars pull against each other.
  **No setting meets both.** Shipped is the one that protects the child's graph.

- **The 1% bar cannot be measured on 45 responses.** The smallest non-zero rate this gold set can
  express is 1/45 = 2.2%. The goal file already says `gold_responses_min: 300` for exactly this
  reason, and 45 is where we are. More gold is not admin — it is the only way the bar becomes a
  measurement rather than a coin flip.

- **The nine that remain are two named causes, not a long tail:**
  1. **Free-response boxes** (4 of 9, all on `G2-CAM-A` q7 and q8): the child's whole column method
     fills the box and nothing on the page marks which number is final. A rule is possible — the
     number under the rule line — but untested. The honest alternative is a model that never reads
     digits and only *chooses* among the numbers OCR already read, which cannot hallucinate an
     answer because it is picking from a list.
  2. **Faint pencil read at low confidence** (the rest): genuinely at the engine's limit. Image
     preparation before Textract — contrast, deskew, binarisation — is the untried lever, and
     nothing here has tested it.

- **Also fixed, found by the DPI sweep:** Textract refuses an image over 5 MB *or* over 10,000 px on
  a side with `UnsupportedDocumentException`, naming neither the limit nor which one was crossed. A
  WhatsApp scan is a 4,575 × 6,782 photograph before any render. `ocr.fit` now keeps an image inside
  both, degrading quality and then size rather than failing.

- Suite **319 passed**, `engine audit` → 12 invariants, 0 violations.

## The codebase, measured (2026-09-20)

Nimish asked for the confidence level, the size, and whether the quality steps have actually been
taken. Measured, not asserted.

- **Size.** Engine 8,745 lines of Python, tests 3,846, web app 9,719, migrations 1,360, n8n 871,
  goals 410, docs 5,838. Seed is 97,613 but that is the skill registry as data, not code. Call it
  **~18,500 lines written by hand, with 3,846 lines of test beside them.**

- **Tests: 319 passing, 63% line coverage** (`pytest --cov=engine`), and the shape matters more than
  the number:
  - Core logic is well covered — `tags` 100%, `loaders` 100%, `misconceptions` 97%, `verify` 94%,
    `audit` 94%, `items` 93%, `bank` 92%.
  - **The command line is 0%**: `cli.py` (252 statements), `cli_check`, `cli_legacy`, `cli_read`,
    `read_eval`, `stale`. Everything a person actually types is untested, and the three test
    failures earlier today were all in that blind spot.
  - `scenarios_week.py` is 12%.

- **`engine/assess/mark.py` is 247 statements at 0% coverage and nothing imports it.** Built for
  the QR-sheet path and never wired. Named here rather than deleted (rule 3: pre-existing dead code
  is mentioned, never removed by a session that did not create it) — but it is dead, and it will rot.

- **aislop: 32 / 100, "Critical"** — 16 errors, 32 warnings. The label overstates it and the
  breakdown says why: **24 of the findings sit in `research/spike_prompt_gen.py`**, a research spike
  that is not production and holds 15 of the 16 lint errors and all 9 `print()` warnings. The engine
  itself had **2** lint errors, both orphans of this session's own edits, now fixed — `ruff check
  engine/` → `All checks passed!`. What remains against the engine is real but structural:
  4 files over the size ceiling (`items.py` 743, `legacy.py` 570, `loaders.py` 481, `cli.py` 462),
  3 functions too long, 3 with too many parameters, a repetitive dispatch ladder in `render.py`,
  and the standing `ruff format` decision that was never taken.

- **The repo's own best rule is broken by its newest code.** Rule 1 says nothing structural lives in
  code — bands, rungs, thresholds and prompts are all rows, and that is this project's strongest
  property. But `adapters/ocr.py` hard-codes every number it was tuned on: `MIN_CONFIDENCE = 70`,
  the column tolerance `0.085`, the drop `0.095`, the row-clustering band `0.02`, `FIRST_PAGE_MASK`.
  Those are exactly the values a second paper will want different, and today they can only be
  changed by editing Python. **They belong in `threshold` rows.** This is the clearest piece of debt
  in the session and it is new, not inherited.

## Three complements tested; the one I expected to help made it worse (2026-09-20)

Nimish: "use all the features of tesseract well and if see any such complementing capabilities can
help it better." Tesseract itself is not the tool — it is not installed here, the prototype already
tried it and rejected it, its own docstring says it is not for handwriting, and the 2026 benchmarks
put specialist HTR at 0.9% word error against Tesseract-class engines far behind on handwriting.
But the instinct was right: we were using one Textract call out of several available. Three tested.

- **Textract `AnalyzeDocument` FORMS** — finds `Answer: → 155` as a key/value pair directly, which
  is exactly the label our geometry hunts for. But of the 34 pairs it returned, many came back with
  an empty value, and **none says which question its `Answer:` belongs to** — the linkage our
  geometry already solves. At $50 per 1,000 pages against $1.50 it is 33× the cost to replace the
  part that already works. Possible later as a second opinion, not as the reader.

- **Textract `AnalyzeDocument` QUERIES — the real find.** Asked in plain English about the four
  free-response answers geometry cannot resolve ("What number did the student write as the estimate
  for the baker question?"), it recovered **3 of 4**: `7a` 282 at confidence 98, `7b` 282 at 32,
  `8b` 1228 at 66, and `8a` wrong (427, the figure from the question text) at 52. As a primary
  reader that is unsafe — one of the four is a confident-looking wrong answer. As a **second opinion
  on answers geometry has already flagged**, accepted only above the confidence floor or where it
  agrees with a candidate already found, it is the measured-agreement principle again and it is the
  clearest remaining lever on the free-response class. $15 per 1,000 pages, and only on flagged
  answers, so a few rupees for the corpus.

- **OpenCV preprocessing — measured WORSE, and I had called it the most likely lever.** On a phone
  photo: as rendered, 74 handwritten words at mean confidence 90.6 with 9 below 70; deskew found the
  page already square (+0.00°) and changed nothing; CLAHE contrast gave **87.9 mean and 13 below
  70**; both together the same. Textract does its own preparation and ours interferes with it. The
  lever named in the previous section as "the untried lever most likely to help" does not help, and
  that is worth more written down than quietly dropped.

## Grade 3 read for the first time: a photograph, and one silent error (2026-09-20)

Nimish: "Grade 3, before anything is built on the current numbers." Every measurement in this file
until now came from Grade 2 PDFs — flat scans of a printed paper answered in pen. Grade 3 is a phone
photograph: page curved, taken at an angle on a patterned tablecloth, answers in pencil, and the
educator's own tick or cross sitting beside every one of them. Not one had ever been read.

- **The paper is entered — the first Grade 3 paper the engine can read.** `G3-BASE16`, the
  16-question baseline diagnostic all five of Aseem's reports are written from. Check:
  `bin/engine legacy paper supabase/seed/papers/G3-BASE16.json` → `18 questions`. Eighteen slots for
  sixteen printed questions, because question 3 asks for 236 in expanded form and the child writes
  three numbers on one line — one slot per ANSWER, which is the rule `docs/w3-paper-inventory.md`
  exists to enforce. Entered from the printed page by eye, not from the manifest.

  **`8500 − 3647 = 5147` is not on this paper.** It is question 5 of a *second* Grade 3 paper in the
  same folder — "Grade 3–4 Mathematics Quiz", 20 questions, dated 24/7/2026, marked 8/20 — whose
  question 18 is the `56 × 3 = 1518` of Aseem's report. Each Grade 3 child's four photographs are
  two papers of two pages, not one paper of four. That paper is not entered yet.

- **The gold is one whole sitting, read off the photograph by eye**: `supabase/seed/read_gold.json`
  now holds 63 responses over 5 sheets, of which 18 are this Grade 3 sheet. It records what the
  CHILD wrote, including `27 + 15 = 40`, `342 + 579 = 763`, two questions left blank with the
  teacher's cross over them, and one answered with `<` rather than a number.

- **The first Grade 3 number.** `bin/engine read eval --reader ocr --runs 2`, worst of two:

  | sheet | exact | silently wrong |
  |---|---|---|
  | `G2-CAM-A` (flat scan) | 22/27 81.5% | 0 |
  | `G2-WORD-SEP17` ×3 (flat scans) | 14/18 77.8% | 0 |
  | **`G3-BASE16` (phone photograph)** | **12/18 66.7%** | **1** |
  | **total** | **48/63 76.2%** | **1 (1.6%)** |

  `given a row at all 100.0%`, spread over 2 runs `76.2% – 76.2%`. Grade 2's own figure is
  **unchanged at 36/45 = 80.0% with 0 silently wrong**, so nothing below was bought by trading the
  scans away.

- **The approach survives the photograph. The geometry did not need one new rule.** Fifteen of the
  eighteen questions anchored on an angled, curved page at 150 dpi; every answer came back either
  read or flagged; the educator's crosses beside two blank answers were correctly ignored, and both
  blanks were reported as blanks rather than as unreadable. What the photograph broke was three
  things that were broken everywhere and had never been exercised:

  1. **One lost token stopped a question matching at all.** Textract reads the printed
     "234 + 178" as "234 + 78" — the child's own "No." loops over the 1 — and `_in_order` advanced
     only on a hit, so the first token it could not find ended the count: question 15 scored 3 of 8
     against a 0.6 bar and never anchored, and its correct answer was lost. It is now a
     longest-common-subsequence count, which scores that line 7 of 8 and can only ever score a line
     higher than before.
  2. **The answer was required to be the last thing on the line.** The child's `412` came back from
     Textract as `412-`, the printed answer line running into the digits, and `value_of` matched a
     number only at the end of the text — so a page holding a correct answer was recorded as
     **blank**. It now takes the last number in the text wherever it sits.
  3. **A false blank is a silent error, and the eval was not counting it.** `blank` is not a flag,
     it is a claim: the child did not attempt this skill, and it lands in the graph as exactly that.
     `read_eval.score` counted only a wrong `written` value as silently wrong, so both defects above
     scored as quiet misses. It now counts any reading the engine STANDS BEHIND — `written` or
     `blank` — and leaves `illegible` and `not_found` uncounted, because those reach a person.
     Re-scored under the corrected metric, Grade 2's 45 responses are still **0** silently wrong:
     every one of its nine misses is `illegible`.

- **The reader must not claim a blank on an answer it cannot read.** Question 13 is
  "Compare using >, <, or =: 456 ___ 465". Textract found the child's `<` (at 55.7% confidence) and
  the engine threw it away, because `value_of` reads numbers — then reported the region as blank at
  full confidence, on a question the child got right. The paper row already knows the expected
  answer is not a number, so `legacy.symbolic_slots` names those slots and `ocr.answers_for` sends
  them to a person instead. `legacy.mark` carries the same refusal as a second line of defence:
  an expected answer that is not a number now returns `needs_teacher` rather than crashing
  `int("<")` on the whole import.

- **The one silent error, named.** Question 6: the child wrote `763` for `342 + 579`; Textract read
  `363` at **79.8% confidence**, above the 70 floor, so the engine stands behind it. Verified by eye
  at 14× — the first glyph has a flat top bar and a straight diagonal, the same 7 the same child
  writes in `743` on question 4. Raising the floor to 85 would flag it, and STATE.md's own frontier
  measurement says that costs Grade 2 80.0% → 73.3% exact. **It is not retuned from one sheet.**
  This is the class of error the approval screen exists to catch: a reading in the 70–85 band, on a
  photograph, that no amount of geometry will resolve.

- **What else the photograph flags rather than guesses** (all four reach a person, none is wrong):
  question 3's expanded form, which Textract returns as the single token `200+30+6` where three
  slots are expected; question 4, whose printed `287` is overwritten by the child's own erased
  working so the line reads `4. -67 456 + = 743` and no anchor matches; question 13's symbol.

- **Marking already names the mistake.** Question 11 — "A shop had 350 pencils. 128 were sold" —
  the child wrote **238**, and `M_SMALL_FROM_LARGE` predicts exactly 238 for those operands. Check:
  `select responses->0->'misconceptions' from item where item_key = 'legacy/G3-BASE16/11'` →
  `{"M_FACT_PM1": 221, "M_WRONG_OP": 478, "M_FACT_PM10": 232, "M_NO_DECREMENT": 232,
  "M_SMALL_FROM_LARGE": 238}`. That is Aseem's own diagnosis of this child, reached from a row.
  Questions 1 (`40`) and 6 (`763`) match no predictor — they are the unclassified wrong answers
  `engine bank unclassified` was built in W1 to surface.

- **A paper on a rung that lives only as a row now says so.** `engine/assess/ladder.py` maps the
  addition/subtraction ladder; `M1` (multiplication) was added as rows in W1 gate 3 and is not in
  it, so a times-table question raised a bare `KeyError: 'M1'`. `skill_for` now refuses with a
  sentence naming the fix, and the paper's five multiplication items carry their own skill.

- **A sitting can be several photographs.** A Grade 2 sitting is one PDF; a Grade 3 sitting is one
  JPEG per page. A gold sheet may now name `files` in page order instead of `file`.

- Suite **340 passed**, `ruff format --check` and `ruff check` clean, `bin/engine audit` → 12
  invariants, 0 violations, and W1 and W2 were green before and after. Textract spend for the whole
  exercise: under ₹2.

## The teacher approval screen: the page beside the reading, and the correction that feeds it (2026-09-20)

Nimish: "Not a reward for finishing the reader — the mechanism that improves it. Every correction a
teacher makes IS a hand-verified response." Built as `Capture & Mark`, the screen `BUILD-ORDER.md`
has listed as W3's human gate since the plan was written.

- **The queue, and one paper.** `/capture` lists every paper that has been read, newest first, with
  how many answers are waiting; `/capture/<paper>` is one child's copy of one paper. The unit is the
  SHEET, not the file: a Grade 2 sitting is one scanned PDF and a Grade 3 sitting is one photograph
  per page, and a teacher signs off the paper either way. Check, at a laptop and at a phone:
  `cd apps/web && AUTH_DEV_BYPASS=1 npx playwright test --project=screens` → `19 passed`, twice in a
  row, including two new cases that open a real paper and assert no sideways scroll.

- **The page image sits beside the reading, cropped to the answer.** Every reading now records the
  region it was read from (`item_result.raw_read.box`, four page fractions), the engine serves that
  patch from the school's disk — `GET /capture/{id}/page/{n}.jpg?box=…` — and the app proxies it
  behind its own sign-in so the engine key never reaches a browser. The scan never enters the
  database or git (rule 6). Check: `curl -s -o /dev/null -w "%{http_code}"
  "http://localhost:3000/api/scan/<capture>/1?box=0.0124,0.7972,0.3976,0.8972"` → `200`, and the
  9,951-byte JPEG it returns is question 14's answer line with the educator's cross over it.
  A teacher confirming eighteen answers against a whole photograph would not check eighteen.

- **A person is asked what the child wrote, never whether it is right.** The mark is recomputed by
  the same `legacy.mark` the import path uses, because marking these papers is a lookup against
  numbers computed when the paper was entered. The four answers code genuinely cannot mark — a
  comparison symbol, "find the mistake" — are the only ones that ask a person for right or wrong.

- **A correction is a new row, and the engine's own reading survives it.** Proved on the real page,
  through the screen, by hand: Child A's question 6, where Textract read `363` at 79.8% and the child
  wrote `763`. Check:
  ```
  select model_read, human_read, by from read_correction  →  363 | 763 | dev@local
  select status, raw_read from item_result …/6            →  wrong |
      {"child_answer": "363", "answer_state": "written", "confidence": 79.77…, "box": [...]}
  ```
  The mark moved; the machine's reading did not. That is rule 4, and it is also the only way the
  reader stays measurable: overwrite the read and it can never again be scored against the page.
  Two corrections of one answer leave two rows, in order (`tests/test_legacy.py`).

- **The gold set now grows by use.** `read_eval.gold_sheets(conn)` returns the seed file plus every
  correction any teacher has made, matched to the sheet it belongs to by the path both name, with
  the teacher's reading winning where they overlap. 63 hand-typed responses today; the bar wants 300
  with 100 of them phone photos, and the rest should arrive as a by-product of marking rather than
  as a data-entry project. Check: `tests/test_legacy.py::test_a_correction_feeds_the_next_measurement_of_the_reader`.

- **Coverage becomes 100% the moment a paper is signed off**, which is the screen's real argument:
  every answer is either read confidently or confirmed by a person, and the ones in between are
  counted on the screen rather than averaged away. Child A's paper opens at `12 read and marked · 6
  the reader could not settle · 0 signed off`, and the sign-off button says what it will and will
  not cover.

- **A signature now means the person read the thing they signed.** `confirm_results` took every
  candidate answer a child had, wherever it came from — right for Child Growth, wrong for a screen
  showing one photograph. Migration `20260924090000_confirm_one_paper.sql` adds an optional capture,
  `20260924093000_settle_one_paper.sql` makes `resolve_result` use it, and every existing caller is
  unchanged because the parameter defaults to null. Check:
  `tests/test_legacy.py::test_signing_off_one_paper_does_not_sign_off_another`.

- **Grade 3 goes through the real ingest path, not just the eval.** Check:
  `bin/engine legacy import "…/WhatsApp Image 2026-08-16 at 18.02.42.jpeg" --paper G3-BASE16
  --child Child A --section G3 --pages 1` → `16 answers read, 7 for a person`, and `--pages 2` on the
  second photograph → `2 answers read, 0 for a person`. Question 11 came back
  `read '238' wrong M_SMALL_FROM_LARGE` — Aseem's own diagnosis of this child, reached from a row
  with no model involved. A photograph is its own page: `--pages 2` on a one-image file used to
  return nothing at all, because the page filter meant for PDFs was applied to it.

- **Three defects found in the web suite while proving this, all of them older than this session
  and all of them hidden behind each other** (the run is serial, so the first failure skipped the
  rest):
  1. Editing a skill set in the app and restoring it left the set in **draft** — the versioning
     trigger withdraws a ratification whenever content changes, so the restore withdrew it again in
     the same statement that tried to put it back. Every `npm run test:e2e` therefore left
     `engine audit` red. The restore is two statements now, the second touching no content field.
  2. "Ratifying records who did it" had been red since W1 gate 1 closed: it clicks a button that is
     only on the page while a set is in draft, and every set has been ratified since 2026-09-19. It
     makes its own starting state now instead of hoping for one.
  3. The end-of-run sweep called the database dirty over **93 items retired on 2026-09-19** by the
     bank's own review. It compares against what was there before the run now, not against zero.
  Check: `cd apps/web && npm run test:e2e` → `35 passed` then `8 passed`, and `bin/engine audit` →
  12 invariants, 0 violations, after the run rather than before it.

- **`.panel` may now shrink below its content.** A grid item's minimum width is its content unless
  told otherwise, so the queue's table pushed the whole page 353px sideways on a phone. One line in
  `globals.css`, and every panel in the app is safer for it.

- Suite **353 passed** (13 new), `ruff format --check` and `ruff check` clean, `bin/engine audit` →
  12 invariants 0 violations, `bin/engine goal w1-build-the-bank` → 6/6, `w2-assemble-and-print` →
  5/5, aislop engine **69/100** (0 errors) and web **83/100** (0 errors, up from 78 after
  `lib/queries.ts` was split at its 400-line ceiling into `lib/queries-read.ts`).

- **`ENGINE_URL` is now a setting** (`.env.example`), because the app needs the engine for the page
  images and for marking a correction. On this laptop it is `http://localhost:8931`: ports 8000 and
  8011 are both held by other projects of Nimish's, and the engine's own default is 8000.

- **One correction row in the live database was made by `dev@local`** while proving the path
  through the screen. Its value is true — the child did write 763, which is what the hand-verified
  gold already says — so it changes no number; it is named here rather than deleted, because
  deleting a correction is the one thing rule 4 forbids.

## The whole corpus, entered and read (2026-09-20)

Nimish: "Now finish the whole extraction." Every paper in `~/cornerstone/assessments` is now entered
and every in-scope scan has been read once, by the reader in service.

- **What is on disk, counted again.** 84 files / 194 pages. **In scope: 71 files / 108 pages.**
  Excluded: 13 files / 86 pages — 8 SOF Olympiad booklets (multiple choice, excluded from W3's bar
  by `goals/w3-read-and-graph.yaml` and measured separately when there is a measurement to set a
  floor from) and Aseem's 5 typed reports, which are the gold and not the input. **The eighth
  Olympiad booklet was hiding**: `G2/Hriday/Hriday sept. 2nd assessment.pdf` is a 10-page IMO
  booklet, not a Week 2 paper. Hriday has no Week 2 paper, and `manifest.md` says he does.

- **Sixteen distinct papers, every one entered from its printed page.** Four existed at the start of
  the day, of which one was proven wrong and two unchecked. Each of the twelve new ones was read off
  a real scan, question by question, and the four old ones were checked the same way:

  | paper | children | slots | how it was settled |
  |---|---|---|---|
  | `G2-CAM-A` | 4 | 27 | already corrected, verified earlier |
  | `G2-CAM-B` | 4 | 24 | page 2 checked today: 6a/6b/7/8 exactly as entered |
  | **`G2-CAM-C`** | 1 | 20 | new — four grids, two working boxes, two number lines, two word problems |
  | **`G2-CAM-D`** | 1 | 20 | new — the foundational form, single digits |
  | `G2-SEPW2-S1` | 6 | 12 | verified against a real page; the three extra sums on one copy are in the educator's hand, not printed |
  | **`G2-SEPW2-S2`** | 1 | 10 | new |
  | **`G2-SEPW2-S3`** | 1 | 8 | new |
  | `G2-WORD-SEP17` | 6 | 6 → **10** | **page 2 was never entered**: questions 7–10 are on every child's scan and had no slots, so four answers per child were dropped on every import |
  | **`G2-DIAG-B`** | 6 | 15 | new — the 18 loose Grade 2 photographs are not extra pages of another paper, they are this one, three pages each |
  | `G3-BASE16` | 5 | 18 | entered earlier today |
  | **`G3-QUIZ20`** | 5 | 20 | new — where `8500 − 3647` and `56 × 3` live |
  | **`G3-SEPW1-A`** | 2 | 40 | new |
  | **`G3-SEPW1-B`** | 1 | 30 | new |
  | **`G3-SEPW2`** | 4 | 9 | new |
  | **`G4-SEPW1`** | 1 | 40 | new — the same thirteen questions as G3 Level A, checked page by page |
  | **`G4-SEPW2`** | 1 | 9 | new — the same nine as G3 Week 2 |

- **No file was attributed by its name.** The Cambridge level, the Week 2 set number, which of three
  photographs is page 1 and which of a Grade 3 child's four photographs belongs to which paper were
  all read off the page — the printed level band, the header set, the section headings. Check:
  `classify.py` / `classify3.py` (kept outside the repository: they name children, rule 6) →
  38 photographs placed, and **Child A's four are in a different order from every other child's**, so
  a file-name guess would have put two of his pages in the wrong paper.

- **The corpus as read.** `ingest.py`, 71 files, every one with `again=True` so an earlier reading is
  superseded rather than overwritten (rule 4):

  ```
  section  sittings  children  files  answers  correct  wrong  blank  to a person
  G2             30        11     42      484      183     86     29          186
  G3             19         5     29      385       87     58     58          182
  total          49        16     71      869      270    144     87          368
  ```

  **49 sittings, all 16 children, 869 answers, 0 files failed.** Every answer on every in-scope page
  now has a row; 501 of them the engine settled itself and **368 (42%) reached a person**.

- **Nothing has been signed off, so no child has a ladder.** `bin/engine graph` → `0 states`, and
  that is the system working: the graph reads confirmed evidence and nothing else, and the whole
  corpus is queued behind the approval screen. **218 answers that had been confirmed from the
  replaced vision model are superseded** and no longer reach the graph — they are still in the
  database, as rule 4 requires.

- **The graph was still reading superseded evidence, and now does not.**
  `rebuild_child_skill_state` and `next_difficulty` joined `evidence_event` without looking at
  `capture.superseded_by`, so a re-read replaced a reading everywhere except in the ladder it fed.
  Migration `20260924100000_the_graph_ignores_a_superseded_read.sql`. Every screen already honoured
  the flag; the graph is the thing that matters most and was the one place that did not.

- **Two more reader defects, both found by running the corpus rather than by reading code:**
  1. **A stacked sum could not be found at all.** A column sum prints as "53" and then "+ 24", so no
     single line holds the question and every one came back `not_found` — six of ten answers on one
     paper went to a person because the engine could not find the sum, not because it could not read
     the child. `ocr._candidates` now offers each line and each line joined to the one below it.
     Measured on the same sheet, same reader: **4 of 10 anchored → 8 of 10.**
  2. **A child's answer that is not a number was still being called blank.** A child wrote `40` and
     Textract read the word `to`; with no number in the region that came back **blank at full
     confidence** — the engine asserting the child did not attempt the skill. The rule that
     separates it from a real blank is whose hand it is: a child writes INTO the paper's own line,
     an educator's tick or cross sits alone in the margin. Both halves are pinned by tests, because
     the Grade 3 papers carry a cross beside every blank answer and those must stay blank.

- **A one-digit sum is not a two-digit column sum.** `rung_for` read "4 + 3" as width 2 without
  regrouping and filed it under R4 — so a child who cannot add within 10 would have been recorded as
  failing at place-value columns. It returns R1, R2 and R3 now. The Cambridge Level D paper is
  entirely single digits and it is the paper the weakest child in the school sat.

- **Where the flag rate actually comes from**, measured per paper (% of answers that reached a
  person): `G3-SEPW1-B` 87, `G2-CAM-D` 80, `G4-SEPW1` 73, `G3-SEPW1-A` 70 … `G3-SEPW2` 8,
  `G4-SEPW2` 0. The split is not grade or regime — it is **layout**. A paper with one answer per
  question flags 0–35%; a paper of fill-in-the-box grids flags 70–87%, and almost all of it is
  `illegible` rather than `not_found`: the question IS found, and the region holds a different
  number of candidates than it has slots, so the engine refuses to assign them positionally.
  The commonest cause is a child writing their answer twice — once in the box and once on the
  printed `Answer:` line. **Collapsing candidates that agree in value is the next lever**, and it is
  not taken here because two boxes on one row can legitimately hold the same number, and collapsing
  those would trade a flagged unknown for a silent error. It must be measured against the gold set
  before it ships.

- **The reader's own number is unchanged by any of this**:
  `bin/engine read eval --reader ocr --runs 2` → `76.2% exact (48/63)`, `100% given a row`,
  `SILENTLY WRONG 1.6% (1)`, spread `76.2% – 76.2%`.

- Suite **356 passed**, `ruff format --check` and `ruff check` clean, `bin/engine audit` → 12
  invariants 0 violations, web `35 passed` (1 skipped: a rung cannot be opened until a paper is
  signed off) and `8 passed`. Textract for the whole extraction, at $1.50 per 1,000 pages including
  the 38 classification reads: **about ₹18**.

## The paper's own boxes are the fields: 58% → 70% settled by the engine (2026-09-20)

Nimish: "You're not researching how this problem has been solved before, and you're just trying to
reinvent everything from scratch." Correct, and the criticism stands. The established pipeline for
a form is: align the scan to a template, then read each field at its known coordinates — turning a
recognition problem into a cropping problem (PyImageSearch's document-OCR tutorials; OMRChecker's
template layouts; `_labelled_boxes` is the same idea as a form template naming its fields).

This reader had no field layer at all. It found the printed question, drew a region around it, and
hoped the count of numbers matched the count of slots. That is why 42% of the corpus went to a
person: not because the handwriting was hard, but because the engine never knew where the answers
were supposed to be.

**What was built instead of an alignment step.** These papers print a box around the place an answer
goes, so the boxes are the template — and they are on the child's own scan, which means a
photograph taken at an angle is read where its boxes actually are, with no homography at all.
`ocr.printed_boxes` pulls long horizontal and vertical strokes out of the page with morphological
opening (the textbook table-cell recipe), and the closed rectangles are the fields. A paper says
whether its answers live in boxes — `fields: boxes`, a row, nine of sixteen papers.

```
                    answers   settled by the engine   waiting for a person
before                  869        501  (58%)              368
after                   867        606  (70%)              261
G2 (30 sittings)        484        365  (75%)              119
G3 (19 sittings)        383        241  (63%)              142
```

Of the 261 remaining, **39 are structural** — an ordering, an explanation, a tick, a comparison
symbol: answers that are not numbers, which this transcriber cannot read by design and which the
paper row marks so they always reach a person.

- **The rules, each paid for by a measured regression on the 82-response gold set.** The first cut
  put five silent errors in; every one is now a test:
  - a box whose printed label matches a slot is that slot's field, exclusively — and what is
    written in it, and on the `Answer:` line the paper prints under it, is nobody else's candidate
  - a frame round a number line is not a field; a box holding only printed words is the paper
    (a balance scale prints 40 and 30 in boxes, and only the empty pan is the field)
  - ink in a box with no readable word is a doubt, never a blank
  - a claimed question still bounds the question above it
  - working and the answer in one box read as the answer — the last number, the rule the region
    path was already measured with
  - an expanded form Textract returns as one word ("200+30+6") is three answers when, and only
    when, the pieces match the slot count exactly
  - **a number the question prints is an echo, never an answer** — unless the child declared it
    with a label or a sentence, because 52 − 26 really is 26
  - **red ink is the educator's and is inpainted out before the page is read.** Child A's 5147 under
    a red circle came back `147` at 95%, his 533 as `53`. Inpainted rather than whited out: a white
    gap through a 7 leaves a 1. Measured both ways on the gold — same 78.0% exact, and silently
    wrong 3 → 1. It is a row (`ocr.red_pen_mask`), so it can be turned off for a school that marks
    in pencil.
  - a word on the question's own printed line belongs to it, by geometry — Textract gives a child's
    large digits a line of their own, and 5147 sat a hair above the region's top edge

- **`engine read eval --reader ocr --runs 2` → 78.0% exact (64/82), 100% given a row, 1.2%
  silently wrong (1), spread 78.0–78.0%.** The gold grew from 63 to 82 with Child A's Grade 3–4 quiz,
  the worst page in the corpus: a phone photograph under heavy red marking.

- **A sixteenth paper was hiding.** The Grade 4 child's baseline is not the Grade 3 baseline — same
  header, same sixteen-question shape, entirely different questions (division, fractions, numbers
  in words), which the page classifier could not tell apart. His sitting had been read against the
  wrong paper, twelve of sixteen answers came back `not_found`, and that is what surfaced it.
  `G4-BASE16` is entered; the misfiled reading is superseded, not deleted.

- **Still open, and named rather than tuned away:** `G3-BASE16` question 6 — the child wrote 763,
  Textract reads 363 at 80%, on a pencil photograph. One silent error in 82. The 222 non-structural
  flags are dominated by two papers whose answers sit on plain underlines with no box at all
  (`G3-SEPW1-A`, `G4-SEPW1`), which is where a real template — one blank page per paper, aligned
  with a homography — would earn its keep next.

- Suite **362 passed**, web **34 passed (1 skipped) + 8 passed**, ruff clean, `engine audit` → 12
  invariants 0 violations. `adapters/ocr.py` is now 859 lines against a 400-line ceiling and wants
  splitting along the transcriber/geometry seam; an attempt at it this session was abandoned rather
  than half-landed.

## The 261 that reach a person, counted by cause (2026-09-20)

Nimish: "261 is a lot of teacher approvals — how come you aren't able to figure so many out?"
Counted rather than characterised, so the next session works the biggest class first:

```
  39  (15%)  not a number by design — an ordering, an explanation, a tick, a comparison symbol
  20  ( 8%)  the question was never located on the page
 104  (40%)  the region or box count did not add up
  84  (32%)  read, but under the 70% confidence floor
  14  ( 5%)  other
```

- **Only the 39 are a floor.** They are the slots whose expected answer is not a number, which this
  transcriber cannot read by design and which the paper row marks so they always reach a person.
- **104 is the free-response box**: the child works the whole method inside it, so the region holds
  five numbers where the paper asks for two and the engine refuses rather than guess. Not hard
  handwriting — the engine not knowing which number is the answer.
- **84 sit at 50–69% confidence**, one band under the floor, which is a resolution problem: the
  page goes to Textract at 150 dpi and a 40×25-pixel answer inside it is at the limit.
- **16 of the flags were read perfectly and routed to a person anyway** because `legacy.mark` sends
  every `kind: text` item to a human. The judgement ("is Achal correct?") is not checkable, but the
  number the child wrote is, and 5 of the 16 match the key exactly. That is a marking rule, not a
  reading one.

The slots that flag on the most children, with the average confidence where there was one:
`G2-DIAG-B` q11 (5 children, count), `G3-QUIZ20` q3 and q8 (5 each, read at 77–80% and routed by
kind), `G2-WORD-SEP17` q4 (4, at 48%), `G3-QUIZ20` q1 (4, at 44%), `G2-CAM-A` q7b/q8a/q8b (3 each,
count). Four of them are in `scratchpad/flagged-samples.jpg`, each showing the exact patch the
engine read.

**What is not yet tried, and is the reason 70% is not the ceiling:** there is no blank copy of any
paper on disk, so the template half of the standard pipeline — align each scan to an unmarked page
with a homography, read fields at known coordinates — has never been available. It can be
reconstructed by median-averaging the aligned copies of a paper across the children who sat it
(≥4 copies exist for 9 of 16 papers), which removes the handwriting and leaves the printed page.
That is the next session's first move, and `HANDOFF.md` carries the full plan with a target for
each class.

## A rule written this morning was deleting correct answers, and Nimish spotted it on a crop (2026-09-20)

Nimish, looking at four flagged samples: "It's very clear that the child has written 15 + 15 = 30,
and the working for the next one is also there in the birds one. Where is the issue here?"

He was right, and the cause was mine, from earlier the same session.

- **What the page holds.** Textract found Hridhima's answer perfectly: `15`, tagged HANDWRITING, at
  x=0.371, **97% confidence**, sitting in the blank of "Find the missing number: 15 + ___ = 30" —
  distinct from the printed `15+` at x=0.324 and the printed `30` at x=0.435. The engine read it
  and then deleted it.

- **Why.** Child A's quiz prints "24,568 + 37,845 =" and Textract returned the printed `37,845` a
  second time, tagged as handwriting, on top of where it is printed — and the engine stood behind
  it as his answer at 94%. The rule added to stop that dropped **any** number the question
  mentions. But the answer to "15 + ___ = 30" IS 15, and the answer to "52 birds, 26 flew away"
  IS 26. The rule threw away correct answers, at 97% confidence, across two whole papers.

- **The fix is position, not value.** A number is the paper's only where a printed word of the same
  value **overlaps it on the page** — the same mark found twice. Child A's duplicate overlaps its
  printed original and is dropped; a child's answer written in a blank, or below their working,
  overlaps nothing and is kept. The "unless the child declared it with a label or a sentence"
  escape hatch is gone: it was a patch over the wrong test, and it only saved the children who
  happened to write `ans=`.

- **Measured.** `bin/engine read eval --reader ocr --runs 2` → **79.3% exact (65/82)**, 100% given
  a row, **1.2% silently wrong (1)**, spread 79.3–79.3%. Child A's quiz sheet is unharmed at 15/19
  with 0 silent errors, which is what the rule was written to protect.

- **Across the corpus**, re-read in full: **242 waiting for a person, down from 261**, and the
  engine now settles **625 of 867 (72%)** — Grade 2 **79%**, Grade 3 **64%**.

- **The lesson worth keeping.** Both defects were in the same rule, one day apart, and the gold set
  caught neither: Child A's duplicate because his quiz was not yet in the gold, and this one because
  `G2-DIAG-B` still is not. **A person looking at four crops found in a minute what 82 hand-verified
  responses did not.** The approval screen is not only how the gold set grows — it is the only
  place a rule that is wrong in a way the gold cannot see will show itself.

## The 242, worked: 242 → 229, one silent error found by looking, and the plan that did not survive (2026-09-21)

W3, gate 2 (the reader). Started from the four checks green: W1 6/6, W2 5/5, audit 12/0, gold
79.3% (65/82), 1.2% silently wrong, no spread.

```
                         answers   settled by the engine   waiting for a person
start of session             867        625  (72%)              242
end of session               867        638  (74%)              229
```

**Nimish, 2026-09-21: "let's keep this coverage for now and move ahead."** 229 is the coverage W3
carries into the graph half; the reader is not worked again until the graph has been proven.

- **Every flag now says why** (ADR 0021). `bin/engine read waiting`:
  ```
   78 (34%) under the confidence floor
   74 (32%) the region held a different count of numbers than the question has answers
   30 (13%) the answer to this question is not a number             <- the floor, with the 11 below
   20 ( 9%) the printed question was not found on the page
   11 ( 5%) read cleanly; the judgement is the teacher's
   16 ( 7%) no number in the handwriting / ink but no number / every number printed
  ```
  The count by SQL inference said the biggest class was "five numbers where the paper asks for two".
  Counted by the engine's own branch: **57 of the 74 hold FEWER numbers than the question has
  answers** — the engine is not seeing the child's answers, not drowning in them.
- **The second look** (ADR 0020): a flagged answer is cropped out and re-read at 500 dpi.
  `bin/engine read eval --reader ocr --runs 2` → **81.7% exact (67/82)**, 100% given a row,
  **1.2% silently wrong (1)**, spread 81.7–81.7%. It recovered 7 of 83 under the floor, not half,
  and two guards were each paid for by a silent error on the gold (fewer digits than the page saw;
  the echo test again on what the crop resolved).
- **"Find the mistake" is marked where the number agrees with the key.** 5 of 14 read the key
  exactly; the other 9 read a fragment or a printed operand and still go to a person.
- **A silent error in the corpus, found by looking at crops.** `G2-CAM-C` q2d "29 + 4 =" was
  recorded as **64 at 99.8%** — the child's answer to 2b (58 + 6). She wrote 33. A box claimed by
  its printed label had its words withdrawn from the page but the box itself was still offered to
  the unlabelled slots as a field. Fixed in `answers_for`, pinned by a test built from that page's
  geometry that fails without the fix. Re-read of all 71 files: **exactly 2 readings of 867
  changed** — 2d wrong(64) → correct(33), 2b flagged → correct(64). The gold set does not hold this
  paper; the crop sheet did. That is the second session running where this happened.
- **Measured and rejected, recorded where they would be retried:** the page at 200 dpi (84.2%
  exact, **5 silently wrong**); at the scan's own 198–282 dpi (76.8%); white margins round the crop
  (80.5%, 2 silently wrong — a margin makes a fragment readable too). `render_pdf.DPI` and
  `adapters/ocr.py` carry the numbers. `printed_boxes` had two sizes in pixels; they are fractions
  of the page now (unchanged at 150 dpi).
- **The blank-page template, measured before building on it.** Reconstruction works: median of the
  aligned copies, ORB + RANSAC, 300–1000 inliers a page, clean printed pages for 9 papers
  (`scratchpad/template.py`, not in the repo). But the printed question failed to anchor **0 times
  in 95** on the gold sheets, the box path already claims 18 of 20 fields where boxes exist, and the
  flags it would fix are not the ones that exist. `G3-SEPW1-A` and `G4-SEPW1` are the same printed
  paper (three copies, not two and one). Not built.
- **Ten crops, one or two per cause** (sent to Nimish): 4 are the floor (explanations, a
  true/false table, two column workings with no answer line), 2 are legible but under the floor
  ("A 51"; "3556" under a red tick), and **4 are the engine misreading page structure on answers
  any person reads instantly** — the wrong-box one above; `G4-SEPW1` q7 (two boxes wider than
  `ocr.box_max_width`, "Answer: 252" / "Answer: 15"); `G3-SEPW1-A` q5 (nine answers in nine small
  printed boxes, one found); `G4-SEPW1` q3 (the child's digits sit INSIDE the printed question line,
  so the question never matches). `G2-CAM-C` q1b reads "98" at 74.8% where the child probably wrote
  48 (a closed-top 4) — a person should look.
- Suite **389 passed**, ruff clean, `engine audit` 12/0, web **34 passed (1 skipped) + 8 passed**,
  lint's 5 errors all the pre-existing ones in `library/page.tsx`. Textract for four corpus re-reads
  and the probes: about ₹80.

## The approval screen, first used for real: what it showed Nimish, and what that found (2026-09-21)

Nimish opened `/capture` (local, `web` + `engine api` in `.claude/launch.json`, dev sign-in) and
corrected and signed off Child A's Grade 3–4 quiz. **16 corrections, every `POST /capture/correct`
→ 200.** Then: *"I am seeing a lot of entries with ~80% confidence … extremely easy to make out."*

- **Most of what he was checking was never in his queue.** Of 225 waiting, 11 read at 70%+; the
  108 answers the engine *settled* at 70–89% sat on the same page as the doubtful ones, each saying
  "It is 82% sure", which reads as a question. The paper page now shows what needs a person first
  and folds the engine's own marks under "N answers the engine marked itself — open to check"; no
  percentage is shown on a reading the engine stands behind; the list's "Waiting" column (which
  counted every unsigned answer) is "Not signed yet". Checked in the pane: 32 of 32 crops load,
  page 1 folds 11, page 2 folds 3. `tsc` and `eslint` clean on the changed files.
- **His first correction outside the seed killed the eval.** A correction on a paper the gold did
  not hold became a new gold sheet named "~/cornerstone/…", joined to the assessments folder
  unexpanded → a file that does not exist → `cv2.imencode` on an empty image. Behind it: a Grade 3
  sitting is one photograph per page, and a correction on photograph 2 was matched only against
  a sheet's FIRST file and read as page 1. `sheet_pages` expands the name and returns the paper's
  page number; corrections are matched against every file of a sheet. Test pins both.
  `bin/engine read eval --reader ocr --runs 1` → **81.9% exact (68/83)**, 1.2% silently wrong — the
  gold grew by one response from his corrections.
- **The floor, measured again, on 83** (runs 2, spread 0 each):
  ```
  floor 70   81.9%   silently wrong 1     <- stays
  floor 60   86.8%   silently wrong 2     72 recorded as "2"
  floor 50   87.9%   silently wrong 4     + 282 as "1", 84602 as "3892"
  floor 40   90.4%   silently wrong 4
  ```
  Every error a lower floor lets through is a FRAGMENT of the right number. Easy answers under the
  floor stay with a person until something can tell a whole answer from a piece of one.
- **The engine service is started by the desktop app and stops when its tab is closed.** It was
  stopped 29 minutes into his session and every crop returned 503; his corrections had all landed
  first. Leave the `engine api` tab open.

## The question bank on screen, and a paper with its QR (2026-09-21, a side session beside W3)

Asked for by Nimish for the founder: "an interface for people to see" the ~12,000 questions and how
a paper with a QR is made from them. A W1/W2 screen, not a W3 gate — W3's gate did not move here.

- **`/library` shows the whole bank.** A grid of all 17 skill sets × 4 levels by name, each count
  a link to its questions; 50 per page with paging; all 12 kinds of question drawn as the child
  sees them. Before this, 8 of the 12 kinds printed as "undefined + undefined" (~5,000 questions).
  Check: e2e `every kind of question in the bank is drawn with its own numbers` — fails on the old
  drawing ("265 undefined undefined"), passes now.
- **A mistake is named for the question's own operation.** `M_WRONG_OP` has three names (one per
  + − ×) and `misconceptionNames()` picked one arbitrarily: "92 − 4" showed "Added instead of
  multiplying". `mistakeNames()` keys by `code@op`. Check: e2e `a mistake is named for the
  question's own operation` — fails on the old lookup, passes now. **Still open:** number walls
  (216) and two-step word problems (1,093) record no operation, so their `M_WRONG_OP` shows the
  code, not a guessed name; and `/capture/[id]`, `/growth/[id]` still use the arbitrary lookup.
- **`/worksheets/<code>` shows one paper**: the page as printed (QR on every page, from the PDF via
  `GET /sheet/{qr}/page/{n}.jpg`), five one-line facts from its rows, and its answer key. Check:
  `uv run pytest tests/api/test_week_routes.py` → 6 passed; e2e `a paper opens from its code…`.
- **Every `<table class="grid">` in the app had its header out of line with its columns** —
  Tailwind's `grid` utility set `display: grid` on the table. `table.grid { display: table }`.
- `queries.ts` went past 400 lines; the bank and paper queries moved to `lib/queries-bank.ts`.
- The approval e2e test left `approved_by` on unapproved sheets; it now restores it (9 sheets cleared).
- Commands, 2026-09-21: playwright (e2e bank/paper + all screens) → **27 passed**; `bin/engine audit`
  → 12 invariants, 0 violations; `tsc --noEmit` and `eslint` clean. Not committed.

## Stopped, restored, researched (2026-09-21, evening)

Nimish: *"You just keep on shuffling between different things, finding errors … stop … research how
this kind of problem needs to be solved."* Stopped. What is true now:

- **The stencil is off.** Its blanks are parked in `data/paper-templates.parked/` (not deleted), so
  `stencil.read_page` falls back to the old path. Measured on its re-read: it settled 16 more answers
  and fixed 6 silent "blank" claims, but put in 5 new silent errors (812→752, 65→15, 600→46, 35→5,
  13→3) — the extra ink it found made the "last number is the answer" rule pick working. The corpus
  was re-read with it off: **0 settled answers differ from before it** (`diff.py before-stencil
  after-restore`), `read eval` → 81.9% (68/83), 1 silently wrong.
- **A re-read had taken six of Nimish's corrections** (Child A's quiz p2, q11–16) and one from
  2026-09-20, because the guard protected signed-off papers only. `legacy.worked_on` now protects any
  capture a person has signed off OR corrected (test pins both). The seven were re-applied under
  their original corrector; `read_correction` rows on live readings: 18 of 18.
  `bin/engine read waiting` → **225 of 867 waiting, 642 settled**.
- **Research**: `research/reports/Reading handwritten worksheet answers.md` (notes in
  `research/research_notes/`). Its finding: every working system fixes WHERE an answer is (a box drawn
  once per layout, or printed boxes found via corner marks + QR) before reading it; the engine infers
  location from the ink, and 94 of the waiting answers are location failures, not reading ones.
- Suite, ruff: clean on the files touched. No reader change ships until Nimish agrees the approach.

- **An unsure reading keeps its guess** (`raw_read.guess`, both reading paths): what the reader
  thinks it saw, for a person to confirm with one click, never marked from — `mark` reads
  `child_answer`, which stays empty. Test pins both halves. `read eval` unchanged: 81.9% (68/83),
  1 silently wrong. Suite **412 passed**.

## One page per question; the bank can print every kind it holds (2026-09-21, same side session)

Nimish, on the list: "+4 more isn't opening … all these questions should have a page which
highlights everything about that question and option to correct/edit something along with a
snippet of how it will appear in the paper … simpler and clearer."

- **8 of the 12 kinds in the bank could not be printed at all** — `bank.item_from_row` looked up
  working space in `verify.FORMATS`, which knows four kinds, so any paper drawing on the other
  ~5,000 questions raised `KeyError`. Every paper printed so far was subtraction, which is why it
  never showed. `assess/layout.WORKING_LINES` holds all 17 kinds the generators make, and
  `test_items` fails if a generator disagrees with it. Check: `test_every_kind_in_the_bank_can_be_printed_again`
  fails on the old lookup (`KeyError: 'balance_scale'`), passes now; `bank.sheet` printed
  WORD.BUDGET, MENTAL.BRIDGE_EQ (walls) and ESTIMATE.ROUND10 papers.
- **Number walls printed broken** — 24 mm bricks under four 8.4 mm answer boxes. Bricks are now as
  wide as the widest answer. Check: `test_a_number_wall_keeps_every_answer_box_inside_its_brick`
  (measured in Chromium) → 3 spilling bricks before, 0 after.
- **`/library/<key>`**: the question as it prints (`GET /bank/item/{key}/printed.png`, the paper's own
  `render_item` and CSS), its answer, every wrong answer with its mistake and example, the level's
  rule, where it came from, and two actions. **Correct the wording**
  (`POST /bank/item/{key}/correct`, `engine/question.py`) keeps every number (code compares them), so
  the answer cannot change; it refuses a changed number, "borrow", an unchanged sentence, no reason,
  and the three kinds that print from numbers alone. The correction is a new row
  (`item.corrected_from`, migration `20260925090000`, applied) and the old one retires with who and
  why; exposures carry over. `bank.recheck` accepts a correction's own key. **Remove** moved here.
  The list is question · answer · kind, each opening its page.
- Mistake sentences follow names: an example that differs by operation is not shown on a question
  that records none (2 of 60 names).
- Commands, 2026-09-21: `uv run pytest -q` (engine) → exit 0, 413 passed; playwright e2e bank/question/
  paper + all screens → 29 passed; `bin/engine audit` → 0 violations; `bin/engine bank recheck` →
  0 mismatches; ruff clean.
- **Open:** walls and two-step problems record no operation, so their wrong-operation mistake shows
  its code; `engine bank sheet` fails for the G2+ reasoning sets; every paper is titled "Addition and
  subtraction". The two engine-side items are queued as tasks. 7 word problems say "1 marbles" —
  each is a one-minute correction on its page.

## Papers are titled by what they practise; the reasoning sample sheets print (2026-09-21)

- **Every paper was titled "Addition and subtraction"** — head, footer and every "continued" line —
  so a Grade 3 multiplication paper said addition and subtraction. `Sheet.title` now carries the
  skill set's own name (`skill_set.name`) from both builders — `assemble.render` (a child's paper)
  and `bank.sheet` (a staff sample); the head and the "continued" line print it, the footer keeps to
  school and grade so a long name never wraps the page number. A name is escaped for the page's
  HTML and for the JavaScript template literal that lays it out.
- **`bank.sheet` crashed on REASON.EXPLAIN and REASON.FIND_MISTAKE** — rungs X1/X2 carry band "G2+",
  which the `GRADE_TITLE` table did not hold. A band is now said in words by rule ("G2+" → "Grade 2+").
- Checks, each read back from the printed PDF:
  `test_every_sample_sheet_is_titled_with_its_own_skill_set` (every skill set x difficulty with ≥ 8
  questions — 68 sheets) failed first on "Grade 1 · Addition and subtraction" for ADD.1D.BRIDGE10;
  `test_a_multiplication_pack_is_titled_multiplication` (a real per-child MUL.1D pack) failed on
  "Grade 2 · Addition and subtraction"; both pass. Page 1 of one sheet per skill set (17) was looked at.
- `test_fill_native_honours_a_kind_list_across_the_shortcut_families` failed once in the first W2 goal
  run and passed in 60 direct runs and three full suites: it counted only questions not already in the
  live bank, so a nearly-full family could vanish from a run. It is now seeded and dry.
- Commands, 2026-09-21: `cd packages/engine && .venv/bin/python -m pytest` → 415 passed;
  `bin/engine audit` → 12 invariants, 0 violations; `bin/engine goal w2-assemble-and-print` → 12/12
  scenarios, 5/5 criteria, GOAL ACHIEVED.

## The website builds without a database (2026-09-21)

- Every Vercel Preview build since 2cd0797 failed: `next build` loads every route to read its settings,
  Preview has no DATABASE_URL, and `apps/web/lib/db.ts` threw at import. Now a missing URL is reported
  at first use — a query or `sql.json` — with the same instruction; with a URL nothing changes.
- Checks: on a clean checkout with no `.env` and no settings, `npm run build` failed exactly as on
  Vercel before the change and exits 0 after; importing the module and calling it throws the
  instruction; `gh pr checks 1` at 72d7d00 → engine pass, web pass, Vercel pass.

## The website is published with the engine's address (2026-09-21)

- `deploy/go-live.sh` (Nimish ran it) added ENGINE_URL/ENGINE_KEY to Vercel Production at 07:47Z, but
  the live website had been built at the 07:26Z merge, and Vercel applies settings only to new builds.
  A redeploy failed "No Next.js version detected": the project's Root Directory was `.`, and earlier
  builds had passed only on a restored build cache. Root Directory is now `apps/web` (Vercel settings,
  with Nimish's yes); the redeploy built clean — no cache, `npm install` and `next build` from
  `apps/web/vercel.json`, "Detected Next.js version: 16.3.5" — and is aliased to
  https://cornerstone-assessment.vercel.app. The root `vercel.json`, now never read, is removed.
- The engine at https://3-111-248-87.sslip.io, called with the key: `GET /health` 200;
  `/bank/item/WP1-7eecdd4c/printed.png` 200 image/png; `/sheet/CS167023/page/1.jpg` 200 image/jpeg
  (160,659 bytes, identical to the Mac's); without the key 401.
- Not yet proved: a signed-in page on the live website drawing its picture through the engine. The
  only login is Nimish's (`app.staff` holds one person).

## The live website: one serif font, menu items visible on hover, bank counts that open (2026-09-21)

- Published by PR #2 (merge faf8178, 08:29Z); the production build ran from `apps/web` (Root Directory)
  and is aliased to https://cornerstone-assessment.vercel.app. Check: the live CSS holds "Source Serif 4"
  and none of JetBrains/Young Serif/Atkinson; its `a:hover` sits inside `@layer base`.
- Tests: "a menu item stays readable while the pointer is on it" fails on the old unlayered rule
  (rgb(38, 36, 31) on rgb(38, 36, 31)) and passes; "a count on the skill map opens exactly those
  questions"; playwright screens + e2e bank/question/paper/skill-map 31 passed.
- Seen in the Vercel logs: POST /login and page loads timed out 13:05–13:11 IST ("canceling statement due
  to statement timeout") while the engine's full test suite and the W2 goal were running against the
  same database. The tests share the live database; long runs there can stall the live site.

## Step 1 of five — the site answers (2026-09-21, afternoon)

- **The hang, reproduced and fixed (ADR 0024).** Through the transaction pooler (the live road), queries
  stacked on one connection: `node scripts/check-pooler.ts` (8 value-less `select now()` at once, the app's
  own `db.ts`) → **2 of 8 answered** before, **8 of 8** after `max_pipeline: 0`, three runs. The Question
  bank's own four queries: hung (3 of 3) before, 1.4 s after.
- **Before, from the platforms' own logs** (`bin/engine live check --since 3h`, 15:02 IST): 42 requests ·
  16 timed out · database 3 statement timeouts · slowest checkpoint 203.5 s. Exit 1.
- **Tests on a local copy (ADR 0025):** `bin/testdb` → "copied: 45 tables, 45607 rows, every count equal to
  live" (9 s). Engine suite on the copy: 421 passed in 23.9 s. `tests/test_test_database.py` refuses a
  remote TEST_DATABASE_URL (subprocess exits "refusing to run tests against a database that is not on this
  machine").
- **Browser tests on a production build** (Playwright starts `next build && next start` and its own engine,
  both on the copy, a real session cookie): 55 passed, 1 skipped. Each new test was watched failing on the
  old behaviour first: with table links pre-loading, 15 non-menu pages loaded ahead; with the old
  error-swallowing staff check, a locked `config` sent the page to /login.
- **Damage the old tests did to live rows, found while writing step 2:** `SUB.2D.EXCH` was rewritten 153 times
  by the e2e suite; since 2026-09-19 20:38 its Easy level read "edited in the app" under "Ratified · Nimish
  Shah". Restored from the seed in step 2 (which withdraws that signature, correctly).
- Shipped: PR #3 merged 09:39Z (`67c14ae`); Vercel production Ready; the live JS carries the new error screen;
  an unsigned `/library` redirects in 2 s. `bin/engine goal s1-site-answers` → 5/6; the sixth is the live
  click-through, which needs a person signed in on the public address.

## Step 2 of five — the skill map as outcomes (2026-09-21)

- `bin/engine spec outcomes` on the live wording before: **11 of 17** (six too long, "algorithm", "planted
  misconception", one starting "Given"). The 17 rewritten sentences: 17 of 17 by the same rule (20–28 words).
- Applied to the copy with the step's one-off script (outcome + the restored Easy level): 18 rows changed,
  each versioned and waiting for approval.
- `tests/s2-skill-map.spec.ts` on a production build against the copy: 6 passed — every skill by grade led
  by its outcome, every link on the map opens (all 200), all 17 skill pages show four levels with a sentence
  and a drawn question, words-only editing withdraws approval, one-page approval in the approver's name,
  phone widths without sideways scroll.
- Known and intended: `tests/test_goal.py::test_every_invariant_holds` and `engine audit` report 17 specs
  waiting for approval until a person approves them on `/skill-sets/approve`.

## Step 3 of five — every question on a numbered worksheet (2026-09-21)

- **The library, on the copy:** `bin/engine library check` before → "0 worksheets · 0 of 68 skill-levels
  ready · 136 problems"; `bin/engine library build` → "made 1123 · retired 0"; check → "1123 worksheets · 68
  of 68 skill-levels ready · 0 problems"; `build --dry-run` → "would make 0 · would retire 0".
- **The first deal was wrong on real data, and the made-up tests had not caught it:** a level with two kinds
  got 8 of one and 4 of the other per worksheet, and two Grade 1 levels used questions 4–6 times. The deal now
  fixes each worksheet's share of each kind first, then deals each kind in laps. Pure tests over every level
  size the bank holds (22–216) plus the real build: 0 problems.
- **Removing a question from its page retired it in the database only; worksheets now follow in the same
  transaction** (`question.remove` / `question.correct` → `library.build(only=level)`, `POST
  /bank/item/{key}/remove`). A patch that would leave a small level uneven deals the level afresh (found by
  `test_removing_a_question_retires_it_and_replaces_the_worksheet_it_was_on`: 4–8 uses, two worksheets alike).
- **A worksheet prints:** `GET /worksheet/{code}.pdf` renders on first request with the paper renderer (its
  code in the QR), then serves from disk — R5-H03, R1-E04 and X2-A07 looked at page by page.
- **The website:** the Worksheets page leads with the library (every skill × level, a level filter, the list);
  a skill's page lists its worksheets with Easy/Medium/Hard/Advance; a worksheet's page shows its twelve
  questions and answers with Print (PDF); a question's page names its worksheets.
- **Tests:** engine 451 passed + the audit's known 17 waiting approvals; browser 61 of 61, three runs in a row,
  the library whole after each. Found on the way: with the loading screen, a page first arrives as "Loading…"
  and streams in — two tests read too early and now wait for content; test cleanups now restore a level's
  worksheets exactly (`tests/library-state.ts`).

## Step 4 of five — the validation queue (2026-09-21)

- **The corpus re-read for guesses** (`bin/engine read again`, driver rebuilt from capture rows, papers a person
  signed off or corrected skipped): "71 read · 0 missing · 0 failed · 0 settled answers changed". `read waiting`
  before and after: 225 of 867. Unclear readings carrying the reader's guess: 0 of 194 before, **73 of 194** after
  (the 20 not-found and 11 judgement answers have none, by design). `tests/test_read_again.py` (stand-in reader):
  every live capture read from its own rows, a changed settled answer named, one failing file does not stop the rest.
- **`/capture/check`** (menu: Check answers): one waiting answer at a time — the crop, the question, why it is here
  in words, the guess as "Yes, the child wrote 47"; type, or "Nothing is written here"; Right / Wrong / Blank for a
  judgement; one spot-check per paper (smallest md5 of the answer's id among settled written answers, shown until a
  person has looked). The Capture list shows each sheet's score once nothing on it waits.
- **Found and avoided:** the paper screen's Right/Wrong/Blank (`resolve_result`) signs off the whole page. In the
  queue a person sees one answer, so the queue judges that answer only (`judgeOne`) and records who. And
  `max_pipeline: 0` rules out postgres.js `sql.begin` (UNSAFE_TRANSACTION) — `judgeOne` is one statement; noted in
  `db.ts`.
- `tests/s4-validation-queue.spec.ts` on the copy: 7 of 7 — the count equals the engine's own, a real guess confirmed
  in one click in the person's name, typed and blank answers marked, a judgement leaves the paper unsigned, a
  spot-check, a sheet's score, the menu and a phone.
- Live corrections are all "dev@local" (25, made through the local preview's development sign-in on 2026-09-20/21):
  the person is lost that way. The local preview now reads the copy (`.claude/launch.json`), so validations happen on
  the live site, each in the name of whoever signed in.

## Step 5 of five — the bank explains itself (2026-09-21)

- `/library` leads with three sentences — what the bank is (with the live counts), how a question is made and
  checked, and its ties to a skill, a level, a kind and a worksheet — and every question row shows its worksheets as
  links. `tests/s5-question-bank.spec.ts`: 3 of 3, every link on the first page opens (200).
- All browser tests on a production build against the copy: 71 passed, 1 skipped. Engine: 454 passed plus the audit's
  17 skills waiting for approval.

## The five steps, where each goal stands (2026-09-21, 16:45 IST, after PR #6 merged as 3c81b66)

`bin/engine goal <name>`, every criterion that does not need a signed-in person on the public address passes:

```
s1-site-answers              4 of 6 · the engine suite now also reports the 17 skills waiting for approval; the live click-through
s2-skill-map-outcomes        2 of 4 · approval of the 17 skills; the live click-through
s3-worksheet-library         4 of 5 · the live click-through
s4-validation-queue          3 of 4 · the live click-through
s5-question-bank-explained   1 of 2 · the live click-through
```

Checked on the public address without signing in: every protected page redirects to sign-in in under 2 s; the live
engine prints R5-H03 (200, 140 KB, 2.1 s first time, 0.08 s after) and serves a waiting answer's handwriting crop
(200, 0.75 s); `bin/engine live check --since 2h` → 5 requests · 0 timed out · 0 failed · database 0 statement
timeouts, slowest checkpoint 38.5 s (still slow for a small write; the free tier's disk allowance — watch it).

## The approval page's handwriting, on the live link (2026-09-21, evening)

- **Broken on the public link.** Nimish opened a Grade 2 paper (`/capture/123f4ce2…`, two WhatsApp pages) and every
  picture was a broken image. Vercel's own log (`vercel logs --environment production --query 05167c88`): 12 × 502
  at 17:47:45 and 11 × 502 at 17:51:11 IST — every crop and both pages of one page load — then single requests 200.
  The engine answers the same request alone in 0.3 s. The 502 is Caddy's: the engine behind it had been killed.
- **Cause, reproduced on the copy.** A WhatsApp "scan" is a photograph in a 36 × 54 inch PDF page, drawn at 150 dpi
  as 5490 × 8138 (45 MP, 134 MB decoded). Each picture request drew the whole paper for itself (`lru_cache` lets
  twelve callers miss at once), and every crop decoded the 45 MP page again. A 12-thread cold-cache burst of
  `legacy.page_crop` on that capture (the session's `burst.py`): **1 at once 610 MB · 12 at once 3,315 MB, 6.6 s**,
  on a 2 GB server. The step-4 check above ("serves a waiting answer's handwriting crop, 200, 0.75 s") asked for one
  picture; the page asks for a dozen at once.
- **Fix, display path only** (`legacy._rendered` / `page_crop`; the reader's `render_pages` and `crop` unchanged): a
  page is shown at most 2400 px on its long side — about 200 dpi on A4, above the 150 it is read at, so A4 (1755 px)
  is untouched — and one lock, so a burst draws a paper once. Same burst after: **12 at once 908 MB, 0.7 s · 24 at
  once 897 MB**. The two unclear answers' crops (q4, q7) compared at on-screen size, before and after: the same
  legibility; the new crop is 1420 × 329 for a 400 px box.
- `tests/test_legacy.py`: `test_a_page_is_shown_no_larger_than_a_screen_needs` (WhatsApp page → 2400, A4 → 1755) and
  `test_a_burst_of_requests_for_one_paper_draws_it_once` (8 requests → 1 drawing; 8 drawings before the fix). Engine
  suite: every test passes except the audit's 17 skills waiting for approval.
- **Live, after PR #8 merged and `deploy/go-live.sh` (exit 0, 970e605):** the approval page's own load — both pages
  and ten crops of capture 05167c88, twelve at once, against https://3-111-248-87.sslip.io — **12 of 12 × 200**,
  each 5.4 s on the first view (the server drawing the 45 MP page once), then 12 of 12 in ≤ 0.29 s. A full page is
  388 KB instead of 3.2 MB.
- **The 5 s first view, removed at its cause** (the same evening): the page was still drawn at 45 MP and only then
  shrunk. `render_pdf.render(long_side=)` now draws it at the size it is shown (A4 stays 150 dpi, 1755 px — a cap
  never enlarges); `legacy.render_pages(long_side=)` passes it through and shrinks a photograph; the reader's calls
  pass nothing and draw exactly as before. Burst on this Mac: **1 at once 278 MB · 12 at once 374 MB, 0.2 s** (was
  908 MB, 0.7 s). Crops q4, q7 compared again: same legibility. `test_render_pdf.py::test_a_long_side_…`; engine
  suite on a fresh copy: **459 passed** — the audit's invariant is green since Nimish approved the 17 skills
  (`bin/engine audit` on live: 12 invariants checked, 0 violations).

## A typed answer that is not one number is marked, not sent back to a person (2026-09-21, evening)

- **Reported by Nimish from the live queue:** typing `12,34,45,78` for "Arrange from smallest to largest: 45, 12,
  78, 34" (G2-DIAG-B q10) was never accepted, for any child. Cause, traced: `mark` stripped the commas as if the
  answer were 1,264, the single number 12344578 met a key that is not a number ("12, 34, 45, 78"), and every such
  answer went straight back to a person. On live, **29 waiting answers** had such a key — True 8, Not true 7, the
  order 5, `<` 4, even 4, 1/2 1 — and 3 had already been typed and stayed stuck.
- **Fix, in `mark`, the one function both the reader and a correction go through:** a key that is not one number
  is marked by its own form — numbers in order by the numbers in order, a sign by the sign, a word or fraction by
  its letters ignoring case and spacing. Only a person's reading reaches this branch: `ocr.answers_for` hands these
  slots over with no guess. The queue's line for them now says what to type ("the numbers in order, the sign, or the
  word the child chose"). `test_a_typed_answer_whose_key_is_not_a_number_is_marked_by_the_keys_own_form` (failed
  before: `needs_teacher`); engine suite 460 passed.
- **Clicked through on the local preview against the copy:** `/capture/check?from=5`, the q10 answer, typed
  `12,34,45,78`, Save → "208 answers left" (was 209), the row `correct`, the reading kept as a `read_correction`.
- The 3 stuck answers stay in the queue; one Save each settles them once this is live (2 come out right, 1 wrong).

## The engine settles only a right answer on its own (2026-09-21, night — ADR 0029)

Placed here rather than at the end so it merges cleanly beside step 7's notes; it is the newest section.

- **Why.** A random 40 of the answers the engine had settled with no person touching them (per status by
  `order by md5(item_result.id)`: 20 `wrong`, 10 `correct`, 10 `blank`), each crop looked at: **correct 10 of
  10 right.** wrong: 11 read and marked right; **4 right answers** (61 read as 6 twice, 158 as 15, 252 as 204,
  the top line of the working); 2 read from the wrong place; 3 illegible to me. blank: 3 truly blank; **5 right
  answers** written where the reader did not look (612 in a box, 44, 272 beside the `=`, 5, the digits 6 and 5
  inside `4[6] + [5]4 = 100`); 2 crops do not show the answer place. So 9 of 30 engine-settled wrongs and
  blanks were the reader's failure (about 1 in 6 to 1 in 2 at this size). A misread almost never lands on the
  exact key, which is why `correct` holds. It also covers the narrower question raised with Aseem's findings
  (send a reading that equals a printed number to a person): every wrong and blank now goes.
- **What changed.** `legacy.mark_read` → `(status, codes, working, read)`: a wrong or a blank becomes
  `needs_teacher`, the reading kept, `guess` = the reading, `why` = `legacy.HELD[...]`. The import path and
  `legacy.remark` use it; a person's reading (`legacy.correct`) still goes through `mark`. `engine legacy
  remark --every-child`. `engine audit`: "no wrong or blank answer stands on the engine's reading alone". The
  queue asks a held answer as a reading to confirm, not as Right/Wrong.
- **Tests.** `pytest` on the copy → **471 passed, 0 failed** (junit: tests 471, failures 0, errors 0). The two
  new ones failed first on the old rule (`('wrong', ['M_NOCARRY']) == ('needs_teacher', [])`). Five existing
  tests now walk the new flow — read → held → a person's reading → confirmed: the scan-to-graph test, the
  correction test, the re-mark test, the sign-off test (1 answer confirmed on the paper, not 4) and
  `test_gold.py`'s 5147 (waiting → a person → not yet signed off → in the graph). ruff format and check clean.
- **Browser.** `npx playwright test` → **74 passed, 1 skipped** (a ladder opens only on signed-off evidence).
  `s4-validation-queue.spec.ts` 10 of 10, three new: a held wrong settles on "Yes, the child wrote {guess}" as
  `wrong` in the person's name; a held blank on "Nothing is written here"; on its paper a held answer offers
  "What the child wrote" filled with the reading and no Right/Wrong, which would drop the named mistake.
- **Rehearsed on the copy** (`DATABASE_URL=$TEST_DATABASE_URL bin/engine legacy remark --every-child`). Before,
  candidates no person touched: correct 332 · wrong 184 · blank 90 · needs_teacher 24 · unreadable 169.
  `274 results changed across 16 children`. After: correct 332 · needs_teacher 298 (184 "read as a wrong
  answer…", 90 "read as blank…", 24 as before) · unreadable 169. Exactly the held rows moved.
- **Live: not yet.** After the merge: `deploy/go-live.sh`, then `bin/engine legacy remark --every-child` on
  live (185 wrong + 95 blank on the evening's numbers), then `engine audit` → 0 violations and `engine read
  waiting` naming the two reasons. No paper is signed off before that.

## Next: six steps — written, and step 6 begun (2026-09-21, evening)

- **The order and its goals**, agreed in principle by Nimish ("start building for the next steps … with the right
  goals in the system, and the three parts of the queue"): `BUILD-ORDER.md` "Next: six steps" — 6 W3 closes · 7 a
  child's paper from the library · 8 a question counts for every skill it uses · 9 combined-concept questions · 10
  mixed papers · 11 W4. Goal files `goals/s7…s10`, `goals/w4-close-the-loop.yaml`, and W3's restated to the night
  decision (ADR 0028: 10 runnable criteria; its 36 reading scenarios kept under `superseded_scenarios`). `bin/engine
  goal` lists all 13.
- **Step 6, Aseem's reports as gold.** Transcribed into `~/cornerstone/assessments/gold_findings.json` (beside the
  reports, never in the repository — it names children): **24 findings** — 11 examples from his "faulty" sections,
  13 strong concepts. Table `gold_finding` (migration `20260927090000`), `engine gold load | confirm | check`,
  `engine read coverage`. `tests/test_gold.py` (3): 8500 − 3647 = 5147 goes from the page to M_SMALL_FROM_LARGE in
  the graph and the check says "in the graph"; a misread is "read differently"; a changed finding needs confirming
  again. Mutation check: with the misread test's branch removed, 1 of 3 fails.
- **On the copy, before any Grade 3 paper is signed off** (`engine gold check`): 2 in the graph — the
  smaller-from-larger subtraction, already a pattern, and strong addition; 18 not yet signed off; 3 waiting for a person
  (a 34 × 2, a comparison sign, a 62,413 copied out); **1 read differently — a "3 boxes of 6 pencils" read as 3 at
  99.4% confidence from the teacher's red "(6+3)" beside the child's crossed 9**, settled without a person. The same
  crop's q11 was read as 128 (the child's working) where the child wrote 222 with a teacher's tick. Of the 12
  engine-settled answers people looked at on live today, 2 had been misread.
- **Three mistakes his reports name that the vocabulary lacked**, now rows with code that computes them:
  M_MUL_UNITS_REVERSED (34 × 2 → 86, 56 × 3 → 85), M_COMPARE_REVERSED (the other sign, stored on a comparison question
  when its paper is entered), M_DIGIT_DROPPED (a digit lost copying out a 4+ digit answer — a marking rule used only
  when no predicted wrong answer matches). 42 vocabulary rows.
- **Found and fixed before it ever ran on live rows: `legacy.remark`** rebuilt every mark from the reader's own
  reading, so it would have put back a reading a person corrected and sent a person's Right back to the queue; it
  also rewrote superseded readings. Now it skips any answer a person settled and any superseded reading.
  `test_marking_again_never_undoes_what_a_person_said` (failed before: `wrong`). On a fresh copy, re-entering every
  paper and marking again changes exactly **3** answers — the three new names — where it counted 62 before.
- Engine suite: **468 passed**; ruff clean.
- **Live after PR #9 merged (9cab230) and `deploy/go-live.sh` (exit 0):** the website's Vercel deployment "has
  completed"; the approval page's twelve pictures at once on capture 05167c88 — **cold 12 × 200, slowest 1.12 s** (was
  5.4 s), warm 0.29 s. The typed-answer fix waits on a person typing on the live queue: at 19:17 IST the 29 answers
  with a key that is not one number were all still waiting (True 8, Not true 7, the order 5, `<` 4, even 4, 1/2 1).
- **A judgement is not a reading** (found on live the same evening): a find-the-mistake 48 + 27 read as 76 was judged
  Right on the queue, and `judgeOne` stored the engine's 76 as the person's reading — which the reader's gold set
  (`legacy.corrections`) then counted as verified, scoring the reader right on its own misread. 3 such rows on live.
  Migration `20260927100000_a_judgement_is_not_a_reading` adds `read_correction.judged` and marks the old rows (2 on
  the copy, which predates the third); `judgeOne` sets it; the gold set, the gold check and the screens' "what a
  person said the child wrote" read only rows where it is null. The judgement screen now also offers "Not what the
  child wrote? Type it". Clicked through on the local preview against the copy: that 76 answer, typed 75 → `correct`,
  stored as a reading, "200 answers left" (was 201). `test_a_judgement_is_never_counted_as_a_reading`; the queue's
  browser tests on a production build **7 of 7** (the judgement test now also checks `judged`); engine suite 469.
- **Live after PR #10 (merged 234dea3, 2026-09-21 19:27 IST):** migrations `20260927090000_gold_finding` and
  `20260927100000_a_judgement_is_not_a_reading` pushed to live minutes after the website deployed — no request in
  between touched the missing column (`vercel logs --query judged`: 0; no 5xx); 3 live rows marked `judged`. Step 6's
  data job on live: vocabulary 65 → 68 rows (`loaders._misconceptions` alone — `engine load` would also re-upsert
  every other seed), 17 papers re-entered (on the copy this changed only mistake lists: 15 multiplications gained
  M_MUL_UNITS_REVERSED, 1 comparison M_COMPARE_REVERSED), **3 answers marked again** (as on the copy), `engine graph`
  8 states, `engine gold load` 24 findings. `engine audit`: 12 invariants, 0 violations. `engine gold check`: 24
  "transcription not yet confirmed". `engine read coverage`: 49 papers · 1 signed off · 13 scored · 196 waiting.
  `deploy/go-live.sh` at 6da4519 (exit 0); the twelve pictures, cold, 12 × 200 in ≤ 0.99 s.
- **Aseem's 24 findings confirmed by Nimish** ("correct", in chat, 2026-09-21) → `engine gold confirm --by "Nimish, in
  chat, 2026-09-21"`: 24 confirmed. `engine gold check` on live: **2 in the graph** (Child A's M_SMALL_FROM_LARGE, a
  pattern in the graph; his strong addition) · 18 not yet signed off · 3 waiting for a person (a 34 × 2, a comparison
  sign, a 62,413 copied out) · 1 read differently (the "3 boxes of 6 pencils" read as 3 from the teacher's red pen;
  the child wrote 9).

## Aseem's findings checked by machine; the engine's own "wrong" marks hold silent misreads (2026-09-21, night)

- **The transcription holds, checked by machine against his PDFs** (Nimish confirmed it too, 35945ef). `pdftotext` on the five reports: all 11
  examples are the question on that child's paper; each of the 7 named mistakes reproduces the wrong answer he quotes
  (`assess.misconceptions.predict('×'|'-', a, b)`, `predict_sign('<')`): 8500 − 3647 → 5147, 56 × 3 → 1518,
  34 × 2 → 86, 350 − 128 → 232, 3 × 6 → 9, 456 _ 465 → `>`, and 62,413 → 6,243 is a dropped digit. Two gaps:
  `words` is verbatim for only 7 of 24 (the rest paraphrase him), and one example he quotes is missing —
  48 × 5 = 00 (`legacy/G3-QUIZ20/20`), which the engine holds as `blank`; `predict('×', 48, 5)` gives 0 under
  M_MUL_UNITS_REVERSED, the rule of the same child's 34 × 2 = 86.
- **His mistakes, against the engine's readings before any sign-off:** 8 of the 11 error findings have a reading;
  7 match his answer and mark, and the 3 among them where he names a method carry that method. 3 are unreadable
  (waiting); 1 is the red-pen misread (3 boxes of 6 read as 3).
- **His strengths do not match:** three children's "strong" skills have more `wrong` than `correct` on the engine's
  own marks (Addition 7/8, Addition 7/5 + 2 blank, Subtraction 3/5). Crops looked at: 600 − 245 = 355 with the
  teacher's tick, read as 921 — the next question's answer — at 89%; 204 + 48 = 252 with a tick, read as 204, the
  top line of the working, at 95%; 6,342 − 2,875 = 3567 read as 6342 at 99%. Each settled without a person.
- **Across the corpus:** of 612 answers the engine settled with no person touching them, 185 are `wrong`, and 23 of
  those read a number printed in the question (15) or another question's answer on the same paper (8) — 3.8% of
  everything the engine settled alone, against the 1.2% silent-wrong figure the reader hold rested on. None is signed
  off, so none is in a graph; signing a paper off shows only its doubtful answers and one spot-check.
  ```sql
  -- s: current captures, no read_correction; rd = raw_read.child_answer without spaces/commas
  -- printed: rd ~ '^\d{2,}$' and rd is one of regexp_matches(replace(question, ',', ''), '(\d+)', 'g')
  -- another: rd ~ '^\d{3,}$', rd <> key, and rd is the key of another item on the same capture
  → correct 332 (7 printed) · wrong 185 (15 printed, 8 another) · blank 95 · 0 signed off
  ```
- **The gold check passes a strength the graph does not show.** `gold.outcome` calls a `strong` finding "in the
  graph" once any confirmed evidence exists and no mistake repeats; it never reads the state. Child A's "strong in
  addition" is one of today's 2 "in the graph" while `child_skill_state` has NUM.OPS.01 `not_enough_yet` on R9
  and R12 (2 of 4 confirmed answers right). Only the M_SMALL_FROM_LARGE pattern is a real match.
- **Open for Nimish:** send a reading that is a number printed on the page to a person instead of marking it
  (~23 more on the queue; it reverses the coverage hold of 2026-09-21).

## Step 7 — a child's paper from the library (2026-09-21, night)

- `assemble.for_week` hands each prescription a library worksheet (ADR 0026) instead of drawing twelve questions afresh:
  never one the child sat, none holding a question they saw inside the exposure window, none holding a question
  another child has this week, none holding a question that has left the bank (a flag retires an item before the
  library is rebuilt); least handed-out first. Spares are worksheets nobody was given. A child who cannot be given one
  is named with the reason in words (`why`, printed by the CLI and by the F2 flow's message) — never a short paper
  or a repeat. The printed label carries the worksheet ID ("… · Worksheet R6-H07").
- **Two things the change would have broken, caught by the suite and fixed at the cause:** approving a week approved
  nothing (it found papers through the template's week, and a library worksheet has none) — a printed copy now
  records its week, class and kind (`20260927120000`), and approval reads them; and a short child's id failed the
  week endpoints' replay store (`TypeError: UUID`) — the endpoint now hands it over as text
  (`test_a_child_who_cannot_be_given_a_worksheet_is_named_in_the_answer`). The page geometry printed for a child
  lives on that child's `sheet_instance.key` (`20260927110000`); a library worksheet is never written to.
- The website: a paper's page says "Worksheet R6-H07 from the library, one of 18 at this level" and links to it; the
  week's list shows each child's worksheet; a spare is found by its own week and class.
- **`bin/engine goal s7-paper-from-library`: 6/6 criteria · GOAL ACHIEVED** — `tests/test_paper_from_library.py` 7;
  `engine goal w2-assemble-and-print` GOAL ACHIEVED (its scenarios on library worksheets); `engine library check` 0
  problems; `tests/s7-paper-from-library.spec.ts` 3 of 3 on a production build (the whole G2 class, 11 children,
  given 11 different worksheets through the engine's own week endpoints, the test's week removed afterwards);
  `engine audit` 0 violations; engine suite 477.
- **Live after PR #11 (merged 10e51cc, 2026-09-22 04:52 UTC):** the website deployed at 04:53:15; migrations
  `20260927110000` and `20260927120000` pushed to live minutes later (the merge came before them, again — see memory
  "nothing waits on the merge"); every `/worksheets` request in the window was before the merge (04:29–04:40, all 200),
  `vercel logs --query "does not exist"`: 0. `deploy/go-live.sh` at d521da4 (exit 0). Live: the twelve pictures cold,
  12 × 200 in ≤ 1.01 s; `engine library check`: 1123 worksheets · 68 of 68 skill-levels ready · 0 problems;
  `engine audit`: 12 invariants, 0 violations.

## Step 8, widened — the team's taxonomy and every skill a question uses (2026-09-22)

- **Measured before the work** (live bank, 12,567 active questions): of the taxonomy's 252 cases, 112 hold ≥ 12
  questions, 14 hold 1–11, 126 hold none. Page: claude.ai/artifact/769ATqK16k5iuBVyPLnhKQ. Several gaps are levels
  whose rule names keys no generator reads (`order`, `layout`, `n_costs`, `planted`, `extra_information`).
- **`engine load` took every staff password away** — `app.staff` was upserted from a seed that holds none. Fixed at
  the cause: a config row marked `seed_once` is the app's after its first load
  (`test_load_config_keeps_a_password_set_in_the_app`, failed before the fix). The copy's value was restored from live.
- **8a — a question's skills are read from the question** (`assess/skills.py`; rules are config rows
  `skills.by_operation / by_kind / by_symbol`; ADR 0030). On the copy, `engine bank relabel` changed 10,319 of the
  12,331 generated questions (0.7 s); a second run: `skills: 0 would change`. Every 3-digit addition now carries
  addition alone; every budget problem `NUM.PRB.02, NUM.MEAS.04, NUM.OPS.01, NUM.OPS.02`. `engine audit` holds
  "no question carries a skill it does not use". `tests/test_every_skill.py` 12; engine suite green. Live not yet
  relabelled.
- **8b — the skill a mistake charges.** Migration `20260928090000`: `misconception.skill_from` ('operation' or
  'row') + `skill_code`, `item.mistake_skills`. 39 of the 68 named mistakes name their own skill (equality, rounding,
  budget steps, explaining); the rest take the question's operation. `skills.charges_by_kind` (config) covers the
  kinds where a mistake charges something else — choosing the wrong operation in a story is a word-problem slip.
  On the copy `engine bank relabel`: `mistake_skills: 11657 changed`; a budget question now records
  `M_SUM_ONLY → NUM.OPS.02, M_ONE_STEP_ONLY → NUM.PRB.02`. **Waits for one approval** (`engine audit`: "the table of
  what a mistake charges on each kind of question waits for one approval"); the suite counts only what code keeps
  (`audit.AWAITS_A_PERSON`).
- **8c — evidence per skill.** Migration `20260928100000`: `confirm_results` writes one row per skill a right answer
  used, one per skill a wrong answer's named mistakes charge (each row carrying its mistakes), one on the question's
  own skill for an unexplained wrong answer or a blank; `next_difficulty` counts answers, not rows (a four-skill
  right answer no longer weighs four). On the copy: a right budget answer → 4 rows; "added but never subtracted" →
  1 row against `NUM.OPS.02`; a one-skill column sum → 1 row as before (`tests/test_every_skill.py` 25). The 236
  pieces of evidence already on live all come from old papers' one-skill questions, so none needs rewriting.
- **8d — the graph reads it.** `engine graph` on the copy: 8 states. The Growth screen already keeps one row per rung
  × skill and files each answer under every skill lane it counts for (`childMap`, `childEvidence`), so it needed no
  change. `engine gold check` counts a paper's questions by any skill they use; copy and live read the same:
  "18 not yet signed off · 3 waiting for a person · 2 in the graph · 1 read differently" — the 18 wait on the
  validation queue, not on step 8.
- **8e — the cases are rows, and one command counts them.** Migration `20260928110000`: `taxonomy_case`, 269 rows
  from `supabase/seed/taxonomy_cases.json` (sections 2–11 of the document; 5-digit numbers and §10.2's language
  notes left out, as the page said). `assess/tags.py` measures what the cases read (`regroup_at`, `exchange_zeros`,
  `carry_into_zero`, `answer_zeros`, `zero_operand`, `zeros_in`, `knock_on`, `carry_max`, the missing number's and
  missing digit's place, a story's `structure`); "answer size" gains the document's `-MULTIPLE` and `ZERO`.
  `assess/taxonomy.py` reads a case's `match`. `engine bank relabel` recomputes tags too (copy: `tags: 9204
  changed`). `tests/test_taxonomy.py` 306: every case accepts the document's own example, twelve twin pairs stay
  apart. **On the copy `engine bank taxonomy`: 269 cases · 102 covered · 156 missing · 11 thin** — stricter than
  the morning's estimate because stories that predate their stored shape have none yet (8g).
- **8f — a level made of cases.** A level's rule may list `cases`; `assess/draw.py` draws the same number from each,
  keeping a question only when, as measured, it is that case and inside the level's bounds (`max_total`, `digits`,
  `op`); where a case does not fix the layout, questions alternate columns / line exactly. Defaults a question needs
  (no number ending in 0, no equal numbers, no difference under 5) are lifted only by a case about that very thing.
  Built numbers for three cases chance cannot find (347 + 100, 68 + 32, 503 − 498), and answers that shrink drawn from
  the answer up (100 − 7). `bank.fill_cases` stores each question with `generator = 'case:<code>'`; `verify` judges a
  case level as the union of its cases; scenarios and the known-mistakes check draw from cases too. With no level
  bounds every plain-sum and missing-number case yields ≥ 24 distinct questions except 7 − 7 and 7 − 0 (18 each —
  all there are). `tests/test_taxonomy.py` +4; suite green.
- **8g — every kind of question the cases need.** One file per family, each a generator code checks:
  `assess/equality.py` (the missing sign, two missing signs, a balance with the same or two operations, the same
  number in both boxes, true or false, <, = or > without working; fact families from an addition or a subtraction;
  checking with the inverse), `assess/reasoning.py` (the closest estimate, could that answer be right, odd or even,
  tens then ones), `assess/diagnosis.py` (find the mistake with 16 plantable slips — column, alignment, three
  numbers, reversed, digit, equals — and which column it first went wrong in; across a zero and exchanging in the
  wrong place at 3 digits), `assess/missing_digits.py` (one answer only, proven by trying every digit; the same
  letter twice; an inequality). Story templates are rows (`engine/assess/word_templates.json`, 41 — ADR 0010's
  debt); a stored story's shape is read back from its words (`words.structure_of`), never stored beside it; an
  `eval` in `words.py` replaced by `words.evaluate`. WORD.BUDGET's four levels now print what they ask (2–4 costs,
  one a product). `bands.READS`: `engine audit` holds "every key a level sets is one its generator reads" and
  "every case a level names is a row". `tests/test_new_kinds.py`: each kind prints, marks, maps every wrong option
  to a named mistake, and names its skills. Each prints on paper (`render.py`) and on screen (`question.tsx`).
- **8h — the levels hold the cases.** 13 skills' levels rewritten and 4 skills added (`ADD.MULTI.SMALL`,
  `EQUALITY.INVERSE`, `MISSING.DIGIT`, `ESTIMATE.HUNDRED`; rungs R15–R18); every one of the 269 cases is listed by a
  level. The words Nimish approved are kept; only levels and kinds changed; all 17 wait for his one approval, with
  the table of what a wrong answer counts against (8b), on `/skill-sets/approve`. The 2- and 3-digit skills keep
  their missing-number and story questions, each a case inside the level's number bounds (ADR 0031). Grade 1
  floors, measured as all there are (a second refill found no more, ADR 0011): `ADD.1D.BRIDGE10` Medium 131 (144 exist; 6 are Grade 2 questions still in their own level, 7 retired rows a question cannot be stored twice past);
  `ADD.1D.WITHIN10` Medium 86, Hard 24, Advance 82; `SUB.1D.WITHIN20` Medium 110, Hard 44. `engine bank levels`
  lists the rewrite before `--apply` writes it.
- **8i — refilled and rebuilt, rehearsed on a fresh copy of live in the order live will run** (scratchpad
  `rehearse.sh`): `bin/testdb` (46 tables, every count equal to live) → `engine load` (`app.staff` unchanged,
  md5 before = after) → `engine bank levels --apply` (13 sets) → `engine bank refill` in 21 s: **"retired 4756
  questions outside their level · added 10049"** (retired through `item_feedback`, actor "engine (step 8i)", each
  kept with its reason) → a second refill: +4, one case (`M22`, "□ − 7 = 8" within 20: 48 exist against a share of
  72) finding four the first search missed; a third: **0** → `engine library build`: "made 1160 · retired 742"; a
  second build: **"made 0 · retired 0"** → `engine library check`: **"1541 worksheets · 84 of 84 skill-levels ready ·
  0 problems"** → `engine bank taxonomy`: **"269 cases · 269 covered · 0 missing · 0 thin"** → `engine audit`: 18
  violations, all the two that wait for a person (17 skills, 1 table).
  Found and fixed at the cause on the way, each with a test that failed first: refill judged questions on stale
  tags (relabel now runs first); a question was credited to its first case only, so levels overfilled (every case
  it is); a case whose numbers had run out spilled its shortfall onto the other cases on every refill
  (`test_top_up_a_second_time_adds_nothing_when_a_case_has_run_out`: 167 before, 0 after); the library kept
  worksheets with an unfair mix of kinds and dealt patches that looped (one `_unfair` for build and check); the
  approval page's table never matched (postgres.js sends a string bound for `jsonb` as a JSON string —
  `::text::jsonb`). Website on the copy: **77 passed, 1 skipped** (the long-standing "no paper signed off" skip).
- **Live, 2026-09-22** (PR #13 `4803aab`, PR #14 `450467b`). Migrations `20260928090000`, `…100000`, `…110000` pushed
  before the merge; `engine load` (`app.staff` md5 unchanged); `bank levels --apply` (13); `bank refill` **"retired
  4756 questions outside their level · added 10049"**; `library build` "made 1159 · retired 742"; `library check`
  **"1540 worksheets · 84 of 84 skill-levels ready · 0 problems"**; `bank taxonomy` **"269 cases · 269 covered · 0
  missing · 0 thin"**; `engine audit` 18 violations, only the 17 skills and 1 table waiting for Nimish.
- **The live engine was down 13:16–13:56 IST.** After PR #13 deployed it crashed on start: `words.py` read the story
  templates from `supabase/seed/`, which the server's image (`engine/` alone) does not hold. Fixed at the cause in
  PR #14 — the file beside its reader; `tests/test_image.py` starts the engine from `engine/` alone and failed first
  with the server's own error. This Mac's network then corrupted every transfer to the server above 16 KB (ssh
  "incorrect signature"), so `go-live.sh` could not upload the code: the server fetched commit `450467b` from GitHub
  itself (the repository is public), proved byte-identical to it (370 files, one sha256 over all, equal on both
  sides), and rebuilt — `/health` 200 at 13:56. Website production deployment of `450467b`: success. **Not yet
  proved: a signed-in click-through on the live link** (no session in this browser).
- **Step 8 closed on live, 2026-09-22 afternoon.** Nimish approved the 17 skills and the table of what a wrong answer
  counts against. Live, read-only: `engine bank taxonomy` "269 cases · 269 covered · 0 missing · 0 thin"; `engine
  library check` "1540 worksheets · 84 of 84 skill-levels ready · 0 problems"; `engine audit` "17 invariants checked,
  0 violations". Goal s8-every-skill-a-question-uses still waits on step 6's `engine gold check`.
- **ADR 0029's data job ran on live** (PR #12, run by Nimish): `engine legacy remark --every-child` → "264 results
  changed across 16 children"; `engine read waiting` 190 → **454** (178 read as wrong, 86 read as blank, each now
  checked by a person); 413 stay settled by the engine, all read as right. The engine server still runs the code from
  before #12 — nothing the website calls changed (`legacy.correct` is as it was), but `deploy/go-live.sh` is owed.

## The reader learns from every check — ADR 0032, built on the copy (2026-09-22, evening)

- **Found first:** ADR 0007's loop (2026-09-19) was never built — `child_reading_profile` 0 rows, a correction
  changing nothing after its own row, the reader recording nothing of what it saw when it gave up. Nimish:
  *"this effort better help the case."* Measured on the 121 typed answers that afternoon: the reader right 33 of 42
  at 90+ confidence, 7 of 17 at 70–89, 1 of 30 below 70, 5 of 32 where it gave up.
- **L1 — the record.** Every reading carries `seen` (each number in the region with its confidence, on the
  give-ups most of all). `engine read profile` builds a notebook per checked child (`profiles.build`, pure; ring B):
  right by kind and by confidence, the child's own floor (70/80/90/95), routed kinds (`read.route_above_overturn`,
  unused since day one), digit confusions, eight confirmed samples. A sign-off without a change joins the gold set:
  `engine read eval --gold-only` → **284 gold responses on 33 sheets · 152 typed · 90 signed off** (was 82 + 103).
  On the copy, 9 notebooks: Agastya 46 checked, right 24 of 37, floor 95, routes sums + word problems; Dhanvi 49,
  35 of 41, floor 95, routes word problems; Child A 25, 18 of 20, floor 80, confuses 3>7.
- **L2 — the next read.** `engine/reading.py` is the one reader for the import, the re-read and the replay: the
  child's floor replaces 70; a routed kind or a confused digit is flagged with the reading as the one-click guess
  (`profiles.apply`, never overwriting a doubt or a blank). `test_the_childs_notebook_changes_the_next_import_of_
  that_child`: the child's 8 read for a 3 twice → slot 1 flagged, guess 84, floor 90 handed to the reader.
- **L3 — the second reader.** `read_with_examples` v1 (Haiku 4.5): the crop plus up to eight of this child's confirmed
  answers as labelled examples; proposes, never settles, not shown the question (ADR 0019). **Eval (rule 7), on the
  copy, Agastya + Dhanvi, notebook built without the paper under test: 9 of 16 give-ups guessed right (56%) — sums
  5 of 7, word problems 3 of 7 — Rs 10.67.** `engine read guess` gives every waiting answer its guess.
- **L4 — trust and proof.** `marking.agreement_gate` wired: a right answer waits until the reader's readings of that
  kind matched people 95% of the time over the last fifty checks (`profiles.kind_trust`; `mark_read(gate=)`; the
  import and `legacy remark` both). `engine read report` on the copy: **checked 246 · right 146 of 191 stood behind
  (76%) · silently wrong 45 · gave up 55 (guess right 13); sums 28 of the last 50, word problems 36 of 47, missing
  numbers 15 of 17, written 4 of 6 — no kind trusted yet.** Capture & Mark shows the same panel.
- **The replay (`engine read replay --section G2 --child Agastya --child Dhanvi`), 8 papers, 95 answers people
  settled, each read again without a notebook and with one built from the child's other papers:**
  **without — right 59 · silently wrong 19 · one click 2 · typing 15; with — right 30 · silently wrong 9 · one click
  36 · typing 20.** The dangerous error halved and typing turned to clicking; the reader settles half as much alone,
  because both notebooks read "floor 95" — it had been wrong on these children too often. The 9 that remain: 6 on
  one paper of Agastya's (`G2-SEPW2-S1`) where the reader stood behind wrong numbers at 95%+ and the notebook changed
  nothing — at 95%+ the reader is sure of the digits, so this is most likely a wrong *pick* of the number (the
  working taken for the answer), which no notebook can catch; the gate keeps those from the graph, and the pick
  is the next reader fix, to be confirmed on the crops.
- Engine suite 893 passed; website s4 15 passed (a gate-held answer settles in one click; the second reader's guess
  offered back on the queue and the paper). **Live: not yet** — the order is in HANDOFF.
- **Live, 2026-09-22, 19:55–20:10 IST** (PR #19 merged as `5a450f7`, run by me at Nimish's word "run all of this in
  prod"). Before: `engine read waiting` 382 of 867; audit 0; `child_reading_profile` 0 rows. `engine load` (prompt
  20, `read_with_examples` v1 active; `app.staff` md5 unchanged) → `engine read profile` **9 children profiled**
  (Agastya floor 95, routes sums + word problems; Dhanvi floor 95, routes word problems) → `engine legacy remark
  --every-child` **"242 results changed across 16 children"** (the gate: right answers of untrusted kinds held; a
  signed-off answer is never re-marked, so the queue did not reach 867) → `engine read guess` **74 waiting answers
  given a guess over 33 questions, Rs 8.77** → `engine read report` as on the copy (checked 242, right 142 of 187,
  no kind trusted: sums 28 of 50). After: **624 waiting — 570 one click (427 the reader's own reading, 74 the second
  reader's guess, 69 confirm blank), 53 typing**; `engine audit` 17 invariants, 0 violations; website production
  build of `5a450f7` success. The engine server still runs `450467b`: nothing it serves changed; redeploy when the
  network allows.

## The workflows made visible, and promises made commands — ADR 0033 (2026-09-22, night)

- **The map** `workflows.json`: 12 steps in 4 workflows, every engine file on exactly one step or shared part,
  3 declared connections between workflows, each step marked any-subject or maths-only. `tests/test_layout.py`
  (6 checks) holds the code to it. The engine moved from 40 flat modules to `w1_bank/ w2_print/ w3_read/` on
  `core/ assess/ adapters/`, doors `checks/ api/ cli.py` (git mv). Files over 400 lines 9 → 6, each frozen and
  only allowed to shrink: bank.py split to inventory.py, legacy.py to marking.py (897 → 672), cli.py 505 → 215
  (W1/W2 commands into cli_bank.py, cli_week.py). Engine suite 906 passed; the 894 before the move unchanged.
- **How it works** (`/workflows`, menu): the map with each step's live number from the database. Website 89 +
  the rerun pair passed on the copy; `tests/workflows.spec.ts` 3 passed; Vercel preview of PR #22 built green
  (next.config roots Turbopack at the repository so the page can read the one map).
- **Promises are commands**: `engine promises` — first run found 7 broken promises (w3-read-and-graph's four
  keys nothing ran, incl. the loop line that hid ADR 0007's unbuilt loop; reader-learns without Nimish's words;
  ADR 0032 without its goal; a loose test name in workflows-visible), each fixed at its cause; now "every
  promise has its command". `engine done <goal>` writes the done-report; `engine done workflows-visible` and
  `engine done promises-kept`: every sentence PROVED, NOT DONE only because the branch was not yet on main.
- **Run by themselves**: `bin/check` (layout + promises + lint, ~3 s, no database) in `.githooks/pre-commit`
  (core.hooksPath set on this Mac; the pre-push guard now committed beside it) and in the Claude Code Stop hook
  (`.claude/settings.json` in the repository, and `/Users/nimishshah/cornerstone/.claude/settings.json` for
  sessions started in the workspace). CLAUDE.md rule 14.


## The bank validated question by question against the taxonomy; five defects fixed at their cause (2026-09-23)

Nimish asked for every question and question bank validated against the team's taxonomy (the PDF he shared is the
same text as `docs/sources/addition-subtraction-skill-taxonomy.txt`). Run on a copy built from the repository in a
cloud session (Postgres 16, 25 migrations, `engine load`, `engine bank refill`, `engine library build`) — **not on
live**: this session had no live credentials. Children's names and papers were not used.

- **Checked independently, outside the engine** (solvers that import nothing from it): every sum re-worked from its
  printed numbers (answer, digit lengths, order, layout, where each carry or exchange falls, the answer's length,
  the carry pattern); every missing number, missing digit, balance, equation, fact family, number wall, parity,
  closest-hundred, possible-answer, inverse check, break-apart, estimate, word problem, find-the-mistake and
  compensation claim solved again, and every missing-digit and balance question found to have exactly one answer.
  **16,714 questions: 0 wrong keys, 0 duplicates.** The "why" and "show your method" parts are a person's to judge.
- **`engine bank recheck` covers 7,604 of 16,714** (sums, missing numbers, one-step stories); it skips every kind
  whose spec holds more than two numbers. Named here so its "0 mismatches" is not read as the whole bank.
- **Fixed, each with its tests** (`tests/test_taxonomy.py`, `test_rounding.py`, `test_reasoning.py`,
  `test_items.py`, `test_verify.py`, `test_audit.py`):
  1. `assess/tags.py` read a cascade where a carry left, not where it landed: 391 + 9 was "consecutive", 99 + 28
     and 609 + 715 "cascading"; an exchange from a non-zero place was "across zero" when the column needing it
     showed 0 (530 − 47). 676 questions' tags were wrong; P04, P05, P06, AN6, AZ6 counted the wrong questions.
  2. Estimates rounded a 5 down (Python's half-to-even: 665 printed as 660, 985 as 980) — 105 of 1,188, on the
     printed page. `assess/rounding.half_up` now does school rounding.
  3. "Which is closest?" was answered by the middle option in 216 of 216; 3 had two equally near options
     (483 + 367 = 850). The right option now sits first, middle or last in turn; a sum ending in 50 is never asked.
  4. P16 (the leading digit lends, 105 − 97) counted 76 − 73: tag `highest_place_reduced`; 565 → 447.
  5. New invariant in `engine audit`: **no choice is answered by ticking one place** (limit a row,
     `bank.choice_answer_max_share`). A question made by a rule since corrected leaves the bank on the next
     `engine bank refill` (`verify.key_problems`), and its worksheets are rebuilt; printed papers never change.
- **After, on the copy:** `engine bank relabel` → tags 676 changed (then 4,794 more: the new tag on every
  subtraction); `engine bank refill` → "retired 322 · added 324", a second run "retired 0 · added 0";
  `engine library build` → "made 82 · retired 81"; `engine library check` → "1442 worksheets · 84 of 84 skill-levels
  ready · 0 problems"; `engine bank taxonomy` → "269 cases · 269 covered · 0 missing · 0 thin"; `engine bank recheck`
  → "0 mismatches"; `engine goal s8t-taxonomy-coverage` → 12/12 scenarios. Independent solvers: 0 disagreements;
  closest-hundred answers first/middle/last 66/87/63.
- **Found, not fixed — each needs a person** (in `HANDOFF.md`): the audit's new invariant names 6 levels whose
  right tick is one answer by design — REASON.EXPLAIN Easy/Medium always "yes", Hard/Advance always "no"; the two
  JUDGED estimate levels always "yes" (the seed changed the document's R07 example from 704 to 705, which makes
  every answer "yes"). Estimates print the rounded numbers, so R01–R03 never ask a child to round. 23 mistake
  codes the skill sets name exist only on live (`engine load` ORPHAN; a copy built from the repository fails
  `test_no_code_refers_to_something_that_does_not_exist`). Document lines no case counts: §10.2 addition and
  subtraction words, solving without keywords, writing the number sentence, same story different question;
  §11's "carry written but not added" and "forgotten exchange" folded into X03 and X07.

## The next paper chosen from the child's own graph — goal s11-focus-paper (2026-09-23)

Nimish: *"After 34 evaluations, the system is able to see that there are certain areas where the child lags.
Based on some simple, smart logic, the system is able to go ahead and choose random questions from the skill bank
that it already has."* Built as three modules, on the copy (no live access from this session):

- **`assess/focus.py`** (pure): the graph's lagging rows (`patterned_error`, `emerging`, `practising`), weakest
  first, at most three (`config.focus.most`); each worked on in the bank's skill set for that skill — on its rung,
  else the nearest within `config.focus.reach` rungs, else a set on the rung that uses the skill — at Easy below
  `next_sheet.demote_below`, else Medium. 3-digit subtraction answers on R9 go to SUB.3D.ZERO, not ADD.3D.REG: the
  next-paper fault queued in HANDOFF, fixed for this paper. `tests/test_focus.py` 5 passed.
- **`w2_print/focus_paper.py`**: `plan` draws 12 (`assemble.items_per_sheet`) active questions, split over the
  areas, at random seeded by child and week (the page and the print are one plan), none in `item_exposure`, the
  area's own skill first and the questions that can show the child's repeated mistake before the rest; `make`
  prints it as a `sheet_template` (source `focus`, migration `20260929090000`), the child's `sheet_instance` and QR,
  the questions recorded as seen. `engine week focus <section> <first name> <week> [--make]`; API
  `GET|POST /child/{id}/focus`. `tests/test_focus_paper.py` 3 passed.
- **The Growth page** (`/growth/[id]`): the "Next papers" panel, which showed the rung-grouped `next_difficulty`,
  is replaced by "Next paper, from their own work" — each area, its level, why in one sentence, the questions, and
  "Make this paper"; the paper opens on `/worksheets/[qr]`. `apps/web/tests/s11-focus-paper.spec.ts` 1 passed on
  the copy (production build, signed in).
- Checks: `bin/check` 12 passed; `engine promises` "every promise has its command"; engine suite 940 passed with
  the same 7 failures as before (2 the orphan codes, 5 needing the children's papers or `pdfunite`); web `tsc` and
  `eslint app lib components tests` clean.
- **Not changed:** the class's weekly paper (`engine week prescribe`, `/worksheets`) still takes one skill set from
  the teacher and `next_difficulty` still groups by rung; steps 9 (combined questions) and 10 (mixed papers) are
  not built.

## The worksheet library read by the taxonomy — goal s12-worksheets-by-taxonomy (2026-09-23)

Nimish: *"The worksheet library view, ideally, should give a very clear taxonomy and the worksheets attached to the
taxonomy … do we have the worksheets mapped to the right taxonomy?"* On the copy:

- **A question names its cases** (`item.case_codes`, migration `20260929100000`): measured by code from its tags
  (`cases.of`), written when the question is made, recomputed by `engine bank relabel` ("cases: 15050 changed", a
  second run 0), held by `engine audit`'s "no question carries a skill it does not use". The stored count agrees
  with `engine bank taxonomy` for all 269 cases (`test_every_question_names_the_taxonomy_cases_it_is_and_the_count_agrees`).
- **The mapping, measured:** 247 cases sit on worksheets at the level the rules set them at; 22 are patterns that
  questions at many levels show and no one level owns (§4 lining up, §5 carry and exchange patterns, R01–R02
  estimating); 0 only away from their level; 0 on no worksheet; 162 worksheets hold no case (multiplication,
  explaining a claim).
- **`/worksheets/taxonomy`**: the document's chapters, each section's cases with the example, where the rules set
  each, and the worksheets holding it (links); linked from the Worksheet library. A worksheet's page lists its cases.
  `apps/web/tests/s12-worksheets-by-taxonomy.spec.ts` 3 passed (incl. a phone). The map query ran in 4.9 s until
  its worksheet totals were computed once (`materialized`): 0.15 s.
- Seen, not changed: a skill's outcome sentence can disagree with its Easy level (ADD.3D.REG says "regrouping …
  every time"; its Easy level holds the no-carry cases A25–A28 by rule). Pre-existing, not this change:
  `s3-worksheets.spec.ts` "fit a phone" fails on `/skill-sets/ADD.2D.REG?level=Easy` (21 px) on main as well.

## U1 — Today and the menu as the teacher's week (2026-09-23)

The plan for the website is in BUILD-ORDER ("the website as the teacher's week", U1–U7). U1, on the copy:
- **The menu:** Today · Children · Marking · Papers · Curriculum · Question bank · How it works; old addresses kept
  (Marking holds /capture and /capture/check, Papers holds /worksheets and /home, Curriculum holds / and /skill-sets).
- **`/today`**: answers to check (the queue's own count), papers to sign off (Capture & Mark's own), next papers to
  make (children with a red or amber skill and no next paper this week), class papers to approve for print (per
  class, week and kind), skills to approve — each its count and one click, or "Nothing waiting".
- **Red / amber / green / grey** in one place, `apps/web/lib/rag.ts`, from the graph's states; the ladder now
  colours "under half right" (`emerging`) red, as decided.
- `apps/web/tests/u1-today.spec.ts` 3 passed; the menu tests in `e2e`, `s1`, `s4`, `screens` updated to the new
  labels and passing. Failing on main as well, not this change: `s4` "the queue counts what the engine counts" and
  `e2e` "no two children share questions" on this copy's data.

## U2 — Children (2026-09-23)

Goal `goals/u2-children.yaml`, written with its tests before the code. On a copy built from the repository in a cloud
session (Postgres 16, 27 migrations, `engine load`, `engine bank refill` → 16,714 questions, `engine library build`)
— no live rows; the test class is three made-up Grade 2 children with checked answers chosen to show every colour.
- **`/growth`** is each grade and its classes, each class with its children's seen steps counted by colour.
- **`/growth/class/<class>`**: the children down the side, every step of each skill across the top (the grade's
  ladder, each rung once per skill it carries, plus any step a child has answers on), each cell the graph's own state
  in its colour from `lib/rag.ts`. No aggregation into one colour per skill: the engine has no per-skill verdict, and
  one colour would hide a red step behind a green one. Steps are named in the school's words, never rung codes.
- **A child's page** opens on one sentence ("Asha needs help on 1 step, is practising 1 and has got 1; 4 steps have
  too few answers to say."), counted from the same steps the knowledge graph shows; then the graph, **Repeated
  mistakes** (each mistake, the step, how often), **Next paper, proposed by the engine** with **Approve this
  paper**, and **Their papers** (every paper made for or read from them: purpose, who approved it, answers checked).
- **Approval is the engine's record, not the website's:** `focus_paper.make` writes `approved_by`/`approved_at` and
  `print_status = 'printed'` (as a class pack's approval does), refuses a second next paper for the child in the same
  week (409; the page then shows who approved it), and takes a row lock on the child so two clicks cannot both print.
  `engine week focus … --make` now refuses without `--by` — a paper prints only in a person's name.
- Fixed on the way: the child page's tiles counted "under half right" as practising (now red, from `rag.ts`); the
  graph's footnote said the same; lanes were hidden by whether answers had item rows, not by the graph's own states.
- `apps/web/tests/u2-children.spec.ts` 5 passed, together and each on its own (as `engine done` runs them), twice in a
  row with nothing left behind; the class grid names steps in words, and its names column stays put on a phone; `s11`, `u1`, `screens`, `e2e` menu updated and passing;
  `test_focus_paper.py` 5 passed, `test_cli.py` 21 passed; `bin/check` green; `tsc`, `eslint` clean.
- **Failing on unchanged main as well, on this copy — named, not inherited silently:** `e2e` "no two children share
  questions" and `s7` "names the worksheet each child was given" (need live's G3 class and week T2W1); `s4` "the queue
  counts" (needs read papers); `s2` "the map and a skill page fit a phone" and `s3` "the library and a worksheet fit
  a phone" — real layout faults on Curriculum and Papers, owned by U5 and U4. Engine: `test_goal` audit, `test_loaders`
  (23 mistake codes only on live, drafts unratified), `test_profiles`, `test_read_again` (need scans), `test_week`
  multiplication pack (`pdfunite` not installed in the container).

## U3 — Marking (2026-09-23)

Goal `goals/u3-marking.yaml`, written with its tests before the code. On the same cloud copy as U2.
- **Where each answer stands is now the engine's one definition** — migration
  `20260930090000_where_each_answer_stands.sql`: the view `answer_standing` puts every answer on a live read in
  exactly one place — *waiting* (status unreadable / needs_teacher), *person* (a `read_correction` exists: a person
  typed, confirmed or judged it), *engine* (otherwise) — and says whether it is signed off. `engine read waiting` and
  the Marking screen both count from it (`tests/test_answer_standing.py` 3 passed).
- **Fixed at the cause:** `resolve_result` (the Right / Wrong / Blank on a paper's page and a child's page) left no
  record of who judged, so a person's judgement looked like the engine's mark; it now writes the same
  `read_correction` row the queue's judgement always wrote. **Judgements made through it before this migration left
  no row and count as the engine's** — nothing records who made them, so nothing guesses.
- **`/capture` is Marking:** the queue of answers to check first, with its count and one click; papers in, answers
  settled by the engine, checked by a person, still waiting, papers to sign off; the same read **by class**, **by
  child** (the default, as before) and **by worksheet** (every child's copy of one paper); how the reader is doing.
  Check answers and a paper's page sit inside it (menu, "← Marking").
- **Found and fixed on the way:** naming a panel by wrapping it in a `<section>` lost `.panel`'s `min-width: 0`, and a
  wide table then pushed a phone's page sideways (U2's Children pages had the same wrapper). `Panel` now takes
  `label` and `id` itself; U2 and U3 each gained a test that their pages fit a phone *with their own data on them*.
  `screens` "phone /capture/<paper>" matched a missing scan by the console text, which never holds the address; it
  now reads the message's location. The s4 typing test crashed on an empty copy; it now skips as its siblings do.
- `apps/web/tests/u3-marking.spec.ts` 5 passed; s4 (all but the one needing a real scan) passed; `bin/check` green;
  `tsc`, `eslint` clean. Engine: 950 passed; the same five environment-only failures as U2 (audit on a fresh copy,
  mistake codes only on live, scans, `pdfunite`). Web: the same five failing on unchanged main as U2 (STATE, U2).

## L1–L3 and U5 — the levels read from the taxonomy, and Curriculum as a tree (2026-09-23)

ADR 0034; goals `s13-levels-by-taxonomy`, `s14-graph-by-skill`, `s15-answer-boxes`, `u5-curriculum`.
- **Fifteen calculation skills, one operation and digit shape each** (`ADD.1D1D` … `SUB.4D`, rungs R19–R33), levels
  the taxonomy's cases on the skill's own numbers (`check.within`). `engine bank taxonomy` → "269 cases · 256 placed
  in a level · 13 patterns the levels climb · 0 unplaced". The old ladder is gone: `engine bank rehome` moved 7,281
  questions (0 without a place), deleted ten skill sets and ten rungs; `assess/ladder.py`, the prototype's blueprints
  and builder, and `coverage_target` removed. Refill added what thin levels lacked; `library check` → "102 of 102
  skill-levels ready · 0 problems".
- **A child's answers count on their question's skill** (`evidence_placed`), recorded answers untouched; old papers'
  sums placed by the same rule (`assess/placing.py`). Each calculation rung carries only its operation's registry
  skill and reads as its skill's name on children's pages.
- **Answer boxes = the answer's digits; working space 14–34mm** (`assess/answer_space.py`, split from `render.py`,
  whose ceiling ratchets to 409). Cost, accepted by Nimish: a wrong answer longer than the right one has no box.
- **Curriculum (`/`) is one tree**: grade → subject → skill → levels, each with its sentence, questions and worksheets
  → the worksheets. A skill shows only the levels it defines on its page, its edit form, the approval page and on save
  (1-digit − 1-digit has no Hard). Skill tables scroll inside themselves on a phone (s2 and s3 phone faults fixed).
- Engine suite: only the environment-only failures named under U2. Web: 87 passed; `e2e` "no two children share
  questions", `s4` "the queue counts", `s7` "names the worksheet" still need live's data, as on main before.

## S16 — a printed paper is read in its boxes; a photographed page keeps its pixels (2026-09-24)

Goal `s16-read-the-boxes` (`bin/engine goal s16-read-the-boxes`). Nimish, on Advika's 24 Sep paper: "reading some
numbers from the working while you have only designed it as a working section" — and "150 dpi, and that is 4 pixels".
- **Read where it printed** (`w3_read/boxes.py`, `assess/geometry.py`): the scan is lined up with the PDF it came from
  (ORB + RANSAC, ≥ 60 inliers, no corner marks needed), each answer's boxes cut out at the recorded place, only that
  strip handed to the reader. Blank, inked-box count and "working written in" are pixel counts. A reading stands only
  when its digits equal the inked boxes. Papers without a geometry (the teachers' old papers) keep the old reader.
- **The photograph's own pixels** (`render_pdf.photo`): a phone scan is a 2000–3000 px photo letterboxed on an A4 PDF
  page; drawing it at 150 dpi halved it. `sorting.qr_of` decodes with zxing-cpp over five looks × three binarizers,
  then OpenCV. On the real 24 Sep file (16 pages): **3 → 13 of 16** codes read here; the rest fall to the printed code.
- `cd packages/engine && .venv/bin/python -m pytest tests/test_boxes.py tests/test_sorting.py` → `13 passed`
  (five new: every box digit read and no working digit; working is the third signal; a count mismatch waits; a blurred
  compressed code reads; a page that is not the paper does not line up). Full engine suite green here (database tests
  skip: no local copy). `bin/check` → green (render.py 419 → 394 by moving the geometry record out; ceiling unchanged).
- **Not verified on live**: no Textract here (the sandbox's AWS key is invalid) and no route to the live database. The
  24 Sep papers are read on the Mac or the server after merge; then a child-wise table from `copies.tally`.
- **A scan arrives by link** (`w3_read/inbox.py`, `POST /read/file`, Marking's "Read a scan" form, n8n `f3-read-scans`):
  fetched into `~/cornerstone/assessments/inbox`, a `flow_run` answered at once, read after answering.
  `cd packages/engine && .venv/bin/python -m pytest tests/test_inbox.py` → `7 passed` (link forms, inbox naming, only
  a PDF taken, the route answers at once and starts the reading, a refusal in words). `tsc`, `eslint` clean.


## The school operating system council — research and synthesis (2026-09-26)

Research and design only: no engine claim changes, and no gate moved (W3, step 6).

- Nine seats' notes exist, each ending in one council-position section.
  Check: `grep -c -i "^## Council position" "research/research_notes/School operating system council/"*.md` →
  `1` for each of the nine files.
- The consolidated report, "Own the evidence, amplify the teacher", is about 10,000 words and cites 218 of those
  sources. Check: `wc -w "research/reports/School operating system council.md"` → `10160`
- The notes cite 625 distinct links, each opened by a seat. The seats could not open some primary sources; those
  claims are marked unverified in the notes and kept out of the synthesis's rulings.
  Check: `cat "research/research_notes/School operating system council/"*.md | grep -oE "https?://[^) >\"]+" | sort -u | wc -l` → `625`
- The synthesis and the proposed ADR exist.
  Check: `wc -w docs/school-os-council-2026-09-26.md docs/adr/0036-the-school-os-grows-from-the-engines-spine.md`
  → `7665`, `801`.
- **Not verified by a command:** the seats' figures are their readings of sources they opened. The chair
  re-checked three claims against the notes and corrected the synthesis: the tutoring study was of university
  undergraduates, the DPDP 18-month date, and CBSE's weekly observation guidance.

## Level 2 of the spine — the founders' draft, validated by a command (2026-09-26)

Design only: no engine claim changes, no gate moved (W3, step 6).

- The draft holds 192 behaviours in 32 cells and every cell passes the proposal's nine checks.
  Check: `python3 research/level2_validate.py docs/school-os-level2-behaviours-draft.json` →
  ```
  behaviours 192 · cells 32 · cells passing 32/32
    foundational capable=35  kind=16  unafraid=13
    preparatory  capable=42  kind=14  unafraid=11
    middle       capable=41  kind=11  unafraid=18
    secondary    capable=45  kind=14  unafraid=16
  every stage passes V1–V9
  ```
- First-pass validity, recorded for the eval's baseline: 25 of 32 cells on the first run; seven failures (three
  "behind", one "weight", one "always", two single-mode cells); one regeneration by hand; 32 of 32 on the second run.
  The "behind" and "weight" hits were false positives of the crude banned-word check on "the reason behind it" and
  "lifts a weight"; the check is kept crude on purpose (a row a founder can tune) and the sentences were rephrased.
- **Not verified:** the founders' acceptance rate, which the sitting produces; coverage of the profile's eight
  "observable at 16" sentences, which a person maps once at the sitting. Both are eval numbers 2 and 3 and stay
  unrecorded until then.

## The subject-platform survey — three seats and one report (2026-09-26)

Research only: no engine claim changes, no gate moved (W3, step 6).

- Three seats' notes and one consolidated report exist.
  Check: `ls "research/research_notes/Subject learning platforms survey/" | wc -l` → `3`;
  `wc -w "research/reports/Subject learning platforms survey.md"` → `12917`
- **Not verified by a command:** every vendor fact is the seats' reading of pages they opened on 2026-09-26, with
  blocked pages named as gaps; prices are the vendors' published US prices; the cost roll-up is arithmetic on them.
  Nothing has been bought, trialled or contracted.

## Level 2 draft, v2 — after the four-seat council (2026-09-26)

- **Claim:** every live row of the reviewed draft passes the validator; the council's verdicts were reconciled by rules in code,
  not by hand; every change is logged with its reason.
- **Command:** `python3 research/level2_validate.py docs/school-os-level2-behaviours-draft.json`
- **Output:** `behaviours 204 live (8 retired) · cells 32 · cells passing 32/32 … cells with one capture mode (reported, V4): 9 …
  every stage passes V1–V9`. Words per stage: Foundational capable 39 · kind 16 · unafraid 18; Preparatory 45 · 13 · 11;
  Middle 45 · 13 · 20; Secondary 46 · 15 · 16.
- **Command:** `python3 research/level2_council.py --draft docs/school-os-level2-behaviours-draft.json --seats research/level2_council/{educator,parent,development,rights}.json --chair research/level2_council/chair.json --out /tmp/v2.json --log /tmp/log.md`
  (run on the v1 draft, commit 82cbdb8, to reproduce v2)
- **Output:** `outcomes {'accepted': 94, 'edited': 90, 'added': 20, 'retired': 8} rules {'R6': 93, 'R4': 43, 'chair': 42, 'R5': 11, 'R1': 3}`;
  accepted as written per seat: rights 149/192 (78%), development 148 (77%), educator 145 (76%), parent 159 (83%);
  `needs chair 0 · dangling grows_from 0`.
- **What the numbers are:** the seats' acceptance is measure 4 of the proposal's eval, a proxy; the founders' acceptance
  (measure 3) is not yet measured. The 8 retired rows stay in the file, struck through, for a founder to restore.
- **Command:** the same run with `--ages research/level2_council/ages.json --added-reviews research/level2_council/added_review_development.json research/level2_council/added_review_rights.json`
- **Output:** every one of the 53 live Foundational rows carries `from_age` (17 at three, 25 at four, 9 at five, one at six, one at seven,
  the development seat's judgement, not a citation); the 20 added rows were checked again by the development seat (17 as written,
  3 edited) and the rights seat (12 as written, 8 edited), and the chair took every edit.
- **Not verified:** that the founders agree with any of it; that the `from_age` values are right (one seat's judgement); that the
  banned-word list catches paraphrase (the rights seat found it does not, and rewrote by hand).

## S17 — the digit reader: PaddleOCR in its boxes, off the shelf (ADR 0035, 2026-09-26)

Goal `s17-step1-reread-both-scans` (step 1), **not green**: the live re-read of 24 Sep and 23 Sep has not run yet.
Nimish: "Accept ADR 0035, Paddle alone at 0.90, build it."
- **The reader** (`adapters/digits.py`): PaddleOCR 3.7 (PP-OCRv6 medium detect + recognise), in a process of its own
  started by the first answer and ended after 60 s idle; a killed reader is started again once, then the run says so.
  Floor: `read.auto_confirm_above` (0.90). Textract stays for printed codes and old papers.
- **What it is handed** (`boxes.photo`): the settled run of boxes as photographed, 2 mm around it, its own edge repeated
  1 mm. The cleaned strip is gone: it cut the pencil lying on the lines (8→3, 3→2). Code still counts ink on the
  cleaned mask. Two words are one pencil read twice only when one covers the other's middle.
- **Measured on the real 24 Sep file, production path** (133 answers with a sure gold, the session's, not a person's):
  125 read exactly, 112 stand at 0.90, 2 wrong (`copy07_q09` 145→195, `copy10_q02` 419→919). Before: Textract on the
  cleaned strip, 68 exact, 64 stand, 6 wrong. Harness: `docs/adr/0035-bench/`.
- **The server image** (built here, `packages/engine/Dockerfile`): 3.95 GB (was 2.38; the server has 21 GB free); the
  models are baked in and read with no network. Under a 1,060 MB cap (the server's available memory): 158 answers in
  53 s, the reader's peak 707 MB (437 MB its own), the engine's 57 MB. The server: 2 CPUs, 1.9 GB, no swap.
- One OpenCV: the engine now depends on `opencv-contrib-python` (4.10), the build PaddleX pins; the two packages wrote
  the same `cv2` folder. Engine suite on 4.10: `857 passed, 246 skipped`.
- `cd packages/engine && .venv/bin/python -m pytest tests/test_boxes.py tests/test_digits.py` → `23 passed`.
  `bin/check` → `13 passed`. `uv lock --check` → clean.

## The engine no longer runs out of memory reading a scan (2026-09-26)

The first live read after PaddleOCR merged ended "the engine restarted": the kernel killed the engine (`uvicorn`,
1.29 GB), not the reader. It had done so three times before PaddleOCR (25 Sep 08:11, 26 Sep 05:35 and 06:25, ~960 MB
each; `engine-logs.yml` now shows `docker inspect` and the kernel's kills). Measured here on the real files:
- `sorting.sort_file` held every photograph at once to read their codes: 750 MB for 24 Sep. Now `sorting.codes`
  reads a page and lets it go; a page whose QR fails is drawn again only for its printed code.
- OpenCV's detector on the whole page doubled: 240 MB a page. Now the corner is doubled, the page never.
- MuPDF kept every decoded page in its own store (~250 MB): `render_pdf._let_go` empties it after each page.
- Peak reading both scans' codes: **747 → 244 MB**, codes identical page for page (24 Sep 13/16, 23 Sep 29/30).
- `cd packages/engine && .venv/bin/python -m pytest tests/test_sorting.py -k one_page_at_a_time` → `1 passed`
  (fails on the old code: 309 → 468 MB for 2 → 10 pages). Engine suite `858 passed`; `bin/check` green.

## Step 1 on live — both scans re-read with PaddleOCR (2026-09-26)

`POST /read/file {again: true}`, runs `2eecaacc` (24 Sep) and `a5186848` (23 Sep), both `ok`, no restart.
- **24 Sep: 147 of 192 settled** (125 read, 22 blank; the goal's floor 144; this morning 80). 16 of 16 copies on a
  child; 168 of 192 answers read in their boxes. 13 readings saw a non-digit: most the child's own (mirror-written
  digits, a pencil dot between boxes); "T210" and "174-" look like a printed dashed line — both went to a person.
  The three that stood ("6.73", "3:22", "3.22" → 673, 322, 322) match the session's gold.
- **23 Sep: 55 of 108 settled (51%)** — under the floor. These papers were printed before L3 (23 Sep 10:08 UTC):
  their answer rows have more boxes than digits, so they do not line up with today's worksheet PDFs and 87 of 108
  answers fell back to the old whole-page reader. One old-reader reading ("81") came from printed words; it waits
  for a person (the kind is not trusted), so it did not count.
- Waiting for a person, printed papers: **300 → 288** (unreadable 167 → 85; read right but kind untrusted 50 → 108;
  wrong 39 → 51; blank 34 → 36). A better reader moves answers from typing to one click; the count is held by the
  rules of ADR 0029/0032 (every wrong and blank, and rights until a kind is trusted), not by the reader.

## The curriculum spine as one graph, with a clickable map (2026-09-26, ADR 0037 proposed)

- **Claim:** the school's spine, three words down to the engine's rungs, is one checked graph: every edge names two nodes
  that exist; every NCF-SE goal and competency feeds a capability; every competency has grades; every NCERT outcome and
  every school unit has a competency or a written reason.
- **Command:** `python3 research/spine_build.py`
- **Output:** `nodes 2504 · edges 13437 · seats ['arts', 'foundational', 'language', 'math', 'science', 'social']` … `every edge names
  two nodes that exist; every goal and competency feeds a capability; every competency has grades; every outcome and unit
  has a competency or a reason`. Layers: 3 words, 8 capabilities, 204 behaviours, 208 NCF goals, 606 NCF competencies
  (foundational 69, preparatory 127, middle 185, secondary 225), 729 NCERT outcomes (Classes 1–10), 439 school units,
  244 skills, 26 rungs, 7 platforms. Generated links: feeds 1818, expects 1563, evidences 1434, builds toward 986.
- **Command:** `python3 research/spine_council/check_seat.py research/spine_council/<seat>.json` → `OK` for all seven files.
- **Command:** `python3 research/spine_import.py --ncf <NCF-SE text> --elementary <NCERT 2017 PDF> --secondary <NCERT 2019 PDF>`
  rebuilds `docs/spine/sources/` (the PDFs are not committed; their URLs are in the script). NCF-SE's nested minimum
  standards in art and PE (LS-2) keep their own ids; the first import had dropped 49 of them.
- **Page:** `python3 research/spine_page.py` renders `docs/spine/index.html` (not committed): map, node view with its
  neuron diagram, tree, by-grade view, search. Checked at 390 px and 1280 px, no sideways scroll; tree opens three levels.
- **Not verified:** that the generated links are right (the curriculum team's pass decides); NCERT extraction folds a few
  sub-points and truncates a few rows (the seats name them); NCERT has no Hindi or Marathi outcomes in these files; 30
  school units and 6 NCERT outcomes carry a reason instead of a competency.
- **Provenance check (2026-09-27, wired in the same day):** `python3 research/spine_verify.py` runs from any directory. It
  fetches NCERT's three PDFs from ncert.nic.in into data/spine_sources/ and refuses any whose sha256 differs from
  `docs/spine/sources/official_documents.json`. Output: `NCF-SE rows found in full, word for word, in the source:
  814/814` · `NCERT outcomes found in full, word for word, on their stated page: 729/729`.
  - It now compares whole rows. The first version compared only the first 120 and 80 characters, so a changed word late
    in a long row would have passed; the longest rows are 2,227 and 1,238 characters.
  - A lone hyphen counts as punctuation, not as a word: NCERT's "etc.:-" in Class 1 Maths outcome 7.
  - Held by `goals/spine-traceable.yaml`: `bin/engine done spine-traceable` → the three sentences PROVED. Its "NOT DONE"
    comes only from this container not reaching the live database; there is no migration.
  - CI's engine job runs the same tests on every PR, with the PDFs cached under their fingerprints.
  - CI's first run, with nothing cached, failed: ncert.nic.in reset the TLS handshake, and served the same file to the
    next test seconds later. A failed request is now made again after 2, 4, 8 and 16 s; the fifth failure stops the run,
    naming the address. `pytest tests/test_spine_provenance.py` → 5 passed, two of them pinning this.
  - The first run found 19 rows broken at a line-break hyphen ("vice- versa"); fixed where the importer joins lines.
- **Plan view in the spine (2026-09-28):** `python3 research/plan_build.py` runs the same 22/22 official-quote
  check. It lays each grade's syllabus (the school's map for Grades 1–4, NCERT for 5–7, with the seats' unit relabels)
  onto 16 fortnights and writes `docs/spine/plan.json`; `python3 research/spine_page.py` inlines it into the map.
  Items per grade: 479 · 448 · 397 · 426 (school objectives) · 37 · 72 · 89 (NCERT outcomes). The day and the modes
  are the proposal in `docs/spine/plan_design.json`.
- **The spine page reads as one thread (2026-09-28, ADR 0038):**
  - `cd packages/engine && .venv/bin/python -m pytest tests/test_spine_page.py` → `8 passed`. The tests hold
    `goals/spine-readable.yaml`, whose five sentences are Nimish's words, each with its test.
  - `python3 research/spine_page.py` → `rendered … 2565 KB`. The page holds 2,772 threads, one per item (per grade for
    a unit), and 2,467 items open one.
  - `python3 research/plan_build.py` now also writes each scenario's calendar and hours, the day by mode, and the year
    paced fortnight by fortnight. A test proves the tracked `plan.json` is what its inputs build.
  - The page loads with no script error on ten routes and has no sideways scroll at 390 px. Its chart colours pass
    `validate_palette.js` in both themes: five parts for the day, and an ordinal ramp for the hour.
  - 31 of the 637 items the plan places reach no capability (30 units and 1 NCERT outcome); each thread says why.
  - Not verified: how the page reads to Nimish. That is `manual` in the goal.
- **Indicative timetable data (2026-09-28):** `python3 research/timetable_data.py` prints `22/22 quotes found word for
  word on their cited page`. The quotes come from NCF-SE Part A Chapter 4, NCERT's EVS introduction and the graduate
  profile. The script writes them, with the NCERT outcome counts for Grades 1–7, into
  `docs/brainstorms/2026-09-28-indicative-timetable.html`. The timetable on that page is a proposal. The RTE Act's
  minimums are not verified (India Code unreachable on 28 Sep).
- **The spine rebuilds byte for byte (2026-09-27):** `python3 research/spine_import.py && python3 research/spine_build.py`
  leaves `docs/spine/sources/` unchanged, and `spine.json` is identical under any PYTHONHASHSEED. The unit→skill links
  were written in a set's order; they are now sorted.


## The curriculum crosswalk, started from the documents in hand (2026-09-28, ADR 0041, goal crosswalk-start)

- **Cambridge, word for word:** `python3 research/crosswalk_cambridge.py` → `CAM-PRI-MAT-0096: 296 objectives, stages
  [1, 2, 3, 4, 5, 6], 296/296 found word for word on their page` · `CAM-PRI-ENG-0058: 581 … 581/581 …, 2 notes` ·
  `CAM-PRI-SCI-0097: 311 … 311/311`.
  - The copies are other schools' copies of Cambridge's own files, recorded with address and sha256 in
    `docs/crosswalk/sources.json`: Maths 0096 v2.1, English 0058 v2.1, Science 0097 v1.
  - Every code a plain reading of a page shows is read (an independent count per page).
  - A list under an objective ("Understand addition as:", 14 in maths) and a stacked fraction (2Nf.05 "1/4, 1/2, 3/4")
    are kept whole. They were cut short or read as "1 4" before the reader followed fonts and spans.
  - Maths' eight ways of working (TWM.01–08) are read once, from page 14.
  - PE 0069 is in the school's Drive but not read: the Drive connector cannot save a file to disk.
  - Cambridge's words are not in git; the repository is public. The tracked index and tables keep each statement's
    code, place and sha256 of its words. The words are rebuilt into `data/crosswalk_statements/`, and the build
    refuses a mismatch. `pytest tests/test_crosswalk.py` holds this: 1,190 Cambridge rows, none with words.
- **The tables:** `python3 research/crosswalk_build.py` writes `docs/crosswalk/tables/` and `views/` with no FAULT:
  - `framework 6 · framework_document 6 · framework_level 32 · framework_statement 2789 · progression 20`
  - `progression_step 200 · objective_step 1405 · objective_waiting 345 · claim 1848 · claim_decision 0`
  - NCF-SE's 814 statements each now carry a PDF page, found word for word on it.
  - NCF-SE's stage ages are printed (page 62). NCERT's classes and Cambridge's stages carry ages worked out from them
    (Grade g is ages g+5 to g+6; six Cambridge stages over "aged 5 to 11").
- **The drafting method and the sample:** `docs/crosswalk/drafting-method.md` (the prompt, version 1) and
  `docs/crosswalk/drafts/math-number-8.json`:
  - 30 Grade 3 Number objectives, 100 alignments, the outcome, four rubric lines and 14 statements no objective covers.
  - The build refuses a draft that breaks the method: a missing Cambridge Stage 3/4 Number objective is a FAULT.
  - `python3 research/crosswalk_sheet.py MATH.NUMBER.8` → the first-round sheet: 10 objectives, the outcome and its four
    rubric lines, and 5 not-covered statements.
  - It is a Google Sheet shared with Akanksha as editor on 28 Sep (`docs/crosswalk/review/math-number-8.sent.json`).
    Downloaded back as CSV, it has 41 rows and 0 cells different.
  - Her decisions come back with `python3 research/crosswalk_decisions.py MATH.NUMBER.8 <file.csv> --by Akanksha`.
- **Compare with the official files:** `~/cornerstone/assessment-engine/bin/compare-cambridge <file.pdf> …` runs from any
  directory.
  - It tells the framework from the file's first page and reads it with the same reader.
  - It writes the differing words under `data/crosswalk_compare/`, never committed.
  - On the three copies themselves → `296 the same, 0 changed` · `581 the same, 0 changed` · `311 the same, 0 changed`.
  - On a machine without `data/crosswalk_statements/`, it reads the recorded copy again.
  - A file that is not one of the three is refused by name.
- **Tests:** `cd packages/engine && .venv/bin/python -m pytest tests/test_crosswalk.py` → `10 passed`. They read only the
  tracked tables; each of Nimish's ten sentences in `goals/crosswalk-start.yaml` names one.
- **Not verified:**
  - that the drafts are right: Akanksha decides;
  - Cambridge's per-stage ages (inferred from the range);
  - the 345 objectives waiting for a strand: occasions such as projects, quizzes and visits, and course-book units that
    mix reading and writing.
- **Found in the school's objectives** (`supabase/seed/registry.json`, generated from the Skill Map Review, not edited
  here):
  - 78 of the 89 Grade 4 Numeracy objectives have exactly a Grade 3 title, and 212 of the 410 Numeracy objectives
    share a title with another grade.
  - 36 objectives carry a replace of "art" inside words: "PVisual arts 2" for "Part 2", "EVisual artsh" for "Earth",
    "Assembly PVisual artsicipation".
  - Projects are split into fragments at "/".
  - Geography and History units sit under Visual Arts and Global perspectives.

## S23 — a photographed page is lined up by its own print (goal s23-a-curled-photo-lines-up, ADR 0042, 2026-09-28)

Goal `s23-a-curled-photo-lines-up` (step 1). Not green until its live scenario runs: the re-read of 24 Sep after this
deploys.
- **The failure.** R31-H02 copies 01 and 02 of 24 Sep were read as old papers, none of their 24 answers in their
  boxes. The old line-up (ORB, one straight map, at least 60 matched features) matched 37 and 40 on their
  photographs. The corner squares were ruled out on the pages: the scan app cut the top two off both.
- **The tests.** `cd packages/engine && .venv/bin/python -m pytest tests/test_lineup.py` → `8 passed`. On main's
  reader, 7 of them fail for the reason each names:
  - the lifted page misread;
  - the smeared answer read as blank;
  - a crop's true corner outside the box shown;
  - a page refused on 37 matched features;
  - the 7 mm fold misread.

  The eighth, a page that is not this paper, holds on both.
- **On the 46 photographed pages of 23 and 24 Sep** (scans in a scratch folder, not the repository):
  - every page lines up, and 324 of 324 answers are found;
  - the last step, each answer found around its own question, moves a run 0.1 mm at the median, 1.0 mm at the
    99th percentile, and 2.9 mm at most;
  - 1.3 s a page on 4 CPUs.

  Before, 2 pages were refused, and on 23 Sep answers were left up to 7 mm off.
- **The layout each 23 Sep copy was printed in** (ADR 0040) is chosen as before: 2026-09-21 for all four worksheets,
  with the right layout's agreement 1.27–1.84 against 0.0–1.32 for the others.
- **Memory.** One line-up takes 234 MB more at its peak (33 MB before), measured as peak resident memory on one 24 Sep
  photograph. SIFT runs at 1000 px: at 2000 it alone took 715 MB.
- **With the real reader on the 16 photographs of 24 Sep**, the full `boxes.read_page` path, scored on ADR 0035's gold
  (141 sure answers, copies 03–16):
  - 192 of 192 answers read in their boxes (168 before, with copies 01 and 02 read as old papers);
  - 104 stood behind and right (105 before);
  - 2 stood behind and wrong: copy07_q09 145→195 and copy10_q02 419→919, both known since ADR 0035 (3 before, copy14_q04
    1747→174 too);
  - 17 doubts with the right guess (20 before).

  19 of the 141 outcomes moved, in both directions. The reader reads the same crop differently when it moves by under a
  pixel (ADR 0042, Consequences).
  - Copy 01: 10 read, and 2 to a person with the right guess (673, 240).
  - Copy 02: 4 read; its 8 other questions are blank on the paper (6 read blank, 2 marks to a person).
- **On live, 28 Sep.** Merged in #114 and deployed. Then `POST /read/file {again: true}` for the 24 Sep file: run
  d8337ebc, `ok`, 13:57–14:04 UTC.
  - The 5 copies nobody had worked on (03, 06, 08, 12, 16) were read again with the new line-up. All 60 of their
    answers are read in their boxes. Answer by answer, 57 of 60 match the same code run locally on the same
    photographs; the other 3 differ only in the guess the server's second reader adds to a doubt.
  - On those 5 copies the tally moved: right 27→26, wrong 8→6, blank 8→8, unclear 17→20. This is the reader's
    sub-pixel sensitivity, as measured locally.
  - The 11 copies a person had worked on, 01 and 02 included: no answer's reading changed. Every answer on them had a
    person's check or correction, and a re-read keeps those (#107). If an answer had been read again, its reading
    would have changed: new crops change what the reader sees, and the old reader would have dropped `boxes`. So
    copies 01 and 02 are as Nimish corrected them.
  - `GET /read/scan/24 sept.pdf/copies` → 16 of 16 copies on a child.
  - `engine-logs.yml` after the run: `oom_killed=false restarts=0`. Available memory 782 MB of 1906; swap used
    1038 of 2047.
  - `bin/engine done s23-a-curled-photo-lines-up` → both of Nimish's sentences PROVED ("its in proper boxes and qr
    and all": 3 passed; the fold: 1 passed). It reports NOT DONE only because this container cannot read the live
    database's migrations.

## Box reader, re-reads and the loop's end: #100–#110 (2026-09-28)

- **The server does not run out of memory reading a scan** (#100: 2 GB of swap, set up by `deploy-engine.yml`). The 23 Sep
  read had been killed by the OOM killer at 07:14; after the swap it completed.
- **The box reader** (#102, #104, #105):
  - an educator's tick in an empty box is not a digit (`boxes.DIGIT_TALL`);
  - a box's own printed line left in the cell is not ink (`boxes.marks`, `EDGE_LINE`);
  - a child's kept PDF with no geometry gives way to the layout the page matches (`copies._read_from`).
  - Tests: `test_boxes.py`, `test_copies.py`.
- **A re-read reaches the answers nobody has checked** (#107, `w3_read/checked.py`). Signed-off and corrected answers
  keep their rows exactly (`test_legacy.py::test_a_signed_off_answer_keeps_its_signature_when_the_paper_is_read_again`).
  - 23 Sep on live, run `eda671c0`: 80 → 86 of 120 settled (72%).
  - Goal s17's floor is 75%, so s17 is **not green**. What remains is mostly dropped digits, which is step 3's.
- **A mistake is named, and its fix given, for its question's operation** (#102, #109, `core/mistake_names.py`).
  - Checked on live, `GET /report/{child}` for all 11 G2 children: every named mistake carries its `hint` and the
    child's own example.
- **Marking shows the reader's accuracy by confidence band, with today's floor** (#103).
- **The report card** (#109, `/growth/[id]/report`, goal u6):
  - a skill map, the three signals, what goes well, each mistake with the child's own example, next steps;
  - `npx playwright test tests/u6-report-card.spec.ts` → 5 passed.
- **The parent report** (#110, `/growth/[id]/parent`, goal w4c):
  - Code computes the facts; the `parent_report` prompt writes the words and never sees the name; code holds the words
    to the facts; an educator approves.
  - `pytest tests/test_parent_report.py` → 6 passed. `npx playwright test tests/u7-parent-report.spec.ts` → 4 passed.
  - **The prompt is not active yet.** Rule 7 requires a score first: run the `engine eval` workflow on the server.
- **Found:** `parent_note` v1 sent the child's first name to the model (rule 6) and had no eval (rule 7). It is now
  inactive; `parent_report` replaces it.

## Jev on the server, and the parent-report checker reads with Jev first (2026-09-29, goals j4, j5)

- **The engine on the server has Jev's key.** Actions → engine logs (run 36519464404, from this branch):
  `TYPESAFE_API_KEY is set`. The key lives in `~/assessment-engine/.env` on the server; every deploy carries it across.
- **Each of Jev's three uses, scored where it runs** (Actions → engine eval, from this branch, the server's code):
  - `week_skills` (run 36519649576): `the exact skill sets on 21/24 notes · precision 0.935 · recall 0.967`
  - `story_shape` (run 36519781611): `named 65/65, the shape right on 63 · one-step answers computed 44, wrong 0 ·
    left for a person 0`
  - `mistake_guess` (run 36519894157): `the right mistake first 66/120, among the three 108/120 · slips called NONE
    30/30 · slips given a mistake 0` (goal j1's bar: 90 of 120 among three, no slip named — held)
- **An eval Jev cannot answer fails and names why** (before: `week_skills … 0/24` and exit 0 with no key):
  `pytest tests/test_cli.py -k jev_eval` → 3 passed; each eval counts `unanswered` (`jev.counting`).
- **What coins make is code's** (`parent_check._coins`): `pytest tests/test_parent_report.py -k coins` → passed; no
  draft of the gold a person found right is refused.
- **The parent-report checker, code then Jev, on its gold set** (21 drafts, 14 wrong sentences; local copy, real Jev):
  `bin/engine eval parent_review --jev-version 1` → `12/14 wrong sentences caught, 0 flagged that were right, over 21
  drafts (5 by code first) · the model read 0 of 310 sentences`; exit 1 (below the bar). Jev was unsure of 49 of the
  310 sentences, both misses among them (r1 0.27–0.28, e10 0.21–0.22 over two runs).
- **Not yet verified:** the whole chain with the model (`parent_review` v2, Haiku) reading those 49 — its key is on the
  server only. Owed after merge: Actions → engine eval → parent_review, version 2, jev_version 1. Nothing is switched on
  until it catches 14 of 14 with none flagged wrongly (rule 7); until then `review()` reads nothing, as before.
- **The checker's model reads only what Jev leaves it, under names that claim nothing** (goal j5, later the same day):
  - Haiku alone on whole drafts (parent_review v2, Actions run 36520653494 on the server): `10/14 wrong sentences
    caught, 71 flagged that were right` — 65 of the 71 were one misreading: every skill set's line sits under the
    draft's `can_do`, and in the facts `can_do` means secure, so a line for a nearly secure skill set read as a claim.
  - Skill lines are now asked of Jev as lines about their skill set (`parent_review.skills` v1) and given to the model
    as `skill_lines`. Code then Jev (local copy, real Jev): `bin/engine eval parent_review --jev-version 1` →
    `12/14 wrong sentences caught, 0 flagged that were right, over 21 drafts (5 by code first)`; Jev unsure of 16 of
    310 sentences (49 before the skills question), both misses among them (e10 0.20, r1 0.30).
  - A prompt row names how hard its model thinks (migration 20261016090000, `prompt.effort`); `llm._call_anthropic`
    sends `output_config.effort` to the row's own model, never a fallback: `pytest tests/test_llm.py -k effort` and
    `pytest tests/test_loaders.py -k effort` → passed.
  - The settings loaders (prompts, thresholds, config) are their own module, `core/settings.py`; `loaders.py` 468 →
    413 lines and its frozen ceiling lowered to match.
  - **Not yet verified:** parent_review v3 (Haiku 4.5), v4 (Sonnet 5.5, low effort), v5 (Opus 5.5, low effort) on the
    server, each with jev_version 1 — after merge, when the migration and the seed are live.

## S24 — question 5: a split that adds up is right (goal s24-a-split-that-holds-is-right, ADR 0043, 2026-09-29)

- **An equation's boxes are marked by the equation** (`assess/equation.py`, `marking.correct`): 600 + 19 + 19 is right
  for "638 = 600 + [ ] + [ ]", as 30 and 8 are; each side is its own claim (1100 + 0 + 13 right beside a total of 1112).
  `pytest tests/test_equation.py tests/test_legacy.py tests/api/test_capture_routes.py` (local copy) → `77 passed`.
- **Every equation the school's papers name is one their own key makes true:** 26 boxes in eight equations, question 5
  of G3-SEPW1-A, G3-SEPW1-B, G4-SEPW1; a paper whose key does not make its equation true is refused when entered.
- **Every seed paper enters where `bank rehome` files it** (local copy, all 17 papers entered in one transaction, rolled
  back): `rehome._old_papers` → 0 sums to move; 9 before the loader filed a sum by its shape first (G2-CAM-A 7b R11 →
  R26; G2-WORD-SEP17 1-3, 5-8, 10 R8 → R22/R24). Pinned: `test_every_paper_is_entered_where_bank_rehome_files_it…`
  fails with `assert 9 == 0` on the old rule.
- **Every deploy enters each paper again** (`deploy-engine.yml`, after the engine is up; a paper that cannot be entered
  fails the deploy): `test_a_deploy_enters_every_paper_again_as_its_file_now_says` → passed.
- **`marking.py` 397 → 326 lines:** naming a wrong answer's mistake moved to `w3_read/naming.py`. `bin/check` →
  `13 passed`, lint and format clean.
- **Whole suite, local copy:** 115 failed or errored on the branch; 113 of them fail identically on main (seed data and
  models this container lacks). The other two were the capture routes' tests patching the moved functions by their old
  module; fixed, `tests/api/test_capture_routes.py` → `12 passed`.
- **On a copy of live** (Actions → rehearse update-live, run 36547703784, from this branch): every seed paper entered
  with the new loader, then `bank rehome` → `moved 0 questions · 0 old papers' sums onto their skill`; relabel 0
  changed, `3010 worksheets · 102 of 102 skill-levels ready · 0 problems`, `233 states · 359 questions with confirmed
  answers`. The run's last check failed on two lines already failing before any step ran, on live's own rows:
  this branch's migration 20261016090000 not yet on live (applied on merge), and `paper CS57B729: 12 answers counted
  for 12 questions printed, 6 counted twice` — two live captures of one sheet with results for the same six
  questions. Pre-existing, not this work's; it waits for a person to say which capture is superseded.
- **With main merged (#130, #131), on a database built as CI builds it** (`bin/testdb fresh`, 45 migrations, local
  Postgres 16): `pytest tests/test_equation.py tests/test_legacy.py tests/api/test_capture_routes.py
  tests/test_loaders.py tests/test_layout.py tests/test_promises.py` → all passed, including
  `test_a_signed_off_equation_is_put_right_one_saved_box_at_a_time` (a signed-off box marked again by its own Save,
  its evidence with it; a signed-off partner untouched until saved).
- **Not yet verified:** on live. After merge the deploy enters the papers; then each box of each question 5 equation
  still marked wrong is saved again.

## The parent report's checker: three models scored on the server, and what code now holds (2026-09-29, goal j5)

- **Behind Jev (jev_version 1), before the rules below** — Actions → engine eval, main 3e15a79:
  - Haiku 4.5, parent_review v3 (run 36571102880): `13/14 wrong sentences caught, 8 flagged that were right … the
    model read 16 of 310 sentences`
  - Sonnet 5.5 low, v4 (run 36572682537): `13/14 …, 7 flagged that were right … the model read 17 of 310 sentences`
  - Opus 5.5 low, v5 (run 36573750680): `13/14 …, 3 flagged that were right … the model read 18 of 310 sentences`
  - All three missed e10's "Try the kite question beside this together"; all three flagged e7's summary "[child] can
    add two 2-digit numbers …" of a skill only improving. Nothing is switched on.
- **Nimish ruled, the same day,** two sentences the provisional gold called right to be wrong (ok4, e7, e12's
  improving-skill claim; r1's 3-digit subtraction the facts do not hold). The gold is relabelled: 18 wrong sentences.
- **Code holds two more things** (`parent_check`): a question, story or example the words name is one the facts hold;
  a summary sentence that names an improving skill says it has improved. `pytest tests/test_parent_report.py
  tests/test_parent_review.py` (local copy) → 34 passed; no draft of the gold a person found right is refused.
- **Code then Jev, relabelled gold** (local, real Jev): `bin/engine eval parent_review --jev-version 1` →
  `16/18 wrong sentences caught, 0 flagged that were right, over 21 drafts (11 by code first) · the model read 0 of
  227 sentences`; Jev unsure of 14, r1's two-clause sentence among them.
- **Not yet verified:** the three models scored again on the server after merge, each reading those 14.

## S25 — a reading is marked by what it says; every deploy marks again (goal s25-a-reading-is-marked-by-what-it-says, ADR 0044, 2026-09-30)

- **Found on live** (Nimish's Marking page, the Grade 4 September Week 1 paper): question 11B "odd + odd = odd" and
  11C "odd - odd = odd", "You said the child wrote false", both wrong and signed off. The keys were right
  ("Not true"). `marking._against_the_key` compared the letters of "false" with "Not true". The same boxes are on
  G3-SEPW1-A (11a-d), G3-SEPW1-B (9a-c) and G4-SEPW1 (11a-d); the reader hands every one of them to a person.
- **Marking by meaning:** `marking.TRUTH` gives true and not true however a person types them; any other key is
  marked as it was before.
  - `pytest tests/test_legacy.py -k claim_ticked` → passes.
  - Without the fix: `AssertionError`, "false" is wrong against "Not true".
- **Marking again:** `marking.mark_again` (now `again.mark_again`, S26) (`engine legacy mark-again --by`) marks each answer a person read by the rule
  as it now stands.
  - A changed mark on an answer not yet signed off is written in place.
  - A changed mark on a signed-off answer gets a new evidence batch; the old one stays in `evidence_event`, and
    `evidence_placed` reads the new one.
  - What a person read is kept, and so is a person's judgement.
  - A second run changes nothing.
  - Command: `pytest tests/test_legacy.py -k rule_put_right` → passes.
- **Runs on:**
  - every deploy, after the papers (`deploy-engine.yml`);
  - `bin/update-live`;
  - the rehearsal on a copy of live.
  - Pinned by `test_a_deploy_marks_every_answer_a_person_read_by_the_rule_as_it_now_stands`.
- **ADR 0043 amended:** a signed-off box of question 5 whose side holds is now put right at the next deploy, with no
  Save needed.
- **Checks:**
  - `pytest tests/test_legacy.py tests/test_equation.py tests/api/test_capture_routes.py tests/test_gold.py
    tests/test_layout.py tests/test_report.py`: all pass (local Postgres 16, the `ci` database).
  - `bin/check` → exit 0.
- **`marking.py` is at 392 of 400 lines.** The next rule added there splits it along a real seam first, for example
  comparing a reading with its key into `assess/`.

## S26 — the right answer shown as stored, and an educator corrects it for every child (goal s26-the-right-answer-shown-and-corrected, ADR 0045, 2026-09-30)

- **Asked on live:**
  - Question 4A on the Grade 4 paper was typed 78 and marked wrong. Nimish asked to change the key for every child.
  - The key was right: 48 + 35 is 83. The 78 was 4B's, on the number line.
  - Then Nimish: "the key can be changed by an educator … in any correction, the system should show what the right
    answer is as stored in the system".
- **Built:**
  - Every card on the paper page, and the answer in the queue, shows "Right answer …" as stored (`keys.shown`,
    `GET /capture/{id}/keys`), and who changed it.
  - "Is the right answer wrong? Change it for every child" (`keys.change`, `POST /paper/key`). Code checks the new
    answer first (`keys.check`).
  - The change is a `key_correction` row (migration 20261017090000, append-only). `engine legacy paper` puts it back
    after entering the file (`keys.reapply`), so every deploy keeps it.
  - Every answer to the question is marked again (`again.mark_again` and `again.remark`, limited to the question).
    Signed-off answers get a new batch of evidence.
- **Marking again moved** from `marking.py` (392 of 400 lines) to `w3_read/again.py`.
  - A deploy still marks again only what a person typed.
  - A key change also reaches a signed-off answer no person typed, but only when its reading gives its mark by the old
    key (`again.by_new_key`).
  - A judgement is never changed. One made by the old key is named, and the page counts those.
  - Any other mark is a person's own call and stays: a judgement against the key, or a pre-U3 Right / Wrong / Blank
    that left no row.
  - Caught before merge: the first build re-marked every signed-off answer by the engine's stored reading, so a
    person's Right on a misread 18 would have turned wrong (`test_a_changed_right_answer_reaches_what_was_signed_off_
    as_read_and_leaves_what_a_person_decided`, which failed on that build and passes now).
- **Found and fixed:** the paper page asked for Jev's mistake shortlist by the paper's id, while `naming.unnamed`
  looked answers up by the capture's id, so the shortlist never showed on a paper page. Both now take either
  (`naming.ONE_PAPER`), pinned in `test_a_wrong_answer_no_mistake_explains_is_named_by_a_person_from_jevs_shortlist`.
- **Rehearsal:** the copy recorded no migration it applied from the branch, so its closing "every migration is
  applied" failed on any branch that brings one (run 36672769380). It now records each, as `supabase db push` does.
  On that run's copy of live, the branch's mark-again changed nothing: `legacy/G3-QUIZ20/8` stays wrong (held,
  needs_teacher makes no evidence).
- **Deploy order:** `deploy engine` now waits for `migrate live` to succeed on the same commit when the merge carries a
  migration, so the engine never runs code reading a table live does not have yet. Checked against a stand-in for the
  GitHub API: no migration, a run that appears late and succeeds, one that fails, and one that never finishes.
- **Checks:**
  - `pytest tests/test_keys.py tests/test_legacy.py tests/api/test_capture_routes.py tests/test_equation.py
    tests/test_gold.py tests/test_report.py`: all pass (local Postgres 16, the `ci` database with the migration
    applied).
  - `npx playwright test tests/s26-right-answer.spec.ts`: 2 passed, on a production build with the real engine and
    the local copy. The machine's own Chromium was used (`executablePath`), because the pinned Playwright wants a
    newer one.
  - `u3-marking.spec.ts`: 5 passed.
  - `s4-validation-queue.spec.ts` "each paper has one spot-check": fails before loading any page. Its setup query
    finds no spot-check candidate in a fresh copy (live's rows), so it fails the same way without this change.
  - `npx tsc --noEmit` and `npm run build` pass. `bin/check` → exit 0.

## W4d — every parent report that is due, written by one command (goal w4d-every-report-written, 2026-09-30)

- **Asked:** Nimish, 2026-09-30: "the reports havent been generated for grade 3; please go ahead and generate all the
  reports". Until now a report was written only when someone pressed each child's button. On 2026-09-29 that was done
  for G2's eleven and G3 roll 1. G3 rolls 2-5 had nothing signed off then, and their papers were signed off after.
- **Built:**
  - `engine report parents --by … [--band G3]` (`w4_close/every_report.py`) finds every active child with signed-off
    answers whose newest report is missing or out of date (`due`).
  - It writes each in turn with the page's own `parent_report.start` and `.write`, so each report is held to its facts
    and kept as a draft for an educator to approve.
  - It prints each child by band, class and roll, never by name, with "kept" or why not. It exits 1 while any report
    due was not kept.
  - `.github/workflows/write-reports.yml` runs it on the server (band: all, G2, G3 or G4).
- **Checks:** `pytest tests/test_every_report.py tests/test_parent_report.py tests/test_cli.py tests/test_layout.py` →
  58 passed (local Postgres 16). `bin/check` → exit 0.

## S27 — G3 roll 5 is a Grade 3 child; a class works at its children's grade (goal s27-a-child-in-their-own-grade, 2026-09-30)

- **Found:** writing every report due, the command named "G4 G3 roll 5": class G3, band G4. Their report said
  "Grade 4". Nimish: "G3 roll 5 should be band G3, fix it".
- **Cause:** only the class list sets a child's band (`engine week roster`, `core/roster.py`), so the slip is in that
  file, kept outside the repository because it holds names.
- **Fixed:**
  - Migration 20261018090000 moves class G3 roll 5 to band G3, only while they still say G4.
  - A class's grade is now its active children's most common band, the lower on a tie (`roster.class_band`). The
    week's declaration and its proposal had taken it from whichever child Postgres returned first (`limit 1`).
  - Loading the class list names each child whose grade it changes, so the old file loaded again cannot undo the fix
    unseen.
- **Still manual:** correct roll 5's band in the class list file itself.
- **Checks:** `pytest tests/test_roster.py tests/test_week_note.py tests/test_week.py tests/api/test_week_routes.py
  tests/test_every_report.py` → all pass (local Postgres 16; the two tests that render a PDF need the pinned Chromium,
  run with it). `bin/check` → exit 0.

## U8 — the Children table (goal u8-children-table, 2026-09-30)

- **Asked:** Nimish, over the Children page's dot cards: "We have a proper tabular view here that outlines children
  with their grades or something like that, and then that is clickable". He chose "Standing + next step" as the row.
- **Built:**
  - /growth is now one table per grade: roll, name, grade, class, the skill they most need help on (red before amber,
    the least often right first), how many skills are secure and how many practising, last paper read, and the parent
    report (none, draft, approved, or out of date once answers were signed off after it) (`childTable`).
  - A click anywhere on a row opens the child: one link per row, stretched over the row. Any heading sorts
    (`?sort=`).
  - Each class still opens as its children against every skill. Names come through `pii.read_child`, which logs who
    asked.
  - The class cards' query `classes()` had no other caller and is removed.
- **Checks:** `npx playwright test tests/u8-children-table.spec.ts tests/u2-children.spec.ts` → 10 passed;
  `screens`, `gate`, `s1-site-answers` → 32 passed (production build, real engine, local copy; the machine's own
  Chromium, and the engine's PDFs with it). `npx tsc --noEmit`, eslint and `bin/check` pass.

- **Fixed before merge (3c6dc18):** a sorted heading said "descending" for every column, Name (A to Z) included; each
  column now carries its own direction ("other" where the order is what needs doing first). The row-click test scrolls
  the row into view first: with more classes on the copy the row sat below the fold and the click landed nowhere.

## U9 — Papers, one menu item and one list (goal u9-papers, 2026-09-30)

- **Asked:** Nimish: "I really don't think marking and marking papers as two different types are essential. We can
  merge them into one" and "one list of papers with the right filtration and all, and a good view".
- **Built:**
  - The menu is Today, Children, Papers, Curriculum. Papers covers /papers, /capture, /make and a child's own printed
    paper (/worksheets/CS…); a library worksheet stays under Curriculum.
  - /papers is one table of every paper: the paper (its skill and level, or its title), kind (class practice, class
    assessment, home assessment, a chosen paper, or an earlier paper), class, child, week, stage (made, printed,
    scanned, checked, signed off), answers waiting for a person, and the score once checked (`paperList`). Void papers
    are left out; the newest 300 show, and the page says when there are more.
  - The stage chips count each stage under the other filters, and each one is the filter. A form filters by class,
    child, kind and week.
  - A click anywhere on a row opens the paper where its work is: its answers once scanned, the page before.
  - Making a paper, reading a scan (the same form as /capture, which now returns to the page it was sent from), and
    the queue of answers to check all start here. The pages under it say "Papers · …" above their titles.
  - Names are read once per shown child through `pii.read_child`.
- **Checks:** `npx playwright test` on u9-papers, u3-marking, u1-today, s1-site-answers, s4-validation-queue,
  m2-make-papers, u8-children-table, screens and e2e → 65 passed, 1 failed, 7 skipped. The one failure is
  e2e "every child's paper has its own code": it needs a G3 T2W1 week, and this copy has no T2W1 paper at all. The 7
  skipped are the serial e2e tests after it. CI does not run the browser suites; its web job typechecks and builds.
  `npx tsc --noEmit`, eslint and `bin/check` pass.
- **Fixed after the first run (0c430b4):** a paper drawn for one child (`focus_paper.make`) records no skill set on its
  template, so its row was titled by its QR code. It is now titled by its questions' skill sets and levels.

## M3 — the maker (goal m3-the-maker, 2026-09-30)

- **Asked:** Nimish: class practice, class assessments and home assessments, each "for multiple children", in "an
  interface in itself": "the same skill paper for multiple children", "individual papers for each child", and "choose
  the right skill and the grade level, and then choose the children and generate different questions".
- **Built:**
  - `w2_print/maker.py`: `plan` (writes nothing), `make` (in the educator's name) and `pdf` (the batch as one PDF, in
    roll order). It serves any children of one class, in three ways:
    - `same`: one paper for all, the same questions on every copy, none any of them has been given;
    - `each`: the chosen skill and level, a different draw for each child, no two sharing a question;
    - `own`: each child's next step from their graph, which the educator can change for any child.
  - Every paper is drawn and printed as a home paper is (`focus_paper.print_paper`, now shared): its own code, kind,
    class and week, and its questions recorded as seen, so it lands in Papers and in the class's pack.
  - A child the bank cannot fill is named with why. `make` then refuses the whole batch rather than printing part of
    a class. A home assessment is one a child a week, whoever chose it.
  - Routes: `POST /papers/plan`, `POST /papers/make` (the same form sent twice makes its papers once),
    `GET /papers/pack.pdf`.
  - Screen: /papers/make ("Make a paper" on Papers). Pick the class, what the paper is, how, and the children; see
    every child's paper; make them; print them all as one; see them in Papers. The old /make is titled "Home
    assessments", which is what it lists.
- **Checks:**
  - `pytest tests/test_maker.py tests/test_focus_paper.py tests/api/test_maker_routes.py tests/api/test_paper_routes.py`
    → 21 passed.
  - `npx playwright test` m4-the-maker, m2-make-papers, u9-papers, screens, u2-children and u1-today → all passed.
    That includes the maker at phone width: its table scrolls, the page does not.
  - `npx tsc --noEmit`, eslint and `bin/check` pass.
- **Fixed on the way:** two u2 checks passed vacuously while the page was still a skeleton. The "nothing to approve"
  child (Chetan) is secure on every answer, so he is stretched; Bina, with no answers, is the child with nothing.

## U10 — tables that read straight; the reader as one table (goal u10-tables-read-straight, 2026-09-30)

- **Asked:** Nimish, over the Marking page's reader tables: "The column names are not well formatted and
  center-aligned … the table alignment is distorted across all the places", and "just one table, which can have a
  toggle around confidence levels, the date, etc. … which very clearly shows how the engine is improving or not".
- **Root cause of the drift:** every `<th className="text-right">` in the app was silently left-aligned. The shared
  rule `table.grid th { text-align: left }` outranks a utility class. So numbers sat right under headings on the left.
- **Built:**
  - `table.grid .num` now centres a short value (count, share, date, level, pill) and its heading together. Names and
    sentences stay left.
  - All 19 files with tables are swept: 26 headings take `num`, and pill, date, level and grade columns take it on
    heading and cells alike.
  - The reader panel is one table with a toggle (`capture/reader-table.tsx`):
    - by day first, with each day's move against the day before (▲/▼ points) and one sentence on the first day read
      against the latest;
    - by kind of question, every kind in words from `KIND`, and the school's earlier papers named as such;
    - by how sure it was.
- **Checks:** `npx playwright test tests/u10-tables-read-straight.spec.ts` → 3 passed.
  - It compares every heading's computed alignment with its column's on /papers, /capture, /growth, /make, /library
    and /worksheets, and in each reader view.
  - It checks the day-against-day arithmetic from the table's own rows, on two days the test seeds.
  - s4, u3, u8, u9, m2, m4, u2, s3, s5 and screens → all passed.

## U11 — what the colours mean, and a check for grey (goal u11-colours-said, 2026-09-30)

- **Asked:** Nimish: "The clarity of what each of the colors means has not been very clearly mentioned. How do we
  classify students across different tiers?" And: for grey, "a clear recommendation around the next set of
  assessments … so that we know where the child is".
- **Built:**
  - `lib/colours.ts` reads the rows `rebuild_child_skill_state` decides by: `state.min_events`,
    `state.min_observers`, `next_sheet.promote_at`, `next_sheet.demote_below`, and `prescribe.band_default`. The
    check size is derived from them: the larger of the minimum answers and the fewest answers in which the green
    share can show (5).
  - `components/colour-key.tsx` is "What the colours mean", on Children, each class and each child. For each colour
    it gives when a skill is that colour, in those numbers, and what comes next.
  - `growth/checks.tsx` lists the checks that would place them:
    - On a class, every step where some child is grey or has no answer, those children with their counts.
    - On a child, their grey skills, then their grade's skills not yet assessed.
    - Each check is a class assessment at the grade's starting level, 5 questions, different for each child. "Make
      this check" opens the maker with the children, skill, level and size already chosen.
  - The class grid's step headings are centred over their dots. u10's alignment check now covers tables whose
    headings span two rows.
- **Checks:**
  - `npx playwright test tests/u11-colours-said.spec.ts` → 2 passed. The key's numbers are compared against the
    threshold rows on three pages, and a check against its children, level, size and the maker it opens.
  - u10, u2, u8, m4 and screens → 41 passed.

## U12 — the curriculum as one table that opens (goal u12-curriculum-table, 2026-09-30)

- **Asked:** Nimish, over the Curriculum page's nested boxes: "this should be like a proper table, and that table
  needs to have some kind of an expand/collapse … within grade 1, within mathematics, there are addition and
  subtraction, and then within that, there is sub." The columns: questions, worksheets, the levels, "number of
  students which have been there", and taught "based on the assessments".
- **Built:**
  - `lib/queries-curriculum.ts` `curriculumRows()`: one row per grade, subject, topic and skill, every row with the
    same numbers.
    - A skill's questions and worksheets are counted at the levels its grade holds. A level another grade holds is a
      dash (a skill's Advance may be Grade 3's).
    - A topic, a subject or a grade adds up its rows.
  - Children assessed: the active children with a checked answer on the skill (`child_skill_state.n_events > 0`). At
    a topic or a grade, each child is counted once across its skills.
  - Taught is read from the answers: a skill is taught once any child has a checked answer on it. A topic or a grade
    says how many of its skills are taught ("4 of 7").
  - `app/(app)/curriculum-table.tsx` is the table.
    - A grade opens its topics; its one subject opens with it. A topic opens its skills. "Open everything" and
      "Close everything" do both at once.
    - A skill's sentence opens its page. A level's count opens those questions in the bank. The worksheets count
      opens the skill's worksheets.
    - A skill waiting for approval says so on its row.
- **Checks:**
  - `npx playwright test tests/u12-curriculum-table.spec.ts` → 2 passed. It opens and closes the table row by row. It
    also recomputes one skill's and one topic's numbers in SQL and compares them with the rows.
  - u5's four tests are rewritten for the table under their own names → 4 passed. s2 and the three e2e skill-map
    tests are moved from the old tree to the table → passed.
  - u10's alignment check now covers the Curriculum too.
  - The whole steps, screens and map suites, on a production build, a fresh copy and the real engine: 113 passed and
    1 failed. The failure is s7 "names the worksheet each child was given": it needs live's G2 class, and a fresh copy
    has none (already named at U2). 6 were skipped (s4, with no read papers here) and 2 did not run (s7's followers).
- **Not proven, by design:** "taught" is inferred from answers, as asked. A check that places a child on a skill
  their class has not been taught (u11) marks that skill taught. No table records teaching itself.

## The previews build again: importing a page touches no database (2026-09-30)

- **What failed:** every Vercel Preview from #140 to #143, about a minute after each push. Production built each time.
- **Cause:** `lib/queries-papers.ts` (U9) built its SQL fragment when the module was imported. A page is imported to
  build it. Preview has no DATABASE_URL (see "The website builds without a database", 2026-09-21), so `sql` was
  the stand-in that refuses on first use, and the build stopped at `/papers`.
- **Why CI missed it:** CI's web build was handed a made-up DATABASE_URL, so `sql` was a real, lazy client there.
- **Fixed:**
  - The fragment is a function, called when a query runs.
  - CI's build now runs with no DATABASE_URL, as Preview does. A page that touches the database on import now fails
    CI before it reaches Vercel.
- **Checks:**
  - Before the fix, `next build` with no DATABASE_URL → "Failed to collect configuration for /papers … DATABASE_URL
    is not set". After the fix → exit 0.
  - CI's own steps (typegen, `tsc`, build) with no DATABASE_URL → exit 0.
  - u9 and u3 → 7 passed.

## Phase 0, PR 1: papers survive a deploy; live waits for CI; our functions answer only their owner (2026-10-01)

Nimish on 2026-09-30 asked for a scored review and "a code quality of 9/10 from a proper reviewer". On 2026-10-01 he
said "go ahead with phase 0". This PR is steps P0.4, P0.3 and P0.1, in that order: every later Phase 0 merge deploys,
so papers had to survive a deploy first.

- **Papers survive a deploy** (`goals/p0-papers-survive-a-deploy.yaml`).
  - The engine writes papers, worksheets and packs under `db.REPO_ROOT / "data"`, which is `/app/data` in the image.
    That folder was the container's own, so every deploy's rebuild deleted it.
  - `compose.server.yml` now mounts `~/cornerstone/data` there.
  - The deploy that switches over copies the old container's folder across once.
- **Live waits for CI** (`goals/p0-live-changes-wait-for-ci.yaml`).
  - `deploy-engine.yml` and `migrate.yml` start from `workflow_run` once `ci` completes on main, only on success, and
    each checks out the commit CI passed on.
  - Only main's newest commit changes live. The server records the commit it runs (`~/cornerstone/engine-commit`), and
    a merge that touches nothing the engine runs leaves it alone.
  - Before the engine restarts, live itself is asked whether it has every migration in that commit.
- **Our functions answer only their owner** (`goals/p0-the-database-answers-only-its-own.yaml`).
  - On a copy built from the migrations, `anon` and `authenticated` could execute all 12 functions we own. Seven of
    them are SECURITY DEFINER, including `confirm_results`, `correct_signed_off` and `pii.read_child`.
  - Migration `20261019090000` revokes EXECUTE from `public`, `anon` and `authenticated` on every function we own in
    `public`, `pii` and `internal`. It also changes the default privileges, so later functions start closed.
- **Checks:**
  - `pytest tests/test_db_privileges.py` failed 2 of 3 before the migration and passed 3 after.
  - `pytest tests/test_deploy.py` passed 4 on these files; on main's files it failed 3.
  - The 10 engine test files that call those functions, plus the two new ones, passed 153 on the local copy.
  - `bin/check` passed.
- **Not proven here:**
  - The live database's privileges, which need one query on live (the goal's manual step).
  - The first `workflow_run` deploy itself, which this merge exercises.
- **Known gap, Phase 1:** Vercel still publishes the website on the merge itself. Website code that reads a new table
  can therefore reach live up to one CI run (about 15 minutes) before `migrate live` adds the table. Before this
  change, the two started together.

## Phase 0, PR 2: every page checks who asks; one answer counts once; one roll order (2026-10-01)

Steps P0.2 and P0.5 of the plan Nimish approved ("go ahead with phase 0").

- **Every page checks who asks** (`goals/p0-every-page-checks-who-asks.yaml`).
  - Nine pages relied on the `(app)` layout's check. Next 16's auth guide says a layout neither re-renders on
    navigation nor stops the page rendering into its payload. Each page now calls `requireStaff` itself.
  - `proxy.ts` turns away a request with no good session cookie before anything renders: pages go to sign-in, API
    routes answer 401. The cookie is read by `lib/session-cookie.ts`, which touches no database.
  - `currentStaff` runs once per request (React `cache`) and no longer carries the password hash.
  - Honest scope: a forged request against main answered 500, not data. The leak was never shown; this closes the
    documented risk.
- **One answer counts once** (`goals/p0-one-answer-counts-once.yaml`).
  - A right answer writes an evidence row per skill its question tests. A real three-skill question counted as 3
    answers in the parent report.
  - The new view `answer_placed` has one row per signed-off answer, from its latest batch.
  - What now reads it:
    - the report card's per-skill-set counts;
    - the parent report: answers, wrong, blank, "improving", and the "can do" and "nearly" scores, which were per-skill
      sums;
    - a child's answer count;
    - `engine live data`.
  - Per-skill counts (the class grid, the graph's states) stay per skill, as they should.
- **The split:** `parent_report.py` reached 401 lines against the 400 ceiling. What a report may say (`facts` and its
  counting) moved to `w4_close/parent_facts.py`, which `workflows.json` places on the same step. Drafting, review and
  approval stay in `parent_report.py` (230 lines), and `parent_report.facts` still answers.
- **One roll order** (same goal).
  - `roll_order(text)`: by the roll's first number, a roll with none last.
  - It replaces 12 copies. Three web copies sent `'\D'` as `'D'`, so "12A" broke `::int`, and `card.py` sorted "10"
    before "2". The JS sort in `capture/views.tsx` matches it.
- **Checks:**
  - `test_web_gate.py`: 2 of 4 failed before (9 pages, no proxy); 4 passed after.
  - The gate suite passed 10, including a payload request and an API request without a session. The payload test
    fails on main's code.
  - `test_parent_report.py`: the new test failed (3 answers for 1) before and passes after; the file passed 25.
  - `test_roll_order.py`: 2 passed; the static half failed on main with 15 lines.
  - u6: the card's numbers are now checked against the answers themselves, with a two-skill answer in the fixture.
    The old row count shows "17 right" against 16, and the test fails.
  - The 23 engine test files that touch these modules passed 315.
  - The full browser suite passed 123. As before, 1 failed (s7, which needs live's G2 class), 6 were skipped and 2
    did not run.
  - `tsc`, eslint and `bin/check` passed.

## Phase 0, PR 3: the maker makes what it shows (2026-10-01)

Step P0.6 of the plan Nimish approved ("go ahead with phase 0"): the code review's correctness pass over PRs #141–#143
found 15 defects in the maker, the colours and the curriculum. PR 2 fixed one (the roll order); this PR fixes the other
14 (`goals/p0-the-maker-makes-what-it-shows.yaml`), plus the `engine audit` crash found while proving them.

- **The engine (`w2_print`):**
  - **Two alike lines repeated questions.** What a paper may not use held other children's papers, never its own
    lines. Now its own lines' questions are excluded too. With six questions left, main printed one of them twice.
    A second line the bank cannot fill is now refused, saying "no line above on this paper holds".
  - **N+1 catalogue reads.** Planning read the catalogue, levels, rule and names again for every child. They are now
    read once per batch (`shelf.one_batch()`).
  - **One browser per batch.** Making a class launched Chromium once per paper; a batch now shares one
    (`render._browser`).
  - **The split.** `focus_paper.py` reached 413 lines against the 400 ceiling. What a paper is drawn against (the
    catalogue, the levels, the rule, a home paper's length, the per-batch cache) moved to `w2_print/shelf.py`, on
    the same step in `workflows.json`; `focus_paper.py` is now 319 lines.
  - **A paper says how it was chosen.** Every maker paper's page said "chosen from this child's own checked papers",
    including class practice an educator chose. `print_paper` now keeps `how` (the engine's words) and `areas` on the
    paper. The paper's page reads them; a paper from before says only "drawn for this child".
  - **A changed child's paper length.** It was 12, the website's own `OWN_N`. It is now the `assemble.items_per_sheet`
    row; the route takes a change with no length.
- **The website:**
  - **A slow engine.** It took down the maker (planning) or said "nothing was changed" of papers it went on to make
    (making). Planning now says so on the maker. A make that gets no answer comes back with the same `once`, so the
    form sent again makes the papers once. The test holds a lock the engine waits on and sends the form twice; the
    copy then holds 2 papers, not 4.
  - **A refused batch** came back with the whole class ticked (`batchQuery` lacked `of`), and a change for a child no
    longer ticked made the engine refuse the plan (`forChildren`).
  - **Make made the papers shown** even after the choice changed. Any change to the choice now stops the button until
    the papers are seen again, and the button names the kind it makes.
  - **Checks.**
    - The class page gave a skill no child has answered no check. It now gets one for the whole class.
    - A rung that tests two skills gave its skill two checks, on the class page and the child's. There is now one per
      skill, and the child's two lines say which skill each is.
  - **Words and counts.**
    - Amber is said in the rule's own number of papers.
    - `checkLevel` takes the level order from `DIFFICULTIES`.
    - The waiting-skill count is per skill, not per row.
    - The maker's first line starts at the home paper's length row.
- **The audit crash.** `engine audit` stopped with `StopIteration` on a generated sum with no "ans" response; such a
  sum is now named. These came from u6, u7, u9 and u10, which planted their test questions as generated items. They
  now plant them as `legacy`, and the copy's 20 were converted.
- **Checks:**
  - **Engine.** The six new engine tests and the route test each fail on main's code: a repeated question,
    catalogue read twice, `[]` for `[10]`, `KeyError: 'how'`, `StopIteration`, 3 Chromium launches, and 422 for a
    change with no length. All seven pass here. The full engine suite passed 1,315.
  - **Browser, on main's code with the copy** (labels adapted to main's button):
    - 9 of the new or changed tests fail. Make stays enabled after a change. Chetan comes back ticked. The slow
      engine shows no words. The paper's page says "own checked papers". There is no single check for
      WORD.1_2STEP, and the class checks were keyed per column. Amber says "on one paper". The count says 25
      waiting where 24 are distinct.
    - The s11 wording change also fails there, as expected.
  - **Browser, here.**
    - Every test of m4, u11, u12, s11, u2, u5, u6, u7, u9 and u10 passed.
    - The full suite passed 141. 2 failed:
      - s7, as before: it needs live's G2 class;
      - e2e's "every child's paper has its own code". The copy holds no G3 class (0 children, 0 prescriptions),
        so the week page has no row. It fails the same way on main's code with this copy, and that page's code is
        not touched here.
    - 7 were skipped and 7 did not run (the rest of e2e's G3 tests, s4 without its readings, s7's).
  - `tsc` and eslint (`app lib components tests proxy.ts`, 0 warnings) passed. `bin/check` passed.
  - `engine promises`: every promise has its command.

## Phase 1, PR A: the gates hold (2026-10-01)

Nimish: "go ahead with phase 1". The first of Phase 1's five PRs (`goals/p1-the-gates-hold.yaml`).

- **Web lint in CI.** The web job runs `npx eslint --max-warnings 0`, which ran nowhere before. The browser tests'
  build output (`.next-test`, `test-results`, `playwright-report`) is ignored.
- **A coverage floor.**
  - The engine job runs `pytest --cov=engine`, and `[tool.coverage.report] fail_under = 79` fails a run under it.
  - Measured here today: 79.57% of 10,239 statements, 1,325 tests.
  - Coverage uses Python 3.12's `sys.monitoring` (`core = "sysmon"`): the suite took 681 s, against about 590 s
    without coverage. The default tracer was too slow to finish.
- **The ceiling covers the website.** `workflows.json` `ceilings.covers` names `engine/` and `apps/web/`. The
  website's only file over 400 lines, `tests/e2e.spec.ts`, is frozen at its 466.
- **Complexity has a baseline.** ruff measured 30 functions past C901 10 or PLR0915 50; each is frozen in
  `workflows.json` `complexity.frozen` at today's measure, and `test_layout.py` holds every function to the
  limits or its frozen measure. The worst: `ocr.answers_for` (28 branches, 78 statements), `render.render_item`
  (28, 90) and `parent_check.check` (26, 51).
- **The ratchet.** `engine ratchet --base <commit>` (`engine/checks/ratchet.py`) fails when a limit rises, a
  frozen number grows, anything new is frozen, a measured root is dropped, or the coverage floor falls. CI runs
  it against the pull request's base, or main's previous commit. `bin/check` runs its tests against HEAD.
- **The `-qq` problem.** The pyproject's `addopts = "-q"` is gone. With a criterion's own `-q` it made `-qq`,
  which prints no "passed", so 11 goal criteria could never pass.
- **Checks:**
  - Each gate fails on a planted violation:
    - a lint warning: eslint exits 1;
    - a 401-line web file: "apps/web/lib/long.ts has 401 lines";
    - one more branch in a frozen function: "learned_rules.py::answer measures C901 15, past 14";
    - a frozen size raised in the map: the ratchet exits 1;
    - main's pyproject: the criterion test fails;
    - main's ci.yml: 3 of the CI tests fail.
  - `test_gates.py`, `test_ratchet.py` and `test_layout.py`: 17 passed. `bin/check` passed.
  - The full engine suite under coverage: 1,325 passed.

## Phase 1, PR B: every browser test in CI, on a fresh database, none skipped (2026-10-01)

The second of Phase 1's five PRs (`goals/p1-browser-tests-in-ci.yaml`).

- **A browser job in CI.**
  - It installs the engine and the website, builds a database from the repository alone (`bin/testdb fresh`), and
    runs every spec against a production build and the engine, as `playwright.config.ts` starts them.
  - A last step reads Playwright's JSON report and fails on any skipped, unexpected or flaky test.
  - `test_gates.py` holds the job to this, and to no spec calling `test.skip`, `fixme` or `only`.
- **Every spec builds its own rows** (`apps/web/tests/rows.ts`: `aClass`, `aWorksheet` through `engine legacy
  paper`, `aReadPaper`):
  - **s4, the answer queue:** a class of two, read on one worksheet. Asha's first paper holds every kind the queue
    holds: a guess, two unclear readings, a judgement, a held wrong, a held blank, an explanation held blank, a
    right answer, and one the reader gave up on. Her second paper has nothing waiting; Bina's has two answers
    waiting. Nine tests skipped themselves without live's readings; their queries now read the spec's own papers.
  - **s7, the week:** its own class of four, not live's "G2". The week is prescribed, assembled and rendered through
    the engine's routes. e2e's seven week tests moved here from live's "G3" week T2W1. `e2e.spec.ts` is 314 lines
    and off the frozen list.
  - **screens:** a child of its own with four signed-off answers and a read paper, not the first class live listed.
  - **m2:** Chetan is given all but three of a level's questions, so "the bank cannot fill it" holds whatever the
    bank's size.
  - **u9:** its setup sent `item_ids` as null into a not-null column. It passed only because the copy already held
    those papers; on a fresh database it failed. It now sends an empty list.
- **The concurrency test keeps one class.** It made a class each run, then deactivated it: a child cannot be
  deleted, because `evidence_event`'s append-only trigger refuses even an empty cascade. That left 24 children in
  the copy. It now uses one class, `CONCURSEC-TEST`, made once and kept.
- **The coverage floor rises to today's number:** 79.5% at one decimal (CI measured 79.51% on PR A).
- **CI's first run caught an order-dependent test** (149 passed; s4's spot-check found none, and the 7 after it did not
  run):
  - Settling an answer on a paper's own page signs the whole paper off (`resolve_result`, by design since
    2026-09-24). s4's "Right" on Asha's first paper did so, and left that paper no spot-check. Her second had one only
    when the smallest md5 of three random ids fell on an answer no one had checked: one run in three it did not.
  - The spot-check now reads Chitra's paper, which no other test settles.
  - A seeded paper holds only what the engine can write: a settled wrong or blank carries a person's reading, and
    `aReadPaper` refuses one without. The engine's invariant test caught three such answers on a database the browser
    suite had used.
  - A paper read again is superseded, as the reader supersedes a scan, not deleted: a signed-off answer's evidence is
    append-only, so the second local run failed to delete it.
- **Checks:**
  - **On a database built fresh here:** 155 passed, 0 skipped. The one failure was u9 (above), which then passed.
  - **The full suite on another fresh database, in CI's order:** 157 passed. A statement log showed the one
    `resolve_result` that signed Asha's paper off. After the fix, s4 and screens passed twice in a row on that
    database (40 and 40), and the engine's invariant test passed on it.
  - **On main's code:** s4 skipped 9, screens 2 and m2 1, and e2e's G3 tests and s7 failed without live's classes.
  - `test_gates.py`: 6 passed. The concurrency test passed twice and leaves one class.
  - `tsc`, eslint and `bin/check` passed.

## Phase 1, PR C: the types hold (2026-10-01)

The third of Phase 1's five PRs (`goals/p1-types-hold.yaml`).

- **A type checker reads every engine file.**
  - pyright 1.1.414 is pinned in the dev extras with its own Node (`pyright[nodejs]`). It reads `engine/` at its
    basic level, and `assess/` and `core/` strictly (`[tool.pyright]`).
  - `tests/test_types.py` runs it (about 15 s) and holds its verdict; `bin/check` runs it before every commit.
  - On main's code it found 5,277 errors: 4,825 missing annotations in `assess/`, and 260 findings of other kinds
    across the engine (216 of all kinds in `core/`).
- **Nothing it calls wrong stands.** Every finding is fixed where it is. Among them:
  - **The one connection was typed as giving tuples.** `psycopg.connect` ignores its row factory in its types.
    `db.Conn` names the dict rows, so every `row["id"]` downstream is checked against a dict.
  - **A query that must return a row says which one when it does not.** `db.one()` replaces `fetchone()["x"]`
    where that would have failed as "None is not subscriptable".
  - **Two latent crashes:**
    - `engine eval` on a reviewer with no hand-judged case raised a KeyError; it now says there is nothing to score.
    - `draw` raised a KeyError when a case allowed neither ADD nor SUB; that attempt is now refused like any other.
  - **OpenCV calls take the shapes their types declare.** Each was proved to give the same result: the red-ink
    mask, the line-up's features, the borders.
  - **Shared helpers are public.** Eleven helpers named private were used across modules; they are now public.
    Dead code is gone: an unused class, unused variables, and a pick helper nothing called.
- **The base is strict and clean:** `core/` went from 216 errors to 0.
- **The maths library's missing annotations are frozen.** 4,816 across 26 files sit in `workflows.json`
  `types.frozen`, exactly; a file that sheds some writes its new number down.
- **The ratchet holds the type check.** Its level, the roots it reads, the roots it reads strictly, what counts as a
  missing annotation, and every frozen count may only tighten.
- **A shrunk frozen number is written down.** The line ceiling and the complexity list now require a frozen file or
  function to sit exactly at its number:
  - `mark.py` 417 → 414 lines, and `loaders.py` 413 → 411;
  - `cli.eval_` C901 20 → 18 and 85 → 74 statements, its reviewer scoring split out;
  - `mark.roundtrip` 52 → 51 statements.
- **The website calls the engine only by its routes.**
  - `bin/engine contract` writes `apps/web/lib/engine-routes.ts` from the engine's OpenAPI document: 53 routes,
    each POST's body as TypeScript.
  - `lib/engine.ts` takes only those paths (each `{name}` any text, a query string allowed) and only those bodies.
  - `tests/test_contract.py` fails when the list is stale, and `tests/engine-contract.ts` holds six calls that must
    not compile.
  - It found four bodies the engine does not declare: a mistake's shortlist and a week's proposal parsed as
    anything, a bank verdict as any string, and a crop's query as any text. Each is now checked where the form
    arrives.
- **Checks:**
  - `test_types.py`, `test_contract.py`, `test_ratchet.py` and `test_layout.py` pass, and so does `bin/check`
    (25 tests).
  - The full engine suite under coverage on a fresh database: 1,332 passed, coverage 79.72%. Its two failures were
    fixed at their cause:
    - the effort test read the call's arguments, so it is now read off the HTTP request itself;
    - the invariant test caught the browser seeds' engine-only wrongs (PR B's fix).
  - `tsc` and `eslint --max-warnings 0` pass on the website.

## Phase 1, PR D: each service its own role (2026-10-01)

The fourth of Phase 1's five PRs (`goals/p1-the-roles-hold.yaml`).

- **Two login roles, `app_web` and `app_engine`**, made by a migration (`20261021090000_each_service_its_own_role`),
  with no password.
  - **The engine is the system's writer.** It may read and write every table in `public` and run every function of
    ours, but it cannot change, remove or empty a ledger row, and it has nothing on `pii.child`.
  - **The website reads every table in `public`** and writes the five a person changes on it: `read_correction`
    (insert), `item_result`, `prescription`, `skill_set` and `config` (update). It calls four of our functions:
    `confirm_results`, `resolve_result`, `roll_order` and `pii.read_child`.
  - **Row security** stays forced on every table, and a policy for the two roles is made with each table
    (`internal.apply_conventions`).
  - **A ledger is held the moment it has its trigger.** That is any table `internal.forbid_change` guards: eight
    today. The same function revokes its update, delete and truncate at the end of every migration.
- **Names only through the logged accessors.** `roster.find` and the gold set read `pii.child` themselves until now;
  `pii.find_child` (new) and `pii.read_child` each write the read to `access_log`.
- **Proved from the database itself.** `tests/test_roles.py` reads each role's privileges with
  `has_table_privilege` and its kin, and a planted wider grant fails it. Four were planted: update on
  `evidence_event`, select on `pii.child`, insert on `item`, and a function the website does not call.
- **Proved wide enough.** CI's browser job gives both roles a password for the run and starts the website and the
  engine as them; the specs still write their own rows as the owner.
  - Run that way here, the suite passed 154 of 157 and found one grant too narrow. Editing a skill set (s2) fires the
    trigger that writes its history, and it ran as the website's role.
  - The trigger now writes as its owner (`security definer`), since history rows are the system's to write. s2 then
    passed 6 of 6 as the roles.
- **Checks:** `test_roles.py` 5 passed, with each of the four planted grants failing one test. The tests the change
  touches (the lookup route, the week, the gold set, the report, the gates, the layout, the promises) pass, 54 in
  all. `bin/check`, `tsc` and eslint pass. ADR 0046 records the rejected alternatives.
- **Live switches by Nimish's hand** — until then both services keep the owner's connection and nothing changes:
  1. In Supabase's SQL editor, as the owner: `alter role app_web password '<new>'` and
     `alter role app_engine password '<new>'` (two long random passwords, kept in the password manager).
  2. Vercel, Production and Preview: `DATABASE_URL` → the transaction pooler (6543) as `app_web.<project-ref>`.
     Redeploy.
  3. The engine server's environment: `DATABASE_URL` → `app_engine.<project-ref>`. Restart the engine.
  4. Migrations, `bin/engine week roster` (it writes names) and `bin/update-live` keep the owner's URL.
  5. Check: sign in and open a child's page, and read one paper from Capture.
  - I am not certain the pooler takes custom roles as `<role>.<project-ref>`; Supabase's pooler docs say how.

## Phase 1, PR E: done means every check (2026-10-01)

The last of Phase 1's five PRs (`goals/p1-done-means-every-check.yaml`).

- **`engine done` runs the whole goal.** Each of Nimish's sentences with its test, then the goal's own scenarios and
  criteria, every one run now. It says DONE only when all of them pass and all of it is live. Before, a goal's
  sentences could be proved while its own criteria were red. The scenario loop now lives once in
  `goal.run_scenarios`, which `engine goal` and `engine done` both use.
- **Every eval is held to a bar, and the bar is a row.**
  - `eval.<purpose>.<measure>` threshold rows hold 17 bars for 8 of the 9 purposes `engine eval` scores. A measure
    ending `_at_most` is a ceiling, such as a count of wrong answers.
  - Each bar is either the bar Nimish set (`parent_report`, every draft held to its facts; `parent_review`, every
    wrong sentence caught and none flagged wrongly) or the score the prompt was made active on, with the source named
    in the row: DECISIONS-LOG and STATE.md, for `story_shape`, `mistake_guess`, `week_skills`, the two reviewers and
    `misconception_list`.
  - `engine eval <purpose>` prints each bar it misses and exits 1. An eval with no bar on record does not pass.
  - `item_generate` has none: no score has been recorded since it was made active. Its bar is Nimish's step:
    Actions → engine eval → item_generate.
  - Seven of the nine evals printed a score that nothing held to a bar until now.
- **`engine eval`'s dispatcher shrank.** Its C901 measure went from 18 to 15 and its statements from 74 to 60, with
  `item_generate`'s scoring split out. Its "no eval for" message now names every eval, from one `EVALS` list that the
  test reads too.
- **CLAUDE.md's verify command `engine eval read_cells` named an eval that does not exist.** The `read_cells` prompt
  is designed in SPEC.md, but no engine code uses it. The line now says `engine eval <purpose>`.
- **Checks:**
  - `test_bars.py` 3 passed: a score below its bar fails through the command (story_shape at 60 of 65, a reviewer at
    0.83 against 1); at its bar it passes; with no bar, `item_generate` fails.
  - `test_promises.py`'s new test passes: one scenario short or one criterion red makes it NOT DONE.
  - `test_goal.py` and `test_cli.py` passed 29, and pyright on the changed files found nothing.

## Phase 1, loose ends: nothing active is idle; each check shows its proof (2026-10-01)

Found while closing Phase 1 (`goals/p1-no-loose-ends.yaml`).

- **Two prompts were active with nothing asking for them.** `read_cells` and `word_context` had been active since the
  first seed. No engine code has ever named either (`git log -S` finds no commit that does), and neither has an eval.
  Rule 7 makes a prompt active only once its eval is scored, so both are now inactive.
  - `read_cells` waits for step R1 in BUILD-ORDER.md, one answer box read whole. That step makes it active once
    `engine eval read_cells` scores it.
  - `word_context` is designed in SPEC.md; no step in BUILD-ORDER.md names it.
  - `tests/test_settings.py` reads every active purpose from the seed and every string the engine's code holds whole.
    It fails on an active prompt that no code asks for, and it failed on these two before the seed changed.
  - Live takes the change on the next deploy: `engine load --settings` sets `active` from the seed.
- **`engine done` quotes the line that passed a criterion.** It quoted whatever the command printed last, so the
  browser suite's line read `[WebServer] }`. It now quotes the last line carrying the criterion's expected text (a
  tally such as `57 passed (3.1m)`), or the last line when none does (`done.evidence`).
- **Checks:**
  - `pytest -q tests/test_settings.py tests/test_promises.py tests/test_loaders.py tests/test_llm.py tests/test_bars.py
    tests/test_audit.py` → 50 passed. Both new tests failed first: `['read_cells', 'word_context'] == []`, and the
    criterion line without its tally.
  - `engine audit` on the local copy found the same 27 violations with and without the change. All are local data (26
    specs not ratified, one mistake-charge table not approved); none is about prompts.

## Phase 2, PR 1: live is watched (2026-10-01)

`goals/p2-live-is-watched.yaml`. Nimish: "go ahead with phase 2", built to ponytail's rules (the laziest thing that
works; https://github.com/dietrichgebert/ponytail).

- **`engine live watch`** (`checks/watch.py`) prints what is wrong on live, one line each:
  - runs still running after `watch.stuck_minutes` (30);
  - runs that failed, and website errors, in the last `watch.window_minutes` (30);
  - the server's disk below `watch.disk_free_gb` (2).
  It prints counts, flow names and page patterns only: never a run's error text, an id or an address.
- **The website records each error a page raises** (`apps/web/instrumentation.ts` → `web_error`, by the page's
  pattern). There is no message, because a message can carry a child's name; Vercel's log keeps it, found by its digest.
  `app_web` may insert into `web_error`, and nowhere else new.
- **`.github/workflows/watch-live.yml` runs every 10 minutes.** It asks the engine over SSH, checks the engine's
  `/health` and the website's `/login`, and asks again a minute later before it says anything. Then it opens an issue
  mentioning @nimishshah1989, keeps its body current, and closes it when all is well. The repository is public, so the
  engine's address is masked in this workflow's logs, and now in the deploy's too.
- **Checks:**
  - `pytest -q tests/test_watch.py tests/test_roles.py tests/test_deploy.py` → 15 passed.
  - `npx playwright test tests/p2-website-errors.spec.ts`, run as `app_web` → 1 passed.
  - ruff, pyright, eslint and tsc are clean on the changed files.

## Phase 2, PR 2: live recovers (2026-10-01)

`goals/p2-live-recovers.yaml`.

- **A restart marks every run it killed, whatever the flow** (`api/routes/runs.py::orphaned`, called as the engine
  starts). Until now only a scan reading was marked; a parent report being written said "running" forever. Moved from
  `w3_read/inbox.py`, which no longer has it.
- **A bad deploy is undone by naming a commit.** Actions → deploy engine → Run workflow → a full commit id. The next
  merge deploys main again. Migrations only go forward.
- **Two rebuilds of one child at once both finish.** Reproduced first: the second raised `UniqueViolation` on the
  first's rows. `rebuild_child_skill_state` now takes a lock per child, held to the end of its transaction
  (migration 20261023090000).
- **Every route commits before it answers.** Main's CI went red on #156's merge, on a browser test #156 never
  touched ("removing a question retires it"), which had passed on the same tree an hour before. Root cause:
  FastAPI 0.141 closes a request-scoped dependency after the answer is sent (`routing.py`: `await response(...)`
  inside the request's exit stack), so `get_conn` committed after the website had its answer. The website then read
  the question back before the commit, and still saw it live. Every route now takes `Depends(get_conn,
  scope="function")`, which commits as the route returns. `tests/api/test_deps.py` fails on a request-scoped one.
- **A password is not guessed by trying.** After `sign_in.max_failures` (10) wrong passwords for one email inside
  `sign_in.window_minutes` (15), the sign-in page refuses that email until the window passes (`sign_in_failure`,
  migration 20261023100000). `app_web` may insert there.
- **Checks:**
  - `pytest -q tests/api/test_runs_routes.py tests/test_deploy.py tests/test_graph.py tests/test_roles.py
    tests/test_inbox.py tests/test_watch.py` → 33 passed.
  - `npx playwright test tests/gate.spec.ts tests/p2-website-errors.spec.ts`, run as `app_web` → 12 passed.

## Phase 2, PR 2 (continued): less code says the same (2026-10-01)

`goals/p2-less-code.yaml`.

- **`assess/mark.py` went from 414 lines to 90** and off the frozen list. The prototype's synthetic round trip (fake
  answers, a fake photo, a printed-digit reader, `roundtrip`) had no caller since real scans arrived. `deskew` and
  `read_qr` stay; `w3_read/sorting.py` uses them. Its frozen missing-annotation count fell from 320 to 50.
- **One settings reader.** `settings.config` and `settings.threshold` in `core/settings.py` replace three private
  copies in `assemble.py`, `prescribe.py` and `scenarios_week.py`, which `shelf.py` reached into.
  `tests/test_settings.py` fails on a new copy.
- **No state is told by colour alone.** Each swatch carries a mark (! needs help, ~ practising, ✓ got it); grey stays
  blank.
- **Traced and left as they are, because they are not copies:**
  - "Which level next" is two rules agreed with the school, each with one owner. `next_difficulty()` steps the week's
    practice paper from its last level; `assess/focus.py` picks the home paper's level from the share right.
  - `judgeOne` and `resolve_result` record a judgement the same way. The code review's "level-next in 4 places"
    counted callers.
- **Checks:**
  - `pytest -q tests/test_settings.py tests/test_layout.py tests/test_types.py tests/test_ratchet.py` → passed.
  - ruff, pyright, eslint and tsc are clean on the changed files.
- **ARCHITECTURE.md §5 no longer lists the engine's routes by hand.** Eight of its thirteen were never served
  (`/declare` is `/week/declaration`, `/read` is `/read/file`, and so on). It now points at the list `bin/engine
  contract` writes from the engine's OpenAPI, which `tests/test_contract.py` and the website's type check already
  hold.
- **Skipped, with when to add each** (ponytail):
  - a job queue: a restart marks its dead runs; add one if restarts mid-run become common;
  - the server's `.env` kept in a GitHub secret: Nimish's Mac keeps it, and `go-live.sh` rebuilds a server from it;
  - a restore-drill script: first confirm that Supabase keeps backups;
  - an automated accessibility checker: add one if a second colour-only state ships;
  - STATE.md compacted: BUILD-ORDER reads each workflow's gates here, so archiving them risks that process; archive
    by month when a session's reading cost bites.

## Grade 1 as its educator taught it to September (2026-10-06)

`goals/g1-taught-till-september.yaml`. Nimish forwarded the Grade 1 educator's list: *"Can we incorporate this part
additionally for grade 1? Ensure that this is the entire thing that's mapped to what has been taught in grade 1."*

- **What Grade 1 now holds** (a Grade 1 child's paper, worksheet and week note draw from these and nothing else):
  - 1-digit + 1-digit and 1-digit − 1-digit, every level, as before;
  - the Easy level of 2-digit + 1-digit, 2-digit + 2-digit, 2-digit − 1-digit and 2-digit − 2-digit. That level is
    exactly "no carry, no exchange" (46 + 12, 25 − 13, 28 − 8). It moves to Grade 1 through `skill_set.level_band`:
    from the seed for a new database, and by migration `20261024090000` for live. Their other levels stay Grade 2;
  - **tally marks** (`DATA.TALLY`, rung R34, NUM.DATA.01): read a tally from 5 to 10 (Easy) or 11 to 20 (Medium);
    two tallies, altogether or how many more (Advance);
  - **equal groups** (`MUL.GROUPS`, rung R35, NUM.OPS.03): 2 to 3 groups (Easy) or 4 to 5 groups (Medium), each of 2
    to 6, as a sum (4 + 4 + 4) or as rings of dots; and a story (Advance).
- **Multiplication is two topics.** "Multiplication" holds equal groups and is taught. "Multiplication in columns"
  holds `MUL.1D` and is still not taught: Nimish, 2026-09-23, "we haven't even started teaching multiplication". Tally
  marks are under "Data handling", taught.
- **Two new kinds of question:**
  - `assess/counting.py` makes them: each key is computed, and each predicted wrong answer names a mistake. The new
    mistakes are M_TALLY_FIVE_AS_FOUR, M_TALLY_CROSS_COUNTED, M_TALLY_BUNDLE_AS_ONE, M_GROUP_MISSED and M_ONE_GROUP;
    M_WRONG_OP is reused;
  - `assess/pictures.py` draws every kind that is a picture. The balance and the number line moved there unchanged,
    so `render_item` fell from C901 28 to 27;
  - `components/pictures.tsx` draws the same on the website.
- **A level's grade is read the same way everywhere now.** Two places had still used the rung's grade:
  - library worksheets printed a Grade 1 level as "Grade 2", with Grade 2's smaller boxes. A worksheet printed for
    another grade than its level's is now retired and dealt again;
  - a Grade 1 class's week note could not name the 2-digit skills.
- **45 + 8 is not Grade 1.** 5 + 8 = 13 is an exchange, against her "without borrowing". It belongs to 2-digit
  + 1-digit Medium, which stays Grade 2 until she confirms (BUILD-ORDER, inserted 2026-10-06).
- **Types and ceilings, all down:**
  - typing `items.item`, `items.cells`, `answer_space.op_sign`, `words.templates` and `verify.to_item` took 141
    findings off eleven frozen files;
  - `items.missing_part_20`, which no engine code called, is deleted, so `items.py` went from 579 lines to 571.
- **Checks** (on a database built by `bin/testdb fresh` with these rows: 21,289 questions, 1,845 worksheets; every
  Grade 1 level printed as G1):
  - `pytest -q tests/test_counting.py tests/test_focus_paper.py tests/test_topics.py tests/test_library.py
    tests/test_week_note.py tests/test_new_kinds.py tests/test_items.py tests/test_render.py tests/test_loaders.py`
    → 236 passed;
  - `bin/engine audit`: every structural invariant passes. The two failures are the approvals a fresh database never
    has ("every spec is ratified", "what a mistake charges is approved");
  - `bin/check` → 27 passed, and lint is clean. `npx tsc --noEmit` and `npx eslint` are clean on the changed web files.
  - `npx playwright test tests/s28-grade-1-as-taught.spec.ts tests/s8-taxonomy.spec.ts tests/u12-curriculum-table.spec.ts`
    (production build, roles) → 8 passed. The new spec's first run failed on the check itself: a vertical tally line has
    no width, so Playwright called it hidden. The check now reads each drawing's own label;
  - CI's run of every browser spec then failed on one these three do not cover: `e2e.spec.ts` "every kind of question
    in the bank is drawn with its own numbers" looked for a digit in a question's words, and a tally's numbers are its
    drawing. It now reads each drawing's label with the words, so a missing number still reads undefined or NaN; and a
    one-tally question with no count draws "a tally of NaN", never a tally of 0. `npx playwright test` on a fresh
    database: before the fix, "Error: tally" as in CI; after it, all 13 tests of `e2e.spec.ts` pass (the five CI never
    reached among them), with s28 and s8. Here, the five tests that make a paper failed and the 19 after them in their
    files did not run: the engine's Playwright wants a Chromium build the cloud container lacks (`/week/render` →
    "Executable doesn't exist"). CI installs it and passed all 24 on 2f28b10;
  - `engine ratchet --base origin/main` → every baseline held or tightened.

## Multiplication and division — measured before the build (2026-10-09)

Nimish asked for multiplication and division the way addition and subtraction were done, through the whole loop
(BUILD-ORDER "Inserted now: multiplication and division"). Nothing was built; this is what the plan stands on. Measured
on a database built by `bin/testdb fresh` from the repository (21,289 active questions), not on live.

- **Division exists nowhere.** `cd packages/engine && .venv/bin/python -c "from engine.assess import misconceptions as
  M; M.predict('÷', 85, 4)"` → `KeyError '÷'`.
- **`MUL.1D` does not hold to its own levels' words.** Easy says "no carry into the tens" and Medium "product past 100":
  `select difficulty, count(*), count(*) filter (where ((spec->>'a')::int % 10) * (spec->>'b')::int >= 10),
  count(*) filter (where (spec->>'a')::int * (spec->>'b')::int < 100) from item where skill_set_code='MUL.1D' and
  status='active' group by 1 order by 1` →
  ```
  Advance|216|216|0
  Easy|216|137|216
  Hard|216|165|0
  Medium|216|179|6
  ```
  137 of 216 Easy questions carry from the ones; 6 Medium questions are under 100. It spans three digit shapes, against
  ADR 0034, and carries no taxonomy tags (`tags.derive` measures two numbers only for + and −).
- **A 2-digit × 2-digit question's real mistakes are not predicted.**
  `.venv/bin/python -c "from engine.assess import misconceptions as M; print(M.predict('×', 68, 17))"` →
  `{'M_MUL_ROW_OUT': 1088, 'M_WRONG_OP': 85}`: no placeholder zero (544), no column-by-column (656).
- **A library worksheet question with more than one answer is never read** (`w3_read/copies.py`: `if
  len(it["responses"]) > 1 … unread.append(n)`). `select count(*) filter (where jsonb_array_length(responses) > 1),
  count(*) from item where status='active'` → `4437|21289`: estimate-then-calculate, find-the-mistake, fact families
  and more, addition and subtraction included. A remainder needs exactly this, so M0 fixes it for every kind.
- **July's real multiplication answers sit on one rung.** `grep -c '"rung": "M1"'` over G3-BASE16, G3-QUIZ20 and
  G4-BASE16 → 5, 12, 6: table facts, 8 × ___ = 72, ×10 and ×100, 2-digit × 1-digit and 144 ÷ 12, all on `M1`.
- **The taxonomy draft checks itself.** `packages/engine/.venv/bin/python research/md_taxonomy.py --check` →
  `247 cases in 13 sections, 38 mistakes, 17 skills: every example recomputed, every case placed or listed unplaced,
  0 faults`. Two checks were broken on purpose (a "carry 1" case given carry 2, a two-digit puzzle given a wrong
  answer) and the run named both and failed.
- **A second reader reviewed the draft before it shipped** and found what `--check` does not test. Each finding was
  fixed in `research/md_taxonomy.py` and the doc:
  - labels that did not match their numbers: 612 ÷ 6 given as a zero from a 0 digit; a "fewer digits" 2 × 2 case
    that every other 2 × 2 case shared;
  - two items that were the same item;
  - wrong values that were typed rather than computed. Every mistake's wrong answer now comes from a predictor;
  - implausible mistakes, replaced by common ones: a remainder added to the next digit (72 ÷ 4 → 11 r 1); a first
    row's carry reused in the second (47 × 23 → 1281); "3 times as many" read as "3 more";
  - a blank remainder named as a mistake, against rule 5;
  - levels out of order within a skill;
  - grades later than the school's own objectives place them.
- **Not checked:** what the school teaches in each grade now, and which methods. Both are assumptions (ADR 0047, A1
  and A6) until Achal corrects the doc or an educator declares them.

## M0a — every answer of a question with several answers counts (2026-10-09)

Goal `goals/md0a-every-answer-counts.yaml`. Each claim with the command that proves it:

- **A library worksheet question with several answers is read, one slot per answer, and every answer is marked,
  queued and counted on its own.** `cd packages/engine && .venv/bin/python -m pytest -q tests/test_every_answer.py
  tests/test_each_answer.py` covers 4 estimate-then-calculate, 4 inverse-check and 4 find-the-mistake questions on one
  copy:
  - every answer gets its own row;
  - an estimate is right within its tolerance and wrong outside it;
  - an exact answer is marked against its own key, not the estimate's;
  - a tick or a sentence goes to a person with its crop and the reason, and the digit reader is never called;
  - signing off makes one evidence row per answer;
  - each card shows its own right answer and question number, and says which answer it is;
  - `engine audit` names a result whose answer is not one its question asks for.
- **Nothing else broke.** `cd packages/engine && .venv/bin/python -m pytest -q` → `1438 passed, 1 warning in 849.74s`.
  `bin/check` → `27 passed`. `cd apps/web && npx tsc --noEmit -p . && npx eslint . --max-warnings=0` → clean.
- **The questions this reaches.** `select count(*) filter (where jsonb_array_length(responses) > 1), count(*) from
  item where status='active'` → `4437|21289` on the local database, the bank as seeded. Before this, none of the 4,437
  was read on a library worksheet copy.
- **A second reader reviewed the diff and found what the tests did not.** Each finding is fixed and has a test in
  `tests/test_every_answer.py`:
  - the child's report gave a wrong exact answer its estimate's key as the right answer (`report._example`);
  - the second reader keyed a waiting reading by question, so one answer's guess was written into its sibling's row.
    On a library copy it raised `IndexError` instead, because a library question's key has no `/`
    (`second_reader._slot`). The reading eval and the replay raised the same error on any signed-off library copy; they
    now read old papers only (`reread.old_papers`), which is what they can read;
  - a wrong estimate or check was matched against rules for working the sum: learned mistakes, Jev's shortlist, rule
    discovery. A rule about `a op b` now explains only an answer whose key is `a op b` worked exactly
    (`learned_rules.works_the_sum`);
  - on a printed copy that did not line up, the region reader was handed second answers, ticks and reasons; it reads
    one number a question. The rest now go to a person with the reason (`reading._by_region`, `boxes.UNALIGNED`);
  - a tick or a sentence counted as "the reader gave up" and became a handwriting sample shown to the second reader.
    Both now leave out what the reader was never handed (`profiles.never_read`);
  - a library copy's card showed "Question" with no number. The reader now records each answer's number on its result
    (`raw_read.slot`); the website reads it, with a question's answers in print order (`result_slot`, `result_order`);
  - two tests could not fail. The typed-answer test now types the estimate's key into the exact answer; the audit test
    plants a result that names no answer and expects it named.
- **A third reader reviewed those fixes and found what they reached or missed.** Each is fixed and tested:
  - leaving a question out of the region reader moved the region of the question above it, which then read the next
    question's answer. Every question is now given to it by its first answer, and only the answers it cannot read are
    taken back for a person (`reading._by_region`);
  - a tick on a page that did not line up was counted as the reader failing. It is now a person's to read, as on a page
    that lined up;
  - the second reader, now reaching library copies, cropped page 1 at a page-2 answer: a library question's page is not
    in the bank's row. The page each answer's photograph is on is read from what the reader recorded, in the engine and
    in `answer_checked` (`page`, `file_page`, migration `20261025090000`);
  - the website's reader report still counted ticks and sentences. `answer_checked.never_read` is now the one test,
    read by both;
  - a person could still name a column mistake on an estimate by posting it directly (`naming.name_mistake` refuses);
  - the notebook's "checked" count still included answers the reader never read;
  - `engine read again` was narrowed to old papers, against its promise to read every live scan. That was undone: a
    library copy there is a failure it reports, as before; it is read again through `POST /read/file` with `again`;
  - an answer a person already worked on got no question number on a re-read. The re-read now adds it, leaving the
    reading as they left it (`copies.read`).
- **Not checked:**
  - a real child's handwriting in a second or third box (the tests stand in for both readers);
  - copies read on live before this. They keep their old reading until read again (`POST /read/file`, `again: true`),
    and their cards show no question number until then;
  - the website's screens with these answers, beyond the typecheck, lint and CI's Playwright run.

## M0b — division is an operation wherever one is named (2026-10-09)

Goal `goals/md0b-division-is-an-operation.yaml`.

**Measured before the build.** A read-only sweep of every place the engine names an operation found:
- ÷ in about sixty places, nearly all broken:
  - `compute`, `chain` and `predict` raised KeyError on it;
  - `skills.operations` and the old-paper pattern did not match it;
  - `misconception.op` refused it, and `skills.by_operation` had no Division although the registry has `NUM.OPS.04`;
  - the case dimension `operation` allowed ADD and SUB only;
  - the equation parser read + and − only;
- eleven kinds of question, handed × or ÷, made a subtraction, several printing "+":
  - `number_line_jumps`, `estimate_then_calc`, `find_mistake`, `missing_digit`, `inverse_check`;
  - `choose_estimate`, `possible_answer`, `odd_even`, `break_apart`;
  - `bare_sum` and `word_1step`.

  Only `MUL.1D` asks for × today, through the column sampler that makes it, so no seed level was producing a wrong
  question. Nothing stopped one.
- a story's answer formula read a × as a +;
- the bank's missing-number stem printed "+" for any operation that was not −.

**Now.** Each claim with the command that proves it:
- **What an operation computes has one owner, `engine/assess/operations.py`, and division is in it.** `cd
  packages/engine && .venv/bin/python -m pytest -q tests/test_division_is_an_operation.py` → `30 passed`. It covers:
  - 84 ÷ 4 = 21;
  - 85 ÷ 4 refused as one answer ("21 r 1: two answers") and given as `divide` → (21, 1);
  - ÷, / and : as one operation;
  - the verifier names a remainder in words and calls the shape `DIV.2D1D`;
  - `predict('÷', …)` gives no mistakes rather than a KeyError, and "−" predicts as "-";
  - Division is `NUM.OPS.04`, a case may be MUL or DIV, and a mistake row may name ÷;
  - G4-BASE16's own "144 ÷ 12 =" is now a sum: its paper row gains `"expr": "144 ÷ 12"`. It counts on Division, and a
    paper's own key ("21 r 1") is taken before anything is computed. "/" on an old paper is not ÷, since it may be a
    fraction;
  - an equation with × and ÷ is worked in the taught order and exactly;
  - each of ten kinds refuses × and ÷ in a sentence naming itself and the operation, and `bare_sum` refuses too and
    works "−" as a subtraction throughout;
  - the refusal is heard where the bank, the case drawer and a level's mistake list ask (it was caught as "these
    numbers did not fit" in the last two);
  - a rule's list of operations is not read as one;
  - a story formula with × is refused.
- **Nothing else broke.** `cd packages/engine && .venv/bin/python -m pytest -q` → `1465 passed, 3 failed`. The three
  were the map's gates (ceilings, complexity, types), which read `workflows.json` before its fallen figures were
  written. Rerun with the suites this touches → `323 passed`; `bin/check` → `27 passed`.
- **Older sign tables remain**, not yet read through the owner:
  - `draw.py`, which prints − or +;
  - `tags.py`;
  - `marking._MINUS`;
  - `equality.MINUS`;
  - `mistake_guess.SIGN`, the sums Jev is asked about;
  - `legacy._EXPR`, whose printed signs a test holds to `operations.PRINTED_SIGNS`.

  Each handles + and − only, as their callers do. They move to the owner when M1 and M3 give × and ÷ tags, cases and
  kinds.
- **No file grew past its ceiling and none was raised.**
  - The arithmetic moved out of `misconceptions.py` (500 → 489).
  - `sort_into_table` left `items.py` (571 → 540), with its render, tag and layout rows. No seed level ever named that
    kind, so the bank never made one, and it retires any item whose kind its level does not name.
  - `legacy.py` stays at 652.
  - Eleven files' untyped-code counts fell and were written down; `equation.py` is now fully typed (71 → 0).
- **Migration `20261026090000`** lets a mistake row name ÷. A mistake a model proposes now keeps its example's
  operation (× or ÷), where × used to fall to `any`.
- **Found, and belonging to a later slice:**
  - a two-step story that halves ("add up to", `divide: 2`) does not count on Division (`skills.operations` reads its
    template's `op`, not its `divide`). That changes the skills of stories already on live, so it goes with the
    stories, in M4;
  - the website's mistake names by operation go to M0c.
- **Not done here:** ÷'s own mistakes, kinds and tags (M3 and M1).

## M0c — a skill set is read as itself (2026-10-09)

Goal `goals/md0c-a-skill-set-is-read-as-itself.yaml`; ADR 0048.

**Measured before the build.**
- About twenty-four places read a skill set through its rung: the graph's SQL functions, the class card, the child and
  parent reports, and the website's children, report and curriculum queries. Nothing kept a second skill set off a
  rung. The seed holds one on each (28 on 28), so no report is wrong today.
- A skill set's own skill, which the next paper is chosen by (`w2_print/shelf._catalog`, read by `assess/focus.py` and
  `w2_print/focus_paper.py`), was the most common skill among its questions, ties broken by the alphabet. On the local
  copy, four of 28 differed from the skill their rung declares first:
  ```
  EQUALITY.INVERSE   | R16 | declared NUM.OPS.05  | counted NUM.OPS.01
  MUL.GROUPS         | R35 | declared NUM.OPS.03  | counted NUM.OPS.01
  STRATEGY.EFFICIENT | R13 | declared NUM.OPS.05  | counted NUM.OPS.01
  WORD.BUDGET        | R14 | declared NUM.PRB.02  | counted NUM.MEAS.04
  ```
- `M_WRONG_OP` has three names: subtracted instead of adding, added instead of subtracting, added instead of
  multiplying. The website's Marking cards, picker and lanes, the child's answers and skills panel, the charges table
  and repeated mistakes each took whichever row came first.

**Now.** Each claim with the command that proves it:
- `cd packages/engine && .venv/bin/python -m pytest -q tests/test_a_skill_set_is_read_as_itself.py tests/test_focus.py
  tests/test_focus_paper.py tests/test_maker.py` → `39 passed`. It covers:
  - a second skill set on a taken rung is refused (`UniqueViolation`);
  - every taught skill set's own skill is the one its rung declares, equal groups is Multiplication, and a skill set
    with no question has none, so no paper is drawn from it;
  - one rule names a mistake, in the database (`mistake_name`) and the engine (`name_of`), checked equal for every
    mistake, every operation's skill, and every way an operation is written (`operation_sign` against
    `operations.sign`, sign by sign). The rule: the question's own operation, else the operation of the skill the
    mistake was charged to; failing that, its name for any operation, else its one name, else its code.
- **Website:** every screen that names a mistake passes its question's operation and the skill each mistake was
  charged to, and reads the database's answers (`lib/mistake-name.ts` looks them up and decides nothing). This covers
  the Marking card, picker and lanes, the child's answers and skills panel, the charges table and repeated mistakes.
  `cd apps/web && npx tsc --noEmit -p . && npx eslint . --max-warnings=0` → clean.
- **`M_WRONG_OP` has a name for any operation**, "Chose the wrong operation", where none is known: a story with no
  operation, or a mistake charged to Word problems, which the approval page and the class card showed as a code. It is
  a seed row (`supabase/seed/misconceptions.json`), live after the next `bin/update-live`.
- **A teacher-asked paper** finds the child's repeated mistake on its skill set's own rung (`focus_paper._asked`), so
  `STRATEGY.EFFICIENT` keeps the mistakes charged to Addition and Subtraction there. Before, it took any lagging state
  of the set's own skill from any rung.
- **A second reader reviewed the diff** and found, among the five above, that `tests/test_bank.py` put a test skill set
  on a taken rung (27 errors). Its fixture now gives it a rung of its own (`TEST.R`).
- **Nothing else broke.** `cd packages/engine && .venv/bin/python -m pytest -q` → `1469 passed, 2 failed`:
  - `test_roles`, which did not yet list `operation_sign` among the functions the website may call;
  - `test_mistake_names`, which held "never a guess" as the raw code `M_WRONG_OP`. It now holds the name for any
    operation, which is not a guess either.

  Both fixed; the suites they and this slice touch → `76 passed`; `bin/check` → `27 passed`.
- **Live (2026-10-09).** PR #161 merged as `fee48d7`. `migrate live` run 37961033682: "Applying migration
  20261027090000_a_skill_set_is_read_as_itself.sql... Finished supabase db push." `deploy engine` run 37961033754
  records engine-commit `fee48d7`; 0 answers re-marked. Before the merge, `rehearse update-live` on the branch, against
  a copy of live (run 37956466525), applied every migration (the unique index holds on live's own rows) with
  misconception rows 77 → 78, 3114 worksheets and 0 problems.

## M1 — the taxonomy as rows (2026-10-09)

Goal `goals/md1-taxonomy-rows.yaml`; ADR 0049.

**Measured before the build.**
- `docs/design/multiplication-division-cases.json` held each case's words only: no match, and no example a tag could
  measure.
- `tags.derive` measured nothing of a × or ÷ question beyond its kind. The 864 `MUL.1D` questions and 48
  `MUL.GROUPS` ones were cases of nothing.
- 54 of the 270 addition and subtraction cases name no operation (R06 is any `odd_even` question), so the first ×
  odd-or-even question would have counted as one.
- `case_dimension` was the §12 matrix, read by nothing. 22 of the tags the 270 cases read were no dimension row, and
  `word_structure`'s values were never measured.

**Now.** Each claim with the command that proves it:
- **The 247 cases are rows**, each with the drafted document's code, section, words and example, every straight
  answer recomputed from the row's own numbers (`O.compute`, `O.divide`), not read from the document.
- **Code measures every new tag.** `assess/md_tags.py` (303 lines) measures, among others:
  - the fact, its table and group, and a table read the other way;
  - by 10, 100 or 1000, or a round number whose fact is a table fact;
  - which columns carry and how far, and a knock-on;
  - a long multiplication's rows, whether each regroups, and whether adding them carries;
  - short division's exchanges, a first digit smaller than the divisor, a zero in the quotient;
  - the remainder, and an estimate that must be corrected.

  Column arithmetic is in `assess/operations.py`. 75 hand-stated readings hold it: 56 × 3 carries from the ones,
  804 ÷ 4 has a zero in the middle of its quotient, 47 ÷ 6 leaves the largest remainder, 84 ÷ 12 needs its estimate
  corrected.
- **A case is a case of its own taxonomy.** Each row and match names ADD_SUB or MUL_DIV. A question's `taxonomy` is
  read from its own operations, so no case of one document holds an example of the other, and a × odd-or-even
  question is not R06.
- **No two cases are one.** The test reads every straight × and ÷ question to four digits, in a line and in columns
  (about 100,000 questions, 3,924 distinct readings). No two cases hold the same set. It found D03 and D04 were one
  case, since every 2-digit by 1-digit exchange goes past the tables. They are now by 2–5 and by 6–9 (`divisor_group`),
  and the document says so.
- **The dimension rows are the vocabulary** of both documents: 68 rows. Every tag a case reads, and every value it
  reads it at, is a row; and every reading the code makes of every straight question is a value its row allows. `word_structure` is replaced by the measured `structure`, and the loader removes a dimension
  the seed no longer names.
- **`engine bank taxonomy` counts both, each under its own name.** Local copy, after `engine load` and `engine bank
  relabel` (21,289 tags changed, all adding `taxonomy`; cases changed on 912 questions, the 864 + 48 above, and on no
  addition or subtraction question):
  ```
  ADD_SUB: 270 cases · 269 covered · 0 missing · 1 thin
  MUL_DIV: 247 cases · 26 covered · 205 missing · 16 thin
  MUL_DIV: 247 unplaced, no level in use names them: TF01 TF02 …
  ```
  The 26 covered are what the old `MUL.1D` and `MUL.GROUPS` questions already are. The 247 unplaced wait for M2–M4's
  levels.
- **Refill retires nothing.** × questions now carry `operand_1_digits`, so refill judges `MUL.1D` by its own declared
  digits. All 864 fit: `cases.outside_their_level` → 0.
- **A second reader reviewed the diff and found eleven things; each is fixed at its cause and tested:**
  - the website's taxonomy screen would have shown multiplication's cases under addition's chapters (both documents
    number a §4, §7, §8, §9 and §11). It now reads the document its title names (`lib/queries-taxonomy.ts`);
  - `zero_pattern` read the zeros of the 100 in 45 × 100, so 345 × 100 was no case and 10 × 45 was "×10 of a number
    ending in zero". It reads the number multiplied, and where its zeros sit apart from how many (`zero_count`);
  - ÷ with both numbers round missed its fact (80 ÷ 20, 200 ÷ 40);
  - T13 held 12 × 345; it is 1-digit by 3-digit;
  - missing numbers with no one answer (□ × 0 = 0, 42 ÷ □ = 5, □ × □ = 24) were given made-up numbers, and some
    crashed. Each is now measured as nothing, as are negative numbers, and numbers past five places are named;
  - "3 x □ = 12" was read as × by one reader and not by the other; both now read only ×;
  - `engine bank taxonomy` said "247 unplaced" in the line `goals/s13-levels-by-taxonomy.yaml` reads; it now counts
    each document on its own line;
  - the story-shape reader would have offered the model multiplication's story shapes with no templates and no eval
    (rule 7); it offers the addition and subtraction document's only, until M4 brings both;
  - `test_topics` held "a skill holding a case is taught", which multiplication's untaught cases broke; it reads the
    addition and subtraction document, which is what it promised;
  - 0 × 12 was the 11–12 group; it is the 0–1;
  - the tests now include 13 labels checked against plain arithmetic written in the test, not the code under test,
    and every reading of every straight question checked against the vocabulary.
- `cd packages/engine && .venv/bin/python -m pytest -q tests/test_md_cases.py` → `118 passed`; the suites this
  touches (`test_md_cases test_taxonomy test_topics test_loaders test_rehome test_story_shape test_bank
  test_every_skill test_legacy test_division_is_an_operation`) → `913 passed`; the whole engine suite before the review
  → `1799 passed, 1 failed` (`test_topics`, above);
  `packages/engine/.venv/bin/python research/md_taxonomy.py --check` → `247 cases in 13 sections, 38 mistakes,
  17 skills, 247 rows: every example recomputed and measured, every case placed or listed unplaced, 0 faults`;
  `bin/check` → `27 passed`.
- **The rehearsal on a copy of live** first failed restoring live's rows: the new column's default had been dropped, so
  a row from before it had no value. The default stays (every row older than the column is addition and
  subtraction's), and the loader writes the column for every seed row.
- **Gates.** `tags.derive` complexity 13 → 11; `cli_taxonomy.register` 16 → 14 (statements 55 → under the limit); `tags.py`
  unannotated 283 → 253; `loaders.py` 409 → 405 lines. Each fallen value is written in `workflows.json`.

**Waits for Nimish's next `bin/update-live`** (seed rows; a deploy loads only prompts, thresholds and config): the 517
case rows, the 68 dimension rows, and the relabel that writes `taxonomy` onto every stored question. update-live runs
`engine load`, then `engine bank relabel`, before anything reads a case.

**Live (2026-10-09).** Merged as `1649ed1` (PR #162). On main: `ci` run 444 success; `migrate live` run 37 success
(18:26 UTC, "apply what live is missing"); `deploy engine` run 79 success (18:31 UTC), its step "live has every
migration this commit carries" green, so `20261028090000_a_case_names_its_taxonomy.sql` is applied, and "the server
records the commit it now runs" at `1649ed1`. The seed rows still wait for `bin/update-live`.

## M2 — measured before the build (2026-10-09)

- **The case drawer (`assess/draw.py`) wrote only + and −** (`OPS = {"ADD": "+", "SUB": "-"}`), so no × level could be
  its cases. × was made only by the old sampler (`MUL.1D`: 2 × 1, 3 × 1, 2 × 2 digits) and by equal groups.
- **`predict("×", 68, 17)` named two mistakes** (`M_MUL_ROW_OUT`, `M_WRONG_OP`), neither a long multiplication's; every
  column predictor refused a 2-digit multiplier and any 1-digit number written first (3 × 21).
- **Nothing printed a long multiplication's rows**: the column grid drew the two numbers and the answer.
- **The drafted document's levels, held to the questions they would hold, had four defects** (ADR 0050): TP10 and
  TZ07 hold the same questions in two skills; T03 read only the order, so 2-digit × 1-digit Easy held 7 × 99; the ×
  cases read the written order, so 3 × 47 was no case at all; and 19 × 14 and 68 × 17 were in no 2 × 2 case.
- M2 is three slices (BUILD-ORDER): M2a the drawer and the five straight skills; M2b the methods and Advance's kinds;
  M2c `MUL.1D` re-homed.

## M2a — straight multiplication (2026-10-09)

Goal `goals/md2a-straight-multiplication.yaml`; ADR 0050. M2c, re-homing `MUL.1D`, ships here too: CI showed the five
cannot fill while `MUL.1D` holds the same questions, since a question lives in one level.

**Now.** Each claim with the command that proves it:
- **Five skills on five rungs** (R36–R40, `NUM.OPS.03`), in two untaught topics (`MULFACT`, `MULCOL`): MUL.FACTS,
  MUL.TENS, MUL.2D1D, MUL.3D1D, MUL.2D2D.
  - Each level is its document's straight cases, held to `docs/design/multiplication-division-cases.json` by
    `test_mul_levels.py`.
  - Advance exists only where the document gives it straight questions no lower level holds: MUL.FACTS (the 11 and
    12 tables) and MUL.TENS (a round number with no fact under it).
  - Grades are the document's (A6), except that nothing of the tables is Grade 1's. The tables' Easy and Medium are
    Grade 2's until the Grade 1 educator says otherwise.
- **One home, and a level, for every question in reach.** Every straight × to 3 digits by 1, 2 by 2, the tables, and
  round numbers by 10, 100 and 1000 to a 5-digit answer, in a line and in columns, has exactly one of the five shapes
  and a level (`test_a_multiplication_has_exactly_one_home_among_the_five`,
  `test_every_question_in_the_fives_reach_has_a_level_not_only_a_skill`). 3 digits by 2 and 4 by 1 stay the document's
  unplaced cases, round or not.
- **Every drawn question is what its case's label says**, checked in plain arithmetic written in the test
  (`test_every_question_a_level_draws_is_what_its_cases_label_says`).
- **The drawer makes ×** (`assess/draw_times.py`):
  - facts come from the tables, and a number a case lets be round is a number times 10, 100 or 1000;
  - nothing is × 1 unless the case is about it;
  - in columns the longer number goes on top, and a 1-digit number written first is a line's;
  - an even draw is dealt a case at a time, so cutting it never drops a whole case.
- **A4 is what a level holds.** The tables' Easy to Hard leave out a fact that needs the 11 or 12 tables, measured by
  `fact_group`; their Advance holds every table. An old paper's 12 × 7 is placed at Advance
  (`test_the_eleven_and_twelve_tables_appear_only_at_advance`).
- **Eight more mistakes predicted** (`assess/mul_mistakes.py`; `misconceptions.py` 489 → 380 lines):
  - the second row not moved (68 × 17 → 544);
  - one row (476);
  - column by column (656);
  - a stale carry (47 × 23 → 1281);
  - a carry onto a zero lost (506 × 7 → 3502);
  - a zero too few (45 × 100 → 450);
  - × 0 kept (7);
  - × 1 adding one (8).

  Each is worked the longer number by the shorter. One wrong answer names one mistake where two would be the same
  act (`test_one_wrong_answer_names_one_mistake_where_two_would_be_the_same_act`). The document's error table reads
  them from the engine and checks each against a second, independent computation (`research/md_taxonomy.py`).
- **A stored question keyed by a mistake rule since corrected leaves the bank** (`verify.key_problems`), and refill
  draws its replacement. A printed paper still reads by its stored key.
- **A long multiplication prints a row for each digit of its multiplier**, only in layout row `2026-10-09`
  (`long_rows`). The rows are one working space the reader never takes for the answer, after its own inset. A page
  printed in an older layout re-renders with none
  (`test_a_long_multiplications_rows_are_working_the_reader_never_reads_as_its_answer`).
- **`MUL.1D` re-homed and removed.** The five say they replace it. On the local copy, `engine bank rehome` gave `moved
  596 questions · 268 retired, their story's shape unnamed · removed 1 skill sets and 1 rungs`: 864, none lost.
  An old paper's × sums are filed on the five's rungs (`placing.OPERATIONS`; all 23 on the school's papers,
  `test_every_times_question_on_the_schools_papers_has_a_skill_and_a_level`). The three papers' questions on M1 with no
  sum to place are filed on rungs with a spec, each keeping its own skill:
  - the two-step apple story → WORD.1_2STEP (R8);
  - `8 × ___ = 72` → EQUALITY.INVERSE (R16);
  - `144 ÷ 12` → EQUALITY.INVERSE (R16), until M3 gives division its rungs.

  Rung M1 leaves the seed, and `bank rehome` removes it on live once nothing names it. The × sums' files still say
  "M1": that is only the rung a deploy uses before `bin/update-live` has created the five, and `rung_for` files every
  one of them on the five once they exist (test_legacy).
- **The drafted document, measured** (251 cases, `research/md_taxonomy.py --check` → `0 faults`):
  - TZ01 and TZ07 → MUL.TENS Advance;
  - × cases read the longer and the shorter number;
  - T03, T02, T11 and TZ02 keep to Easy's answer size;
  - MUL.TENS's cases are bounded to their words;
  - T27, T28, TZ09 and TP11 are added.

**A second reader** reviewed `451ae0c` and found ten things; each is fixed at its cause:
- long multiplication's rows were drawn as `.work`, so an answer read as "working shown";
- MUL.TENS drew 6700 × 1000 at Grade 3;
- MUL.3D1D's Advance added nothing harder, and × printed in columns put the 1-digit number on top;
- Easy levels drew Medium's answers;
- MUL.TENS columns drew rows for the wrong number;
- one wrong answer named two or three mistakes by construction;
- "one row out" was predicted for 68 × 17;
- four tests could not fail;
- the "one home" claim was wider than its test (it is now narrowed to the reach above, and a level is tested too);
- 801 × 0 was a "zero in the middle" case.

**CI on `def49e6` and `a61e0dc`** found two more; each is fixed at its cause:
- **Every job died before a step ran**, twice: Docker Hub refused CI's anonymous pull of `postgres:17`
  ("toomanyrequests"). CI now pulls the same official image from AWS's copy of it
  (`public.ecr.aws/docker/library/postgres:17`).
- **CI's bank filled MUL.2D1D Easy to 66 of its 69** (`test_every_invariant_holds`). The level's target is all it holds,
  3 × 21 turns up once in about 3,000 random draws, and the drawer called a case dry after 2,000 misses. A × case that
  runs dry is now listed whole (`draw._rest`, ADR 0050 decision 12). Three questions held back from each level drawn
  whole are found whatever the random draws do
  (`test_a_level_whose_target_is_all_it_holds_is_filled_to_the_last_question`; the old drawer found 0 of 3 for
  MUL.2D1D Easy). To keep `draw.py` under 400 lines, the three + and − cases built rather than drawn by digits moved to
  `assess/draw_sums.py`.

**Proof** (on a database built as CI builds it, `bin/testdb fresh`):
- `bin/engine goal md2a-straight-multiplication` → `17/17 scenarios met the bar completely`, `3/3 criteria met · GOAL
  ACHIEVED`. Its criteria are the suites this touches (`1011 passed`), `research/md_taxonomy.py --check` (`251 cases
  … 0 faults`) and `bin/check` (`27 passed`).
- The whole engine suite on that database: `1917 passed`, then the 6 it found fixed (the crosswalk's MUL.1D claim, rung
  M1, three expectations) and those suites rerun, `171 passed`.
- `bank refill` → `retired 0 questions outside their level · added 23343`.
- `library build` → `made 2040 · retired 0`.
- `library check` → `2040 worksheets · 121 of 121 skill-levels ready · 0 problems`.
- `bank recheck` → `0 mismatches`.
- Every MUL level is full. The smaller ones hold their whole range:
  - MUL.FACTS 26 / 82 / 89 / 56 (Hard's own after Medium's, since a table read the other way is both);
  - MUL.2D1D Easy 69.

**Waits for Nimish's `bin/update-live`** (it carries M0b, M0c, M1 and M2a):
- seed rows: the five skills, their rungs and topics, the eight mistake rows, the 251 case rows, the layout row;
- `bank rehome`, which moves `MUL.1D` and files July's × answers on the five;
- the questions and worksheets refill and the library make;
- after that, the five wait on Curriculum → Read and approve.

The week-note eval's gold names the new skills for its two multiplication notes, so `bin/engine eval week_skills`
records its score again.

## M2b — measured before the build (2026-10-09)

M2a is live: main `5916b28`, `migrate live` and `deploy engine` green (22:34 and 22:40 UTC); no migration in that
slice. `bin/engine done md2a-straight-multiplication` on a database built as CI builds it: every sentence PROVED,
`17` of 17 scenarios MET, `3` of 3 criteria PASSED (`1016 passed`, `251 cases … 0 faults`, `27 passed`); it ends
"NOT DONE" only because this container cannot read live's migrations, which the two runs on main stand for. Its data
waits for `bin/update-live`.

What the three Advance levels need, measured:
- **Every kind they are made of refuses ×** (`O.require`, whose default makes + and − only): a missing digit
  (`missing_digits.py:130`), finding the mistake (`diagnosis.py:188`), an estimate (`estimate.py:18`), a one-step story
  (`words.py:84`, and its templates are filtered to + and −), and a shortcut, whose three kinds are all + or −.
- **Their cases name no kind**: Q07, Q08, Q11, Q16, C01–C03, C09, V01–V03, V07, B06, B08, B12, H01, H07 and Q15 carry
  no `fmt` in their match, so the drawer finds no generator for them; addition's kind cases name theirs (X12:
  `find_mistake`).
- **T13 (6 × 125 in a line) cannot be an Advance**: since a × case reads the longer number and the shorter (ADR 0050),
  every T13 question is one MUL.3D1D's Easy to Hard already hold. It joins T14 among the ways that skill's questions
  are printed.
- **The measuring is there already** (M1): a × question's numbers, a missing digit's boxes and solved numbers, a
  story's shape, a planted mistake, an estimate's shape, a shortcut's `strategy` are all read by `tags.py` and
  `md_tags.py`.
- **The methods are a slice of their own (M2d)**: nothing renders a grid, a lattice, an array or skip counting; the
  number line jumps only for + and −; and the two methods' mistakes, a grid cell dropped and tens partitioned as ones,
  are neither rows nor predicted. C06, finding that second mistake, goes with them.

**Found while proving M2b, older than it (named here, fixed next, before M2d).** On a database built as CI builds it,
the bank holds no question at all of these cases its levels list; on main `5916b28` the same cases draw nothing in
300 tries each:
- addition's and subtraction's Advance kinds: estimates R01, R02; missing numbers M01–M05, M24, M25; finding the
  mistake X03, X06–X09; stories W02, W03, W06; and SUB.3D3D's straight SZ6 and SZ9, at Hard as well. R01 and R02
  cannot be drawn because a case level names no `regroups` for the estimate it asks for.
- Not a defect: a few small straight cases an Advance shares with Hard, which Hard holds whole (MUL.2D1D's T08, T10,
  TZ05; MUL.3D1D's TZ06; MUL.FACTS's TF01, TF02; MUL.TENS's TP09). A question lives in one level.

## M2b — the second reader (2026-10-10)

A second reader of the slice found four things wrong; each is fixed at its cause in this PR.

- **A × missing-digit box no carry reaches named nothing and was drawn again**, so MUL.2D1D's Q07 was only ever the
  ones after 2, 4, 6 or 8, and the test that checked it worked the same rule as the code. A box now names the table
  one row out where its column alone allows no second digit (ADR 0051, decision 4).
  - Check: 300 of Q07's draws now give an odd multiplier 153 times, a lead box 150 times, M_MUL_ROW_OUT 226 times and
    M_MISSING_DIGIT_LOCAL 74 times.
  - Test: `test_a_missing_digit_is_asked_in_every_place_after_every_multiplier`; each box's mistake is now worked from
    its definition in the test (`_named`), not copied from the code.
- **A column tick one slip always answers the same way**: a carry lost onto a zero (C09) is always lost in the tens,
  and MUL.3D1D's Advance plants nothing else. The reader said C01 and C02 too; measured, they are not (2-digit by 1:
  tens 457 and hundreds 60 of 517 pairs for C01, 497 and 92 of 589 for C02).
  - The same was already true of addition and subtraction on live, behind the claim that "a level mixes it with
    others". Measured over every level that plants a slip (each level's own cases drawn 160 times), ADD.2D1D's Advance
    ticked the ones every time, ADD.3D2D's the ones, ADD.4D's the ten-thousands.
  - The rule is now one for every operation (ADR 0051, decision 7): where a slip's first wrong digit is always in one
    column, it asks the answer and why.
  - Check: on fresh8, a database built before the rule, 485 of 1,199 active find-the-mistake questions are flagged by
    `verify.key_problems`, every one a one-column slip. `DATABASE_URL=… bin/engine bank refill` then printed
    `retired 507 questions outside their level · added 511` (4m12s): the 485, and MUL.2D2D's 22 combination stories in
    their old words (below). After it, 0 active questions are flagged, and 498 of 1,186 finding the mistake ask the
    column.
  - Tests: `test_a_worked_answer_asks_its_first_wrong_column_only_where_that_column_can_move`,
    `test_an_addition_or_subtraction_asks_the_column_by_the_same_rule`,
    `test_a_stored_question_asking_a_column_that_never_moves_leaves_the_bank`.
- **Three boxes in a multiplication could hide the answer's digit twice**, and a request for more boxes than digits
  waited for ever. Now a box is chosen once, and the search for more is bounded; + and − draw as before.
  - Test: `test_three_missing_digits_are_three_boxes`.
  - Not a defect, and unchanged: three boxes in a 2-digit subtraction leave more than one filling 2 times in 30, on
    main as now.
- **A request no question can meet recursed for ever or printed 0**: a number near a round one of 3 digits, × 5 as
  × 10 then halved on 1 digit, a × slip on a table fact, rounding a 1-digit number to the ten. Each is refused by name
  (`CannotMake`). Test: `test_a_kind_asked_for_numbers_it_cannot_use_says_so`.

- **The update-live rehearsal on `0ea78e8` failed at `library check`** (run 23): "MUL.GROUPS Medium: two worksheets hold
  the same questions". This is older than M2b and is not multiplication's. The dealer never asked whether its
  worksheets differ, and this slice's draws, which shift what refill makes, gave G1's 16-question level a deal with a
  repeat.
  - Measured: 16 questions dealt onto ten worksheets of twelve repeat one in 6 levels of 300; 14 questions of two
    kinds and 16 of four kinds repeat too. The test of "no two alike" started at 22 questions.
  - `deal` now takes the first of 20 rounds whose worksheets all differ. Round 0 is the deal as before, so a level
    dealt before stays as it is. `build` also retires a worksheet that repeats an earlier one, which it used to keep,
    so it repairs what `check` refuses.
  - Tests: `test_a_small_levels_worksheets_all_differ`, `test_two_worksheets_alike_are_made_different_by_building_again`.
  - Not a defect: a level of exactly 12 questions cannot make ten different worksheets, and `check` says so. None
    holds fewer than 16.

Also: the two combination stories are worded for 2-digit counts (a sticker book's animals and backgrounds, a racing
game's cars and tracks), where 34 kinds of sandwich read as nonsense.

**+ and − draw as before.** Measured once, against a checkout of main `5916b28`: 919 questions drawn from the same
seeds on both (every + and − slip at 2, 3 and 4 digits, 12 each; every missing-digit request of 1 to 3 boxes, 10 each).
715 are identical. 204 differ only in the column tick a one-column slip no longer asks: lined up from the left 36,
copied out of a line 36, a final carry dropped 36, an exchange from the wrong place 36, the two across-a-zero
exchanges 24 each, a decrement forgotten 12 (2 digits only). Nothing else differs. Left out: three boxes asked in one
row, which main waits on for ever (the third finding above).

## AS1 — measured before the build (2026-10-10)

M2b is merged and deployed: main `d4435d8`, CI, `migrate live` and `deploy engine` green (01:49 UTC); no migration.
`bin/engine done md2b-times-advance` on a database built from that tree: 17 of 17 sentences PROVED, 3 of 3 scenarios
MET, 3 of 3 criteria PASSED. It ends "NOT DONE" only because this container cannot read live's migrations
(`UndefinedTable`); the runs on main stand for that.

Each (case, level) pair the seed lists, drawn alone on its level as the bank draws it (605 pairs, 32 s):
- **35 pairs gave nothing, for four causes.**
  - An estimate on a level made of cases: R01, R02. Every draw raised `KeyError: 'regroups'`, swallowed by
    `draw._native`, 6,000 times a level.
  - A + or − mistake found in two numbers of the first's length: X03, X06 to X09 on the 2 by 1, 3 by 1 and 3 by 2
    levels. All 300 of each made, all refused for the second number's size.
  - A case its level's numbers can never be: 20 missing numbers (M01 to M05, M24, M25 where the box's size is no
    number of the level's), and SZ6, SZ9 on SUB.3D3D (1000 − 476, 1000 − 999: a 4-digit first number).
  - The stories W02, W03 (SUB.1D1D) and W06 (ADD.1D1D) draw on their own. They go missing only when the level is
    filled whole: a story's key is its numbers, and the cases listed before them take all 36 (or 72). That is AS2.
- **Swallowed by the drawer:** `KeyError` 12,000 times (R01 and R02 only), `RuntimeError` 96 (numbers that did not fit),
  `ValueError` never.
- **After the fix:** 0 pairs empty, and only `RuntimeError` swallowed (96). The survey takes 8 s.
- **Raising what was swallowed found two more:**
  - A fresh bank stopped at WORD.1_2STEP's Advance: `ValueError: no one-step story for shape 'EXTRA_INFORMATION'`.
    W25 lists the one-step and the two-step kind, and only the two-step's templates hold a number to leave out. Half
    its draws had failed unseen, and drawing 2 of each pair had missed it. The drawer now picks only a kind whose
    templates hold the case's shape (`bands.makes`).
  - E07's test drew its balance-scale kind with no `hi` (its real level, EQUALITY.INVERSE Medium, gives 50). That is a
    defect of the test, which now draws the case by the kind it tests.
  - Surveyed again at 20 draws a pair (605 pairs, 171 s): 0 empty, nothing raised, `RuntimeError` swallowed 703 times.
  - The invariant audit raised `KeyError: 'op'`: it drew a level of cases from the raw rows, not on the level's own
    numbers as the bank does (`cases.for_level`). K02 (number-line jumps) on ADD.1D1D names no operation, and its
    level gives addition. Drawn as the bank draws it, the audit then found four claims no question can make good:
    ADD.1D1D M_CONCAT, ADD.3D3D M_ALIGN_LEFT, SUB.1D1D M_NO_DECREMENT and M_SMALL_FROM_LARGE, SUB.2D2D M_ALIGN_LEFT.
    They leave the seed, and migration `20261029090000` removes them from a database loaded before.
  - `engine load` never overwrites a skill set. A changed level reaches live only through `bank levels --apply`,
    which withdraws the approval of the 11 skills AS1 changes.
- **Not a defect:** EQUALITY.INVERSE's Advance holds a 3-digit M25 above its `hi` of 50. Its own words ask for "a
  3-digit number to work back to: □ − 275 = 418", and the 50 bounds its other cases.

## AS2 — measured before the build (2026-10-10)

AS1 is merged and deployed: main `9a4b366`, CI, `migrate live` (migration `20261029090000`) and `deploy engine` green
(03:18 UTC).

Each 1-digit Advance level filled whole, as `bank refill` fills it and a scenario asks for it (dry run, three seeds,
`draw.level` with the level's own target), on AS1's tree:
- **SUB.1D1D's Advance (108): W11, W02 and W03 held 0 times.** W04, W05, W08 and W09 took 9 each: all 36 pairs of two
  1-digit numbers a − b. A story's key was its numbers, so the shapes listed after them found every pair taken. STATE
  and BUILD-ORDER had named W02 and W03; W11 starves the same way.
- **ADD.1D1D's Advance (216): W06 held 0 times.** W01, W07 and W10 took 24 each, all 72 pairs.
- Every seed the same: the order of the case list decides which shapes a level never holds.

## AS2 — found on the way (2026-10-10)

- **A story a person reworded lost its shape at the next relabel, and the refill retired it.** A story's shape was read
  from its words (`words.structure_of`), and a rewording matches no template. On a copy, rolled back: SUB.2D2D's
  `WP1-004ec883` (JOIN_CHANGE, W02) reworded keeps its shape and case; `bank relabel` changes its tags, cases and
  charged skills (shape `None`, cases `[]`); `cases.outside_their_level` then names it "dimension outside every case
  the level holds". update-live runs `relabel` and `refill` every time, so every story an educator reworded would leave
  the bank at the next update. The shape is now in the spec, which a rewording copies; `bank rekey` gives a stored
  rewording its story's shape, followed back through `corrected_from`.
- **A two-step story's key held no operation.** UNKNOWN_FIRST (a − b + c, a + b − c), EXTRA_INFORMATION (a − b, a + b)
  and CONSTRAINT (a − b + c, (a − b) ÷ 2) each hold two arithmetics under one shape: two different questions shared a
  key, and the second was dropped as held. The key holds the operations now; a test holds every pair of templates that
  key alike to one answer.
- **`bank_proposal` is append-only**, so a re-keyed story's proposal cannot follow it. A key change is a row of
  `item_key_change`; `current_item_key()` leads an old key to its question for every reader that may hold one: the
  question page (engine and website), a rewording or removal, a proposal decided, the "already proposed" check, a gold
  file loaded.
- **`bank recheck` would have dropped every one-step story from its audit.** It rebuilds only specs whose fields it
  knows, and a story's spec now holds its shape. `structure` is one `verify.to_item` makes, so it is let through; a
  test names a story whose answer was changed by hand.
- **One reworded story re-dealt every worksheet of its level.** The whole suite on AS1's tree (fresh11): 2012 passed, 1
  failed, `test_question::test_rewording_a_question_moves_it_onto_a_new_worksheet_and_retires_the_old_one`. Replayed on
  the same copy: ADD.2D2D's Advance, 221 questions on 19 worksheets; the reworded story's worksheet (R22-A19, dealt
  last) held the level's 7 repeated questions, so 5 were left uncovered; the patch filled the other 7 places by use and
  then key, all one kind (5 column sums where the fair share is 1.8); the patch failed its fairness check and all 19
  worksheets were retired and dealt again. CI's bank put that story on another worksheet, so CI passed. The filler
  now takes each kind to its fair share (`library._filler`); replayed, 18 worksheets kept and 1 made.
- **CI on `2cd814c`: the browser suite, 152 passed, 4 failed, all one cause.** `item_key_change` named its question
  `on delete cascade`, and its append-only trigger fires for each statement: every `delete from item`, which two browser
  tests run to put their rows away, cascaded a DELETE into the ledger and was refused even with no row to remove. The
  e2e rewording test's clean-up stopped half-way, its reworded question stayed active with no worksheet, and the bank
  page lists the newest first, so both question-bank tests then found a first row with no worksheet link. The reference
  now has no cascade (migration `20261030090000`, never applied to live): a question whose key never changed is deleted
  as before, and one whose key did is kept, as its ledger row is.
- **The rehearsal on a copy of live passed without running `bank rekey`.** It keeps its own list of update-live's steps,
  and the new one was not in it. A test now holds the rehearsal to every command update-live runs, in its order
  (`test_update_live.py`, failing first on the old list).
- **A copy printed before a story was keyed again would not have read its boxes.** A worksheet's key file names each box
  by its question's key as printed (ADR 0050 rejected changing a stored key in place for this), and the reader matched
  boxes to the question's key now. `copies.paper` reads the key file through `current_item_key`; a test rewrites a
  rendered worksheet's key file to name a story by its old key and reads every box by the key it has now.
- **The rehearsal of `2cd814c` on a copy of live** (without `bank rekey`): 13 skill sets wait for approval (as AS1's);
  `bank rehome` moves 606 and retires 258 stories whose shape no template names, as on every rehearsal since M2a (ADR
  0050: `MUL.1D`'s); refill retires 541 and adds 4,561; 3,388 worksheets, 124 of 124 levels ready, 0 problems; every
  after-check ok. Live holds 20 one-step stories with no shape, the model-written ones (the rehearsal's own listing).

## M2d1 — measured before the build (2026-10-10)

AS2 is merged and deployed: main `7990be2`, CI, `migrate live` (migration `20261030090000`) and `deploy engine` green
(04:42 UTC). `bin/engine done as2-a-story-is-its-shape` on a database built as CI builds it: 11 of 11 sentences PROVED,
2 of 2 scenarios MET, 2 of 2 criteria PASSED (1,099 tests, `bin/check` 27); "NOT DONE" only for live's migrations,
which this container cannot read (`migrate live` on main applied them). `bin/engine done as1-every-listed-case-draws`
on main `9a4b366`'s tree: 8 of 8 PROVED, 9 of 9 MET, both criteria PASSED (1,065 tests; `bin/check` 27 once a stray
`pyrightconfig.json` in the session's scratch folder, above the worktree it ran from, was moved aside).

M2d is two slices (BUILD-ORDER): M2d1, `MUL.MODELS`; M2d2, the written methods and their mistakes.

`MUL.MODELS`' eight cases, each drawn alone on a × level through today's drawer (4 asked, 300 tries each):
- G03 (skip counting), G05 (an array), TF17 (a cell of the multiplication square): 0 of 4. The drawer never passes a
  case's `method` or its table to a kind, so every draw is refused by the case's own match.
- G04 (equal jumps on a number line): `KeyError: 'hi'`. The number line makes + and − only.
- G14 (a table swapped to a known one): `ValueError: no equation shape 'SWAP_TO_A_KNOWN_TABLE'`.
- B04, B11, B13 (an array, twice as many, area in squares): `CannotMake`. No × story template holds those shapes.
- `MUL.MODELS` is no row; `M_TIMES_AS_MORE` ("reads 3 times as many as 3 more", the drafted table's) is no mistake row.
- `draw.py` is at its 400-line ceiling: passing `method` means first moving the cases a kind draws for itself (and
  what a case allows, its operation and sizes) into a module of their own.

## M2d1 — MUL.MODELS built (2026-10-10)

What the eight measured failures became (ADR 0054), each proved by `tests/test_mul_models.py` (9 tests):
- G03 skip counting and TF17 a cell of the multiplication square are kinds of their own, `skip_counting` and
  `multiplication_square` (`assess/times_models.py`); the drafted rows had filed them as `bare_sum`. Corrected in
  `research/md_rows.py` and written again by `research/md_taxonomy.py` (251 rows, 0 faults); only G03, TF17 and G05's
  example changed, and the shape vocabulary gained `ARRAY`.
- G05 an array: a shape of equal groups, read in three labelled boxes (rows × in each row = in all).
- G04 equal jumps: the number line is one kind drawn two ways (`assess/number_line.py`, moved typed out of `items.py`).
- G14 the swap: an equation shape reading the level's `known` tables (`equality.from_rule`, `equality.swap`).
- B04, B11, B13: × templates of an array, twice as many and area; "times as many" names adding its numbers
  `M_TIMES_AS_MORE` both ways into the bank, a story whose misreading would be right (2 times as many as 2) is drawn
  again, and one keyed before is a key problem, so the refill retires it (`verify._stale_story`).
- The first rehearsal (run 38028938414, `770c97e`) found the three stories thin on a copy of live — 9, 7 and 8 held,
  where a case is covered at 12 — because Advance asked 24 of three cases and twice as many over a 1-digit number has
  7 questions. Advance is 36 now, and twice as many takes a number to 20 (its template's own range, `numbers`);
  `test_a_filled_level_holds_each_of_its_cases_as_often_as_the_case_asks`. The same run: 541 retired outside their
  level and 4,561 + 88 added — the AS2 rehearsal's 541 and 4,561 and `MUL.MODELS`' 88 — so the slice retires nothing
  on live; 128 of 128 skill-levels ready, 0 problems. The second rehearsal (run 38029876300, `eda75e3`): `MUL.MODELS`
  Easy +24, Medium +16, Hard +24, Advance +36; "MUL_DIV: 251 cases · 103 covered · 148 missing · 0 thin" and
  "ADD_SUB: 270 cases · 270 covered · 0 missing · 0 thin"; 128 of 128 skill-levels ready, 0 problems; every
  `engine live data` check ok after the update.
- `MUL.MODELS` (R41, Grade 2 at every level) has no `within`, so `placing` never reads it as a calculation skill. It
  sits in a topic of its own, Multiplication models, untaught: CI's `test_topics` (run on `770c97e`) failed it filed
  under the taught Multiplication, where it would have been taught by default. `MUL.2D1D` names `M_TIMES_AS_MORE`
  (seed; migration `20261031090000` for a database loaded before).
- A sheet of one question of every case, printed through Chromium as a paper is: every answer has its boxes in the
  key's geometry, the array's three included (`test_every_model_answer_is_where_the_printed_key_says_it_is`).

Ratchets, written down where they fell: `draw.py` 400 → 356 lines (`draw_case.py` holds what a case allows), `items.py`
540 → 439 lines; untyped findings `bands.py` 312 → 289, `draw.py` 183 → 177, `items.py` 439 → 359; the four new
modules carry none.

Found and named, not changed (files this slice does not touch): the marker charges a wrong answer to every mistake
that predicts it (`w3_read/marking.py`: 3 × 3 answered 6 is both `M_MUL_ROW_OUT` and `M_WRONG_OP`), while the counting
kinds name neither when two mistakes share an answer (`assess/counting.named`). One rule should hold for both.

## M2d2 — measured before the build (2026-10-10)

M2d1 is merged and deployed: main `4f548d5`, CI, `migrate live` (migration `20261031090000` applied) and `deploy
engine` green (07:06 UTC). `bin/engine done md2d1-multiplication-models` on a database built from main's tree:
11 of 11 sentences PROVED (the browser test included), 4 of 4 scenarios MET, 2 of 2 criteria PASSED (1,051 tests,
`bin/check` 27); "NOT DONE" only for live's migrations, which this container cannot read.

M2d2 is the written methods (BUILD-ORDER): assumption A1 has Easy to Hard print each calculation in every written method
the document lists for the skill, in fair shares — `MUL.2D1D` in a line (T02), partitioning (G07), a grid (G08),
expanded columns (G10) and columns (G11); `MUL.3D1D` in a line, the 1-digit number first too (T13, T14), expanded and
columns; `MUL.2D2D` in a line (T22), a grid (G09), long multiplication (G12) and a lattice (G13).

Each method case drawn on its skill's Easy, Medium and Hard through today's drawer (4 asked, 300 tries each):
- In a line (T02, T13, T14, T22), columns (G11), long multiplication (G12): drawn.
- Partitioning (G07): `CannotMake: break_apart makes + and − questions, not ×`.
- A grid (G08, G09), expanded columns (G10), a lattice (G13): 0 of 4. The drawer prints a calculation in a line or in
  columns and nothing else (`draw.LAYOUT`).
- No level lists a method: the straight cases accept only a line, columns and long multiplication
  (`match.method`), and T01 fixes columns, T02 a line and no regrouping. A grid of Easy's numbers would be none of
  Easy's cases — outside its level — and T02, the document's "in a line" for `MUL.2D1D`, crossed with Medium's
  regrouping numbers would hold no question at all.
- `M_PARTITION_TENS_AS_ONES` (C06's planted mistake) and `M_GRID_CELL_DROPPED` are no rows, so C06 cannot draw.
- No multiplication uses addition (`skills.operations` reads `op` alone), so `M_NOCARRY` on a multiplication's rows
  would charge multiplication, against A11; and nothing adds more than two numbers without a carry (`add_nocarry`
  takes two).
- A long multiplication's rows are drawn and never read (`answer_space._rows_worked`): only its answer has boxes.
- `verify._stale_mistakes` finds a stored mistake whose value changed, never one newly predicted: the long
  multiplications on live would never name the rows added without a carry.

## M2d2 — the written methods built (2026-10-10)

What the measured failures became (ADR 0055), proved by `tests/test_mul_methods.py` (16 tests) and
`apps/web/tests/s30-multiplication-methods.spec.ts`:
- **Four kinds, every step a box.** `partitioning`, `grid_method`, `expanded_columns` and `lattice`:
  `assess/written_methods.py` makes them, `assess/written_pages.py` prints them, the website draws them. A sheet of
  every method printed through Chromium has every step's boxes where the key's geometry says, each marked against its
  own key.
- **A level's `methods` is a row**, and the drawer deals each case's share over them in fair shares (`draw_case.ways`,
  `draw.level`). `bin/engine goal md2d2-multiplication-methods`: 10 of 10 scenarios met (12 to 36 asked a level, every
  answer recomputed, 0 off its rule, 0 undiagnosed, 0 alike), C06 on `MUL.2D1D`'s Advance among them.
- **The straight cases are about numbers.** T01 is "no regrouping" in any method, T02 `MUL.2D1D`'s "in a line", a grid
  sized by its shorter number (`digits_min`); corrected in `research/md_rows.py`, rows written again by
  `research/md_taxonomy.py`.
- **The methods' mistakes are rows:** `M_PARTITION_TENS_AS_ONES` and `M_GRID_CELL_DROPPED`; the steps or rows added
  without a carry (`M_NOCARRY`) count against addition (`skills.by_method`, `skills.charges`). Migration
  `20261101090000` puts them on the three skills' lists of a database loaded before.

Found while proving, fixed here:
- `test_md_cases` chose the straight cases as those listing exactly a line and columns. Once × straight cases listed
  six kinds, it silently checked only division's 52 of the 128. It now takes them from `research/md_rows.STRAIGHT`
  and compares them on every × in each written method as well: no two hold the same questions, every label holds.
- `written_methods.make` crashed on a zero (a grid of 0 × 23: `max()` of nothing). It now refuses (`CannotMake`), and
  the drawer never asks: a zero case (TZ02, TZ03, TZ09 on `MUL.3D1D`) lifts the rule against drawing a 0, and its
  expanded columns made 0 × 146 as 6 × 0, 40 × 0 and 100 × 0 before the case's own match threw it away
  (`written_methods.prints`, `draw._usable`).
- Nothing re-keyed a stored written method, so a × slip predicted later would never reach its steps.
  `verify._stale_method` makes each again from its own numbers and compares every box: of the 786 the refill stored
  on a fresh database, 0 flagged (nor any of its 12,358 straight sums).
- Three tests drew a level by hand without its methods (`test_every_listed_case`, `test_mul_levels`,
  `test_mul_advance`). They now read a level's matches through the bank's own rule (`cases.on_level`).
- `placing` (where a child's answer, an old paper's or a re-homed question goes) counted only a line and columns as a
  calculation, a copy of the old pair: every written method went to Advance or nowhere. It reads the drawer's own
  straight kinds now (`draw.STRAIGHT`), so a written method lands where its numbers in a line land
  (`test_a_written_method_is_placed_where_its_calculation_in_a_line_is`). CI's run on `c56f773` found the same pair in
  `test_rehome`, which the goal's criteria did not run; they run it now, and `test_verify`.

Found and named, not changed (the drafted document's to settle): some of Medium's questions are also Hard's. 25 × 2 is
`MUL.2D1D` Medium's T04 and Hard's T09 (the ones write 0) and TZ05 (a zero only in the answer); 2 × 274 and 6 × 115
are `MUL.3D1D` Medium's TC03 and TC05 and Hard's T12 (every pattern). The drawer draws them for Medium, and `placing`,
hardest first by design, puts the same numbers on Hard: 27 of 360 questions drawn on the three skills' straight levels
(21 in a line or columns, 6 in a written method). Either a Hard case is narrowed to what Medium does not hold, or the
overlap stands; Achal decides.

Rehearsed on a copy of live (run 38038796192, `92db98f`):
- 554 questions retired outside their level and 4,701 added. That is 13 more retired than M2d1's rehearsal (541) on
  the same live bank. The refill prints a total, not reasons; by elimination they are the long multiplications keyed
  before the rows' mistake had a name (`_stale_rows`), the only rule here that live's questions can fail.
- Added per level, Easy · Medium · Hard · Advance: `MUL.2D1D` +35 · +125 · +94 · +216, `MUL.3D1D` +215 · +209 · +86 ·
  +216, `MUL.2D2D` +214 · +216 · +198 · +220. The library made 1,238 and retired 746.
- 3,430 worksheets, 128 of 128 skill-levels ready, 0 problems. "ADD_SUB: 270 cases · 270 covered" and "MUL_DIV: 251
  cases · 109 covered · 141 missing · 1 thin". The thin one is T16 (4 × 1 digits), which no level names, held once by
  a `MUL.TENS` Hard question.
- Every `engine live data` check ok after the update; no signed-off answer left on a rung no skill holds.

Ratchets: untyped findings fell in seven files, written down in `workflows.json` (ADR 0055's table). Lines:
`diagnosis.py` 397, `draw.py` 382, `verify.py` 362, `written_methods.py` 187, `written_pages.py` 82, all under 400.

## M3 — measured before the build (2026-10-10)

M2d2 is merged and deployed: main `e84d285`, CI, `migrate live` (migration `20261101090000` applied) and `deploy engine`
green. `bin/engine done md2d2-multiplication-methods` on main's tree: 14 of 14 sentences PROVED (the browser test
included), 10 of 10 scenarios MET, 2 of 2 criteria PASSED; "NOT DONE" only for live's migrations, which this container
cannot read.

M3 is division (BUILD-ORDER): five skills, `DIV.GROUPS`, `DIV.FACTS`, `DIV.TENS`, `DIV.2D1D` and `DIV.3D1D`, on whose
levels the drafted document places 77 cases, and 8 more as `DIV.2D1D`'s and `DIV.3D1D`'s methods.

Each of the 85 drawn alone through today's drawer (4 asked, 300 tries each):
- **Nothing draws.** The drawer's operations are +, − and × (`draw_case.OPS`), so it never offers ÷.
- **With ÷ offered** (the measurement's own patch, never the code):
  - 59 raise `ValueError: 69 ÷ 4 is 17 r 1: two answers, the quotient and the remainder`: the straight cases, the
    column methods and the missing numbers, each computing one answer for a division that has two.
    `compute` rightly refuses to fold a remainder into one answer, and nothing makes a question with two boxes. The
    numbers are drawn with no idea which one is divided (6 ÷ 8685).
  - 18 refuse in a sentence (`CannotMake`): stories, finding the mistake, a missing digit, a possible answer, the
    inverse check and partitioning (`break_apart`) make +, − and × only.
  - 4 crash: an estimate takes ×'s path (`KeyError: 'digits'`), the number line raises `KeyError: 'hi'`, and ÷ 10 then
    double is no shortcut the kind knows.
  - 5 draw nothing and say nothing: the sharing and grouping pictures and an array divided (× only), the remainder
    missing, halving.
- **No division mistake is a row**, and `predict("÷", …)` names nothing for any division. The draft names 15: 14 a
  calculation shows (the zero left out of the quotient, the exchange lost, the remainder too big, …) and one a story
  shows (a remainder not rounded up).
- **Printed**, an exact division in a line is right ("72 ÷ 4 = □"). In columns it prints as a column sum ("7 2 ÷ 4"),
  not the division layout, and one with a remainder cannot be made.
- **July's 144 ÷ 12** waits on `EQUALITY.INVERSE` (R16) "until M3 gives division its rungs": `placing` places +, − and
  × only.

The drafted levels, held to the questions they would hold. Every straight division in reach was measured by the
engine's own tags: to 4 digits by 1, 2-digit divisors to 12, ÷ 10, 100 and 1000, and multiples of ten.
- **÷'s place value** called every round number divided "place value", whatever is under its zeros (30 ÷ 2 = 15).
  That is against its own rule ("round numbers whose fact once the zeros are off is a table fact"). 7,758 such
  divisions had no level, where 30 ÷ 2 is an exchange from the tens (D03) and 130 ÷ 2 a 3-digit division.
- **Cases that kept their example's accident:**
  - DR01 "a table fact with a remainder" read its example's 2-digit number divided, so 7 ÷ 3 = 2 r 1 had no level;
    DF16 likewise (100 ÷ 11 = 9 r 1).
  - DZ03 "a zero in the quotient from a digit smaller than the divisor" read its example's zeros, so 210 ÷ 2 = 105
    had none.
- **A remainder too early:** DP02 and DP03 (÷ 100, ÷ 1000, Medium) held divisions with a remainder, while ÷ 10's waits
  for Advance (DR10). Medium would print 4567 ÷ 100 = 45 r 67.
- **A table with a remainder, its quotient two digits** (21 ÷ 2 = 10 r 1), is short division's (DR04, `DIV.2D1D`), not
  the tables'.
- **Overlaps the document chose, named and not changed.** A number ÷ itself, ÷ 1 and 0 ÷ a number are both a table
  backwards and Medium's own case (2 ÷ 2 is DF04 and DF02), as × has TF01, TF02 and TF12. 23 of `DIV.3D1D`'s are
  Medium's D07 and Hard's DZ04 (302 ÷ 2).
- **`taxonomy.within` refuses a case whose list narrows the skill's list** (DR10's ÷ 10, 100 and 1000 inside
  `DIV.TENS`'s six kinds), where it should keep the values both allow.

M3 is four slices, as M2 was (BUILD-ORDER): M3a, the four straight skills, the remainder its own answer, the division
layout and the mistakes; M3b, the kinds an Advance needs; M3c, `DIV.GROUPS`; M3d, the written methods.

## M3a — straight division built (2026-10-10)

What the measured failures became (ADR 0056), proved by `tests/test_div_levels.py` (25 tests),
`tests/test_div_mistakes.py` (6), two in `tests/test_render.py`, one in `tests/test_md_cases.py` and
`apps/web/tests/s31-straight-division.spec.ts`:
- **Four skills on rungs of their own** (R42–R45, `NUM.OPS.04`), each level its document's straight cases:
  `DIV.FACTS` (Easy to Advance, G2 G2 G2 G3), `DIV.TENS` (G4 ×4), `DIV.2D1D` (G2 G2 G3) and `DIV.3D1D` (G4 ×3). Two
  topics, "Division facts and place value" and "Division by a 1-digit number", untaught until an educator says so.
  Every division in reach has exactly one home among the four and a level in it, in a line and in the division layout.
- **The drawer makes ÷** as it is checked: a divisor, a quotient and a remainder, the number divided made of them
  (`assess/draw_divide.py`), every candidate of a case listed so its last questions are found by reading it. A
  level's size and its skill's mistake list are counted from those lists, never typed. Seven levels hold fewer
  questions than a class's week (216) and say so (`min_items`): `DIV.FACTS` Easy 27, Medium 134 and Hard 36,
  `DIV.TENS` Medium 106, `DIV.2D1D` Easy 46 and Medium 108, `DIV.3D1D` Easy 208.
- **A remainder is an answer of its own**, in a box after "r" only where there is one (`assess/division.py`,
  `verify.division`). In a line, "85 ÷ 4 = □□ r □"; in the division layout, the quotient's boxes one over each digit
  of the number divided, the divisor's bracket and the bar (`answer_space.divided`). Printed through Chromium, the
  key's geometry holds every box; each box is marked against its own key.
- **"How many 6s make 42?"** (DF15), a fact asked in words: its sentence a row of `word_templates.json`, printed and
  shown without the ÷ sign.
- **The 14 mistakes a calculation shows, and × in place of ÷, are rows under ÷**, each predicted from the question's
  own numbers (`assess/div_mistakes.py`) and agreeing with a hand-worked rule on every straight division a level
  prints. A box names every mistake that writes its value there; where two are the same act on these numbers only
  the more particular is predicted (three pairs, measured), as multiplication's are.
- **An old paper's ÷ sums are placed** (`placing.OPERATIONS`): July's 144 ÷ 12 is `DIV.FACTS`'s, and an exact
  division's one answer is keyed by the quotient's mistakes (`misconceptions.predict`).

Found while building, fixed here:
- The first build keyed each box with the first-named mistake. 17 ÷ 5 answered 2 r 3 (swapped) then read as "one
  group short" in the quotient's box and "the remainder added" in the remainder's. Each box now names every match,
  and three same-act pairs predict only their more particular mistake (ADR 0056).
- `DIV.2D1D` and `DIV.3D1D` were given an Advance of Hard's own questions; `engine load` refused it ("bands sharing
  one region"). They have no Advance until M3b, as `MUL.2D1D` had none until M2b; the goal never promised one.
- The test written first read DP06 ("the fact uses one of the zeros") as ÷ 1 digit only. Its label names no
  divisor's size, and the engine's measure held 600 ÷ 50 = 12 and 2000 ÷ 40 = 50; the test now states the label in
  arithmetic. The same test had no line for DF15; it has one now, and checks DF15's sentence never shows the sign.
- `verify.py` reached 404 lines. A stored question's key made stale (`key_problems` and its rules) is its own module,
  `assess/stale.py`; the native kinds' drawing left `draw.py` for `assess/draw_native.py` (draw.py 407 → 355).
- The scenario runner recomputed every answer with `compute`, which refuses a division with a remainder: it now
  recomputes the quotient and the remainder, each against its own box.
- In a line the remainder's boxes followed the paper's layout row; in the division layout they followed the default.
  One rule draws both now.
- `engine audit` on a database refilled with division found four more, each a place that assumed one answer or
  missed the new skill (`test_goal.py`'s invariants):
  - `bank recheck` handed every stored sum's rebuild `compute`'s one answer, which a division with a remainder
    refuses; the rebuild never read it. It now compares every box, the quotient's and the remainder's.
  - `misconceptions.PREDICTED`, the one list of what a predictor computes, did not hold division's, so a mistake
    only one case shows (3 ÷ 5 worked the other way round) read as computed by nothing.
  - The seven small levels above first set `min_items` only under 40, and counted numbers where the bank counts
    questions ("How many 3s make 24?" and 24 ÷ 3 are two): the bank's target is a class's week.
  - An educator's new key for a paper's division was checked with `compute` too, so a paper printing 85 ÷ 4 = 21 r 1
    could never have its key changed; it is checked as the paper writes it now
    (`test_a_papers_division_is_checked_by_its_quotient_and_remainder_as_the_paper_writes_them`). No paper today
    has one (the only ÷ is 144 ÷ 12).
- The first print of "How many 6s make 42?" chose "a sentence alone" by a stem and a shape together, which the 72
  friendly-pairs sums in a fresh bank also have ("Add them in the easiest order."): on paper and on the website they
  would have lost their numbers. A question asked in words now carries its printed sentence (`text`, as a missing
  number does), and only that prints alone
  (`test_a_question_asked_in_words_prints_its_sentence_and_one_with_an_instruction_its_numbers`, which fails on the
  first rule).
- A rehearsal of `bed5038` on a copy of live (run 38049395861) read four ÷ cases as thin (fewer than a worksheet's 12):
  ÷ 1, ÷ itself and 0 ÷ a number held 11 each. The drawer's defaults asked that every special thing a question is be
  what its case is about, so 1 ÷ 1 (÷ itself and ÷ 1) and 0 ÷ 1 (0 divided and ÷ 1) were drawn by no case, though
  placing puts both on Medium. A question that is two of them at once is either case's now: 12 each. ÷ 1000 holds 8
  (2000 to 9000; 1000 ÷ 1000 is a number ÷ itself, which ÷ 1000 is not about), fewer than a worksheet by its own
  numbers.

Ratchets: untyped findings fell in five files, written down in `workflows.json` (`draw.py` 127 → 72, `verify.py`
96 → 81, `render.py` 367 → 348, `misconceptions.py` 236 → 231, `diagnosis.py` 48 → 47); the five new modules have
none. `render_item` measures C901 23 and PLR0915 71 (was 24 and 77).

Proved on `eb0616d`:
- `bin/engine goal md3a-straight-division` on a database built from this tree alone (`bin/testdb fresh`, 26,348
  questions, 2,351 worksheets): 14 of 14 scenarios met (20 asked a level, every answer recomputed, the quotient and
  the remainder each against its own box, 0 off its rule, 0 undiagnosed, 20 distinct), criteria 1,123 passed,
  `bin/check` 27 passed: GOAL ACHIEVED.
- CI green: engine (the whole suite, with coverage and the ratchet), web, browser (every spec, s31 among them).

Rehearsed on a copy of live (run 38050558566, `eb0616d`):
- 554 questions retired outside their level and 6,882 added: M2d2's 4,701 (live has not run `bin/update-live` since
  M0b) and the four's 2,181, each ÷ level filled to what it holds, Easy · Medium · Hard · Advance: `DIV.FACTS` +27 ·
  +134 · +36 · +216, `DIV.TENS` +216 · +106 · +216 · +216, `DIV.2D1D` +46 · +108 · +216, `DIV.3D1D` +208 · +216 ·
  +220.
- The library made 1,445 and retired 746: 3,637 worksheets, 142 of 142 skill-levels ready, 0 problems.
- "MUL_DIV: 251 cases · 160 covered · 88 missing · 3 thin" (M2d2's: 109 · 141 · 1). Missing are M3b–M3d's kinds and
  the cases no level names. Thin: ÷ 1000 (8, by its own numbers), D14 (an unplaced case, 3 of `DIV.FACTS` Advance's
  2-digit divisors) and T16 as before.
- Every `engine live data` check ok after the update. July's 144 ÷ 12 counts on `DIV.FACTS` (1 answer), kept and not
  shown until an educator says the topic is taught.

## M3b — measured before the build (2026-10-10)

M3a is merged and deployed: main `d52c391`, CI, `migrate live` and `deploy engine` green (13:30 UTC). `bin/engine done
md3a-straight-division` on main's tree: 16 of 16 sentences PROVED (the browser test included), 14 of 14 scenarios MET,
2 of 2 criteria PASSED (1,123 tests; `bin/check` 27); "NOT DONE" only for live's migrations, which this container
cannot read and the two runs on main stand for. Its data waits for `bin/update-live`.

M3b's cases were measured on it, each drawn alone (4 asked, 300 tries), then inside its level's own numbers, as the
bank draws it (`cases.on_level`).
- **None of the document's 21 ÷ kind cases draws a question its level can hold:**
  - 10 refuse in a sentence (`CannotMake`). Finding the mistake (C04, C05, C07), a missing digit (Q09, Q10), a
    possible answer (V09), the inverse check (Y10, G20) and the stories (B07, B14–B17) make +, − and × only.
  - 3 raise. The box first and the divisor missing with a remainder draw a division with a remainder, then compute
    one answer for it (Q05, Q13: `ValueError: … two answers`). ÷ 5 as ÷ 10 then doubled is no shortcut the kind
    knows (H09).
  - 2 crash: an estimate takes ×'s path (V04, V10: `KeyError: 'digits'`).
  - 1 draws nothing: the remainder missing (Q12) is no position the drawer asks.
  - Q03 and Q04 draw inside their level's numbers (□ ÷ 12 = 8, 96 ÷ □ = 8) but name no mistake. `verify` keys none
    "about a missing factor or divisor yet", so every one would be undiagnosed.
- **Seven × cases the document places on `MUL.FACTS`'s and `MUL.TENS`'s Advance are held by no level, and nothing
  defers them:**
  - The cases: Q01 and Q02 (a missing factor), Q06 (□ × □ = 49), Y09 (a fact family) and H08 (a fact from a known
    fact); Q14 (the place-value factor missing) and H10 (a fact scaled by ten).
  - How they were missed: M2a gave those levels their straight Advance and M2b gave only the column skills their
    kinds, and no line of BUILD-ORDER names these seven. Q01, Q02, Q06 and Q14 sit on no `MD.*` skill either, so no
    later slice would have built them.
  - Measured today:
    - Q01, Q02 and Q14 draw but name no mistake.
    - Q14 hides the number, not the factor (100 × □ = 58500), and reaches 9500 × 1000 at Grade 4, past the bound
      `MUL.TENS`'s own × 1000 keeps (a number to 2 digits, TP03).
    - Q06 and Y09 draw nothing.
    - H08 and H10 are no shortcut the kind knows.
  - The cause: nothing checks that a level holds every case the document places on it.
  - The M3a rehearsal's "missing are M3b–M3d's kinds" left these seven out.
- **Two placements no question can meet** (slips in the drafted document):
  - Y10 (check a division by multiplying, `fact` NO) is placed on `DIV.FACTS`, whose every question is a table fact
    backwards, so the two together hold nothing. Its example, 96 ÷ 4, is `DIV.2D1D`'s.
  - H09 (÷ 5 as ÷ 10 then doubled) is placed on `DIV.TENS`, whose round numbers are those whose zeros leave a fact.
    Its example, 240 ÷ 5, is not one (24 ÷ 5 is no fact) and is `DIV.3D1D`'s. On `DIV.TENS` it could hold only 350 ÷ 5
    and its like, where the shortcut saves nothing.
- **Q05, the box first (□ = 63 ÷ 9), allows a remainder**, which Q03 and Q04 do not. "□ r □ = 17 ÷ 5" is no sentence
  a school writes.
- **G20 and Y10 are one kind (`inverse_check`) that the document prints two ways**: G20 as "42 ÷ 6 = □ because
  6 × □ = 42", Y10 as "96 ÷ 4 = 24? 24 × 4 = □". Nothing tells the drawer which way to print a case.
- **The native kinds draw their own numbers** (a story's are 2-digit by 1, no table fact), and the case keeps only the
  draws that land in it. On a tables level, almost none would.
- **A scenario counted a question it could not recompute as recomputed.** `_answer_is_right` returns None for a
  missing number, a fact family or any labelled box, and "answers_recomputed" counted None with True.

M3b is two slices (BUILD-ORDER):
- **M3b1:** the tables' and the tens' kinds, × and ÷, with the seven × cases.
- **M3b2:** the column skills' kinds, `DIV.2D1D` and `DIV.3D1D` given their Advance.

## M3b1 — the tables' and the tens' kinds built (2026-10-10)

What the measured failures became (ADR 0057), proved by `tests/test_facts_advance.py` (19 tests) and
`apps/web/tests/s32-facts-advance.spec.ts`:
- **Each Advance holds its document's kind cases:**
  - `MUL.FACTS`: Q01, Q02, Q06, Y09 and H08;
  - `MUL.TENS`: Q14 and H10;
  - `DIV.FACTS`: Q03, Q04, Q05, G20 and B07.
  - Each holds a class's week (216): `DIV.FACTS` Advance 120 straight, 58 missing numbers, 19 of the table backwards
    and 19 of the cost of one.
- **Every kind is drawn on its case's own numbers**, as a straight question is (`draw._pair`): a tables level's are
  table facts, the tens level's round numbers (`assess/facts_kinds.py`). A kind refuses numbers it cannot use (7 × 7
  has no family of four), and they are drawn again.
- **A missing number:**
  - the box first (□ = 63 ÷ 9), keyed by the division's own mistakes;
  - the same number twice (□ × □ = 49), a square;
  - a place-value factor hidden (45 × □ = 4500), the box always on 10, 100 or 1000 and the number shown at most 2
    digits.
  - Its mistakes are drafted from + and −'s: × read as + (8 × □ = 72 → 64), ÷ read as − (□ ÷ 4 = 7 → 11), the table
    one row out, a zero too few, and the two numbers multiplied where the divisor is the box.
- **A fact family of ×** (4 × 7 = 28: 7 × 4, 28 ÷ 4, 28 ÷ 7), **the table backwards through its fact** (42 ÷ 6 = □
  because 6 × □ = 42), **a fact from the row above** (7 × 8 = 56, so 7 × 9), **a fact scaled by ten** (6 × 7, so
  60 × 7 and 600 × 7) and **the cost of one**, a ÷ story whose words are two template rows.
- **A box in the other operation names no "wrong operation"**, whose name is its question's (`core/mistake_names.py`):
  a × family's divisions name the divisor taken away and the rest, never "added instead of multiplying".
- **Printed and on the website**, the table backwards is its two sentences and a shortcut each box after its sentence.
- **Every level holds every case the document places on it, or the slice that will is named** (BUILD-ORDER). Today
  M3b2, M3c, M3d and M4 are waiting.

Found while building, fixed here:
- **The scenario's own check was wrong twice.**
  - A find-the-mistake about a sentence (□ − 14 = 8, found wrong as 6, answer 22) was read as 22 − 14, so every such
    question read wrong in any scenario that drew it.
  - A lattice's cell keyed "03" for 3 × 1 was compared as text.
  - Every box is worked now from its own printed sentence where it is × or ÷, and compared as a number. What a
    scenario cannot work is counted apart (`answers_with_nothing_to_work`), never as recomputed. Over every
    case-based level: 3,062 worked and right, 526 with nothing to work, 0 wrong.
- **"How many digits" answered itself on paper.** "Say how many digits 84 × 18 has, then work it out" (M2b's V03)
  printed the product in as many boxes as it has digits, the school's rule for every answer, so the boxes gave the
  first answer away. Seen on a rendered sheet of the new kinds, not by any test. A how-many-digits question's exact
  answer now has the room the longest such answer needs: a product's two numbers' digits, a quotient's the number
  divided's (M3b2's V04). `test_how_many_digits_is_never_answered_by_the_boxes_it_prints` fails on the old printing.
- **Q14 drew 4000 × □ = 40000.** Its bound on the shorter number's digits cannot bind when the factor is 10, which has
  2 digits itself. It is bound on the number shown now.
- **`MUL.FACTS` Advance's `min_items` of 56** was "all it holds"; once Easy to Hard hold theirs it holds 531, so its
  target is a class's week.
- **M2a's and M3a's level tests drew every case of a level as straight**: they read its straight cases only now, as
  they already did for the column skills' Advance.
- **Ratchets:** typing `draw.one` and `verify._missing_distractors` took their files' untyped findings from 72 to 40
  and from 81 to 55, and typing `answer_space.cells` took its file's from 53 to 33 and `render.py`'s from 348 to 347,
  all written down; the new module has none.
- **A browser spec read the Question bank before it had arrived.** `s31-straight-division.spec.ts` (M3a) failed in CI
  on `6915414`, a commit that touched no web code. Measured:
  - Every page streams in behind its skeleton (`app/(app)/loading.tsx`). When `page.goto` returns, the main area still
    holds the skeleton, and the page's own content is in a hidden block, swapped in 150–280ms later (12 of 12 loads,
    each in a fresh browser context, as every test has one).
  - s31 read the main area's labels once, without waiting, so it read the skeleton. It failed 19 times in 30 locally,
    every run from the twelfth, once the server was warm and fast enough to beat the swap. In CI it ran 84th and
    failed in 481ms.
  - It waits now on what each check is about (the division layout drawn, the remainder's blank shown), as every other
    spec does. Afterwards: 60 of 60 runs passed, s31 and s32 30 each, sixteen of them in the warm regime that had
    failed. s32 waits the same way.
- **Every other read straight after `goto` is sound, as measured.**
  - The seven phone-fit checks (m2-make-papers, s12, s3, s4, u2, u3, workflows) load with `waitUntil: "networkidle"`,
    which waits for 500ms with nothing on the network, longer than the swap. In 40 of 40 loads of eight of their pages,
    each in a fresh context, the page had arrived.
  - u8 reads the hidden block's rows by CSS, and e2e retries its read.
  - The previous commit said the phone-fit checks measured the skeleton. That was read off the code before
    `networkidle` was seen, and is withdrawn.

Proved on `6915414` (database fresh21, built from `fe08360`, whose seeds and drawer are the head's):
`bin/engine goal md3b1-facts-advance` GOAL ACHIEVED.
- 3 of 3 scenarios at 100%: 80 questions, every answer recomputed, none with nothing to work, none off its rule.
- Criteria: 1,126 tests passed, the drafted document 0 faults, and `bin/check` 27 passed.
- Rehearsed on a copy of live, run 38058373712 on `fe19720`, all green:
  - 554 questions retired and 7,042 added; 3,645 worksheets; 142 of 142 levels ready; 0 problems.
  - Only printing and specs changed after it, and `update-live` prints nothing (`library build` renders on demand).

M3b1 merged and live (2026-10-10): main `ad6c967` (#170).
- `migrate live` (run 38064590958) and `deploy engine` (run 38064590947) are green on it.
- `engine done md3b1-facts-advance`, run on a clean worktree of main against a database built from its seeds:
  - 18 of 19 of Nimish's words PROVED there. The 19th, s32, was not proved only because that worktree's website
    could not build: its `node_modules` was a link, and Next's `find_package` failed. s32 passed on the main checkout
    against the same database, and in CI's browser job on `ad6c967`.
  - 3 of 3 scenarios MET, 3 of 3 criteria PASSED.
  - NOT DONE for one reason this container cannot settle: it cannot read the live database's migrations
    (`UndefinedTable`), as for M3a. The `migrate live` run above is the proof they are there.

## M3b2 — measured before the build (2026-10-10)

Measured on main `ad6c967`, through the drawer as merged with M3b1. Each of the 16 kind cases the drafted document
places on `DIV.2D1D`'s and `DIV.3D1D`'s Advance was drawn alone, then on its level's own numbers (`cases.on_level`,
Hard's `within`, since neither skill has an Advance yet).
- **None draws a question its level can hold.**
  - 13 refuse in a sentence: missing digits, finding the mistake, a possible answer, the check, an estimate inside the
    level, and a story's shape.
  - Q12 (the remainder missing) draws nothing.
  - Q13 (the divisor missing with a remainder) raises: it is drawn into the one-answer path, and alone it drew
    8930 ÷ 9.
  - H09 raises: `times_kinds` knows only multiplication's shortcuts.
  - V04 and V10 drawn alone crash with `KeyError: 'digits'`. `times_kinds.sizes` reads a × rule's digits before
    anything asks the operation.
- **The document places only kinds on these two Advance levels, no straight case.** Its grades are G3 (`DIV.2D1D`)
  and G4 (`DIV.3D1D`).
  - `MUL.2D1D`'s Advance also lists straight cases Hard holds. A question lives in one level, so those give Advance
    nothing (named in M2b as not a defect). It is not copied here.

What a box can name, measured over every question each level can hold. Each figure counts questions; an earlier tally
of mine summed predicted values and is not used.
- **A digit missing in the number divided (Q09, 7□ ÷ 4 = 18)** is found by multiplying, 18 × 4.
  - The division's named mistakes run backwards alone leave 66 of 212 2-digit questions naming nothing.
  - The multiplication's named mistakes, with every shown digit kept, leave 140 of 212.
  - The union names every 2-digit question and all but 117 of 4,935 3-digit ones (2.4%, drawn again):
    - the multiplication worked wrong, its digit at the box's place copied ("wrong operation" excepted, ADR 0057);
    - a division mistake that, made with another digit there, gives the quotient shown.
  - 102 of the 212 2-digit boxes have a digit that gives the quotient shown with something over (73 ÷ 4 = 18 r 1).
    "A remainder left out" is no named mistake, and is drafted for Achal, not added.
- **A digit missing in the quotient (Q10, 936 ÷ 3 = 3□2)**: the division's own mistakes, read at the box's place.
  - Any length names all but 1 of 4,321, but takes digits from 933 or 2808 (÷ read as − or ×).
  - A wrong quotient as long as the printed one leaves 483 (11%) naming nothing, drawn again.
  - Every shown digit kept leaves 85%.
  - The rule is "as long as the printed quotient": a wrong quotient that fits the printed boxes puts its digit in the
    box, and one that does not fit says nothing about what is written there.
- **The remainder missing with the quotient printed (Q12, 38 ÷ 5 = 7 r □)**: no named division mistake keeps the
  printed quotient and changes only the remainder, so 556 of 556 name nothing.
  - The box is found by taking away, 38 − 7 × 5. That subtraction's named mistakes, and the multiplication's with the
    product taken away rightly ("wrong operation" excepted), name all 556 2-digit and all 5,555 3-digit questions.
  - The multiplication one row out writes r + 5 there: the division's own "remainder too big", seen from its box.

M3b is three slices now (BUILD-ORDER).
- **M3b2:** the boxes, estimates and checks, nine cases in six kinds, which code checks alone: Q09, Q12, Q13, V09, Y10
  on `DIV.2D1D`; Q10, V04, V10, H09 on `DIV.3D1D`.
- **M3b3:** the mistake found (C04, C05, C07) and the remainder stories (B14–B17).
  - Finding the mistake needs a module of its own: `diagnosis.py` is at 397 lines.
  - The stories need template rows and a mistake no row holds yet: the remainder not rounded up.

## M3b2 — the column skills' boxes, estimates and checks built (2026-10-10)

What the measured failures became (ADR 0058), proved by `tests/test_divide_advance.py` and
`apps/web/tests/s33-divide-advance.spec.ts`:
- **Two Advance levels, the document's kinds alone** (no straight case Hard holds):
  - `DIV.2D1D` (Grade 3): Q09, Q12, Q13, V09, Y10;
  - `DIV.3D1D` (Grade 4): Q10, V04, V10, H09.
  - Each is drawn on its case's own numbers (`assess/divide_kinds.py`, ADR 0057), and each question measures as its
    case.
- **Each box is keyed by the act that finds it** (ADR 0058):
  - a digit in the number divided by the multiplication that finds it, read at the box's place, and by any division
    mistake that gives the quotient shown with another digit;
  - a remainder by the taking away, and its multiplication;
  - a digit in the quotient by the division's own mistakes whose quotient fits the printed boxes;
  - a check by the multiplication; a step by its own division.
  - A box in another operation names no "wrong operation". Every code a box names has one name in every operation,
    so the website names it in a division too.
- **A claimed answer is right or a named mistake's**, one as often as the other: "could it be right?" against one
  group short, and the check against a slip of the division layout.
- **An estimate rounds the number divided to the nearest hundred**, asked only where it divides, or asks how many
  digits the quotient has; its remainder is boxed after "r".

Found while building, fixed here:
- **An estimate of a division drawn alone crashed** (KeyError 'digits'). The estimate's rule read a × level's digits
  before anything asked the operation; it asks the operation first now, and refuses ÷ in a sentence (`bands._estimate`).
- **Seen on a rendered sheet, not by any test:**
  - a digit missing from a division printed in a column under its own sentence, as a multiplication's does;
  - an estimate's remainder box fell to the next line, away from its "r".
  - A division prints as its sentence and one box now, on paper and on the website, and a quotient, its "r" and its
    remainder stay one answer. `test_a_division_is_printed_as_a_division` fails on the old printing.
- **The scenarios' recompute** works the new boxes from their printed numbers, by its own arithmetic:
  - a digit among a division's digits (only one may fit);
  - an estimate's first box, for every operation;
  - a claim's tick;
  - a check worked × before + ("21 × 4 + 2 = □", "605 − 258 = □").
  - It would have called every judged or checked division wrong: it compared an answer box they do not have.
  - Measured over all 26,954 questions of a database built from this tree: 0 read wrong. 1,396 estimates, 171
    checks and 260 claims judged, once not worked, are worked now and right.
- **`render_item` grew past its complexity.** Printing a missing digit is its own function now (a division as its
  sentence, other operations in columns).
- **Ratchets, all written down:** `render_item`'s branches 23 → 19 and statements 71 → 57; `render.py`'s untyped
  findings 347 → 321 and `bands.py`'s 289 → 279. The new module has none.

Proved on `38d4863` (database fresh23, built by `bin/testdb fresh` from this tree):
`bin/engine goal md3b2-divide-advance` GOAL ACHIEVED.
- 2 of 2 scenarios at 100%, 60 questions: every answer recomputed, none with nothing to work, none off its rule, none
  undiagnosed, every case held.
- Criteria: 1,145 tests passed, the drafted document 0 faults, and `bin/check` 27 passed.
- s31, s32 and s33 passed in the browser against the same database.
- Rehearsed on a copy of live, run 38066563963 on `38d4863`, all green:
  - 554 questions retired and 7,479 added; 3,682 worksheets; 144 of 144 skill-levels ready; 0 problems.
  - MUL_DIV: 179 cases covered, 68 missing (M3b3's and later slices'), 4 thin: unplaced patterns random draws happen
    to match, as in M3b1's run.
  - Every live data check ok.

## M3b2 merged (2026-10-10)

- Merged as `76b7a20` (#171). On main: `ci` success (38068583348), `migrate live` success (38070431545), `deploy
  engine` success (38070431558).
- `bin/engine done md3b2-divide-advance` on main's code, against fresh23:
  - 18 of 18 of Nimish's sentences PROVED, s33 among them in the browser;
  - 2 of 2 scenarios MET;
  - 3 of 3 criteria PASSED: 1,145 tests, the drafted document 0 faults, `bin/check` 27 passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as for M3a and M3b1; the
    `migrate live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live` (below: live has had none since before M2a).

## M3b3 — measured before the build (2026-10-10; kept for it, NY1 and NY2 go first)

On each level's own numbers (`draw_divide.every` within the level's shape, the drawer's own list):
- `DIV.2D1D` holds 331 divisions, every quotient 2 digits, 254 with a remainder. C05 (a remainder too big) shows on
  254 of them, all with a remainder.
- `DIV.3D1D` holds 7,112 (3,541 two-digit quotients, 3,571 three-digit). C04 (the zero left out of the quotient)
  shows on 1,170 (967 with a remainder); C07 (the last digit never brought down) on 7,035 (5,559 with a remainder).
- No "which step went wrong" tick: for C07 its answer would always be "bring down", which a child ticking the same box
  every time would score (the rule `diagnosis.asks_where` keeps). The step is said in the why.
- B14 to B17 (a remainder dropped, rounded up, asked, or both) on `DIV.2D1D`'s 254 divisions with a remainder: every
  question names a mistake, each by the act that finds its answer.
- Printing: `find_mistake` and `word_1step` print one answer box; a division's remainder needs its own.
- The scenarios' recompute checks a division's two boxes; a story's answer by what it does with its remainder needs
  its own.
- Names: 39 names and repair hints of mistakes are written in code beside their predictors. 4 names and 6 hints
  differ from the rows the school edits (`supabase/seed/misconceptions.json`); the hints are read only by a test. A
  division mistake has no name in code, so a ÷ worked answer's "why" would print a code.

## NY — measured before the build (2026-10-10)

Nimish: "I'm not even now able to figure out what all papers I need to validate or for Achal to validate … I'm not
seeing any of the multiplication, division." What stands between him and both:

- **Live has none of the multiplication and division** (rehearsal 38066563963, a copy of live taken 16:11 UTC):
  - `MUL.1D` was still live's only multiplication skill;
  - the update moved 606 questions off it and added 7,479, 6,056 of them × or ÷.
  - So `bin/update-live` has not run on live since before M2a.
  - On the same copy, each child's skills were not what their answers say (12 missing, 1 stale, 11 with other counts)
    until update-live's `engine graph` ran.
- **No screen switches a topic on, and every reload switches it back off.**
  - Nothing in `apps/web` writes `topic.taught`.
  - On a copy built from this tree (ny1m), `DIVCOL` set taught in the database was off again after `bin/engine load`:
    the loader copies `taught` from `supabase/seed/topics.json` every time.
  - Six topics are off there: REASON, MULMODEL, MULFACT, MULCOL, DIVFACT, DIVCOL. Their 11 skill sets are on no
    screen.
- **Nor can they be approved.**
  - The approval page and Today's count read only taught topics (`skillSets()`, `queries-today.ts`).
  - So the eleven can be neither seen nor approved; "untaught until an educator says so" has no place to say it.
- **Nothing is anyone's to do.** Every count on Today is the school's:
  - the signed-in person's role is loaded (`lib/auth.ts`) and read nowhere;
  - sign-in lands on Curriculum, not Today;
  - the design's "Achal confirms the doubtful" (ARCHITECTURE.md, N9) is no route.
- **What Achal is asked is nowhere on the site:**
  - the drafted taxonomy (a shared doc) and its twelve assumptions A1 to A12;
  - the decisions drafted for him in eight goal files (S24, AS1, M2a, M2b, M2d2, M3a, M3b1, M3b2);
  - their pull requests.
- **The queue is built to shrink, but nothing shows it** (for NY2):
  - a kind earns trust at 95% agreement over its last fifty checks (ADR 0032, wired 2026-09-22);
  - every wrong and blank waits for a person (ADR 0029);
  - the last record has no kind trusted;
  - answers already waiting are marked again only by a command;
  - no screen shows the waiting count over time, or how far a kind is from trust.

## NY1 — what waits on a person, and who it is for, built (2026-10-10)

ADR 0059. Goal `goals/ny1-needs-you.yaml`.

- **A topic is switched on or off by a person.**
  - Curriculum lists the topics not taught yet, each with its skills, and switches one on in the person's name.
  - Switching a taught one off is folded away.
  - `topic.taught_by` and `taught_at` say who and when (migration 20261102090000). `engine load` keeps a person's
    switch and follows the rows only where no person has spoken (`core/topics.py`).
- **A skill is approved before its topic is on.**
  - The approval page and a skill's own page read every skill (`skillSets({ untaught: true })`), each saying "Not
    taught yet".
  - Today, Curriculum and the approval page count the same waiting skills (`queries-people.skillsWaiting`).
- **Today is in two parts, "For you" and "For others".**
  - Each card says whose it is, from `people.decides` (drafted from ARCHITECTURE.md, by the staff list's roles): by
    name, or that no one on the staff list has that role yet.
  - New cards: topics not taught yet, and one card of questions per role.
  - Sign-in lands on Today.
- **Questions for a person are rows** (`ask`, `core/asks.py`).
  - 22 drafted: the taxonomy, A1 to A12, the eight slices' decisions drafted for Achal, and whether a topic is taught
    for the whole school.
  - Each is answered on `/asks`, agreed or corrected, in the person's name.
  - A load never touches an answered one. `engine asks` prints them; `bin/update-live` and its rehearsal run it.
- **`loaders.py` is under its ceiling.** Its reference checks are their own module (`core/references.py`), so it
  dropped off the frozen list (405 → 368 lines).
- **Tests updated to the new rule, not loosened:** Today's and Curriculum's count of waiting skills is every waiting
  skill (`u1-today`, `u12-curriculum-table`).

Run on the copy `ny1m` (fresh23's rows, this migration applied):
- engine: `test_asks.py`, `test_topics.py`, `test_loaders.py`, `test_approval.py`, `test_layout.py`,
  `test_update_live.py` — 34 passed;
- browser: u13 (4), gate (12), u1 (3), u5, u12, screens, e2e, s2, s33, u10, u11, workflows — 80 passed;
- `bin/check` 27 passed.

## NY1 merged and live (2026-10-10)

- Merged as `d66bb35` (#172). On main: `ci` success (38074090256), `migrate live` success (38075174968), `deploy engine`
  success (38075175020). The `ask` table and the topic switch's columns are on live.
- `bin/engine done ny1-needs-you` on main's code (copy ny1m):
  - 10 of 10 of Nimish's sentences PROVED;
  - 3 of 3 criteria PASSED: 24 engine tests, 26 browser tests, `bin/check` 27.
  - Its live line cannot read live from here, as before.
- Rehearsed on a copy of live (run 38072254406, on `af10d0d`): the migration applied; `ask` 22 rows, all waiting for the
  specialist; 144 of 144 skill-levels ready, 0 problems; every after-check ok.
- On a copy built from this tree: browser 171 of 171; engine 2,136 passed and 2 failed, both in
  `test_every_answer.py`.
  - The two fail the same way on main's code.
  - Cause: the fixture made an ADD.2D2D worksheet from the first estimates by key, whatever their operation. Since
    multiplication's estimates joined the bank, one of them is a ×.
  - The bank is drawn unseeded (`bank.py:241`), so CI's database, built afresh, held different questions and passed.
  - Fixed in NY2: the fixture takes only + and − questions (9 of 9 pass on fresh23).
- Its rows wait for `bin/update-live`: the 22 questions, and Curriculum's switch, which needs × and ÷ on live first.

## NY2 — measured before the build (2026-10-10)

Nimish: "The system keeps learning from the number of data points that we keep validating, and the number of data
points that we then need to validate becomes lower."

- **Trust has two owners, which can disagree.**
  - The engine decides a kind's trust in Python (`profiles.kind_trust`), over the last 50 checks it stood behind,
    ordered by when the paper was read and then by question key.
  - The website decides it again in its own SQL (`queries-read.readerReport`), its 50 written in again, ordered by
    when the paper was read alone.
  - Every answer of one paper shares that moment, so where the 50th check falls inside a paper the website's window is
    arbitrary.
  - The window is written in code twice, not a row.
- **A kind earning trust leaves its waiting answers waiting.** An answer held only for its kind's trust ("read as a
  right answer; a person checks every answer of this kind until…") is marked again only by `engine legacy remark` or
  `POST /mark`, which nothing calls.
- **Checks arrive two ways:**
  - a typed reading, through the engine (`/capture/correct`);
  - a signed-off paper, through the website's SQL (`confirm_results`).
- **No screen shows the queue week by week, or how far a kind is from trust.**
- **Live, read only** (engine logs run 38074135981, 2026-10-10 ~18:02 UTC):
  - nothing waits for a person; 867 old-paper answers on 71 papers and 420 printed-paper answers on 36 are checked;
  - nothing has been read since 2026-09-29;
  - where the reader stood behind a reading it was right 698 times in 906 (77%), and 208 times wrong without saying so;
  - no kind is trusted. Its last 50, right:

    | Kind | Right |
    |---|---|
    | columns | 47 of 50 |
    | old papers' stories | 41 of 50 |
    | sums in a line | 38 of 50 |
    | two-step stories | 37 of 50 |
    | old papers' sums | 35 of 50 |
    | old papers' missing numbers | 29 of 50 |

  - So the queue will fall only as fast as the reader gets more right. NY2 makes that visible; it cannot make it so.

## NY2 — the queue shrinks, and a person sees whether it does, built (2026-10-10)

ADR 0060. Goal `goals/ny2-the-queue-shrinks.yaml`.

- **One rule for the reader's trust, in the database** (migration 20261103090000).
  - `checks_to_trust()` and the `kind_trust` view give each kind its newest checks the reader stood behind, how many
    matched, whether that is trust, and the right checks still needed.
  - Checks are ordered by when the paper was read, then by question, then by answer.
  - The window is a row, `marking.agreement_window` (50).
  - The engine (`profiles.kind_trust`), `engine read report` and the website (`readerReport`, Today) all read it. The
    Python rule and the website's own SQL are gone, and so are the fifties written into code.
- **A check marks again what trust now settles** (`again.trusted`): every candidate of every trusted kind, from what
  was read.
  - A right answer held only for trust settles. A wrong or a blank still waits (ADR 0029). A spot-checked one still
    waits.
  - `POST /capture/correct` runs it in the same transaction as the check.
  - The website asks `POST /capture/trusted` after a paper is signed off. If the engine is not answering, the sign-off
    stands and the page says the answers leave the queue at the next check.
- **Marking again starts from what the reader said.** `mark_read` removes an earlier hold's reason and guess before it
  marks. Without that, an answer that settled went on saying a person checks it, and the website went on treating it
  as waiting. The test fails without the fix and passes with it.
- **Today shows "Is the queue shrinking?":**
  - the last eight weeks of answers read: settled by the engine alone, checked by a person, still waiting, and the
    share that needed a person (`answer_standing`);
  - how many kinds are trusted, and how many more right checks the nearest one needs.
- **Marking's "By kind of question" ends with "Checks to trust":** "trusted", or how many more.

Run on the copy `ny1m` (fresh23's rows, NY1's and this migration applied):
- engine: `test_profiles.py`, `test_read_again.py`, `test_every_answer.py`, `test_each_answer.py`, `test_legacy.py`,
  `api/test_capture_routes.py`, `test_crops.py`, `test_gold.py`, `test_keys.py`, `test_contract.py`,
  `test_layout.py` — 139 passed;
- browser: u14 (2), u1 (3), u13 (4), u10 (3), s4 (16) — 28 passed;
- `bin/check` 27 passed.
- CI's whole engine suite on `8dd2f26`: 2,142 passed, 1 failed, `test_roles.py`. The website's exact list of the
  functions it may call lacked `checks_to_trust`, which the `kind_trust` view runs as the website. Added to the list,
  as `mistake_name` was: the list stays exact.

## NY2 merged and live (2026-10-10)

- Merged as `5195c89` (#173). `bin/engine done ny2-the-queue-shrinks` on main's code (copy ny1m):
  - 6 of 6 of Nimish's sentences PROVED;
  - 3 of 3 criteria PASSED: 115 engine tests, 28 browser tests, `bin/check` 27;
  - its live line cannot read live from here, as before.
- **CI on main failed once, on two bank tests NY2 does not touch** (`test_bank.py`: 2 kept of 3). The same tree had
  passed on the PR's head (716fe09). Cause: a test database's bank is drawn afresh, unseeded, so a test's fixed sum
  was sometimes stored already. Fixed in #174 (`7a0af06`).
- **Live, meanwhile:** Vercel deployed main's website on the merge, while `migrate live` and `deploy engine` waited for
  CI and were skipped. Today and Marking on live read the `kind_trust` view live did not have, from about 19:47 UTC
  until the migration. The migration was not pushed by hand: `migrate.yml` keeps live's database waiting for green CI
  (goals/p0-live-changes-wait-for-ci.yaml).
- One re-run of the failed job passed (run 38080955970, attempt 2). Then `migrate live` (38083876001) and `deploy
  engine` (38083875988) succeeded.
- **The gap, not closed from the repository:** the website deploys on merge, before CI; the database and the engine
  wait for CI. A red main leaves the website ahead of its database. Closing it needs Vercel to deploy production only
  after CI, or the website deployed by the same workflow after the migration. Both are Nimish's Vercel settings.

## M3b3 — names, measured before the build (2026-10-10)

- The code carries a copy of 41 mistakes' names and repair hints beside their predictors
  (`misconceptions.py`'s tables, `mul_mistakes.PREDICTORS`, `written_methods.NAMES`).
- Two names say otherwise than the rows the school edits: `M_ZERO_DROPPED` ("Drops a placeholder zero when writing the
  answer" against the row's "Drops a leading, trailing or internal zero when writing the answer") and
  `M_CARRY_ALWAYS_1` ("Carries 1 when the column total is 20 or more" against "Assumes a carry is always 1"). Six
  repair hints differ.
- Who reads the copies:
  - a worked answer's "why" prints its name as the rubric (`diagnosis._why`), shown on the Question bank as "Looks for",
    beside the planted mistake named from its row — two names for one mistake on one page, where they differ;
  - Jev's shortlist is shown the code's names (`mistake_guess.options`);
  - the repair hints are read by a test alone (`misconceptions.catalogue`).
- A division's mistakes have no name in code, so a worked division's "why" would print a code.
- So the rows are the one source (rule 1): the copies go, the "why" names no mistake, and Jev is shown the rows'
  names. Jev's input changes for `M_ZERO_DROPPED` alone; `engine eval mistake_guess` is run after the deploy.

## M3b3 — the mistake found in a division, and stories with something left over, built (2026-10-10)

ADR 0061. Goal `goals/md3b3-divide-mistakes-and-stories.yaml`.

- **Finding the mistake in a division** (`assess/divide_found.py`, a module of its own: `diagnosis.py` is at 396).
  - C05 on DIV.2D1D; C04 and C07 on DIV.3D1D. Each worked answer is its planted mistake's own prediction on the
    level's numbers.
  - A question is made wherever the mistake shows, and nowhere else: 254, 1,170 and 7,035, as measured.
  - The right answer goes in the division's own boxes (`division.boxes`). The "why" names no mistake, and no step is
    ticked.
- **Stories that divide** (`assess/divide_stories.py`; B07's exact story moved there from `facts_kinds.py`).
  - B14 to B17 on DIV.2D1D: the full boxes, the rickshaws needed, how many are left over, or both.
  - Their words are eight template rows, two for each use, each saying what it does with the remainder. The use is
    in the story's spec, so it is part of its key.
  - Each box names its own mistakes:
    - the division's quotient box, or its remainder's;
    - for the rickshaws, `M_REMAINDER_NOT_ROUNDED_UP` (a new row, drafted for Achal) and each division slip rounded
      up as the child would.
  - The scenarios recompute a story's answer by what it does with its remainder (`scenarios.USED`).
- **Printed:** a story that asks both, and the right answer to a worked division, print the quotient's box, its "r" and
  the remainder's box as one answer (`answer_space.answered`).
- **A mistake's words are its row alone:**
  - the code's tables hold predictors only; `written_methods.NAMES` and `misconceptions.catalogue` are gone;
  - the "why" rubric names no mistake, and the Question bank shows that same sentence for questions stored before;
  - Jev is shown the rows' names (`mistake_guess.options(conn, op)`).
- **The two levels list the new cases** (`skill_sets.json`), and DIV.2D1D lists the new mistake. Every placement the
  document makes on the two levels is held (`test_divide_advance.py`); nothing waits for M3b3 in `test_facts_advance.py`.
- **Ratchets:** pyright's unannotated counts fell, written down: `diagnosis.py` 47 → 42, `misconceptions.py`
  231 → 224, `render.py` 321 → 317. `render.py` is at 393 lines.
- **Fixed with it:**
  - `test_bank.py` draws only sums the bank does not already hold. It failed CI on main for the NY2 merge; reproduced
    on a copy with 478 − 87 stored.
  - The audit's measure of what a level's own numbers can show (`spec.known_misconceptions`) draws at least eight
    questions of each case (`SAMPLE_PER_CASE`). Its 40 per level, shared among DIV.2D1D's ten cases, left too few of
    the remainder missing to show the subtraction mistakes its box names.

Run on the copy `ny1m`, after `engine load`, `bank levels --apply` and `bank refill`:
- M3b3's own tests (`test_divide_found.py`, `test_divide_stories.py`, `test_mistake_rows.py`, `test_divide_advance.py`,
  `test_facts_advance.py`, `test_mistake_guess.py`, `test_misconceptions.py`): 80 passed;
- the goal's criteria list: 1,216 passed, 2 failed before these two fixes (a test still unpacking the old tuples, and
  the audit's sample); `test_goal.py`, `test_mul_mistakes.py`, `test_spec.py` after them: 64 passed;
- browser: `s33-divide-advance.spec.ts` 2 passed (a worked division's page names its mistake by its row);
- `research/md_taxonomy.py --check`: 0 faults.


## M3b3 merged and live (2026-10-10)

- Merged as `0492849` (#174), at the head CI and the rehearsal on a copy of live had passed (`f9f5804`: ci 38085843773,
  rehearse-update-live 38086482405).
- Main: `ci` green (38087656889), then `migrate live` (38089427451) and `deploy engine` (38089427383) succeeded.
- `engine eval mistake_guess` (v1, Jev shown the rows' names), on the server after the deploy (run 38089777698): the right
  mistake first 70/120, among the three 109/120, slips called NONE 30/30, slips given a mistake 0; every bar met
  (DECISIONS-LOG.md). Before: 108/120 among the three (run 36519894157).
- `bin/engine done md3b3-divide-mistakes-and-stories` on main's code (a worktree at `0492849` with its own engine and
  website installs), against `m3b3done` (`ny1m` and main's `engine load`):
  - 15 of 15 of Nimish's sentences PROVED, s33 among them in the browser;
  - 2 of 2 scenarios MET;
  - 4 of 4 criteria PASSED: 1,177 tests, the drafted document 0 faults, s33 2 passed, `bin/check` 27 passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as for M3a to M3b2; the
    `migrate live` run above is the proof they are there.
  - The first run's s33 could not start the website: the worktree linked the branch's `node_modules`, which Next
    refuses outside its project. Installed in the worktree, it passed.

## M3c — measured before the build (2026-10-10)

`DIV.GROUPS`' nine cases, each drawn alone through today's drawer on a level shaped as `MUL.MODELS`' (12 asked, 300
tries each; `groups` and `size` 2 to 6):
- G15 (dots shared into rings), G16 (dots ringed in groups), G19 (an array divided): 0 of 12, and nothing said.
  `equal_groups` makes a × picture whatever operation the case asks, and the case's own match refuses each one.
- G17 (taken away again and again to 0): 0 of 12, and nothing said. It prints as a straight division, which is not its
  method. The draft filed it as a `bare_sum`, which every reader of that kind takes for "15 ÷ 3 = ___": the defect
  ADR 0054 found in skip counting.
- G18 (jumps back on a number line): `KeyError: 'hi'`, not a sentence. The number line hands ÷ to the + and − jumps.
- B02, B03, B05, B24 (stories of sharing, grouping, an array, "each"): `CannotMake`, in a sentence. No ÷ template has
  their shape and uses nothing left over.
- Nothing bounds a story's numbers. A model skill carries no `within` (ADR 0054: placing would hold 12 ÷ 3 in two
  skills), and B02's match alone allows 18,276 exact divisions with quotients up to 4,999. The four cases' own examples
  are a table read backwards (24 ÷ 4, 24 ÷ 6, 35 ÷ 5, 30 ÷ 5); their rows do not say so.
- **A right answer would count for the wrong skills.** `skills.by_kind` gives every `equal_groups` question
  multiplication and addition (`NUM.OPS.03`, `NUM.OPS.01`: Grade 1's groups added again). A sharing picture would use
  `NUM.OPS.04`, `NUM.OPS.03` and `NUM.OPS.01`, and `confirm_results` makes evidence for every skill a question uses.
- `DIV.GROUPS` is no row: no rung, no topic. The mistakes a child makes with the models (counting them all, writing the
  number the question gives for the one it asks, counting the start as a jump) are no rows.
- `M_KEYWORD_OVERGENERALISED` has one row, for any operation, whose repair hint is about subtraction ("Give a
  non-subtraction context containing the keyword"). The drafted table names it on ÷ stories that say "each".
- A story template names the mistake its wrong operation is in a field called `added`, read as "adding its two
  numbers". In a story that divides, the wrong operation is multiplying.

## M3c — division's first models, built (2026-10-10)

ADR 0062. Goal `goals/md3c-division-models.yaml`.

- **The models** (`assess/divide_models.py`). Each is made from its level's `groups` and `size`, as `MUL.MODELS`' are,
  and each is the exact division `a ÷ b`.
  - Equal groups that divide, by their case's method:
    - SHARING (G15): the dots loose, the rings empty;
    - GROUPING (G16): the dots loose, no ring;
    - ARRAY (G19): read as in all ÷ rows = in each row, in three labelled boxes.

    Asked for any other operation, equal groups refuse in a sentence (`bands._groups`).
  - Jumps back to 0 on a number line (G18): a mark at every number, its start said, no jump drawn.
  - A number taken away again and again to 0 (G17): a kind of its own, `repeated_subtraction`, printed whole from its
    numbers. Its row is corrected in `research/md_rows.py` and written again by `research/md_taxonomy.py`.
- **The mistakes.** Three are new, each a row drafted for Achal: `M_DIV_ALL_COUNTED`, `M_DIV_GROUPS_FOR_SIZE`,
  `M_DIV_START_COUNTED`. They are named beside `M_WRONG_OP` (÷: multiplied) and `M_DIV_SUBTRACTED`, each where its act
  can happen. The drafted document's error table holds all three, computed.
- **The stories** (B02, B03, B05, B24). Eight template rows, two per shape: the grouping stories never say "each", and
  the "each" stories do. They divide a table to 10 read backwards, as their four rows now say (`fact`, `fact_group`).
  - A template names the mistake its other operation is: `wrong_op_as`, which was `added`, read as "adding" and wrong
    for a division.
  - "5 for each child" multiplied is `M_KEYWORD_OVERGENERALISED`, which has a ÷ row now; the "any" row's hint is about
    subtraction.
- **A right answer counts for division alone.** `skills.by_kind` may give a kind's skills per operation: equal groups
  that multiply keep multiplication and addition, and equal groups that divide get division alone.
- **Found and fixed with it.** `verify.to_item` wrote a story's other operation as `a + b` for every operation but +.
  - For ÷ that named adding as "multiplied".
  - For a + or − story with a 0 or a 1, it keyed the right answer, or another mistake's, as the wrong operation.
  - The predictors already give each operation's own; the override is gone.
- **Rows.**
  - Rung `R46` (G2, `NUM.OPS.04`);
  - skill set `DIV.GROUPS` (four levels, every one Grade 2, no `within`);
  - topic Division models, untaught;
  - four mistake rows, eight template rows, and the asks row of the decisions drafted for Achal.
  - No migration: the set, rung, topic and mistakes are new rows, and cases are written again on every load.
- **Website.**
  - The drawn kinds (tally, equal groups, skip counting, the square, repeated subtraction) moved from `question.tsx`
    (382 of 400 lines) to `pictures.tsx` as `Drawn`, where the engine's `pictures.py` keeps the paper's.
  - The ÷ pictures and the subtraction drawn there.

Run on the copy `m3c` (`ny1m`, then `engine load` and `bank refill`: DIV.GROUPS +112 questions, 0 retired anywhere):
- `bin/engine goal md3c-division-models`: 4 of 4 scenarios met the bar completely (24, 24, 16 and 48 asked, each
  produced, recomputed, on its rule, diagnosed and distinct);
- `s34-division-models.spec.ts` passed; `research/md_taxonomy.py --check` 0 faults; `bin/check` 27 passed;
- the criteria's test list named a file that does not exist (`test_skills.py`); it now names the files that test
  skills. Run again: 1,118 passed, 1 failed, `test_loaders.py` holding the seed's exact counts (37 rungs, 37 skill
  sets); R46 and DIV.GROUPS make 38 of each, written down, and the file passes (12).

Rehearsed on a copy of live (rehearse-update-live 38089159350 on `f4ba7bc`, success). Live has not run `bin/update-live`
since before M2a, so this is everything since, at once:
- `engine load`: 39 skill sets, 40 rungs, 13 topics, 24 asks (Achal's M3c question among them), 109 mistakes;
- `bank rehome` moved 606 questions and retired 258 whose story's shape is unnamed, removing `MUL.1D` and its rung;
  `bank refill` retired 554 outside their level and added 7,590, DIV.GROUPS 24, 24, 16 and 48 of them;
- `library build` made 1,530 and retired 746; `library check`: 3,722 worksheets, 148 of 148 skill-levels ready, 0
  problems; every check after reads ok.
- Seen, not explained from here: answers kept but not shown (their topic untaught) were 92 on `MUL.1D` before and 93
  after (DIV.FACTS 1, MUL.2D1D 21, MUL.FACTS 59, MUL.TENS 12). `bank rehome` (M2c) places an answered question by its
  shape, so one × question answered on a taught topic's skill would now wait with them. The checks that every
  signed-off answer counts on a skill and every child's skills are rebuilt both read ok. Telling which answer it is
  needs live's rows.

CI on `fff76a9` (ci 38090232676): web and browser passed, the engine's suite 2,174 passed and 1 failed:
`test_facts_advance.py` keeps a line for every slice the document's placements wait for, and fails once a slice holds
all of them, so the line goes. DIV.GROUPS held every case placed on it, so its "waits for M3c" line is gone. The goal's
criteria did not run that file, which is why it was not seen here; it runs them now. Reproduced on `m3c` (1 failed),
then the file passes (20).

## M3c merged and live (2026-10-10)

- Merged as `97cb9cc` (#175), at the head CI had passed (`6350e65`: ci 38091634852). The rehearsal on a copy of live
  ran on `f4ba7bc` (38089159350); after it only documents and tests changed.
- Main: `ci` green (38093378655), then `migrate live` (38094297507) and `deploy engine` (38094297496) succeeded.
- `bin/engine done md3c-division-models` on main's code (the worktree at `97cb9cc`), against `m3c`:
  - 15 of 15 of Nimish's sentences PROVED, s34 among them in the browser;
  - 4 of 4 scenarios MET;
  - 4 of 4 criteria PASSED: 1,139 tests, the drafted document 0 faults, s34 1 passed, `bin/check` 27 passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as for M3a to M3b3; the
    `migrate live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a.

## M3d — measured before the build (2026-10-10)

Each method case drawn alone on its skill's Hard level (main `0492849` with M3c's code; scratchpad `measure_m3d.py`, 6
asked, 300 tries each):
- G21, partitioning the number divided (DIV.2D1D's methods): refused, "break_apart makes + and − questions, not ÷".
- G22, chunking (both skills): 0 of 6, nothing said. G24, long division (DIV.3D1D): 0 of 6, nothing said: a division in
  columns by one digit is measured as short division, so nothing the drawer prints is long division.
- G23, short division (both): 6 of 6, printed as the plain division layout (the quotient's boxes and the remainder's):
  no exchange written small, none read.
- G25, halving (DIV.2D1D's methods and MD.MENTAL's Hard): 0 of 6, nothing said.
- No level of DIV.2D1D or DIV.3D1D lists `methods` (ADR 0055's fair shares): every division prints in a line or in the
  division layout.

The drafted document, read against itself:
- **DIV.3D1D prints in no line.** Its methods column is G22, G23, G24, against A2 ("division prints in a line by
  default", from the school's July papers). Today DIV.3D1D does print in a line, because no level lists methods;
  following the column would take the line away.
- **Halving has two homes.** G25 is on DIV.2D1D's methods and MD.MENTAL's Hard. A1 lists division's written methods
  as "in a line, short division, long division, partitioning the number and chunking", not halving; doubling, its
  mirror, is MD.MENTAL's alone.
- **Chunking cannot print a 3-digit division.** It takes ten lots at a time (`md_taxonomy.chunks`), and the document
  places it on DIV.3D1D: 588 ÷ 3 is nineteen take-aways of 30 and then 6, 998 ÷ 2 forty-nine.
- **D02 is a case and a method at once**, on DIV.2D1D's Easy and its methods, as T02 was before ADR 0055 made it
  MUL.2D1D's in-a-line method.

Charges: a long division's take-away slips name subtraction's mistakes, `M_FACT_PM1` among them, which has a row for +
and one for −; `skills.charges` charges another operation's mistake only when it has one row, so it would count against
division.

## M3d — division's written methods, built (2026-10-10)

ADR 0063. Goal `goals/md3d-division-methods.yaml`.

- **The methods** (`assess/divide_methods.py`, every step a box with its own key):
  - partitioning the number divided: the most tens of lots of the divisor, then the rest, each divided, then the total
    (72 ÷ 4: 40 ÷ 4 = 10, 32 ÷ 4 = 8, 18); a part that leaves a remainder has its box after "r";
  - chunking: for each place of the quotient, largest first, the lots, what they take away and what is left (96 ÷ 4:
    20, 80, 16; 4, 16, 0; 24);
  - long division: the first number divided is the leading digits, as few as reach the divisor; then each product and
    each number left with its digit brought down (516 ÷ 4: 4, 11, 8, 36, 36, 0; 129);
  - short division is the division layout, a small box before every digit but the first, read where a remainder is
    exchanged into it (72 ÷ 4: 3; 588 ÷ 3: 2, then 1). A new print layout row, `2026-10-10`, draws them.
  - Printed by `assess/divide_pages.py` (partitioning by `written_pages`), drawn on the website by
    `components/methods.tsx`. `assess/written.py` names every written method of both operations.
- **The levels' methods** (`skill_sets.json`): DIV.2D1D D02, G21, G22, G23; DIV.3D1D D15, G22, G23, G24. DIV.2D1D's
  Easy holds D01 alone.
- **The mistakes, from the numbers, no new code.**
  - The zero left out of a part's or a lot's quotient, carried into the total.
  - One group short, and a digit not brought down.
  - An exchange's small division's remainder slips.
  - A product's multiplication slips, and a take-away's subtraction slips. Never the wrong operation, whose name on a
    division is the division's.
  - The skills' mistake lists gain what the steps name; migration `20261104090000` carries them to a database loaded
    before.
- **What a slip counts against.** `skills.charges` charges a mistake with no row for the question's operation to the one
  other operation it has a row for among those the question carries out. Long division and chunking multiply and take
  away (`skills.by_method`). The copy's 26,102 stored questions with mistakes: none is charged otherwise.
- **Corrected at the source** (`research/md_taxonomy.py`, 252 cases): D15 (A2); chunking by place; halving MD.MENTAL's
  alone (M4); D01 and D02 as T01 and T02; G21, G22, G24 name the kinds that print them; a straight division accepts
  every written method of its operation.
- **The scenarios recompute every step** from the two numbers (`scenarios._division_steps`): on every number from 10 to
  999 by 2 to 9, 23,222 written divisions and every division layout agree.
- **Found by the local rehearsal, fixed at the cause:**
  - The refill topped a level up per case, so a level the bank filled before it listed methods kept its old ways.
    DIV.2D1D's Easy held 46 questions, all in a line or the division layout. Now each case is topped up in every way its
    level prints it (`refill.top_up`, `draw.split`): Easy gained 12 partitioning and 11 chunking.
  - A division layout with exchange boxes kept the key of the layout it replaced, so the retired ones blocked their own
    numbers for good (Medium refilled with no division layout at all). Now its spec says where its exchanges are
    (`exchanged`), which makes it a question of its own; the inventory rebuilds it with them.
  - A sample sheet read a chunking question back and found no working space for it (`layout.WORKING_LINES`).
- **Split as files passed 400 lines:** `assess/straight_pages.py` out of `render.py` (403), `assess/draw_pair.py` out of
  `draw.py` (397 before). A division's numbers now pass the method's own check (`draw_pair.sets_out`). Untyped findings
  fell: `answer_space.py` 33 to 0, `render.py` 317 to 314.
- **Rows:** 252 case rows (D15 added), the levels' methods, the layout row, `skills.by_method`, the two mistake lists,
  Achal's question (`md3d-division-methods`).

Rehearsed on the copy `m3d` (`m3c`, then the migration, `engine load`, `bank levels --apply`, `bank refill`,
`library build`, as `bin/update-live` runs them):
- the migration updated 2 skill sets; `bank levels --apply` left DIV.2D1D and DIV.3D1D waiting for one approval each;
- `bank refill` retired 292 questions (division layouts printed before their exchanges had boxes) and added 614:
  DIV.2D1D Easy 23, Medium 58, Hard 126; DIV.3D1D Easy 104, Medium 162, Hard 141. No multiplication level was short of
  a method;
- every level holds every method it lists (DIV.2D1D Easy: 23 in a line, 23 in the layout, 12 partitioned, 11 chunked);
- `library build` made 211 worksheets and retired 130; `library check`: 2,478 worksheets, 148 of 148 skill-levels
  ready, 0 problems; MUL_DIV 252 cases, 200 covered, 49 missing (M4's and the unplaced), 3 thin;
- the goal's six scenarios met the bar completely: 16, 24, 24, 16, 24 and 40 asked, each produced, recomputed step by
  step, on its rule, diagnosed and distinct, every listed case held.

## M3d merged and live (2026-10-11)

- Merged as `d75767c` (#176), at the head CI had passed (`4e5148d`: ci 38097090416). The rehearsal on a copy of live
  ran on the same head (38097095667). CI's first run (`733c0ae`) failed 3 of 2,195 tests M3d had not carried: the
  taxonomy test's count of 251 cases (now 252) and the rehome tests' own list of straight kinds (now with chunking and
  long division). Each was reproduced on a copy and fixed in the PR.
- Main: `ci` green (38098163028), then `migrate live` (38099162995) and `deploy engine` (38099162961) succeeded.
- `bin/engine done md3d-division-methods` on main's code (the worktree at `d75767c`), against a copy of `m3d`:
  - 21 of 21 of Nimish's sentences PROVED, s35 among them in the browser;
  - 6 of 6 scenarios MET;
  - 4 of 4 criteria PASSED: 1,196 tests, the drafted document 0 faults (252 cases), s35 1 passed, `bin/check` 27
    passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as for M3a to M3c; the
    `migrate live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a.

## M4 — measured before the build (2026-10-11)

On main `d75767c` and the rehearsed copy `m3d`. M4 places 74 cases on five skills (`research/md_taxonomy.py` SKILLS).

- **29 of the 74 are also on another skill**, all of MD.WORD's Easy and MD.ESTIMATE's Medium among them: B01, B02,
  B03, B05, B04, B11, B13, B06, B08, B07, B12, B14–B17 (MD.WORD); H10, H01, H07, H08, H09 (MD.MENTAL); Y09, Y10
  (MD.EQUALITY); V07, V01, V03, V02, V04, V10, V09 (MD.ESTIMATE). This is addition's own practice, not a defect:
  31 addition and subtraction cases already sit on two skill sets (M01–M25, W01–W11, X01–X09). A case is a pattern;
  the item key keeps each question in one level. Two levels drawing the same numbers for one case share one pool of
  questions, measured when each slice fills its levels.
- **Of the 45 cases only an M4 skill holds, 1 draws** (Y04, anything × 0), each drawn alone on every calculation
  skill's Advance as `test_every_listed_case` draws. No generator makes `multiples` (F01–F07); no word_2step template
  carries × or ÷ (B18–B23); none of the seven new mental methods, eleven new equation shapes, C08, DR09's remainder,
  V05, V06 or V08 for × draws.
- **MD.MENTAL against the school's objectives (A6):** LO-G2-0498 "Apply doubling and halving strategies" puts both at
  Grade 2, where the draft has halving (G25) at Hard, Grade 3. H10 (6 × 7 = 42, so 60 × 7) sits at Easy, Grade 2;
  a multiple of ten times a digit is MUL.TENS's, from Grade 3. H09 (240 ÷ 5 as 24 × 2) sits at Hard, Grade 3;
  dividing by 10 is DIV.TENS's, every level Grade 4. G06's label lists × 8, which is H05's own case.
- **The five shortcuts M2b and M3b1 built** draw on a level with no digit shape (H01, H07, H08, H09: 4 of 4), except
  H10, which reads MUL.TENS's shape (0 of 4).
- **One kind under two codes:** V06 (MD.ESTIMATE, "7 × 9 and 6 × 13: odd or even") and F08 (MD.MULTIPLES, "Is 6 × 7
  even or odd?"); F08's match is V06's narrowed, so every F08 question would count as V06 too.
- **Stories:** 76 templates in `assess/word_templates.json`; two carry a range of numbers (A9 asks it of all). The
  largest number in a stored × or ÷ story is 121; what A9 has left to fix is sense ("A racing game has 84 cars and 78
  tracks", MUL.2D2D). The one template that halves counts on subtraction alone: `skills.operations` reads a two-step
  story's `op` and not its `divide`.
- **The eval rule 7 asks for** is `story_shape`'s: its 65 gold stories are 18 shapes, all + or −. Jev is reachable
  from this machine (`TYPESAFE_API_KEY` set).
- **The mistake table (A11):** 8 of the 40 × and ÷ mistake rows name a skill; `skills.charges_by_kind.approved` is
  empty, addition's table included.
- **Split** (BUILD-ORDER): M4a MD.MENTAL, M4b MD.EQUALITY and MD.ESTIMATE, M4c MD.MULTIPLES, M4d MD.WORD.

## M4a — mental multiplication and division, built (2026-10-11)

Goal `goals/md4a-mental-methods.yaml`, ADR 0064.
- **Each method asked as the sums it works out** (`assess/mental.py`): a box for every step, its sum printed beside it,
  then the answer's (13 × 8 as 13 × 2, 13 × 4, 13 × 8). Seven new: doubling (× 2, × 4), halving (÷ 2, ÷ 4), × 8
  doubled three times, × 9 as ten groups less one, × 11 as ten groups and one more, double one and halve the other,
  × 25 as a hundred groups divided by 4. The five built before draw on MD.MENTAL's levels; a fact scaled by ten builds
  its numbers where a level names no round ones (`draw_times.built`). The website draws every step with a blank.
- **Levels by the school's objectives (A6):** Easy G2 (G06, G25), Medium G3 (H10, H01, H04, H08), Hard G3 (H02, H03,
  H05, H07), Advance G4 (H06, H09). Corrected at the source: halving to Grade 2, H10 to Grade 3, H09 to Grade 4; G06 is
  × 2 and × 4 (`research/md_taxonomy.py`, 252 cases, 0 faults).
- **Mistakes, the method's own first on its answer:** `M_MENTAL_STOPS_SHORT` and `M_MENTAL_ONE_NOT_GROUP` are new;
  `M_COMPENSATION_SIGN` and `M_CONFUSES_COMPENSATION` gain a × row (the wrong way; both doubled). A step's slips are its
  operation's as it names them; halving 74 as 32 is short division's exchange lost. The five built shortcuts name their
  methods' own too; copies stored before keep a key that names fewer, never wrongly. Each method's own counts against
  mental maths (NUM.OPS.05).
- **Found while building, fixed at the cause:**
  - `named` lived in `counting.py` and made `mental` → `counting` → `words` → `times_kinds` → `mental` a cycle: it moved
    to `misconceptions.py`, the mistake module, and its six users import it from there.
  - A first cut named one mistake per wrong answer across a whole box, which would have dropped division's own second
    name (720 ÷ 5 answered 100 is the exchange lost and the remainder added, `div_mistakes.in_box`): only the method's
    own now take a value from the rest.
  - The goal named two new codes for acts compensation already names; it reuses those rows.
- **Rows:** MD.MENTAL on rung R47 (NUM.OPS.05) in topic MDMENTAL, draft and untaught; four mistake rows; Achal's
  question; migration `20261105090000` (MUL.2D1D and DIV.3D1D's lists). `bands.py`'s untyped findings fell 279 to 272.

Proved on copies:
- **Tests:** `test_mental.py` 19 passed. The goal's criteria list on a fresh database (`bin/testdb fresh`, as CI): 1,177
  of 1,178 passed, the last the loader's counts of rungs and skill sets (fixed, 12 passed). `bin/check` 27 passed.
- **The goal's four scenarios** on the fresh database: 16, 24, 24 and 16 asked, each produced, every answer and step
  recomputed from its printed sums, on its rule, diagnosed and distinct, every listed case held.
- **Browser** on a copy: s35 and s36, 2 passed.
- **The update-live rehearsal** on a copy of `m3d` (the migration, `engine load`, `bank levels --apply`, `rekey`,
  `relabel`, `rehome`, `refill`, `library build`, `library check`, `bank taxonomy`): the migration updated 2 skill
  sets; MD.MENTAL loaded as a draft in an untaught topic; the refill added 144 (24, 48, 48, 24) and retired none;
  `library build` made 40; `library check`: 2,518 worksheets, 152 of 152 skill-levels ready, 0 problems.

## M4a merged and live (2026-10-11)

- Merged as `578c44e` (#177), at the head CI had passed (`a52b2fb`: ci 38102530018). The rehearsal on a copy of live
  ran on the same head (38102534317).
- Main: `ci` green (38104022733), then `migrate live` (38104987614) and `deploy engine` (38104987615) succeeded.
- `bin/engine done md4a-mental-methods` on main's code (the worktree at `578c44e`), against a copy of the rehearsed
  database:
  - 21 of 21 of Nimish's sentences PROVED, s36 among them in the browser;
  - 4 of 4 scenarios MET;
  - 4 of 4 criteria PASSED: 1,178 tests, the drafted document 0 faults (252 cases), s36 1 passed, `bin/check` 27
    passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as for M3a to M3d; the
    `migrate live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a.

## M4b — measured before the build (2026-10-11)

On main `578c44e`. MD.ESTIMATE holds 10 cases (Easy V06, V07; Medium V01, V03, V04; Hard V02, V08, V10; Advance V05,
V09), MD.EQUALITY 18 (Easy Y01, Y04, Y05, Y06, Y16; Medium Y02, Y09, Y10, Y15; Hard Y03, Y11, Y12, Y13, Y14; Advance
Y07, Y08, DR09, C08). Each case drawn alone, 12 asked, on a level of cases with no shape of its own, as theirs will be,
and on its other home.

- **MD.ESTIMATE draws none of its ten as its example is.**
  - V01, V02, V03, V07 fail aloud (`KeyError: 'digits'`); V04, V09, V10 draw numbers past Grade 4 (1180 ÷ 6,
    4199 ÷ 4, 8686 ÷ 3). On their other homes (MUL.2D1D, MUL.2D2D, DIV.2D1D, DIV.3D1D Advance) each draws 12 of its
    example's sizes, from that level's shape. One cause: a row says what its case is about and not its numbers' sizes,
    though every example does (48 × 6, 67 × 75, 156 ÷ 4). Each shared case's example has the sizes of its other home, so
    the row can say them without changing what that home draws.
  - V05, V06, V08 refuse (`CannotMake`): possible answer, odd or even and the closest estimate make + and − only.
- **The three judging kinds name no mistake on many + and − questions.** A closest estimate named one on 50 of 313 draws;
  a right claim judged possible names none, half of what that kind asks. R04 and R05 (ESTIMATE.HUNDRED) are those
  questions; no goal's scenario holds those levels, so it never failed. A scenario does not recompute an odd or even
  answer or a closest estimate either: it counts them as nothing to work out.
- **MD.EQUALITY draws 3 of its 18, past their examples' sizes.**
  - Eleven are shapes the equation kind has none of (`no equation shape`): Y01, Y02, Y03, Y05, Y06, Y07, Y08, Y11,
    Y12, Y15, Y16. Y13 and Y14 draw nothing: the missing sign and the comparison make + and − only. DR09 (a remainder
    checked) and C08 (a claim explained) draw nothing, on their examples' sizes too.
  - Y04, Y09, Y10 draw past their examples: 8644 × 0, the fact families of 1296 × 9 and 167 × 417, 4424 ÷ 7 checked.
  - `assess/equality.py` is 283 lines: eleven shapes need a module of their own.
- **Grades (A6):** the school's objectives name rounding (Grades 2 to 4), odd and even (Grade 2, generalised at 3 and
  4) and comparing with <, > and = (Grade 2), and none for estimating a product or × and ÷ as inverses. The draft's
  grades stand as assumed; no case needs an operation taught after its level's grade.
- **V06 and F08 are one kind of question,** a product odd or even. F08's example is a table fact (6 × 7); V06's are a
  table fact and a product past the tables (7 × 9 and 6 × 13), answered "without working". Settled by their numbers:
  F08 the table facts (MD.MULTIPLES, Grade 3), V06 the products past them (Grade 4), its example 6 × 13.
- **So M4b is two slices** (BUILD-ORDER): M4b1 MD.ESTIMATE, the cases' sizes in their rows, the judging kinds for ×
  with a named mistake on every question; M4b2 MD.EQUALITY, its shapes in a module of their own.

## M4b1 — estimating products and quotients, built (2026-10-11)

Goal `goals/md4b1-estimates.yaml`, ADR 0065.
- **Every estimate on its example's sizes.** V01 to V10's rows say their numbers' sizes, as their examples do
  (`research/md_rows.py`): on MD.ESTIMATE's levels, which name no shape, each draws them (four had failed, three drawn
  past Grade 4). Their other homes draw the very questions they drew before, tested both ways; the rehearsal's relabel
  changed no question's case.
- **A product judged as a sum is** (`assess/reasoning.py`, built on the case's own numbers through `reasoning.builder`):
  odd or even (V06), the closest estimate (V08: the larger number rounded to three tens in a row, each times the
  other), whether it can be right (V05: the product, or a named slip of another length, 812 for 23 × 4).
- **Every judging question names a mistake, + and − too:** rounding up always (`M_ROUNDS_AWAY_ZERO`, a row for any
  operation now), down always (`M_ROUNDS_TOWARD_ZERO`, new), one number only; a right claim judged wrong
  (`M_REVERSES_CLAIM_TRUTH`); a claim accepted without its size. The right option sits first, in the middle or last a
  third of the time each (300 draws each way within 0.42).
- **A scenario works out odd or even and the closest estimate** from the two numbers (`scenarios._without_working`).
- **V06 and F08 told apart by their numbers** (F08 a table fact, V06 past the tables); V08's options are what rounding
  gives (52 × 9: 360, 450, 540), corrected at the source.
- **Rows:** MD.ESTIMATE on R48 (NUM.PV.03, NUM.PRB.03), Grade 4, topic MDESTIMATE untaught; two rounding rows;
  Achal's question. `reasoning.py` typed throughout (123 untyped findings to none); `bands.py` 272 to 268.
- **Found while building, fixed at the cause:**
  - The closest hundred drawn numbers first and a place they showed a slip in put a subtraction's right option in the
    middle 51% of the time (its slips sit next to the right answer); needing a slip in all three places asked no
    subtraction at all. The place is drawn first, then numbers that show a slip there: 0.33, 0.34, 0.33 for each.
  - Odd and even balanced by a coin kept three products in four even (34 of 48); an even product is kept one time in
    three.

## Achal is a teacher (2026-10-11)

Nimish: *"Achal is a teacher, so he's the one who will be responsible for doing all of this."* The rows NY1 drafted
took Achal for a specialist. Corrected to the workflow agreed with the school ("everything approved by the teacher"):
`people.decides` gives an educator the answers to confirm, what was read to sign off (N9), the class papers (N7), the
home papers (N11, "Achal confirms") and what is taught; all 27 questions drafted for Achal are an educator's
(`asks.json`). The skills stay with the coordinator: the same workflow has Aseem ratify them (N1). ADR 0059 corrected;
`test_asks.test_achal_is_a_teacher_so_what_waits_on_him_is_an_educators`. On live, Achal's entry on the staff list
(`app.staff`, which the app owns) must say educator.

## update-live stopped on an empty OpenCV (2026-10-11)

Nimish's run of `bin/update-live` stopped at its seed rows: `module 'cv2' has no attribute 'SIFT'`. Reproduced on a
copy: OpenCV's builds share one `cv2` folder; when `uv sync` removes one it deletes the files the other installed,
still counts that one installed, and a plain sync never repairs it (cv2 had no version and no SIFT before and after).
`uv sync --reinstall-package opencv-contrib-python` put it back. Step 1 of `bin/update-live` now checks the engine's
OpenCV after its sync, reinstalls it when it is empty, and stops in a sentence if it still is.

Proved on copies (M4b1 and the two corrections):
- **Tests:** `test_estimates.py` and `test_reasoning.py` 19 passed. The goal's criteria files without a database:
  1,003 passed, 11 skipped (their database tests). With a database built fresh as CI builds it (`bin/testdb fresh`):
  180 of 181 passed, the last the loader's counts of rungs and skill sets (fixed: `test_loaders.py` and `test_asks.py`
  17 passed). `bin/check` 27 passed.
- **The goal's six scenarios** on the fresh database: 24, 36, 36, 24, 24 and 24 asked; every one produced, every answer
  worked out again (odd or even and the closest estimate among them; none left with nothing to work), on its rule,
  diagnosed and distinct; every listed case held.
- **Browser:** s36, s37 and u13 (4), 6 passed, u13 once the copy held the corrected rows.
- **The update-live rehearsal** on a copy of the post-M4a database (`engine load`, `bank levels --apply`, `rekey`,
  `relabel`, `rehome`, `refill`, `library build`, `library check`, `bank taxonomy`, `asks`): rungs 40, skill sets 40,
  mistakes 116; nothing re-keyed, relabelled or re-homed; the refill added 120 (24, 36, 36, 24) and retired none;
  `library build` made 40; `library check`: 2,558 worksheets, 156 of 156 skill-levels ready, 0 problems; every
  question for Achal an educator's.

## M4b1 merged and live (2026-10-11)

- Merged as `00a107b` (#178), at the head CI had passed (`5fe61c5`: ci 38109049518). The rehearsal on a copy of live
  ran on the same head (38109051612). CI's full suite found two tests M4b1 had not carried, each fixed in the PR: the
  loader's counts of rungs and skill sets (40 each), and `test_facts_advance`'s slice map, which still named "M4b".
- Main: `ci` green (38110668144), then `migrate live` (38112277226) and `deploy engine` (38112277221) succeeded.
- `bin/engine done md4b1-estimates` on main's code (the worktree at `00a107b`), against a copy of the rehearsed
  database:
  - 19 of 19 of Nimish's sentences PROVED, s37 among them in the browser;
  - 6 of 6 scenarios MET;
  - 4 of 4 criteria PASSED: 1,145 tests, the drafted document 0 faults (252 cases), s37 1 passed, `bin/check` 27
    passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as before; the `migrate
    live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a. Nimish's run of it stopped
  at its seed rows on an empty OpenCV, before this merge; the guard ships with it.

## M4b2 — measured before the build (2026-10-11)

On main `00a107b`. MD.EQUALITY holds 18 cases (Easy Y01, Y04, Y05, Y06, Y16; Medium Y02, Y09, Y10, Y15; Hard Y03, Y11,
Y12, Y13, Y14; Advance Y07, Y08, DR09, C08), placed G3 G3 G4 G4. Measured in "M4b — measured before the build":
three draw, past their examples' sizes, and fifteen draw nothing. Their causes:
- **Eleven shapes no kind makes** (`equality.equation`: "no equation shape"): the order (Y01), the grouping (Y02), a
  factor partitioned (Y03), × 1 and ÷ 1 (Y05), a number ÷ itself and 0 ÷ a number (Y06), true or false about ÷ 0
  (Y07), a division's order (Y08) and a product's (Y16), a balance against − (Y11) and against ÷ (Y12), a factor
  doubled (Y15).
- **Two shapes make + and − only:** the missing sign (Y13) and comparing without working (Y14) draw their own + and −
  numbers.
- **The division check refuses a remainder** (`divide_kinds.checked`: "checked here against an exact division"), so a
  remainder checked by multiplying back (DR09: 21 × 4 + 1 = □, is 85 ÷ 4 = 21 r 1?) can never be drawn.
- **A claim to explain is addition's only** (`diagnosis.explain_claim`: moving one between the numbers, or a ten
  exchanged), so explaining by multiplying back why 804 ÷ 4 = 21 cannot be right (C08) can never be drawn.
- **Three rows do not say their sizes** (as M4b1 found for the estimates): Y04 drew 8644 × 0 (its example 456 × 0),
  Y09 the fact family of 167 × 417 (its example a table fact), Y10 a check of 4424 ÷ 7 (its example 96 ÷ 4).
- **Grades:** "Missing numbers in equations" is the school's objective at Grade 3 (LO-G3-0937) and Grade 4
  (LO-G4-1334), and comparing with <, > and = at Grade 2: the draft's grades stand.
- **Mistakes:** rows exist for × 0 left as the number (`M_ZERO_AS_ONE`), × 1 adding one (`M_ONE_ADDED`, × only), a
  number ÷ itself as 0 and 0 ÷ a number as the number (`M_DIV_SELF_AS_ZERO`, `M_DIV_ZERO_DIVIDED`), a division turned
  round (`M_DIV_BIGGER_BY_SMALLER`), = read as "the answer comes next" and every number added (`M_EQUALS_MEANS_ANSWER`,
  `M_ADD_ALL`), the wrong sign (`M_WRONG_OP`, × and ÷ rows), a comparison turned round (`M_COMPARE_REVERSED`) and a
  claim's truth reversed (`M_REVERSES_CLAIM_TRUTH`). None yet for ÷ 0 read as 0, for ÷ 1 read as taking one away, or
  for a remainder left out of its check (85 ÷ 4 checked as 21 × 4 = 84).
- **The scenarios' check** works out a sentence with one operation (`md_tags.solved`); a balance, a grouping, a
  partitioned factor, a true-or-false, a missing sign and a comparison need a sentence worked out for itself.
- **A true-or-false whose answer is always false** (9 ÷ 0 = 0, 12 ÷ 3 = 3 ÷ 12) is answered by ticking one place: each
  needs true sentences beside it, as often.
- `assess/equality.py` is 283 lines: the shapes go in a module of their own.

## M4b2 — equations with × and ÷, built (2026-10-11)

Goal `goals/md4b2-equality.yaml`, ADR 0066.
- **Thirteen × and ÷ equation shapes** (`assess/times_equality.py`), each sentence a response of its own, printed on its
  own row: its box where its □ stands, or its ticks after it (`straight_pages.equation`). `equality.from_rule` hands a
  multiplication case there (`taxonomy`, a drawer hint that draws nothing), so the missing sign and the comparison are
  × and ÷'s own there and + and −'s on their cases.
- **No tick answered by guessing:** each true-or-false beside its other (9 ÷ 0 = 0 beside 0 ÷ 9 = 0; 12 ÷ 3 = 3 ÷ 12
  beside 12 × 3 = 3 × 12; 7 × 6 = 6 × 7 beside 9 − 4 = 4 − 9), the missing sign and the comparison a × sentence beside
  a ÷ one, in either order: in every place, each answer at most 0.7 of 60 draws.
- **A remainder checked by multiplying back** (DR09), the product written alone named (`M_DIV_REMAINDER_LEFT_OUT`, on
  DIV.2D1D's checks too, its list by migration); yes to a remainder too big names that mistake. **A wrong ÷ answer
  explained by multiplying back** (C08): the claim a named slip of the layout (804 ÷ 4 = 21), its product a box, the
  reason read by a person.
- **Every question names a mistake;** three new rows drafted for Achal (÷ 0 read as 0, a remainder left out of its
  check, a bigger divisor taken to give a bigger answer), in the draft's table too (41 to 44 mistakes); two equal sums
  compared name the first number's change seen and its partner's missed (`M_APPLIES_COMPENSATION_ONE`).
- **Sizes:** Y04, Y09, Y10, DR09 and C08 say their examples' sizes; MUL.FACTS and DIV.2D1D draw what they drew before,
  tested both ways.
- **The scenarios' check works out every equation from its own sentence** (`checks/sentences.py`): exact, + − × ÷ and
  brackets, a balance's pans read as one sentence, a sentence with no single answer failed. EQUALITY.INVERSE's Medium,
  Hard and Advance went from 0, 12 and 0 of 24 worked out to 24 of 24 each.
- **Found while building, fixed at the cause:** + and −'s missing sign printed a difference below zero (7 □ 9 = -2,
  about one draw in 35, a Grade 2 skill), found when the new check could not work it out. The larger number comes
  first now, and a stored one is retired on refill (`stale.key_problems`).
- **Rows:** MD.EQUALITY on R49 (NUM.OPS.05, NUM.PRB.03), Grade 3 at Easy and Medium and Grade 4 at Hard and Advance,
  topic MDEQUALITY "Equations with × and ÷", untaught; 33 mistakes on its list; Achal's question. The website calls
  `explain_claim` "explain a claim" (a C08 claim is shown wrong, not judged true or not). Ratchets fell: `render_item`
  57 to 56 statements; untyped findings `render.py` 314 to 301, `equality.py` 164 to 127.

Proved on copies:
- **Tests:** `test_md_equality.py` 19 passed. The goal's criteria files on a database built fresh as CI builds it
  (`bin/testdb fresh`: 27,538 questions, 2,556 worksheets): 1,113 passed. An earlier run, started on an older copy
  before the build was complete, failed 9: three the build changed by design, updated with it (the slice map's
  MD.EQUALITY line, DIV.2D1D's list, the division check's expected key); the loader's two (its counts, and a copy
  without R49); four that pass on the final code.
- **The goal's seven scenarios** on the fresh database: every question produced, every answer worked out again (none
  with nothing to work), on its rule, diagnosed and distinct; every listed case held.
- **Browser:** s38 and s37, 2 passed, on the rehearsed copy.
- **The update-live rehearsal** on a copy of the post-M4b1 rehearsed database: the migration; `engine load` (rungs 41,
  skill sets 41, mistakes 119); nothing re-keyed, relabelled or re-homed; the refill retired 2 — the two sign
  questions below zero it held (7 □ 9 = -2, 7 □ 8 = -1) — and added 218 (MD.EQUALITY's 60, 48, 60 and 48, and the two
  retired ones' places); `library build` made 42 and retired 2; `library check`: 2,598 worksheets, 160 of 160
  skill-levels ready, 0 problems. MD.EQUALITY is a draft until approved; Achal's question waits, an educator's.
- **The draft:** `md_taxonomy.py --check` 252 cases, 44 mistakes, 0 faults. `bin/check` 27 passed.

## M4b2 merged and live (2026-10-11)

- Merged as `a66d16d` (#179), at the head CI had passed (`cae1954`: ci 38116856364); the rehearsal on a copy of live ran
  on the same head (38116872773). The CI failure on `73b06cd` was the goal's tests committed before the build, as
  intended.
- Main: `ci` green (38118495794), then `migrate live` (38120153585) and `deploy engine` (38120153580) succeeded.
- `bin/engine done md4b2-equality` on main's code (the worktree at `a66d16d`), against a copy of the rehearsed database:
  - 21 of 21 of Nimish's sentences PROVED, s38 among them in the browser;
  - 7 of 7 scenarios MET;
  - 4 of 4 criteria PASSED: 1,113 tests, the drafted document 0 faults (252 cases, 44 mistakes), s38 1 passed,
    `bin/check` 27 passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as before; the `migrate
    live` run above is the proof they are there.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a; it also retires live's two
  sign questions below zero.

## M4c — measured before the build (2026-10-11)

On main `a66d16d`. MD.MULTIPLES holds 8 cases, placed G3 G3 G4 G4: Easy F01 (the multiples of 6 up to 60), F02 (is 45
a multiple of 5?), F06 (is 340 divisible by 2, 5 and 10?); Medium F03 (the factors of 12), F04 (the factor pairs of 24),
F08 (is 6 × 7 even or odd?); Hard F05 (common multiples of 3 and 4 below 30); Advance F07 (is 117 divisible by 3, from
the sum of its digits?).
- **Seven draw nothing:** F01 to F07 name the kind `multiples`, which no generator makes ("no native generator for
  format 'multiples'"). F08 draws (odd or even of a table fact, M4b1).
- **Grades:** "Tables, multiples and factors" is the school's objective at Grade 3 (LO-G3-0942) and Grade 4
  (LO-G4-1339): the draft's grades stand. Divisibility by 3 from the sum of the digits names no school objective; it
  is Advance.
- **Four answers are lists** (F01, F03, F04, F05). The reader reads one strip of boxes per answer, a blank box no
  position in it (`boxes.read_page`); marking marks each answer by itself (`marking.mark`), and is reached from four
  places (the reading, marked again, a person's reading, a key changed). A list keyed box by box would mark every box
  after one missed factor wrong; marking compares a key of several numbers by its numbers in order already, for what a
  person types (`marking._against_the_key`). A list answer today would go to a person unread (`reading.py`: every
  answer not `digits`).
- **Mistakes:** no rows yet for a multiple written for a factor, a number past the limit, a multiple of one number only
  taken as common, divisibility by 3 judged from the last digit, or a factor pair counted twice.

## M4c — multiples and factors, built (2026-10-11)

Goal `goals/md4c-multiples-and-factors.yaml`, ADR 0067.
- **Seven shapes** (`assess/multiples.py`): the multiples of a number up to a limit (F01), a multiple or not (F02),
  divisible by 2, by 5 and by 10 (F06), all the factors (F03), the factor pairs (F04), the common multiples below a
  limit (F05), divisible by 3 from the sum of the digits (F07); F08 draws as before. Factors are asked of numbers up to
  60 with four to eight of them and a factor pair from the tables (28, never 57); factor pairs of numbers up to 100,
  since up to 60 only 17 numbers have three to five pairs, too few for 24 different questions.
- **A list is one answer** (kind `list`): printed as groups of boxes, two more than it holds, each as wide as its widest
  number, beside "You may not need every space" (`straight_pages.multiples`); read group by group as any number is and
  joined in the order written (`w3_read/lists.py`), a doubted group making the whole list a person's; marked as a whole
  (`multiples.judge`, from `marking._not_one_number`), so the factors of 12 with 4 left out are one wrong answer naming
  a factor left out, and 24 added names a multiple written for a factor.
- **No yes-or-no answered by guessing:** in every place a tick is asked (a multiple or not, by 2, by 5, by 10, by 3,
  and F08's odd or even), each answer at most 0.7 of 60 draws. A wrong tick names the last-digit rule used where it
  does not work (34 a multiple of 4; 117 judged by its 7), the first digit read for the last (805), or divisible by 5
  taken for 10 (345), where the question's numbers say so; otherwise the claim reversed.
- **Twelve new mistakes** drafted for Achal, each counting against multiples and factors (NUM.CNT.08), in the draft's
  table too (44 to 56 mistakes). MD.MULTIPLES names 15 on its list, computed from what its levels draw.
- **Rows:** MD.MULTIPLES on R50 (NUM.CNT.08, NUM.OPS.03: "Tables, multiples and factors", the school's objective at
  Grades 3 and 4), Grade 3 at Easy and Medium and Grade 4 at Hard and Advance, topic MDMULTIPLES "Multiples and
  factors", untaught; Achal's question `md4c-multiples`; the kind's skill (`skills.by_kind`). No migration. The website
  calls `multiples` "multiples and factors".
- **The scenarios' check works out every list and tick from the question's words** (`checks/multiples.py`).
- **Found while proving, fixed at the cause:** a paper made from MD.MULTIPLES's stored questions could not be printed
  (`inventory.item_from_row`: `KeyError: 'multiples'`, no row in `layout.WORKING_LINES`), found by the criteria's
  sample-sheet test on the fresh database. The test that holds the table to the generators drove only levels named by
  one `format` and a hand list; a level made of cases never reached it. It now holds every kind a case can draw to a
  row too, and fails without the new one. Achal's question and the goal's line to him are one text again (the row had
  grown past the goal's line).
- **Ratchets fell:** `render_item` 19 to 18 (C901) and 56 to 54 statements, the kinds drawn whole now one table
  (`straight_pages.PAGES`); untyped findings `render.py` 301 to 295. `boxes.py` 392 to 394 lines (two lines that hand a
  list's groups to `lists.py`).

Proved on copies:
- **Tests:** `test_md_multiples.py` 17 passed. The criteria's test files without a database: 994 passed, 7 skipped
  (the 7 need one).
- **The goal's four scenarios** on a database built fresh as CI builds it (`bin/testdb fresh`): 120 of 120 produced,
  every answer worked out again from its words (none with nothing to work), on its rule, diagnosed and distinct, every
  listed case held.
- **Browser:** s39 and s38, 2 passed, on the rehearsed copy.
- **The printed paper,** one of each shape, looked at: groups with two to spare, a pair's two either side of ×, each
  yes-or-no on its own row, the digit sum's box after its sentence. A filled copy, scanned as a phone hands it over, read
  and marked right; one group left empty, one wrong answer naming the multiple left out.
- **The update-live rehearsal** on a copy of the post-M4b2 rehearsed database: no migration; `engine load` (rungs 42,
  skill sets 42, mistakes 131); nothing re-keyed, relabelled or re-homed; the refill retired 0 and added 120
  (MD.MULTIPLES's 36, 36, 24 and 24); `library build` made 40 and retired 0; `library check`: 2,638 worksheets, 164 of
  164 skill-levels ready, 0 problems. MD.MULTIPLES is a draft until approved; Achal's question waits, an educator's.
- **The draft:** `md_taxonomy.py --check` 252 cases, 56 mistakes, 0 faults. `bin/check` 27 passed.

## M4c merged and live (2026-10-11)

- Merged as `1062d83` (#180), at the head CI had passed (`a55461c`: ci 38123027773) and the rehearsal had passed on
  (38123036281). CI's failures on `de2a9fb` were the goal's tests committed before the build, as intended; those on
  `b8546f9`, `1ac41c9` and `e044900` were the three the fix in `a55461c` answers (a kind with no working space, two
  tests; Achal's question and the goal's line to him).
- Main: `ci` green (38124737098), then `migrate live` (38126061390) and `deploy engine` (38126061368) succeeded. The
  website deployed on Vercel once the repository was public again: from 07:35 to the switch Vercel refused this
  private organization's repository on its Hobby plan, so nothing deployed in that window.
- `bin/engine done md4c-multiples-and-factors` on main's code (the worktree at `1062d83`), against a copy of the
  rehearsed database:
  - 19 of 19 of Nimish's sentences PROVED, s39 among them in the browser;
  - 4 of 4 scenarios MET;
  - 4 of 4 criteria PASSED: 1,093 tests, the drafted document 0 faults (252 cases, 56 mistakes), s39 1 passed,
    `bin/check` 27 passed.
  - Its live line cannot read the live database's migrations from here (`UndefinedTable`), as before; M4c has no
    migration.
- Its rows, questions and worksheets wait for `bin/update-live`, with everything since M2a.

## M4d — measured before the build (2026-10-11)

On main `1062d83`. MD.WORD holds 26 cases, drafted G2 G2 G3 G4. Each drawn alone (`draw.level`, 12, rows as seeded):
- **Sixteen draw:** B01, B02, B03, B06 (Easy); B04, B05, B07, B11 (Medium); B08, B14, B15, B16, B17 (Hard); B12, B13
  (Advance). Fifteen of them sit on another skill's level too; B01 is MD.WORD's alone.
- **Ten draw nothing:**
  - B09 (times as many: the smaller), B10 (how many times), B27 (half as many): "no one-step story divides for shape
    …" — no template.
  - B18 to B23, the two-step stories with × and ÷: `word_2step` raises `KeyError: 'digits_max'` (a case's rule gives no
    size), and `words.word_2step` works a story's first step with + or − only; its 13 templates are all + and −.
  - B25 (a number the story does not need) and B26 (a price list): "no one-step story for shape … and operation '×'".
- **A9:** 2 of the 76 templates say the range their numbers may take (`numbers`: twice as many, a 3 to 20); the rest
  take their sizes from the level.
- **The eval rule 7 asks for** (`story_shape`): 65 gold stories, 18 shapes, all + and −; Jev reachable here.
- **Halving:** `skills.operations` reads a two-step story's `op`, never its `divide`.
- **A11:** 8 of the 40 × and ÷ mistake rows name a skill; `skills.charges_by_kind.approved` is empty.
- **Split** (BUILD-ORDER): M4d1 the ten stories on MD.WORD's own rows, each new template with its range; M4d2 the older
  templates' ranges, `story_shape` for × and ÷ with its eval, halving on Division, the A11 table.

## M4d1 — stories with × and ÷, built (2026-10-11)

Goal `goals/md4d1-times-stories.yaml`, ADR 0068.
- **Ten stories that drew nothing now draw:** times as many, the smaller (B09) and how many times (B10); half as many
  (B27); × then + (B18), × then − (B19), ÷ then × (B20), two products added (B21), + then ÷ (B22) and a bar model
  (B23); a number the story does not need (B25); a price list (B26).
- **A template that says its own numbers** (`assess/own_stories.py`): 22 new template rows, each with the range of each
  number, its answer as a formula worked exactly (a division that leaves something over draws again), the wrong
  answer behind each mistake, the smallest answer that asks something and the numbers it must tell apart. The older
  makers never draw one (`words.owns`, `words.older`). A price list is a template's table with its numbers named.
- **Found while looking at what MD.WORD drew, fixed at the cause:** its older stories, on a level that gave no size,
  drew 2 digits by 2 at Grade 2 ("A shelf holds 75 books. How many books are there on 72 shelves?"; "₹9459 for 3 bus
  tickets"; 4-digit remainders). Each MD.WORD level now says its sizes as a row: 1 or 2 digits by 1 at Grades 2 and 3,
  as MUL.2D1D's Grade 2 levels place 2 digits by 1. Two of the new stories asked for what they gave ("2 pencils cost
  ₹50. What do 2 pencils cost?"): their two counts must differ.
- **Every question names a mistake;** six drafted for Achal (multiplying because the story says "times", doubling for
  half as many, how many more answered for how many times, the unneeded number used, the other price read, a bar
  model divided by the times alone), each counting against NUM.PRB.02; in the draft's table too (56 to 62). MD.WORD
  names 26 on its list.
- **Rows:** MD.WORD on R51 (NUM.OPS.03, NUM.OPS.04: "Solve multi-step word problems using bar models", the school's
  objective at Grades 2, 3 and 4), Grade 2 at Easy and Medium, 3 at Hard, 4 at Advance; topic MDWORD "Stories with ×
  and ÷", untaught; Achal's question `md4d1-stories`. No migration.
- **The scenarios' check works out every two-step story** from its numbers and shape (`checks/stories.py`), a second
  time and apart from its template's formula.
- **Found while proving, fixed at the cause:** two more readers took every template, the new ones included. The story
  reader for + and − (`story_shape`) shares one shape's name with × (a number the story does not need): its examples
  failed on `{extra}` and its counts would have changed + and −'s. The bank's own candidates for a one-step story
  (`bank`) picked a story by operation alone and filled its words with two numbers: a story that says its own
  numbers (half as many is ÷ 2) is never one of them now (`words.older`). Eight `story_shape` tests that run only with
  a database caught the first.
- **Found in CI, fixed:** s2's edit of a skill's words, on a commit of documents alone, saved the new words followed by
  the old — the box was filled before the page's script took over. The spec reaches the page live (networkidle) and
  checks the box before Save. Ratchet fell: `bands.py` untyped 268 to 253.
- **Found in CI, fixed at the test:** rewording a question held its new one to exactly one worksheet. The library
  promises less: a level the patch cannot keep even is dealt afresh (ADR 0026), and its new question can be one of
  those dealt twice. Reworded one by one on a copy, ADD.2D2D Advance's 68 stories went 1→1 (65), 2→1 (2) and 1→2 (1);
  CI's draw picked the last kind. The test now holds what is promised: the old question on no worksheet, the new one
  on worksheets all newly made, no worksheet edited, `check` clean. All 68 hold; an edited worksheet is caught.

Proved on copies:
- **Tests:** `test_md_word.py` 12 passed; the story and kind tests without a database, 413 passed.
- **The goal's four scenarios** on a database built fresh as CI builds it: 312 of 312 produced, every answer worked
  out again (the two-step stories too), on its rule, diagnosed and distinct, every listed case held.
- **Browser:** s40 and s39, 2 passed; s2, 6 passed; on the rehearsed copy.
- **The printed paper,** one of each new story, looked at: each sentence whole, the price list a table beside its
  question, an answer box for each.
- **The update-live rehearsal** on a copy of the post-M4c rehearsed database: no migration; `engine load` (rungs 43,
  skill sets 43, mistakes 137); nothing re-keyed, relabelled or re-homed; the refill retired 0 and added 312 (MD.WORD's
  48, 60, 84 and 120); `library build` made 40 and retired 0; `library check`: 2,678 worksheets, 168 of 168
  skill-levels ready, 0 problems.
- **The draft:** `md_taxonomy.py --check` 252 cases, 62 mistakes, 0 faults. `bin/check` 27 passed.

## UI1 — measured before the build (2026-10-11)

Every one of the website's 27 pages opened on a copy of the data (the post-M4d1 rehearsed database, test classes and
all), screenshotted at a laptop and a phone, and inventoried: how it is reached from the menu, what it shows, what
waits on a person there. The screenshots hold children's names and stayed on the machine that took them.
- **16 kinds of thing wait on a person.** The 18 answers the reader could not settle wait on "Check the answers",
  which is not in the menu: Today's card or a button on Papers reaches it. Today filed 6 of its 7 queues under "For
  others", because no one on the copy's staff list is an educator. Topics to switch on and skills to approve are
  reached from Curriculum; the questions drafted for an educator only from a Today card, which goes when they do.
- **One act, four words:** an answer is checked (/capture/check), signed off (a paper's page) and settled or
  confirmed (a child's page). Marking is "Marking", "Scans, and how the reader is doing" and "Papers to sign off".
- **Codes where words belong:** weeks as `2026-W41`, class packs as `U9-TEST · U9-W · practice`, worksheets as
  `R22-A19`, mistakes as `M_CARRY_SKIP`. How it works, in every educator's sidebar, is the engineering map.
- **Long lists with nothing to narrow them:** approving the skills is one page of 43 with one button at the bottom; the
  questions for an educator, 30 over 10,700 pixels; the question bank, 393 pages of 50 with no search.
- **Not the website's, the copy's:** the parent report that would not open (`{"facts": {}, "draft": {}}`, written by
  u8-children-table.spec.ts) and the class pack no page approves (made by u9-papers.spec.ts without the plan the
  weekly flow writes) are test rows. Live's packs come from `/week/assemble`, which writes the plan `/worksheets` reads.
- **The plan** (four tabs, one list on Today, each step live on its own) published as
  https://claude.ai/artifact/Ubn4TrkEh5DrBNmhhjcFSD; Nimish approved it and named the educators: Achal and Neha.

## UI1 — the menu and Today, built (2026-10-11)

- **The menu** is Today, Curriculum, Assessments (the Papers tab, renamed; its address stays /papers), Children. Each
  tab carries the count of what waits in it, from `lib/needs-you.ts`, the one list Today shows; the count is the link's
  description, not its name. How it works shows to a coordinator only.
- **Today** is one list under three headings, Assessments first (the day's checking), then Curriculum and Children.
  Each line says how many, what it is, and opens the place it is done: answers to check, papers to sign off, class
  papers to approve (each pack its own link, "Grade 2 · 2B · class practice · week of 5 Oct"), home assessments, scans
  that came back empty (new: they were on Marking only), skills to approve, the engine's questions (one line, whoever
  they were drafted for), topics not taught yet (shown, not counted: switching one on is the school's choice), parent
  reports to approve (new: no page listed them). No line is anyone else's: "For you / For others" is gone, and
  `decides()` with it (the `people.decides` row stays; the engine's `asks` reads it).
- **Weeks in words** (`weekWords`, "week of 5 Oct", by the ISO week's Monday) on Today's packs and its week-by-week table.
- **Measured:** the list costs 46 ms a page warm on the rehearsed copy (228 ms cold); it runs in the layout, so every
  page's menu has it.
- **Proved on copies:** the goal's browser criteria on a database built fresh: 80 tests, 79 passed and one failed on a
  race in the test (it counted Today's lines before they streamed in), fixed and passed; u15 and u1 twice running on
  one copy (a second run found the test child's report not made again; fixed). `tsc`, `eslint` clean. `bin/check` 27
  passed. Looked at Today on the rehearsed copy at a laptop's width.

## UI1 merged and live (2026-10-11)

- Merged as `0aadd04` (#183) at the head CI had passed on (`b0e142f`: engine, web and browser green). Vercel's
  production deploy of `0aadd04` succeeded at 14:26 UTC; the website is the whole of UI1, so nothing waits on
  update-live.
- `bin/engine done ui1-menu-and-today` on main's code against a database built fresh: 5 of 5 of Nimish's sentences
  PROVED, 3 of 3 criteria PASSED (63 browser tests, types and lint clean, `bin/check` 27 passed). Its live line cannot
  read the live database's migrations from here (`UndefinedTable`; no local copy records them), as for M4c; UI1 has
  no migration.

## UI2 — measured before the build (2026-10-11)

- **The maker already makes what Nimish described:** class practice, class assessments and home assessments, for any
  children of a class, one paper for all, the same skill with different questions, or each child's own next step
  (goals/m3-the-maker.yaml); every child's paper is seen before anything is made. Nothing opened it ready for a use:
  Assessments had one "Make a paper" button, and a choice made before the class was chosen was lost.
- **A topic made nothing:** a class assessment took one to three skill-and-level lines chosen one by one.
- **Words:** the stages read made / printed / scanned / checked / signed off; the class column read the class's code
  and the week column the ISO week; a child's page said "settle" and "confirm" where the queue says check and a paper
  is signed off.
- **Not there at all:** choosing single questions from the bank into a paper. The engine makes papers from skills and
  levels, or hands out a ready-made worksheet (`/worksheet/{code}/for.pdf`); a paper of chosen questions is engine
  work (W2), put to Nimish rather than built under UI2.

## UI2 — Assessments, built (2026-10-11)

- **Assessments opens on four ways to make one**, each opening its place ready for that use: for a class (the maker,
  class assessment, one paper for all), for each child (this week's home assessments, one per child from their record),
  for one child (the maker, the engine's next step, no child ticked until one is), a ready-made worksheet (the library).
  The maker keeps a starting point's kind and way until the class is chosen.
- **A class and a topic make its default assessment** (`topicLines`, lib/maker.ts): the topic's skills at the class's
  grade in the ladder's order, as many as a paper has lines, each at Medium where it has one, the home paper's length
  shared between them; the educator sees every child's paper and can change any line before anything is made.
- **Words:** stages are to approve, with the children, to check, to sign off, done (the filter's values stay the stored
  stages); classes Grade 2 · 2B; weeks "week of 5 Oct". A child's page checks an answer and signs answers off: settle and
  confirm are gone from it, and its grade is a word.
- **Proved on copies:** the goal's browser criteria on a database built fresh, 58 of 58 (u16 written first and seen
  failing for the absent "Make an assessment"; m4's opening and u16's own waits fixed on the way). `tsc`, `eslint`
  clean. The Assessments page looked at on the rehearsed copy.

## UI2 merged and live (2026-10-11)

- Merged as `20419f1` (#184) at the head CI had passed on (`65622ac`: engine, web and browser green). Vercel's
  production deploy of `20419f1` succeeded at 15:33 UTC; the website is the whole of UI2, so nothing waits on
  update-live.
- `bin/engine done ui2-assessments` on main's code against a database built fresh: 4 of 4 of Nimish's sentences
  PROVED, 3 of 3 criteria PASSED (58 browser tests, types and lint clean, `bin/check` 27 passed). Its live line cannot
  read the live database's migrations from here (`UndefinedTable`), as for UI1; UI2 has no migration.

## UI3 — measured before the build (2026-10-11)

- **A skill's page** (ADD.2D2D) was one 5,200-pixel scroll: what it means, its levels, its mistakes each under its
  `M_…` code, and its 73 worksheets every level at once, each named by its code. Nothing on the page said where a part
  began.
- **Approving** was one button under all 43 draft skills: an educator could approve every skill or none.
- **Switching a topic on** was twelve "Switch on" buttons on Curriculum, each switching its topic on for the whole
  school in one click, with nothing said of what that does.
- **The engine's questions** (`/asks`) were 30 panels at full length, 10,700 pixels, each with its draft, its reason
  and its form open.
- **Found during the build:** the Question bank had no search, and drew some questions without the sentence the paper
  prints above them ("Add them in the easiest order.", "Write the missing digits.", "Write the missing row."); a class's
  week of papers sat at the foot of the worksheet library, so Today's "Class papers to approve" opened the Curriculum
  tab; eleven pages said "Stage 2", "Stage 5" or "Papers" above their title, none the tab they were under.

## UI3 — Curriculum, built (2026-10-11)

- **A skill's page is in five parts**, each one click from its top: What it means, Levels, Mistakes, Questions (the
  Question bank, filtered to the skill) and Worksheets. Its worksheets show one level at a time (the first, or the one
  chosen; "Every level" shows all), each named "Medium · sheet 3" with its code small and grey; a mistake is named in
  words, its code gone from the page.
- **A skill is approved on its own**, from the approve page grouped under one heading per grade, each skill with its
  own "Approve this skill, as …" button (`only` in `approveSkills`; the charges table is skipped for one skill); the
  button for all of them stays.
- **A topic is switched on only after the person has read what it does:** "Switch on" opens a fold saying it switches
  the topic on for the whole school, and the button inside it switches it.
- **Each question the engine drafted is one line** until it is opened; its draft, reason and answer form are in the
  fold.
- **The Question bank finds a question by its words** (its sentence or its sum), within the skill, level and kind
  already chosen; what is typed is looked for as it is (`%` and `_` are not wildcards). Every kind of question now
  shows the sentence the paper prints above it, so what the search found is what the page shows.
- **Every page says the tab it is under** above its title, and the menu marks that tab. **A class's papers are
  approved under Assessments** (`/papers/approve`, step N7 on the map): each child's paper, its level and why, a level
  changed with its reason, the pack approved; Worksheets is the library alone, and a week's old address there opens
  it at the new one.
- **Proved on copies:** u17 was written first and each of its seven tests seen failing on the old pages for its own
  reason (no parts menu; no grade heading; the switch visible; the answer buttons visible; no search box; no tab
  above a title; the week still under Worksheets). s3's level filter raced the page (every level has as many
  worksheets, so the count passed before the click landed); it now waits for the address. CI caught the same race in
  u17's approval, which waited for an address the page already had and read the database before the approval landed;
  it now waits for `?approved=1` and the notice (21 of 21 over three runs). Three faults in u17 itself
  were fixed on the way: a heading match that took panel titles too (the panels no longer repeat the grade their
  heading gives), a restore that left `taught_at` set against `topic_taught_by_a_person`, and a count of folded
  buttons that read the accessibility tree, where a closed fold's buttons are absent and "hidden" would have passed
  with none. `tsc`, `eslint` clean.

## UI3 merged and live (2026-10-11)

- Merged as `3b6806a` (#185) at the head CI had passed on (`349049c`: engine, web and browser green; the first head's
  browser run caught u17's approval race, fixed in `349049c`). Vercel's production deploy of `3b6806a` succeeded at
  17:15 UTC; the website is the whole of UI3, so nothing waits on update-live.
- `bin/engine done ui3-curriculum` on main's code against a database built fresh: 7 of 7 of Nimish's sentences
  PROVED, 3 of 3 criteria PASSED (77 browser tests, types and lint clean, `bin/check` 27 passed).

## The done report asks live, not the copy (2026-10-11)

- **Found:** every done report since M4c ended "could not read the live database's migrations: UndefinedTable" and so
  NOT DONE. It never asked live: `not_live` read the database the tests had just run on (`DATABASE_URL`, a copy with no
  migration record) and blamed live for it.
- **Fixed** (`engine/checks/done.py`, test `test_the_done_report_asks_the_live_database_and_never_the_copy`): it asks
  live by its read-only address (`LIVE_READONLY_DATABASE_URL`, the one `engine live data` reads by) with a ten-second
  limit; says so when no address is set; and names a live database that does not answer.
- **What that shows from this container:** the address is set, but live does not answer here (outbound is an HTTPS
  proxy; Postgres does not pass). So a report written here says live's migrations are unchecked, and NOT DONE stands
  for that line alone, as it should. Whether the website is live is read from Vercel's production deploy of the merge.

## UI4 — measured before the build (2026-10-11)

- **Sign-in** by email and password already works (`apps/web/lib/auth.ts`, `engine set-password`); what was missing is
  a way onto the list. `app.staff` was seeded from `supabase/seed/config.json`, in the public repository, with a staff
  email in it, and `engine set-password` refused anyone not already on it.
- **Children** (`/growth`): one table per grade, 35 children on the copy, no search.
- **A class's children against its skills** is there already: `/growth/class/[section]`, opened from each grade (14
  children by 11 skills on the copy).
- **A child's page** (1,754 px on the copy): what their answers show, checks, the colour key, repeated mistakes, the
  home assessment, their papers; the parent report only as a link at the top. Parent reports are listed only on Today.
- UI4 is split so the sign-in ships first: UI4a the staff list and the search, UI4b the child's page and the reports.

## UI4a — the staff list and the search, built (2026-10-11)

- **`engine staff add <email> --name <name> [--role educator]`** puts a person on the list in the database with a
  password typed twice and never shown, hashed as the website checks it; refuses an email already on it, a role no
  decision names, and a password under ten characters or typed differently twice. `engine staff list` shows who.
  Both, with `engine set-password`, are `engine/core/cli_staff.py`; the list's rules are `engine/core/staff.py`.
- **The seed's staff list is empty** (ADR 0069): the list is the database's alone, so an educator's email never enters
  the public repository. Nimish's email is still in an n8n notification (`n8n/workflows/f1-build-the-bank.json`); that
  is where he is told, not who signs in, and is left as it is.
- **Children finds a child as it is typed**, by part of a name or a roll number, across every grade, in the browser:
  the words go nowhere, so a name never enters an address or a log.
- **Proved on copies:** `test_staff.py` written first and seen failing (no command); u18's search seen failing (no
  search box); its sign-in test passed before the build, as sign-in already worked for anyone on the list. Engine:
  41 passed (staff, cli, loaders). Browser: u18 4 of 4 over two runs.
- **CI caught what the local run missed:** `test_asks.py` reads the staff roles from the staff list's description
  ("Roles: coordinator, educator, specialist."), which the new description had dropped. Restored; every engine test
  that reads the seed's config, 17 files, run again on a fresh copy: 322 passed. The local run had covered only the
  files the change touched, not every reader of the row it changed.

## UI4a merged and live (2026-10-11)

- Merged as `7a9c0c9` (#187) at the head CI had passed on (`66becf2`; the first head's engine run caught the dropped
  roles sentence, STATE "UI4a — the staff list and the search, built"). Vercel's production deploy of `7a9c0c9`
  succeeded at 19:03 UTC. `engine staff add` reaches Nimish's machine with his next `bin/update-live`.
- `bin/engine done ui4a-staff-and-search` on main's code against a database built fresh: 4 of 4 of Nimish's sentences
  PROVED, 4 of 4 criteria PASSED (41 engine tests, 50 browser tests, types and lint clean, `bin/check` 28 passed). Its
  live line: the live database does not answer from this container.

## C1 — the whole curriculum, measured (2026-10-11)

- **What Nimish saw** (Grade 2 no multiplication, Grade 3 starting at 2- and 3-digit × 1-digit, Grade 4 none) is live
  as it stands: `MUL.1D`, made on 2026-09-19 to prove a new topic could be added (Grade 3, rung M1: 2- or 3-digit × 1
  digit, 2-digit × 2-digit at Advance), and `MUL.GROUPS` (Grade 1). M2a–M4d1 replaced `MUL.1D` with ADR 0047's 17
  skills across Grades 1 to 4 on main; live has not had `bin/update-live` since.
- **On main the mapping was there and hidden:** the Curriculum tree read `skillSets()` without `untaught`, so every
  topic not switched on — every multiplication and division topic — was dropped. The tree already listed a skill under
  every grade its levels belong to (`level_band`; 2-digit × 1-digit is Grade 2 at Easy and Medium, Grade 3 at Hard and
  Advance).
- **Where the grades come from** (ADR 0047, A6): the school's own objectives in the registry (LO-G1-0046 to 0055,
  LO-G2-0492 to 0498 and 0527 to 0530, LO-G3-0942 to 0944 and 0956 to 0959, LO-G4-1339 to 1356) and the July papers.
  Grades 2, 3 and 4 repeat near-identical objectives (facts to 10 × 10; 2-digit × 1-digit by partitioning, grid and
  expanded layouts); none names 3-digit × 1-digit or 2-digit × 2-digit, so Grade 4 for those is the engine's
  assumption. Achal reviews the progression on the Curriculum (Nimish, 2026-10-11).
- **A level moved to another grade carried no name**: `saveGrades` wrote `level_band` alone.
- **The registry's text was broken in 40 places**: an "Art" → "Visual arts" rename run over substrings
  ("pVisual artsitioning", "chVisual artss", "EVisual artsh", "Visual Visual artss"), in 12 Grade 4 maths objectives
  and in art, geography and history units. The engine spec (`docs/sources/assessment-engine-spec-v0.1.md`) had named
  two of them as known.

## C1 — the whole curriculum, built (2026-10-11)

- **The Curriculum shows the whole mapping**, taught or not: every grade lists each skill with a level in it, with that
  grade's levels only, and a topic or skill not switched on says "not taught yet" on its row. Showing is not switching
  on: nothing reaches a child's paper or results until an educator switches the topic on (v1's goal sentence says so
  now).
- **A level moved to another grade carries who moved it and when** (`skill_set.level_band_by`, `level_band_at`,
  migration `20261107090000`); the skill's page says "Last moved by …".
- **The registry reads as the school wrote it:** the 40 broken strings repaired (three titles' capitals restored by
  hand: "Artist Study" twice, "Final Artwork Project"), the crosswalk's two tables and its design key with them;
  `test_registry_text.py` fails if a regenerated registry brings them back. The Skill Map Review artifact it is
  generated from carries the same breakage.
- **The spine reads the repaired registry too.** CI's engine run on #188 failed where the local run had not looked:
  `test_spine_page.py` holds `docs/spine/plan.json` to what `research/plan_build.py` builds, and the plan finds each
  objective's unit by its words in `docs/spine/sources/school_units.json`, still broken (`unit.370`, "Geometry –
  PVisual arts 2"). That table is repaired in place, every id kept, as the seats' records cite them; 12 of its 16
  broken units were halves of a unit the broken text had split in two (`unit.188` and `unit.370`; `unit.359` and
  `unit.427` — the seats had already named `unit.438` "the G4 copy of unit.303 … split off by the garbling"), and the
  plan puts such a unit's objectives under its first id. `spine.json` and the plan rebuilt by their own commands;
  the six broken words left in `spine.json` are the seats' notes quoting the breakage. `test_registry_text.py` holds
  the unit table and the plan to the registry. Every engine test that reads the registry, 11 files, on a fresh copy:
  157 passed — the local run had covered only the files the change touched.
- **Proved on copies:** `test_registry_text.py` and u19 written first and seen failing (a broken objective; no
  multiplication facts in Grade 2; no grades panel to name). C1's browser criteria on a database built fresh: 48 of 48.
  Engine: registry, loaders, topics, papers, approvals 39 passed.

## UI4b1 — a child's profile by topic, built (2026-10-11)

- **A child's page opens on their profile by topic** ("By topic", `growth/[id]/profile.tsx`): one row per taught topic
  they have answers in, its skills counted as needing help, practising, secure, too few answers, and not assessed yet
  (the rest of their grade's skills in that topic), counted by `lib/profile.ts` `byTopic` from the graph's states.
  A topic's name opens its skills further down, each topic a section of its own, those needing help first, then
  practising, then secure; the skills not yet assessed are one line under them, not a wall of grey.
- **Their papers come next and the parent report last**, its state in words: out of date, written and waiting for a
  person to approve it, not written yet, or nothing to report yet (`report-panel.tsx`).
- **Parent reports waiting on a person are one list** (`/growth/reports`): out of date first, then written and
  waiting for approval, then not written; each name opens the report. Today's "Parent reports to approve" opens it.
- **A child none of whose answers is signed off is on no one's list:** the engine writes no report from nothing
  (`parent_facts.SIGNED`), and the first draft of the list asked for one for every such child — 34 on the test copy,
  most of the school on live, burying the two waiting for approval. The list reads signed-off answers as the engine
  does (`lib/queries-reports.ts` `signed`); such a child's page says "Nothing to report yet" with no link.
- **One owner for a report's state:** the Children list had its own copy of the "out of date" query and its own words
  ("draft"). Both now come from `lib/queries-reports.ts` (`reportState`, `reportRank`, `reportWords`), so the Children
  list, a child's page and the reports list say "to approve", "to write" and "out of date" alike.
- **Proved on copies:** u20 written first and each of its three tests seen failing alone on the old code (no "By
  topic" table; no topic link to open; the page ended on "Their papers"). The goal's browser criteria, with u8 and u18
  (the Children list's report column), on a database built fresh: 59 of 59; u20 twice on one copy, 3 of 3 each.
  Types and lint clean.

## UI4b2 — measured before the build (2026-10-11)

- **The Children list** counts every taught topic together: "Needs help on", Secure and Practising are a child's
  across all of them, with no way to ask about one topic.
- **A class** (`/growth/class/[section]`) is one grid of every skill anyone in it has answered, topic headings over
  the columns: a column for every skill of every topic switched on. The tree has fifteen topics, twelve of them
  multiplication and division, not yet switched on; once they are, a Grade 3 class's grid runs to dozens of columns.

## UI4b2 — Children by topic, a class and the list, built (2026-10-11)

- **The Children list reads one topic at a time:** "All topics" or any taught topic, chosen at the top; with one
  chosen, "Needs help on", Secure and Practising are that topic's alone (`childTable(actor, topic)`), a sort keeps
  the topic, and only a taught topic narrows the table.
- **A class opens on its children against its topics** (`class/[section]/topics.tsx`): each cell counts the child's
  skills in the topic that need help, are practising, are secure and have too few answers, each count in words
  beside its mark, the cell the colour of what needs help first. A topic's name opens the skill grid for that topic
  alone, its unanswered skills and checks with it; "Every topic's skills" shows them all again.
- **One test changed with the page:** screens' "a child's page is in words" clicked the first link in a class's
  first table, a child's name until the topic grid came first; it now clicks the first child's name.
- **Proved on copies:** u21 written first, each of its two tests seen failing alone on the old code (no topic choice;
  no topic grid). The goal's browser criteria on a database built fresh: 47 of 47. Types and lint clean.

## UI5 — measured before the build (2026-10-11)

- **Assessments** (`/papers`) is one table of every child's copy, newest first, up to 300 rows, filtered by class,
  child, kind, week and stage: a class assessment for 30 children is 30 rows, and there is no topic.
- **What one assessment is:** a class's papers are each child's own worksheet of the same skill set and level
  (`w2_print/assemble.py` hands each child a different library worksheet), so a copy's template does not name its
  assessment; a kind of paper given to a class in a week on one skill set does. A school's own earlier papers share one
  worksheet and carry no skill set (their questions name none), so they have no topic.

## UI5 — Assessments by assessment, built (2026-10-11)

- **Assessments opens on one row for each assessment** (`assessmentList`): its kind, class, week, how many copies, how
  many stand at each stage in words, the answers waiting for a person, and its score across the copies that are
  checked. A class's home assessments or chosen papers for a week are one row. A row opens its copies, one row each
  ("Each paper", the list as it was), under the same filters.
- **A topic chosen at the top** keeps the assessments on that topic's skills: a paper's topics are its skill set's,
  or each of its questions' own. Only a taught topic narrows the list.
- **The stage, class, child, kind and week filters** narrow both views; a stage keeps the copies at that stage.
- **Moved with the page:** the maker's "See them in Assessments" opens each paper just made; u9's and u16's
  paper-by-paper checks open "Each paper" (`view=papers`), where that list now is. Each table is a file of its own.
- **Proved on copies:** u22 written first, each of its two tests seen failing alone on the old code (no view choice;
  no topic choice). The goal's browser criteria on a database built fresh: 46 of 46. Types and lint clean.

## C1 merged and live (2026-10-11)

- Merged as `c7731d9` (#188) at the head CI passed on (`480a89e`: the first head's engine run caught the spine's
  stale unit table, STATE "C1 — the whole curriculum, built"). Vercel's production deploy at 22:05 UTC; `migrate live`
  applied `20261107090000` at 22:34:55 after CI on main passed; the engine server redeployed at 22:36.
- **The known gap happened:** from 22:05 to 22:35 the website on live read `skill_set.level_band_by` before live had
  the column (STATE "Phase 0, PR 1", known gap: Vercel publishes on the merge itself). Put to Nimish.
- `bin/engine done c1-whole-curriculum` on main's code against a database built fresh: 3 of 3 of Nimish's sentences
  PROVED, 4 of 4 criteria PASSED (48 browser tests, 20 engine tests, types and lint clean, `bin/check` 28 passed).
  Its live line: the live database does not answer from this container.

## UI4b and UI5 merged and live (2026-10-11)

- Merged as `39dd9ca` (#189) at the head CI passed on (`f76a9cb`), all four checks green. Vercel's production deploy
  at 22:35:49 UTC. Website only.
- `bin/engine done` on main's code, each against a database built fresh: ui4b1 3 of 3 PROVED, 3 of 3 criteria PASSED
  (59 browser tests); ui4b2 2 of 2 PROVED, 3 of 3 PASSED (47); ui5 2 of 2 PROVED, 3 of 3 PASSED (46). Types and lint
  clean, `bin/check` 28 passed each. Their live line: the live database does not answer from this container.

## M4d2 — measured before the build (2026-10-11)

- **A9:** 98 story templates; 22 (M4d1's) say their own numbers; of the 76 older ones, 2 say a range and 74 take their
  sizes from the level alone. The bank on the copy holds "has 9685 marbles" (JOIN_RESULT to 9685), 93 × 96
  combinations of stickers and backgrounds, rows of 98 chairs, 3442 mangoes put in a basket. Every one of the eleven
  shapes Grade 4's additions and subtractions draw reaches four digits; none of the older stories' worlds holds them.
- **The rest of M4d2** (`story_shape` for × and ÷ with its eval, halving on Division, the A11 table) is unchanged
  since "M4d — measured before the build". Split: M4d2a the ranges, M4d2b the rest.

## M4d2a — every story's numbers fit its story, built (2026-10-11)

- **Each older template says its range** (`range` in `assess/word_templates.json`): a child's marbles to 300, a bus's
  seats to 60, a box of pencils to 24, a rickshaw holds six, a library's books to 9999. A question of numbers alone
  (`bare_sum`) has none to say.
- **The level sizes the numbers and the story must hold them** (`words.fitting`, ADR 0070): where the drawn template's
  world does not hold the level's numbers, another of its shape and operation that does is drawn; where none does,
  the numbers are drawn again. The + and −, ×, two-step, ÷ and equal-groups stories all draw this way.
- **Twelve stories whose numbers run to four digits** (a library, a mela's visitors, a stadium, a school's fund, a
  day's steps, a fair, a toy factory, a shop's notebooks, a train's passengers, a park's flowers), so every case
  Grade 4's additions and subtractions list still draws. The park was added when SUB.3D1D and SUB.3D2D's part-whole
  case (W08) drew nothing: none of its stories held a 3-digit whole with a 1- or 2-digit part.
- **A stored story outside its range is outside its level** (`cases.outside_their_level`), so `bin/update-live`'s
  refill retires it and `library build` replaces the worksheets that held it.
- **Tests that called a maker directly now draw as the bank does** (`tests/rows.drawn`, shared): `test_story_keys` and
  `test_rehome` retry a story whose numbers no template of its shape holds, as `draw._paired` and `bank.fill` always
  have.
- **CI caught a fifth path the local run did not reach:** the bank's offline sampler (`bank._sampled`, `engine bank
  fill --offline`) chose any story of its operation for its numbers; it now chooses among those that hold them, and a
  pair none holds is not drawn as a story. Seen failing three runs in three on the old `bank.py` (`test_bank`'s recheck
  named the story it had just made), passing on the new. Locally the copy's bank was drawn before ranges: `engine bank
  refill` retired 745 stories outside their ranges and drew 744 in their place, as `bin/update-live` will on live.
- **Proved:** `test_story_ranges.py` written first: the template test seen failing (159 numbers with no range); the
  every-level test seen failing with the ranges in place and the old makers ("Anaya has 601 marbles", "407 mangoes in
  a basket … 3442 more", "A shelf holds 61 books"); the bank test seen failing on the old `cases.py` (the story named
  for another reason, never its range). The goal's criteria with a database: 137 passed.
- **Not proven here:** `story_shape` shows each shape with every one of the engine's + and − stories as its examples,
  so the twelve new stories change what the active prompt is shown. Its eval needs the model, which this container
  cannot reach; it runs again on the server once deployed (engine-eval.yml), held to its bar (63 of 65, no wrong
  answer).


## M4d2b — measured before the build (2026-10-12)

On main `2468dd2`. Three parts, each measured:
- **`story_shape` reads + and − alone.** v1 offers the 18 shapes of the + and − story cases; the taxonomy holds 27 × and
  ÷ story cases (B01–B27). Four of them are one shape (GROUPING) told apart by what the story does with what is left
  over (B14–B17), beside exact grouping (B03); three shapes are shared by two cases each: an array that multiplies and
  one that divides (B04, B05), a price and a price list (B06, B26), and a number the story does not need, + and − or ×
  (W25, B25). A choice keyed by shape cannot name them. The gold: 65 stories, all + and −. `engine eval story_shape`
  always scores the active version.
- **Halving:** `skills.operations` reads a two-step story's `op`, never its `divide`: "Two numbers add up to {a}. One
  of them is {b} more than the other. What is the smaller number?" (`divide: 2`) counts on subtraction alone.
- **A11:** 35 of the × and ÷ mistake rows charge the question's operation and name no skill; `skills.charges_by_kind`
  says what M_WRONG_OP charges on a story and nothing else; `skills.charges_by_kind.approved` is empty.
- **Split** (BUILD-ORDER): M4d2b1 the reader of × and ÷ stories, a new version built switched off with its gold, scored
  on the server before it answers; M4d2b2 switches it on with its score, halving on Division, the A11 table.

## M4d2b1 — the story reader reads × and ÷, built switched off (2026-10-12)

Goal `goals/md4d2b1-times-story-shape.yaml`, ADR 0071.
- **`story_shape` v2** (`supabase/seed/prompts/story_shape.v2.txt`, inactive) chooses among all 45 story cases, + and −
  and × and ÷, each shown with every one of the engine's own stories of it. A case sharing its shape with another is
  offered under a name of its own, the first of what sets them apart (`_keys`): GROUPING and GROUPING_ROUND_UP,
  ARRAY_MUL and ARRAY_DIV, RATE_TOTAL and RATE_TOTAL_TABLE_OR_CHART (shown with its price list), EXTRA_INFORMATION and
  EXTRA_INFORMATION_MUL. Which taxonomies a version reads is its row's (`json_schema.taxonomies`); v1's row says none
  and reads + and − alone.
- **Code works the answer:** × the two numbers; ÷ the larger by the smaller, what is left over used as the case says
  (`divide_stories.answered`, which the story maker's boxes now use too: the full boxes, one more rickshaw, the
  remainder, or both, the remainder returned beside the answer); twice and half as many × and ÷ the 2 their stories fix.
- **Code holds Jev to the numbers:** a case that says nothing is left over, read for numbers that leave some, is a
  person's ("47 ÷ 5 leaves 2 over"); a remainder dropped or rounded up, read for numbers that leave nothing, is exact
  grouping (B03); a one-step × question over three numbers is B25, as a + and − one is W25.
- **The gold:** 81 new stories, three for each × and ÷ case, in words no template uses; every one-step answer worked by
  the test apart from the engine, and by the engine, and the two agree. A reader naming every case right scores 146 of
  146 with no answer wrong, so the gold and code's checks of the numbers agree too.
- **The eval scores a named version** (`engine eval story_shape --version 2`) on the gold of the taxonomies it reads:
  v1 on its 65, as its bar was set; v2 on all 146.
- **v1 answers as it did:** its 18 options and every word it is shown are the same, compared before and after. Found
  and fixed: its two table stories ("The table shows the runs Asha scored") counted as printing no number, so a story
  with none written as digits passed for those shapes; a table's numbers are counted now.
- **Proved:** `test_story_shape_times.py` written first, seen failing on the old module (8 of 9; the gold's own test
  passed, the gold written first); the goal's criteria with a database: 198 passed.
- **Not proven here:** v2's score. It needs Jev, which this container cannot reach; it runs on the server once
  deployed (engine-eval.yml, story_shape, version 2), held to v1's bar (0.9692 right, no answer wrong), before it is
  switched on (M4d2b2).

## L1 — Jev stays on live, found and fixed (2026-10-12)

Goal `goals/l1-jev-stays-on-live.yaml`.
- **Found:** the server eval of `story_shape` (run 38187513234) asked Jev nothing: "no TYPESAFE_API_KEY in the engine's
  environment"; the engine logs (run 38187566481) said the same. Every judgement Jev makes on live (a story's shape, a
  mistake guessed, the week's skills, the parent-report checks Jev reads first) had gone to a person since the key
  went, and the watch said nothing.
- **Cause:** `deploy/go-live.sh`, which every `bin/update-live` runs, swapped the server's folder for the new code (the
  old .env with it) and wrote a .env of the Mac's three settings alone. Jev's key is the server's alone.
- **Fixed:** the swap carries the server's .env across, as `deploy-engine.yml` always has, and the Mac's settings are
  written over it, every other line kept (`test_going_live_keeps_the_servers_own_settings` runs go-live's own command).
  The live watch says "Jev's key is missing on the engine" when it is.
- **Nimish put the key back by hand** (2026-10-12, the server's .env, then deploy engine by hand): the engine logs (run
  for 05:40 UTC) say `TYPESAFE_API_KEY is set`. A re-run of a merge's deploy does not restart the engine: it finds
  nothing changed in the code and stops; only Run workflow does.
- **Found next, fixed:** with the key back, both versions of `story_shape` crashed on live (runs 38209061747,
  38209096119: KeyError 'taxonomy'). Live's case rows predate M1, which also names each row's taxonomy inside its match;
  `story_shape` v2's code read it there. It reads each row's own column now. `bin/update-live` brings live M1's rows and
  the × and ÷ cases with them: live has none of multiplication and division until it runs (STATE.md "NY — measured").
- **Proved:** the three tests written first, each seen failing on main `df851fc` for its own reason; `bin/check` 28 passed.

## M4d2b2 — measured before the build (2026-10-12)

On main `0af28cd`, the local copy's bank (28,483 generated questions, labels recomputed: none stale):
- **A question of two operations charged a mistake to its first skill.** `skills.charges` looked a mistake up by the
  question's operation only when it had one; with two, a mistake with a row for one of them fell through. "Check 42 ÷ 3
  = 11 by multiplying" (`inverse_check`, ÷ and ×) charged times-table slips to Division; a fact family's division slips
  went to Multiplication or the fact family's own skill; the bar model's "leaves the smaller one's part out", whose row
  names Word problems, went to Division.
- **Halving never counted on Division:** `skills.operations` read a stored two-step story's copy of its operations
  before its template, and the template's `divide: 2` was never read.
- **What is left to a choice:** with those put right, the only × and ÷ mistake still landing on a question's own skill
  by default is choosing the wrong operation in an equation or a fact family (Mental maths & missing-number equations).

## M4d2b2 — a slip counts against the operation it happens in, built (2026-10-12)

Goal `goals/md4d2b2-what-a-slip-charges.yaml`, ADR 0072.
- **The rule:** in a question of several operations, a mistake with a row for exactly one of them is charged as that row
  says. A two-step story's operations are its template's, its halving among them.
- **The table** (`skills.charges_by_kind`) names the choice left: choosing the wrong operation in an equation or a fact
  family counts against the equation's skill, as a story's counts against Word problems. The approval page says the rule
  in one sentence above the table. It waits for one approval (A11), as it did.
- **On the bank:** 584 charges move. 530 are on × and ÷ questions, each to the operation the slip happens in, the skill
  its row names, or the table's row; 54 are + and − equations, choosing the wrong operation now counting against the
  equation's skill instead of Addition or Subtraction (the table's row, the same slip). 33 halving stories gain Division.
  `bin/update-live`'s `bank relabel` writes them on live. First reported as "no + or − charge moves": measured before the
  table's rows were added; `engine audit` on the copy showed the equations, measured again.
- **Proved:** `test_md_charges.py` written first, seen failing on main `0af28cd` (5 of 6, each on the measured fault).

## M4d2b2 — the halving retired 33 stories, found after the merge and fixed (2026-10-12)

Goal `goals/md4d2b2-what-a-slip-charges.yaml` (two promises added).
- **Found** on the local copy (`test_goal::test_every_invariant_holds`), then in the audit Nimish's `bin/update-live`
  printed: counting the halving in "Two numbers add up to 605. One of them is 71 more …" on Division (M4d2b2) also made
  `tags.derive` read the story as × and ÷, since a question's taxonomy was "MUL_DIV when its operations hold × or ÷". The
  33 such stories, W29 of the + and − document (its row names ADD_SUB), then fell outside WORD.1_2STEP Advance, the level
  that holds W29: `engine bank relabel` → tags 33 changed; `outside_their_level` → 33; the refill retires them and cannot
  make new ones.
- **The cause and the fix:** the halving is an operation the child carries out (it counts on Division, A11), not what the
  story is about. `skills.operations(..., halving=False)` gives the story's own operations, and the taxonomy is read from
  them. On the copy: `engine bank relabel` → "tags: 33 changed · cases: 33 changed"; `outside_their_level` → 0.
- **Why the rehearsal did not see it:** `rehearse-update-live.yml` left out the audit `bin/update-live` prints
  (`NOT_REHEARSED = {"audit"}`, read as only "what waits on a person"). It runs it now, and
  `test_the_rehearsal_runs_what_update_live_runs_in_its_order` holds it to that (seen failing without it: "update-live
  runs ['audit', 'live data'] where its rehearsal does not").
- **`engine audit` says each check as it finishes** (`audit.each`): on live, from a Mac, the sweep takes minutes and
  printed nothing until the end, and looked stuck. `test_the_audit_says_each_check_as_it_finishes`.
- **On live:** stories retired by the update-live run after #193 come back with the refill of the next `bin/update-live`,
  once this is merged.
- **story_shape v2's live score** (run 38215303003): named 144/146, the shape right on 140, one-step answers computed 99,
  wrong 0, 2 left for a person — 0.9589, below its bar 0.9692; not switched on. Of the six, v1 missed the same two + and −
  stories on live (run 38212446549): "305 tickets … 187 were sold" (gold W04, both read W08) and "I am thinking of a
  number. If I take away 25 and then add 40, I get 100" (gold W29, both read W28, "the unknown in the first step — work
  backwards", which is what the case row says it is). Correcting the gold changes v1's score and so the bar: M4d2b3.

## UI6 — measured before the build (2026-10-12)

Nimish, with a screenshot of Curriculum → skills to approve: "also ths page needs to have proper filters and all; no page
should have such laundary lists like stuff". Every page under `apps/web/app/(app)` read for lists that grow with the data,
each item in full, nothing to narrow them (counts for about 170 children in 8 classes, 60 skills):
- **`/skill-sets/approve`:** a Panel of about seven lines per waiting skill (up to 61 on live), grouped by grade and
  nothing else; one button approves every skill and the mistake table together. UI6a.
- **`/growth/[id]`:** every paper ever made for the child, 3–4 lines each, growing weekly; the answers to check as full
  cards with their scans; repeated mistakes, nothing to narrow any of them. UI6b.
- **`/today`:** "Parent reports to approve" can name up to 170 children as links; class packs uncapped. UI6b.
- **`/asks`:** the answered questions, 2–3 lines each, growing for ever (the open ones are already one line). UI6b.
- **`/papers/approve`:** one chip per class, week and kind ever planned, about 16 more a week. UI6b.
- **`/growth/reports`** (up to 170 rows, no filter) and **`/library`**'s proposals (forms of several lines, as many as
  the engine returns). UI6b.
- Already narrow: Assessments, the Question bank, Worksheets, Children, a skill's page, the check queue.

## UI6a — approving the skills as a table to work through, built (2026-10-12)

Goal `goals/ui6a-approve-filtered.yaml`.
- **One row a skill:** its name, grade, topic ("Not taught yet" where it is not), what a child can do, its levels folded
  under "Read the levels", its own "Approve, as …" and "Change the words first". A row is about a third of a card's height.
- **Choices at the top, each with how many wait under the others:** grade (chips), topic and taught (selects). "Approve
  these N skills" approves exactly the rows shown, and the page comes back under the same choices
  (`APPROVE_PAGE` in the action: the approval page and its three choices, nothing else, is a return address).
- **The mistake table is approved by a press of its own** ("Approve this table as written"); a press meant for some
  skills never approves it. Its rows are folded under "Read the N".
- **Proved:** `u23-approve-filtered.spec.ts` seen failing on the old page ("Expected [ADD.1D1D, ADD.2D2D, DIV.3D1D,
  SUB.2D2D], Received []"); with the page, it and the specs that approve a skill or the table (u17, u13, s2) and every
  screen: 46 passed. `tsc` and `eslint` clean.

## L2 — live's audit, measured on a copy, and the guessable ticks drawn again (2026-10-12)

Goal `goals/l2-live-audit-clean.yaml`.
- **Measured** on a copy of live with #195's code (the rehearsal, run 38223287194, which now prints the audit):
  `19 invariants checked, 41 violations`.
  - 31 skills not approved; the mistake table not approved. Both are a person's.
  - **Six groups answered by ticking one place:**
    - REASON.EXPLAIN's four levels: 216 of 216 each "yes" or each "no";
    - ESTIMATE.HUNDRED Advance (sense): 108 of 108;
    - REASON.FIND_MISTAKE Hard (where): 45 of 54.
    `bank levels --apply` changed nothing: live already holds the corrected levels (DECISIONS-LOG 2026-09-29). The
    questions were made before the correction. Each is a fair question on its own, so no per-question rule retired it,
    and approving a level retires none either. HANDOFF had said they close by approval; they do not.
  - ADD.1D1D Easy 106 of 108 and SUB.2D1D Hard 67 of 72. Both are full on a copy built from the repository (108, 72).
  - Rung R9: no skill holds it.
- **Fixed, the ticks:** `refill.redraw_unfair` retires a group the audit names when its level, drawing today
  (`fill_cases` or `fill_native`, dry run, 3 × `min_questions`), places the answers fairly; the top-up draws it again.
  A level whose own design fixes the answer draws no fairer and is left for a person. One reading of the group, shared
  by the audit and the refill: `inventory.tick_places` and `inventory.unfair`.
  - Tests: `test_refill_fair.py`, both seen failing first (`refill` had no `redraw_unfair`). Then 2 passed, with
    `test_audit.py`: 5 passed.
  - `engine bank refill` says "N answered in one place, drawn again".
- **Not yet explained:** the two short levels and R9. The rehearsal now lists each short level's retired questions with
  why, and what still points at a rung no skill holds, so the next run names the cause.
- **Rehearsed with the redraw** (run 38227555987, a copy of live):
  - `bank refill` → "retired 0 questions outside their level · 972 answered in one place, drawn again · added 972"
    (REASON.EXPLAIN's 4 × 216, ESTIMATE.HUNDRED Advance's 108).
  - Audit: `19 invariants checked, 36 violations`; the tick lines went from 6 to 1.
- **REASON.FIND_MISTAKE Hard (where), 45 of 54, was left:** the level asks "where" on about one question in four, so
  a single draw of 120 held fewer than 40 to judge it by. Today's spread is fair (300 drawn on the copy: 43 at option
  2, 32 at option 3). Now the level is drawn until it has enough (`refill._places_now`;
  `test_a_kind_the_level_asks_now_and_then_is_drawn_until_it_can_be_judged`).
- **The two short levels:** each level's non-active questions number exactly its shortfall:
  - ADD.1D1D Easy: 2, keys `ADD.1D1D.REG0-…`;
  - SUB.2D1D Hard: 5, keys `SUB.2D1D.REG1-…`.
  None has a retirement note. They carry the template today's draws use, so they hold the very keys the level would
  draw, and a level whose whole region is its target (`min_items` 108, 72) cannot be refilled.
  The rehearsal now shows each one's status, source, generator and dates, so the cause is known before the fix.
- **R9:** one active question still points at it (`questions 1 · active 1 · answers 0`). That is why rehome could not
  remove the rung. The rehearsal now names that question.
- **Rehearsed again** (run 38228886028, a copy of live):
  - "1026 answered in one place, drawn again" (FIND_MISTAKE Hard's 54 with the rest).
  - Audit: `19 invariants checked, 35 violations`. No tick line is left: 31 skills, the mistake table, R9, and the two
    short levels.
  - What the rehearsal named:
    - the 7 questions holding the short levels' keys are `generated · retired · pre-provenance · made 2026-09-18`,
      each with no `item_feedback` row, so no reason was recorded;
    - the one question on R9 is `legacy/G2-CAM-A/5`: active, no skill, on the old ladder's R9, an "Emyr did not
      finish his calculation" item. The paper's file now has 5a–5c on R31 instead.
- **Fixed, the short levels:** `refill.top_up` first takes back the level's retired questions that carry no recorded
  reason and that its rules as they stand still hold (`refill.reinstate`, `cases.holds`, shared with
  `outside_their_level`). One retired by a person or a rule, its reason recorded, stays retired. Both tests seen;
  the first failed without the change (`['retired', 'retired'] == ['active', 'active']`).
- **Fixed, R9:**
  - `legacy.load_paper` makes a paper's rows follow its file (`w3_read/paper_file.py`). A question the file no longer
    has is removed when nothing points at it, and retired when an answer or a correction does. `legacy.py` is 639
    lines, its frozen ceiling lowered from 652.
  - `rehome` removes any rung that no skill, question or placed answer holds, not only the replaced sets' rungs.
  - Three tests, each seen failing on its fault ("'legacy/TEST-PAPER/5' not in …", "'active' == 'retired'",
    "'TEST.ORPHAN' in []").
- **Proved:** refill, audit, update-live, taxonomy, bank, paper, rehome, story-range and layout tests on the copy:
  **786 passed**.
- **Rehearsed again** (run 38231324999, a copy of live), `19 invariants checked, 33 violations`:
  - "1026 answered in one place, drawn again · added 1034": the 7 came back, and every unit meets its target.
  - Left: 31 skills, the mistake table, and R9.
  - `legacy/G2-CAM-A/5` was retired, not removed: something points at it (its old answers or the page's hand-read
    gold), so it stayed on R9.
- **Fixed:** a paper question that has to stay moves to the rung its number has in the file, as an old paper's sum
  moves to its skill. G2-CAM-A's 5 goes to R31, the rung of 5a–5c, and R9, held by nothing, leaves with the rehome.
  `test_a_question_something_still_points_at_is_retired_not_removed` now asks for the move; it was seen failing
  first (`'X1' == 'X2'`).
- **Rehearsed with every fix** (run 38232539519, a copy of live with #196's code):
  - rehome "removed 0 skill sets and 1 rungs" (R9);
  - refill "1026 answered in one place, drawn again · added 1033";
  - audit `19 invariants checked, 32 violations`: only "every spec is ratified → 31" and "what a mistake charges is
    approved → 1". Every rung has a spec, every unit meets its target, and no choice is answered by ticking one place.
  - What is left is the coordinator's approval of the 31 skills and the mistake table, on Curriculum → skills to
    approve.

## UI6b — no other page a laundry list, built (2026-10-12)

Goal `goals/ui6b-no-long-lists.yaml`. Each list measured in "UI6 — measured before the build" now shows what is needed
first; the rest is one click away, or narrowed by a choice:
- **A child's page:** their five newest papers, then "Every paper of this child, N in all →", which opens Assessments
  filtered to the child.
- **Today:** the first five classes or children under a line, then "and N more →" to the page that lists them all
  (Approve papers, Parent reports). The menu's counts are unchanged.
- **Questions to answer:** the answered ones folded under "Read the N answered".
- **Approve papers:** the latest two weeks' classes by name; the weeks before them under "Earlier weeks (N)", open
  when the pack shown is one of them.
- **Parent reports:** "Every class" and one chip a class, each with how many wait.
- **Proved:**
  - `u24-no-long-lists.spec.ts`: each of its five tests was seen failing on the old pages, alone, on its own fault.
  - With the pages: those five, and the specs of every page they touch (u20, u1, u15, u13, u17, s7, u22, u2,
    screens), 72 passed.
  - `tsc` and `eslint` clean.
- **Not changed, not yet measured:** the library's proposals (`library/proposals.tsx`). Every proposal the engine
  returns is shown as a form of several lines, neither folded nor capped. How many wait on live is not known; the
  next rehearsal counts them before any change.

## M4d2b3 — the story reader's gold corrected, each miss read with Jev's ranking (2026-10-12)

Goal `goals/md4d2b3-story-gold-corrected.yaml`. Of `story_shape` v2's six misses on live (run 38215303003), three were
the gold's, each held to its case row's own words rather than to the reader:
- "I am thinking of a number. If I take away 25 and then add 40, I get 100": W29 → W28 ("the unknown in the first step
  — work backwards").
- "305 tickets … How many tickets were not sold?": W04 → W08, the form of the football story already W08.
- "a ruler costs ₹12 and a sharpener ₹8": B26 → B25. No list is printed; B26 is `context: TABLE_OR_CHART`.
- **Not moved:** the canteen's list ("Canteen prices: idli ₹10 a plate, dosa ₹30 a plate") stays B26. It is a list,
  so the reader's B25 there stays a miss.
- **Added:** a W29 story with several conditions and a B26 list ("Fruit stall: orange ₹12 each, guava ₹8 each"),
  keeping three in each case. The gold now holds 148 stories; v1 reads 66 of them.
- **Each miss says what Jev leaned to:** `engine eval story_shape` prints Jev's first three choices and how sure under
  every LEFT and MISS. Before, the two stories left for a person (Jev 0.54 and 0.53 sure) printed only the first.
- **Proved:**
  - `test_story_shape.py`, `test_story_shape_times.py`, `test_bars.py`, `test_layout.py`: 36 passed.
  - Before the change, five of them failed on the old gold and the old eval, each on its own fault.
- **Not yet known:** v1's and v2's scores on the corrected gold. They are taken on live once this is deployed
  (engine-eval.yml). The bar (0.9692) is unchanged until then. Expected, not measured: v2's three remaining misses on
  the old run (two left for a person, the canteen) would score about 145 of 148.

## M4d2b4 — `story_shape` v2 switched on (2026-10-12)

Goal `goals/md4d2b4-story-shape-v2-on.yaml`. Nimish, 2026-10-12: "switch v2 today and finish this module".
- **Scored on live on the corrected gold (M4d2b3), before the switch:**
  - v2: named 146 of 148, the case right on 144, one-step answers computed 99, wrong 0, left for a person 2
    (run 38251975489).
  - v1: 66 of 66 on the + and − stories it reads (run 38251971707).
- **The switch:** `prompts.json` makes v2 the active version and keeps v1 as the record. Every deploy loads the
  settings, so live answers with v2 once this is deployed.
- **The bar:** 0.9729, v2's 144/148 rounded down. 144/148 is 0.97297…, so a bar rounded to 0.973 would have failed
  v2 on its own score; `test_bars.py` caught it.
- **What v2 still misses or leaves (Jev's first choices, now printed by the eval):**
  - Kabir's runs (W01): Jev 0.54 two parts of a whole, 0.44 joined. Left for a person, though the answer is 84 either
    way.
  - The plant (B24): Jev 0.54 grouping, 0.46 "each" that means ÷.
  - The canteen's and the fruit stall's price lists (B26): Jev 0.71 and 0.82 one price, then code read the second
    price as a number not needed (B25).
  - The cause of the last three: the prompt tells Jev to read "not the words it uses", and those two pairs of cases
    are told apart by their words and their layout. Fixed at that cause in M4d2b5.
- **Proved:** `test_story_shape.py`, `test_story_shape_times.py`, `test_bars.py`, `test_bank_routes.py`,
  `test_divide_stories.py`, `test_layout.py`: 55 passed. The switch's own test failed before the switch.

## M4d2b5 — the story reader settles by code what code can read (2026-10-12)

Goal `goals/md4d2b5-story-told-apart.yaml`. On live (run 38251975489), v2's four misses, with Jev's ranking:
- **Two pairs differ only in print, and the prompt tells Jev to read "not the words it uses":**
  - The plant: 0.54 grouping (B03), 0.46 "each" that means ÷ (B24).
  - Both price lists: 0.71 and 0.82 one price (B06). Code then took the second price for a number not needed (B25).
  - These are now code's (`w1_bank/story_cases.py`). "each" or "every" makes grouping B24, a config row
    (`story_shape.told_by_words`). A colon then two numbers or more makes a price a price list, B26. Jev's certainty is
    the sum over the pair.
- **Kabir's runs:** 0.54 two parts of a whole, 0.44 joined. Which case it is stays a person's. But both work
  46 + 38 = 84, so the answer is given ("it's 84", Nimish).
- **The gold held to the same rule, every story, not just the misses:** "A gardener plants 54 saplings, 6 in each row"
  was B03, though it says "each". Moved to B24, and a B03 story added: 149 stories.
- **Proved:**
  - Before the code, the four new tests failed on exactly the live misses.
  - After it: `test_story_cases.py`, `test_story_shape.py`, `test_story_shape_times.py`, `test_bars.py`,
    `test_bank_routes.py`, `test_divide_stories.py`, `test_layout.py`: 62 passed.
- **Split:** reading a story and scoring the reader are two jobs. The gold and the eval moved to
  `w1_bank/story_eval.py` when this work brought `story_shape.py` to 401 lines, over its 400 ceiling.
- **On live once deployed** (run 38307557335): 148 of 149 in the right case, 102 answers computed, none wrong, one
  left for a person — Kabir's runs, answered 84. The plant and both price lists are right.

## M5 — measured before the build (2026-10-12)

What each stage of the loop already is, and what nothing yet proves:
- **No test or scenario runs the whole loop, for any operation.** `engine goal` runs two kinds of scenario, `bank` and
  `week` (`checks/scenarios.py`); there is none that reads, marks or rebuilds a graph. `goals/w4-close-the-loop.yaml`
  names `tests/test_close_the_loop.py`, which does not exist.
- **Printing:**
  - Class packs (`prescribe` → `assemble`), library worksheets (`library`), and a child's own paper (`focus_paper`).
  - A child's own paper and the paper maker draw only from taught topics (`shelf.py`), and every × and ÷ topic starts
    switched off (`topics.json`).
- **Reading:**
  - The closest pattern reads a library worksheet with the handwriting reader stood in (`test_every_answer.py`).
  - `copies.read` reads library worksheets only. A child's own paper (`source='focus'`) is skipped when a class scan
    is read, and nothing says it was.
- **Marking and naming:**
  - `marking.mark` names a mistake from the question's own stored wrong answers, which exist for + − × ÷.
  - The engine's own wrong reading waits for a person (`mark_read`).
  - `confirm_results` writes the evidence, and `graph.rebuild` the child's graph.
- **The next paper:**
  - `focus_paper.plan` aims a child's home paper at their repeating mistake.
  - A class pack's `misconception_targets` are stored by `prescribe` but not read by `assemble`.
- **What a person reads:**
  - The class card names a mistake by its operation's name (`mistake_names`). The parent facts carry its name and
    what the school does.
  - The parent check's list of words that name nothing has "addition" and "subtraction" but not "multiplication"
    or "division" (`parent_check.NAMES_NOTHING`).
- **56 × 3 = 1518:** the predictor (`mul_mistakes.concat`) is tested. The sum on Aseem's own paper (G3-QUIZ20, question
  18) has never been put through reading, marking and the graph.
- **The files-per-workflow score:** defined in BUILD-ORDER and ADR 0047. Nothing computes it yet.
- **Split:** M5a, the loop for every new skill at every level; M5b, a paper printed for a child read back (found by M5a,
  below); M5c, 1518; M5d, the website; M5e, the score.

## M5a — every × and ÷ skill at every level round the loop (2026-10-12)

- **What runs:** `tests/test_the_loop.py`, one case per skill set and level, 17 skill sets × 4 levels.
  - Each worksheet is printed for one child as an educator does on the site (Make papers, `handout`).
  - A mistake is planted wherever the worksheet's questions can show it, the key everywhere else.
  - The scan is read by the code on the copy, the handwriting reader stood in.
  - Then: held answers confirmed, signed off, evidence, graph, the child's next paper, the class card, the parent facts.
- **Proof:** `cd packages/engine && uv run pytest -q tests/test_the_loop.py` → 67 passed, 1 skipped in 151 s
  (MUL.GROUPS has no Hard level).
- **What it found, each fixed at its cause:**
  - **The test for 3 charged the wrong skill.** A slip adding the digits counted against multiplication.
    `multiples.ops` now says the test for 3 adds, then multiplies, and `skills.operations` reads it first, so a stored
    question is charged rightly too (`test_md_charges.py`). On live, `bank relabel` corrects the stored charges.
  - **The next paper could not show the mistake it was for, at two levels.**
    - Dividing a number by itself and writing 0 shows only on MD.EQUALITY's Easy questions. A child mostly right is
      given Medium, and the paper looked only upward. It now moves down to the nearest level that can show it.
    - Reversing an equation's claim shows at Medium only in another skill's division check. The paper draws the child's
      own skill first, so it never showed. The level is now chosen where the child's own skill can show the mistake.
    - Both are in `focus_paper._where_it_shows`, and `test_focus_paper.py` has a test for each.
  - **The parent check refused "the multiplication question".** It names no single question, as "the subtraction
    question" does not. "multiplication" and "division" were added to `parent_check.NAMES_NOTHING`
    (`test_parent_report.py`).
  - **A paper printed for a child is not read back when it is not a library worksheet.** Every paper the paper maker
    prints, and every home paper, is `source='focus'`. `copies.read` keeps library worksheets only, and that is the site's
    only door (`inbox.read`). Such a copy is dropped without a word. This is M5b.
- **Not a break:** a class pack's `misconception_targets` are stored by `prescribe` and read by nothing. The agreed
  workflow aims a repeated mistake in the home paper (N11), which this proves; a class pack is a skill set at a level
  (N5, N6).
- **Its cost in CI:** about 2½ minutes. The first version printed the worksheet bare and named the child, so every copy
  was first matched against each layout the worksheet has printed in (`boxes.as_printed`, 8 of 17 s a level). A copy
  printed for a child carries its own PDF, and that is the copy this proves.

## M5b — a paper printed for a child comes back (2026-10-12)

- **Read now, by the code on it:** every copy of a paper drawn for a child (`source='focus'`: the paper maker's three
  kinds and a home paper), against its own template and the PDF printed for that child.
- **A spare** (a class pack's copy with a code and no child) is read by the name said for it, as a bare worksheet is.
  It then becomes that child's copy, and its questions count as seen by them (`copies._given`). Before, a spare was in
  no line of what the reading returned.
- **Every copy in a scan has a line.** One not read says why:
  - no code read;
  - a kind of paper not read from a scan;
  - a code this school did not print;
  - no child said;
  - the PDF printed for the child is not kept.
- **Split:** `copies.py` reached 407 lines. What a copy is read against (the paper as printed, its boxes, which PDF)
  moved to `w3_read/printed_paper.py`; whose a copy is and reading it stay in `copies.py` (275 lines). `copies.read`
  is now within the complexity limit, and its frozen exception is gone from `workflows.json`.
- **Proof:**
  - `tests/test_the_loop.py`: every level now goes round twice. The child's next paper is printed, the mistake made
    again on it, read back by its code, named and counted.
  - `tests/test_read_back.py`:
    - the maker's three kinds, each read onto each child's own copy;
    - a copy whose PDF is gone, named with why, while the rest of the pile is read;
    - a spare read for the child named, and without a name reported.

## M5c — Aseem's 56 × 3 = 1518 (2026-10-12)

- **Proof:** `cd packages/engine && uv run pytest -q tests/test_aseem_1518.py` → 1 passed. No engine change was needed.
- **The path:**
  1. G3-QUIZ20 is entered from its file in `supabase/seed/papers`. Question 18, "56 x 3", is filed on R38 (MUL.2D1D's
     rung) by its shape. Its key is 168, and 1518 is its stored `M_MUL_CONCAT`.
  2. Read as 1518, a person confirms it as written, and the paper is signed off. It is then marked wrong, named
     `M_MUL_CONCAT`, and counted on R38 for NUM.OPS.03.
- **What the graph says, and when:**
  - After one paper: one wrong answer on R38, not yet repeating.
  - After two: `M_MUL_CONCAT` is named as repeating, but the rung is still "not enough yet". The graph judges a rung only
    from `state.min_events` answers, which is 3, and G3-QUIZ20 asks one 2-digit × 1-digit sum.
  - After three: `patterned_error`, and the child's next paper is MUL.2D1D, aimed at `M_MUL_CONCAT` with questions that
    can show it.
- **Not proved here:** reading the child's own handwriting. The scan is not in the repository (rule 6), so the reader
  is stood in; reading is scored by `engine eval`.

## M5d — the website draws every × ÷ kind (2026-10-12)

- **Proof:** `cd apps/web && npx playwright test tests/m5-every-kind-draws.spec.ts` → 1 passed, 57 s, on the local copy.
  No website change was needed.
- **What it checks:** all 80 pairs of a × ÷ skill set and a kind of question the bank holds, with their topics
  switched on. Each must:
  - be one of the kinds an educator can pick, which only a kind with a name in the school's words is;
  - list its questions;
  - show its numbers in each question, written or in a picture's label ("5 rows of 3");
  - never show "undefined", "NaN", "null" or a code.
- **Shown able to fail:** with lattice's name taken out of `KIND`, it failed on `MUL.2D2D lattice`. Two earlier
  versions of the check passed with the name missing, and were rewritten:
  - The first looked for "_" in the Kind column, but a kind with no name shows the bank's own, and "lattice" has none.
  - The second read the kind from the filtered page's links, but its level chips carry the kind too.

## M5e — the score: files each × ÷ slice changed, per part of the map (2026-10-12)

`bin/engine slices` reads the repository's history (`engine/checks/slices.py`; `tests/test_slices.py`, 3 passed).
- A slice is the name a commit's title starts with, and its record counts as its own.
- Each file it changed is placed by `workflows.json`, and counted once per slice.
- M2c has no row of its own: its re-homing shipped inside M2a (see "Why this order").

Output on this branch, 2026-10-12, with M5a–M5d on PR #201:

```
  slice    files       W1       W2       W3       W4   assess     core   checks    doors  website     rows   schema      map    tests research       ci     docs
  M0a         31        1                14        1        1                 1                 4                 1                 4                          4
  M0b         34        3                 1                17        1                                   3        1        1        3                          4
  M0c         23                 2                                   1                          8        1        1                 5                          5
  M1          24        3                                   3        1                          1        2        1        1        4        2                 6
  M2a         53        2                 1                13                                           10                 1       12        2                12
  M2b         25                                           10                                            2                 1        3        2                 7
  M2d1        40                                           16                                   3        7        1        1        5        1                 6
  M2d2        44        3                                  13                 1                 2        4        1        1       10        2                 7
  M3a         52        2                 1                17                 1                 1        6                 1       14        2                 7
  M3b1        26                                            6                 1                 1        3                 1        5        2                 7
  M3b2        21                                            8                 1                 1        1                 1        4                          5
  M3b3        38        2                 2                12                 1                 1        3                 1        9                          7
  M3c         37                                           11                                   3        7                          9        2                 5
  M3d         49        2                                  19                 1                 2        4        1        1        9        2                 8
  M4a         36                                           13                                   1        6        1        1        6        1                 7
  M4b1        22                                            2                 1                          6                 1        4        2                 6
  M4b2        32                                            7                 2                 1        6        1        1        5        2                 7
  M4c         31                          4                 5                 2                 1        6                 1        5        1                 6
  M4d          2                                                                                                                                               2
  M4d1        27        2                                   5                 2                          5                 1        5        1                 6
  M4d2a       16        2                                   4                                                              1        4                          5
  M4d2b1      15        1                                   1                          2                 3                          3                          5
  M4d2b2      16                                            2                 2                 1        1                          3                 1        6
  M4d2b3      10        1                                                              1                 1                          2                          5
  M4d2b4      10                                                                                         2                          3                          5
  M4d2b5      17        4                                                              1                 2                 1        4                          5
  M5a         13                 1                 1        2                                                                       4                          5
  M5b         12                          5                                                                                1        4                          2
  M5c          5                                                                                                                    1                          4
  M5d          5                                                                                                                    1                          4
```

**What it says about "rows only"** (BUILD-ORDER: after a new operation's code, "printing, the graph and the reports need
no × or ÷ branch"):

- **Printing (W2) and the reports (W4): held.**
  - W2 changed in two slices of thirty: M0c (2 files), when a skill set came to be read as itself, and M5a (1), where
    the next paper is set.
  - W4 changed in two: M0a (1) and M5a (1).
- **Reading, marking and the graph (W3): held after its first general fix, with four exceptions.**
  - M0a changed 14 files so that every answer of a several-answer question counts.
  - After that W3 changed only where an answer took a shape it had not read before:
    - a list read group by group (M4c, 4 files);
    - a remainder story (M3b3, 2);
    - a paper printed for a child read back (M5b, 5);
    - one file each in M0b, M2a and M3a.
- **Rows grew in 23 of the 30 slices.** Skill sets, levels, cases, mistakes and prompts went in as rows.
- **"Rows only" did not hold for kinds of question.** The maths library changed in 22 of the 30 slices: 17 files in M0b,
  16–19 in M2d1, M3a and M3d. A new kind of question is code by design (ADR 0010: the bank's questions are made by
  code), so each new method or picture was a maker, a predictor and a layout in `assess/`. The cost was per kind of
  question, as ADR 0047 said, not once per operation, as BUILD-ORDER's sentence reads.

## M5 — merged and live (2026-10-13)

- **Merged:** #201 as `35f38a7`, by Nimish, 05:36 UTC.
- **Main's runs on `35f38a7`, all success:** `ci` (engine, browser, web), `migrate live`, `deploy engine`, and the
  website's deploy.
- **`bin/engine done`** for each goal, on main's code against a database built fresh (`bin/testdb fresh`). Every one of
  Nimish's sentences PROVED and every criterion PASSED:
  - md5a: 2/2 proved, 2/2 criteria (the loop 67 passed, 1 skipped)
  - md5b: 2/2 proved, 3/3 criteria (`test_read_back.py` 5 passed)
  - md5c: 1/1 proved, 2/2 criteria
  - md5d: 1/1 proved, 2/2 criteria (the browser spec, 1 passed)
  - md5e: 1/1 proved, 3/3 criteria
- **"Not live yet", in each report:** the live database did not answer from this container (ConnectionTimeout), so the
  report could not check live's migrations itself. M5 adds no migration, and `migrate live` on `35f38a7` succeeded.
- **Still to run on live:** `bin/update-live`. Its `bank relabel` charges the test for 3's stored questions to + then ×.

## L3 — a class paper prints on live (2026-10-14)

Nimish, on Make papers for Grade 1 (class assessment, one paper for all, Equal groups · Easy): "The engine refused
(500); nothing was printed." Goal `goals/l3-a-class-paper-prints-on-live.yaml`.

- **The cause, from the live engine's own log** (engine-logs run 38527588877):
  - `/papers/plan` answered 200.
  - `/papers/make` answered 500 at `focus_paper.print_paper` inserting the paper's `sheet_template` with
    source `'focus'`: `CheckViolation … sheet_template_source_check`.
  - It failed before any PDF was drawn. In the same minute a library worksheet's PDF printed (200).
- **Live's rule differs from the migrations'.**
  - `20260929090000` adds `'focus'`, and live records it as applied: `migrate live` run 35863211781 said "Remote database is up to date" on 2026-09-23.
  - The rule without `'focus'` is the one `20260926090000` wrote.
  - How live came to hold it again is not known from here. Live has been changed by hand before (`item_placement`, the
    rehearsal's rule-9 note), and this container cannot read live's catalogue.
- **The fix is a migration, not a hand edit (rule 9).**
  - `20261108090000_a_paper_made_for_one_child_is_a_sheet_on_live` says both rules again: the four sources, and a
    `'focus'` paper names its child.
  - On a database that already holds them it changes nothing.
  - Check: `tests/test_maker.py::test_a_class_paper_prints_on_a_database_whose_rule_lost_the_paper_for_one_child`. It:
    - puts the rule as live had it;
    - sees Grade 1's class paper refused as live refused it;
    - runs the migration;
    - sees every child's copy print;
    - runs the migration again and finds nothing changed.
- **The refusal is raised as itself.**
  - `run_idempotent` ran `fn()` on the request's transaction, so the database's refusal aborted it.
  - Recording the failure then raised `InFailedSqlTransaction` over the real error.
  - `fn()` now runs inside a savepoint. Check: `tests/api/test_idempotency.py::test_a_database_refusal_inside_the_call_is_raised_as_itself_and_recorded`.
  - No call `run_idempotent` wraps commits on its own: the readers that commit run in the background on their own connections.
- Check: `cd packages/engine && uv run pytest -q tests/test_maker.py tests/api/test_idempotency.py` → `18 passed`;
  `bin/check` → `28 passed`.
- **Not live until** this merges and `migrate live` applies the migration.

## F1a — each educator has classes (2026-10-14)

Phase 1 of BUILD-ORDER "One flow for the educator" (ADR 0073). Nimish: "Let's create a mapping of the teacher to the
grade … Then the teachers only see, when Achal logs in, things that are relevant to his grades." D1: an educator is
linked to classes, and the grade follows from the class. Goal `goals/f1a-each-educator-has-classes.yaml`.

- **A person's classes live on their entry in the staff list.** That list is `config.app.staff` (ADR 0069), so sign-in
  is untouched. The rejected staff table is recorded in ADR 0073.
  - `engine staff add --class G2 --class G3` puts a person on the list with their classes.
  - `engine staff classes <email> G2 G3` replaces them, and `--none` clears them; leaving the classes out is refused.
  - A class is a section a child still in school is in, so a typed class that is no class refuses the whole command
    and nothing changes.
  - `engine staff list` says each person's classes; the coordinator's read "every class".
  - Check: `tests/test_staff.py` (three new tests) → with `test_cli.py` and `test_loaders.py`, `44 passed`.
- **Signing in carries the classes, and the menu says them** beside the name: "Teaches G2, G3", "Every class" for the
  coordinator, "No class yet" for someone linked to none.
  - Check: `apps/web/tests/u25-each-educator-has-classes.spec.ts` → 2 passed. Run against the old menu, it failed
    ("Signed in" not found).
  - u15 (menu and Today) and u18 (sign-in) still pass: `8 passed`.
- **Not live until** merged, and then until Nimish runs `bin/engine staff classes` for each educator. Until then every
  educator reads "No class yet". F1b is what narrows the pages.

## F1b — each person sees their own classes (2026-10-14)

Goal `goals/f1b-my-classes-first.yaml`. Nimish: "Then the teachers only see, when Achal logs in, things that are relevant
to his grades."

- **One scope, from who is signed in** (`apps/web/lib/scope.ts`):
  - an educator sees the classes on their staff entry (F1a);
  - the coordinator sees every class;
  - an educator linked to no class sees every class, and Today says why.
- **Every list is narrowed to it:** Today and the menu's counts, Children, the parent reports, Home assessments, Make
  papers' classes, Assessments (both views, and its filters' classes and children), Marking and its queue of answers,
  and Approve's packs. Each query takes the scope as one where-clause piece. The curriculum's lines on Today stay the
  school's (a skill is every grade's); phase 2 narrows Curriculum to a person's grades.
- **Single-item pages are guarded.** A page for another class, child or paper says "not one of your classes" and shows
  nothing of it: a class, its home assessments and its week, a child and their parent report, a chosen paper, a paper
  read, a printed paper. The check reads only the class, before any name is read through the logged accessor.
  - A printed page, a preview and a print of another class's paper answer 403.
  - A scan not yet sorted onto a paper has no class, and stays open to whoever reads the pile.
- **Check:**
  - `apps/web/tests/u26-my-classes-first.spec.ts` → 3 passed. Before the change it failed: the other class's pack was on
    the educator's Today.
  - The specs of every page touched (15 files):
    - First run: 49 of 50 passed. u20's "every parent report … a child's page ends on theirs" failed once
      (`regions.at(-1)`).
    - Second run: u20 passed. Only u26's own new assertion failed: its test paper's code `CSU26A` is no code (not hex),
      so the route answered 400 before the class check. Corrected to `CSF1B026`.
    - Then u26 with u20 → 6 passed.
    - u20's one failure is not explained. It does not touch a page this slice changed for the coordinator, who runs it.
- **Not live until** merged and the educators are linked to their classes (F1a).

## F1c — who decides what, checked on the server (2026-10-14)

Goal `goals/f1c-who-decides-what.yaml`; ADR 0073 decision 3; D3 (educators draft skills, the coordinator approves).

- **Every server action checks before it writes.** That is all 27 actions and the route that prints a worksheet for children.
  - **Its role** (`apps/web/lib/decides.ts`): the signer's role must be one `people.decides` names for that kind of
    decision. The coordinator may take any decision.
  - **Its classes:** every class it touches must be the signer's. That covers the child, the paper, the answer, the
    planned paper and the class's pack, each looked up from the id the form sent, not from the page that showed it.
  - **Refusal:** a refused decision changes nothing. It lands on `/refused`, which says whose decision it is, or that
    the class is not the signer's.
- **`people.decides` names four more kinds**, all the educator's:
  - `skill_drafts` (changing a skill's words or level grades);
  - `reports` (parent reports; workflow N12 names the coordinator, Nimish on 2026-10-11 named the teacher, so the row
    says educator and can be changed);
  - `questions` (correcting a question, changing a key);
  - `week` (the week's declaration).

  An ask is decided by its own `for_role`. A kind the row does not name yet is refused to no one, as before: the row
  reaches live with the engine's settings, a little after the website.
- **Check:**
  - `apps/web/tests/u27-who-decides-what.spec.ts` → 3 passed, with u23 → 5 passed.
    - Before the change, the educator's approval of a skill went through.
    - The tamper test changes the pack form's class by hand, and is refused.
  - The whole browser suite (steps, e2e, gate) → 194 passed. The one failure was u27's own locator (the pack panel has
    no accessible name), since corrected.
  - `tests/test_asks.py` names the ten kinds.

## F1d — questions approved level by level (2026-10-14)

Goal `goals/f1d-questions-approved-per-level.yaml`; ADR 0073 D2. Nimish: "If I just want to approve something for a
grade level today, I'm not able to do that."

- **Each level is approved on its own.** Migration `20261109090000`:
  - `skill_set.level_approved` holds {level: {by, at}}.
  - A skill is approved (`status` 'ratified', which every reader already asks) exactly when every level it has is.
  - Every skill approved whole before keeps its approval at every level, in its approver's name.
- **What withdraws an approval** (trigger `skill_set_version_on_change`):
  - a change to a level's rule — anything of the level but its words — withdraws that level alone;
  - a change to the skill's kinds of question withdraws every level;
  - its name, what a child can do and a level's words withdraw nothing: the questions did not change. That replaces
    the rule of 2026-10-06 (`test_approval.py` now pins the new one);
  - a status set whole, approved or withdrawn, approves or withdraws every level with it. That covers
    `engine ratify`, approving every level at once, and the tests and scripts that set it.
- **On the site:** each level's card on the skill's page approves that level alone for the coordinator. An educator
  reads "Waiting for the coordinator", with no button. "Approve as written" approves every level.
- **Check:**
  - `tests/test_level_approval.py` → 4 passed (one level, a rule, words, a skill approved before). With
    `test_provenance.py`, `test_approval.py` and `test_spec.py` → 24 passed.
  - `apps/web/tests/u28-approved-per-level.spec.ts` → 2 passed.
  - The first trigger left a status set by hand overridden by the levels. u23's set-up, which sets every skill's status,
    broke on it, and two local skills stayed approved by earlier runs. That is fixed at the cause: a status set whole
    approves or withdraws every level.

## F1e — a grade uses its own levels and those below, on every paper (2026-10-14)

Goal `goals/f1e-the-grade-plan.yaml`. Nimish: "whenever a grade two teacher is creating the assessments for that topic,
it's only easy and medium that should come."

- **Measured while building.** Each level already has a grade (`skill_set.level_band`, else the skill's own), set on the
  skill's page by moving a level (goal c1). The home paper already kept a child to their grade or below
  (`shelf._read_levels`).
  - Make papers ignored the grades: its picker listed every level of every taught skill, and `focus_paper._asked`
    checked only that the level existed.
  - A separate grade × skill × level table, the list's first draft, would have been a second source of truth beside the
    level grades, so it was not built. BUILD-ORDER's F1e row and ADR 0073 say so.
- **The engine refuses a level above the grade**, in words: "ADD.2D1D at Medium is Grade 2's; Grade 1 has Easy". That
  holds for one paper for all (the class's grade, `roster.class_band`), the same skill for each child, a chosen paper and
  a changed child (the child's own grade).
- **The site offers only those levels:**
  - Make papers' and a chosen paper's picker (`usesLevel`, the engine's rule);
  - the topic's default lines (Medium where the grade uses it, else its first usable level);
  - the "Make this check" links on a child's and a class's page (`levelsUsedBy`, the same rule in SQL).
- **Check:**
  - `tests/test_maker.py::test_a_class_is_given_only_its_grades_levels_and_those_below`: it failed first, a Grade 1
    class being given Medium. With the maker, focus-paper and week-note tests → 36 passed.
  - `apps/web/tests/u29-a-grade-uses-its-levels.spec.ts`: it failed first, Grade 1 offered three levels too many. With
    the maker specs → 15 passed.
  - L3's test now adds live's old rule `not valid`, so it no longer depends on the database holding no paper made for
    one child.
  - The whole browser suite: the first run failed 11 specs on a child's and a class's page. The cause was `levelsUsedBy`
    writing `'\D'` inside a JavaScript template, which Postgres received as `'D'` ("invalid input syntax for type
    integer: G1"); it is now `'\\D'`. The 11, with u29 → 57 passed; the other 184 had passed in the same run.

## F1a–F1e in CI — two engine tests that passed here and failed in GitHub (2026-10-14)

- **What failed.** The `engine` job was red on every F1 commit; the browser and web jobs were green.
  - `test_web_gate.py::test_every_server_action_checks_who_is_asking` failed because the 27 actions now open with
    `deciding(kind)`, and the gate looked only for `requireStaff(` or `currentStaff(`. `deciding` calls `requireStaff()`
    first, so the gate now counts it. A new test, `test_deciding_checks_who_is_asking_before_anything_else`, holds
    `deciding` to that.
  - `test_staff.py::test_an_educators_classes_are_changed_by_one_command` failed because, under `GITHUB_ACTIONS`, typer
    styles each dash of `--none` on its own. A person reads `--none`, but the test read the escape codes. It now reads
    the plain words through `test_cli.run`, the helper written for the same trap.
- **Why it was not seen before the push.** Only the changed modules' tests were run, not the whole engine suite.
- **Check.** Both reproduced with `GITHUB_ACTIONS=true`, then passed with it and without it (37 and 11 passed). The
  change is to these two test files alone; the whole engine suite is CI's run on this push.

## F1f — taught is said for each class (2026-10-14)

Goal `goals/f1f-taught-per-class.yaml`. Nimish: "people who are there for one thing like educator only see something
that's relevant for their class and their students."

- **Measured first** (every read of `taught`, by an agent's map):
  - Taught was one switch for the school (`topic.taught`).
  - The engine's only gate was `shelf._catalog`. It is read once for a whole batch, with no class.
  - About twenty reads on the site.
  - No database function, view or policy read it.
  - The Curriculum table's "Taught" column counted children with a checked answer, which is "Assessed".
- **Built:**
  - `class_topic` is one row per class and topic a person has spoken for, with who and when (migration `20261110090000`,
    run twice here).
  - `taught_in(tenant, topic, class)` is the one rule. It returns the class's own word, else the school's switch.
  - The engine's catalogue is read per class. A class paper, a chosen paper, the home paper and the hidden-answers
    check all read the child's class.
  - A skill asked for whose topic the class has not been taught is refused, naming the class: "MUL.MODELS is not taught
    in F1F-NO yet: an educator of the class says so on Curriculum".
  - On the site (`apps/web/lib/taught.ts`):
    - a page about a class or a child reads that class;
    - Make papers and a chosen paper offer only what the class was taught;
    - lists for the school or an educator's classes count a topic taught where any of them was.
  - The switch on Curriculum says it of one class, in the signer's name. An educator may say it only of their own
    classes; a form changed by hand is refused.
  - The Curriculum table's answers column is now "Assessed".
- **Not built:** copying today's switch into every class (BUILD-ORDER's first plan). A fresh database's children arrive
  after its migrations, so the copy would have found no class and left nothing taught. Following the school's switch
  until a person speaks changes nothing on the day either (ADR 0073).
- **Moved while building:** `chargesTable` went from `lib/queries.ts` to `lib/queries-charges.ts`. `queries.ts` had
  reached 402 lines, past the 400 ceiling. The charges table has its own types and its own approval.
- **Check:**
  - `tests/test_taught_per_class.py`, 4 tests. Each failed first on the old engine for its own reason:
    - the class taught it was refused, as "no skill set";
    - the refusal did not name the class;
    - a chosen paper was refused;
    - both classes' answers were hidden (2, not 1).
  - With the focus-paper, maker, topics, live-data, class-card, web-gate, layout and report tests → 68 passed.
  - `apps/web/tests/u30-taught-per-class.spec.ts`, 3 tests. Each failed first on the old site:
    - no "Say it is taught" for a class;
    - Make papers did not offer a class what it was taught;
    - there was no "Assessed" column.
  - u12, u13, u17 and u18 follow the switch's new words and the Assessed column.
  - The whole browser suite here: 185 passed, 3 failed, 14 did not run because they follow a failed test in their file.
    - The three failures were e2e "every kind of question in the bank", s2 "every kind of link on the Curriculum" and
      s3 "every skill shows its worksheets". Each one loops over 20 or more pages inside one 30 s test.
    - Pages on this copy take 1.3–1.6 s each, and the same on main's site code: nine pages were timed on both builds.
      So F1f did not slow them. This copy has collected test rows from many runs.
    - CI's browser job on a fresh database passed all of it (6b644c3).

## F1g, first step — what approval would close, measured before it ships (2026-10-14)

Goal `goals/f1g0-what-approval-would-close.yaml`. BUILD-ORDER's F1g row: "measured first on a copy of live: the levels
it would close are named to Nimish before it ships".

- **Measured while planning:** on the test database every skill is a draft with no level approved. The gate as written
  (an unapproved level goes on no paper) would close every paper there, and every skill on live still waiting for the
  coordinator. Live's rows are not read from here, so the list comes from a command Nimish runs.
- **Built:**
  - `shelf.approved_levels` is the one rule the gate will use: the levels in `skill_set.level_approved`.
  - `shelf.closing` covers every class on the roll. It lists each level the class's papers draw on today (taught in the
    class, its grade's or below) whose questions are not approved, with the questions it holds. It reads only.
  - `engine week unapproved` prints one line per level, with the classes it would close for, and a total.
- **Check:** `tests/test_levels_closing.py`, 2 tests. Both failed first: there was no `closing` and no command.
  - A Grade 2 class with 2-digit + 1-digit's Easy approved is told Medium, not Easy.
  - A skill the class was not taught is not named.
  - Only its grade's levels are named, with the bank's own question count.
  - The command writes nothing.
- **Here:** 100 levels in 26 skills would close, for 46 classes. Every level is unapproved on the test database.
- **Next:** Nimish runs `~/cornerstone/assessment-engine/bin/engine week unapproved` against live. With that list read,
  the gate itself is F1g (`goals/f1g-approval-gates-papers.yaml`).

## F1f in CI — two engine tests the neighbouring suites did not reach (2026-10-14)

- **What failed** (CI on 6b644c3; 2468 passed):
  - `test_a_skill_set_is_read_as_itself` called `shelf._catalog(conn)` without the class it now takes. It now passes
    `None`, the school's switch.
  - `test_roles::test_the_website_writes_only_what_a_person_changes_on_it` pins every write the website's role may
    make and every function it may call. It now names `class_topic` INSERT, a person's word on Curriculum, and
    `taught_in`.
- **Why it was not seen before the push:** the same reason as F1a–F1e's this morning. Only the changed modules'
  neighbours were run, not the whole engine suite.
- **Check:**
  - CI's whole-suite run on d207b99, the PR's whole code, failed these two and only these (2471 passed).
  - Both now pass here (8 passed with the rest of their files).
  - The push changes those two test files and nothing else.

## L3b — live says what went wrong, before an educator does (2026-10-14)

Goal `goals/l3b-live-says-what-went-wrong.yaml`. This is the second half of L3: Make papers refused every paper made for
one child on live.

- **Measured first:**
  - A failed Make papers left no `flow_run` row. Its failure was written on the request's own transaction, which the
    route rolls back on the way out, so `engine live watch`, which counts failed runs, saw nothing.
  - Live had recorded migration 20260929090000 while its rule still refused a paper for one child.
- **A failed run's record survives:** `run_idempotent` rolls the request's own work back on a failure (the route would
  unwind it anyway), then writes and commits the failure alone. `inbox.py` did the same on 2026-09-25.
- **A drifted rule is named:**
  - `engine/checks/rules.json` keeps every rule the migrations leave on the school's tables: 246 checks, keys and
    references, as the database prints them.
  - It is written by `engine live rules --write` from a database built from the migrations alone (here `rules_fresh`,
    71 migrations).
  - The watcher compares live's rules with it and names up to five that differ, with the count of the rest. It gives
    names only, because its lines go to a public issue.
  - `engine live rules` runs the same check on any database and exits 1 on drift.
  - The usual test copy (m5done) holds the same 246 rules as `rules_fresh`.
- **Check:**
  - `tests/api/test_idempotency.py::test_a_failed_call_is_on_record_after_the_request_unwinds` failed first with "the
    failure left no record".
  - `tests/test_rules.py`: 2 tests.
    - The test database's rules are the file's.
    - Live's state on 2026-10-14, made again (the rule without a paper for one child), is named by the watcher.
  - With the API, watch, CLI, layout and maker tests → 137 passed.
  - The whole engine suite, rebased on #205's head (6953601), on the local copy: 2475 passed, 1 skipped, 1 failed. The
    failure was `test_goal.py::test_every_invariant_holds`, from rows the browser tests left there (below). Once they were
    repaired: it, and `tests/test_rules.py`, pass.
- **Browser tests wrote answers to a response their question does not have** (found by that run):
  - `apps/web/tests/rows.ts::aReadPaper` wrote every answer as response `'a'`. Since M0a a question names its own
    responses (a bank question's is `ans`), so its answers were shown against another's key.
  - That broke the invariant "every answer names a response of its question" on any database that both suites ran on:
    12 rows on the local copy, written by browser runs at 08:44–10:49 today. CI never saw it, because each suite there
    builds its own database.
  - Fix: the answer takes its question's first response (`responses -> 0 ->> 'rid'`). A question with none fails the
    insert, because `rid` is not null.
  - The local copy's 12 rows were given their question's response.
  - Check: the five browser files that use the helper (s4, screens, u14, u16, u22) → 50 passed. The run wrote 28
    answers, and none names a response its question lacks.
- **Postgres 17, CI's version, prints them alike:** the 71 migrations applied to a database on Postgres 17.11 (PGDG
  binaries, `rules17`) give the same 246 rules as the file, `rules.drift` → 0.
  - Only checks, keys and references are read (`contype` c, f, p, u, x). A later Postgres may list other things as
    rules too (I believe 18 lists each not-null; worth verifying), and no migration names those as rules.
- **Not known from here:** live's own Postgres version (`supabase/config.toml` says 17; live is not read from here).
  If it prints a rule differently, `engine live rules --url <live>` names it, and so does the watcher's first run.

## CI's database with no container image (2026-10-15)

- **What failed:** #206's `browser` job died before its first step. The Postgres 17 service container's pull from
  `public.ecr.aws/docker/library/postgres:17` was refused three times with `toomanyrequests: Data limit exceeded`.
  This is the second registry to refuse CI's anonymous pulls: Docker Hub did the same on 2026-10-09, and that is why CI
  moved to AWS's copy. Runners share addresses, so any registry's anonymous limit can stop every job.
- **Fix at the cause:** no job pulls a database image any more.
  - `bin/ci-postgres` installs Postgres 17 from the PostgreSQL apt repository (apt.postgresql.org) and starts it on
    127.0.0.1:5432 as postgres/postgres, as the image did.
  - It uses the image's own locale, en_US.UTF-8, and checks passwords over TCP (scram-sha-256).
  - The package's own cluster and any older Postgres on the runner are stopped first.
  - CI's `engine` and `browser` jobs and `rehearse update-live` call it as their first step after checkout. The
    rehearsal's separate client install is folded into it.
  - It refuses to run anywhere but a CI runner (`GITHUB_ACTIONS`).
- **Check (here, as a non-root `runner` user with passwordless sudo, as on GitHub's runners):**
  - The script installs and starts it: "PostgreSQL 17.11 … en_US.UTF-8". It puts `/usr/lib/postgresql/17/bin` on the
    job's PATH.
  - A wrong password is refused over TCP. Off a runner, the script refuses with exit 1.
  - `bin/testdb fresh` on it, CI's whole database build (71 migrations, the seed, the question bank, the worksheet
    library): exit 0 in 6 min 31 s. The PR's own CI is the proof on a real runner.
- **The first page was slower on it, and that is fixed in the same PR.** #207's first run failed one browser test of
  231: `laptop /today`, the first page the run opens, said "The database did not answer within 8 seconds". The second
  run passed.
  - Test 1's time, read from the logs: 1.0–1.2 s on the last four runs with the image, 3.8 s and over 8 s on the two
    runs with `bin/ci-postgres`. From test 2 on, both setups take the same time.
  - Not reproduced here. CI's database built with autovacuum off (so no statistics) and a cold restart still served
    `/today` in 1.5 s, and no statement took over 105 ms. So which runner-side cost it is, I am not certain.
  - Fix: `bin/testdb fresh` ends with `vacuum analyze` (about 2 s on its 71 MB). The tests then start on a settled
    database, as live always is, not seconds after some 28,000 rows were written.
  - So the next slow page names its own cause: CI's Postgres logs every statement over a second, and the browser job
    prints them when it fails ("the database's slow statements").
  - Check: the script, run again as a non-root runner user, logs a 1.2 s statement and not a fast one. The step's
    `grep` finds it. The PR's next CI run gives test 1's time on the settled database.

## The watcher's first look at live's rules — `item_placement` to the attic (2026-10-15)

- **What the watcher found** (first run after L3b deployed, 05:46 UTC, issue #208): five rules of `item_placement`,
  "a rule no migration makes". Every other rule on live (246) is the migrations', so there is no false alarm from a
  Postgres version.
- `item_placement` was made on live by hand (rule 9). Nothing in the engine, the website or n8n reads or writes it.
  20261007090000 had let go of its hold on skill_set and rung, and kept its rows for whoever made it to say what they
  are. No one has.
- **Nimish, 2026-10-15:** "move item_placement to attic too".
- Migration 20261111090000 moves it, rows and all, into schema `attic`. Nothing reads `attic`, and no role but the
  owner may open it. Where the table does not exist (every database built from the migrations), nothing happens.
- **Check:** `tests/test_rules.py::test_a_table_made_on_live_by_hand_goes_to_the_attic_with_its_rows`.
  - It failed first, because the migration did not exist.
  - It makes live's table again with a row: the watcher names it, the migration moves it with its row, and the watcher
    names no rule.
  - The privileges, roles, rules and watch tests: 17 passed. `bin/check` exits 0.
- **After `migrate live`:** the watcher's next run should find nothing and close #208 itself ("All well again").

## The website goes live after the live database (2026-10-15, ADR 0074)

- **What happened:** #205 went live on Vercel at 03:00 UTC; `migrate live` applied its migration at 03:26, after CI.
  Every page reading the new rule failed in between. The engine already waits for live's migrations
  (`deploy-engine.yml`, "live has every migration this commit carries"); only the website raced.
- **Nimish, 2026-10-15:** "yes move website deploy after migrate live".
- `migrate live`'s last step sets the commit's `live database` status: green after `db push`, red if the run failed,
  none for a commit main has moved on from. Vercel's Deployment Checks hold each production build until it is green.
- **Check:** `tests/test_deploy.py::test_the_website_goes_live_only_once_live_has_the_commits_migrations`.
  - It failed first: migrate.yml had no permission to set a status (`KeyError: 'permissions'`).
  - It pins the permission, the step coming after `db push`, its gate on main's newest, the state from the job, and the
    context name Vercel waits on. `test_deploy.py`: 7 passed. actionlint is clean on migrate.yml and ci.yml.
- **Merged as #209 (`04c0d5e`).** `migrate live` applied 20261111090000 and set `live database` on it. Nimish then
  added the check in Vercel (Settings → Build and Deployment → Deployment Checks → GitHub → `live database`).
- **Not yet seen working:** the first commit Vercel holds is the next merge to main. Its deployment must stay
  unpromoted until `live database` turns green on that commit.

## SF1 — a kind of question is a row (2026-10-15, ADR 0075)

- **Nimish, 2026-10-15:** approval for "all unique formats of questions", with an engine that "simply checks whether a
  certain question belongs to a certain format"; "it should be skills * format and 100/200/500 is for a skill and
  difficulty level combo". Achal's Grade 2 asks are the first examples.
- **Measured first, on a copy of the bank** (28,031 active questions, 43 skills, 313 skill × kind pairs):
  - every kind of question was a Python function;
  - MUL.TENS already has Achal's zeros (Hard and Advance, Grade 4);
  - multiples had no "nth multiple";
  - × and ÷ stories mix at every level;
  - nothing made a sequence or three numbers multiplied.
- **What a level can make, counted, not 100:**
  - three numbers of 2 to 5 with a product up to 30: **26**; Medium 172, Hard 197, Advance 111 a kind;
  - sequences: Easy 80, Medium 200, Hard 408;
  - multiples: Easy 30, Medium 60, Hard 27.
- **Built:**
  - `assess/cards.py` draws, counts and checks a kind that is a row. It lists every set of numbers a level allows, so:
    - "does this question belong" is a lookup of its printed words;
    - a level's count is exact;
    - a fill never repeats.
  - `question_format` (migration 20261112090000), loaded from `supabase/seed/question_formats.json`.
  - Three Grade 2 skills as rows:
    - MUL.THREE (R54, topic MULFACT), its kinds MUL3.SUM and MUL3.STORY;
    - NUM.SEQUENCE (R52, NUM.PAT.02, a new topic SEQUENCE, not yet taught), its kinds SEQ.ON and SEQ.BACK;
    - MUL.NTH (R53, NUM.CNT.08, topic MULMODEL), its kinds MULT.NTH and MULT.FIRST5. Not MDMULTIPLES: that topic is
      the multiples skill's alone (`test_md_multiples`).
  - A kind that is a row uses its rung's skills as evidence (`skills.used`), so a mark on one names a registry skill.
  - Its working space is the layout's, one per format (`layout.WORKING_LINES["card"]`), not a row's.
  - Nine new mistakes, each the formula of the wrong answer it writes.
  - A level is filled from its whole list, to its target or all it can make (`can_make`). Refill's target is the
    smaller of the two.
  - A stored question is checked against its kind and level as they now stand (`cases.holds`).
  - It prints as the multiples' sentence-and-box or list layout.
  - A wrong list its key predicted names its mistake.
- **Checks:**
  - `tests/test_cards.py`: 30 passed. Every answer is worked from the printed words by the test itself, and counts are
    brute-forced. Achal's "100, 81, 72, 63" belongs to no level; "90, 81, 72, 63" belongs to Hard.
  - `tests/test_card_bank.py`: 4 passed.
  - pyright strict on `cards.py` and `question_formats.py`: 0 errors.
- **Not live:** `migrate live` makes the table, but the skills, kinds and questions arrive only with `bin/update-live`
  (load, refill). They appear on a paper only once a Grade 2 class's topic is switched on.
- **Found while proving it, fixed at its cause:** the groups everyone needs (26 children, 4 to a rickshaw) named
  "one group short" beside "remainder not rounded up" on every 6. One group short and then rounded up (5 r 6, so 6)
  always writes what forgetting to round up writes, and the story has no second box to tell them apart. So a child who
  forgot the children left over was charged a division slip too.
  - It surfaced as `test_the_loop[DIV.2D1D-Advance]` on a fresh build: the next paper went to the other mistake. The
    bank's fill is unseeded, so it depends on which stories a worksheet draws, and main could fail the same way.
  - `divide_stories.rounded_up` now names the not-rounded-up answer by that act alone. `stale.key_problems` retires a
    rounded-up story keyed the old way; on the fresh copy, refill retired 34 and drew 34.
  - Checks: `tests/test_divide_stories.py`, 6 passed. The new test failed first on the doubled 6.
  - Charged on live? None on the copy (live's rows to 2026-10-14): no answer to a rounded-up story, and DIVCOL is not
    switched on. Live after that cannot be read from here.

## SF1 on live; SF2 measured; the UI audit (2026-10-15)

- **SF1 merged as #210 (`1721046`): the first deploy Vercel held.** Vercel built it at 09:31 UTC and waited ("Waiting
  for checks"). `migrate live` set `live database` green at 10:05:39, and Vercel promoted at 10:05:40.
- **SF2 measured on a copy of live** (rehearsal run 38714442140, `.github/measure/sf2_kinds.py`, before update-live):
  - 43 skills (20 approved whole); 168 levels (76 approved); 314 skill × template pairs, 182 skill × format.
  - 38 unapproved levels reach a class's paper (G2, G3): 10 skills, 10,486 questions.
  - Approvals to open them: by level 38, by template 75, by skill × format 48, by format alone 18.
  - Nimish chose a format approved once across skills (ADR 0077).
  - Multiplication is switched on for G2 and G3 on live, so MUL.THREE and MUL.NTH reach those papers once
    update-live runs.
- **UI audit:** every page, as an educator and as the coordinator, at laptop and phone width, on a seeded fresh copy:
  43 views, 172 screenshots, all loaded with no console error. The report is in the session scratchpad (`ui-audit/`),
  cut into slices UX1–UX7 in BUILD-ORDER. Highest:
  - an educator offered approve buttons that are not theirs;
  - a worksheet's print list showing other classes' children by name;
  - class papers labelled "Grade 1 · G2-C";
  - Children one flat table per grade.

## T1 — topics are operations; a class is taught skill by skill (2026-10-15, ADR 0076)

- **Found:**
  - live's chips "Number sense & strategies", "Estimation" and "Word problems" are dead rows: the seed dropped them
    on 2026-09-23, and `engine load` never removed a topic;
  - the seed's 16 topics held nine slices of × and ÷;
  - the topic was also the taught switch.
- **Built:**
  - Six topics: Addition & subtraction, Multiplication, Division, Multiples & factors, Number sense, Data handling.
    `topics.json` lists each topic's skills and the ones the school has taught.
  - The load removes a topic the rows dropped, with every class's word on it.
  - Migration 20261113090000:
    - the school's word per skill (`skill_set.taught`) and each class's (`class_skill`);
    - `skill_taught_in`, the one rule; `taught_in` (a topic: any of its skills); `say_taught`, a topic's switch or
      one skill's;
    - `internal.topic_words_to_skills`, run before any skill moves topic, writes every old word onto each skill;
    - the website's write to `class_topic` revoked.
  - Engine readers: `shelf.catalog` and `live_data.hidden` read per skill.
  - Website:
    - every skill-level read goes through `skillTaughtIn` / `skillTaughtFor`;
    - Curriculum has a switch per skill inside each taught class;
    - chips name only topics with a taught skill a class's children can be given (a level of their grade or below).
- **Checks:**
  - `test_topics.py` and `test_taught_per_class.py` (11 new or changed tests, failing first): 56 passed with
    `test_loaders`, `test_focus_paper` and `test_maker`.
  - `test_regrouping_the_topics_changes_no_classs_paper` compares every class's word before and after the regroup.
  - `test_roles`, `test_live_data`, `test_card_bank`, `test_read_back`, `test_aseem_1518`: 21 passed.
  - `rules.json`: the four new rules. tsc and eslint clean.
- **Left in place on purpose:** `class_topic` and `topic.taught` are read by nothing. They stay so that the old
  website still serving during the deploy finds them; the next migration drops them.

## T1 merged; T1b — the old switch dropped (2026-10-15, ADR 0076 "After")

- **T1 merged** as `271ce9e` (#211) at 11:25 UTC. Its migration and the website go live through main's CI, then
  `migrate live`, then Vercel; Nimish's `bin/update-live` regroups the topics after that, not before (the old website
  reads `topic.taught` and `class_topic`, which nothing writes once the topics are regrouped).
- **T1b, migration 20261114090000:** drops `class_topic`, `topic.taught`, `taught_by`, `taught_at`, the constraint
  `topic_taught_by_a_person`, and `internal.topic_words_to_skills`. Nothing on main read them (searched the engine,
  the website, its tests, `bin/`, the seed and every database function).
- **Tests:**
  - `test_the_topic_is_no_longer_the_switch` (new) failed first: `{'words': True, 'switch': True, 'move': True}`.
  - `test_regrouping_the_topics_changes_no_classs_paper` now proves the lasting promise without the old table: a load
    that moves three skills out of old topics and drops those topics leaves every class's word on them as it was.
  - `test_a_topic_the_rows_drop_is_gone_after_a_load` (renamed): the dropped topic's skill sits under Division and a
    class's word on it survives.
- **Checks:** the migration ran twice on the local copy; `engine live rules --url <copy>`: 0 rules held otherwise;
  topic, role, loader, card and live-data tests: 72 passed.

## UX1 — an educator is shown only what is theirs (2026-10-15, goals/ux1-who-sees-what.yaml)

- **Measured first** (the audit, signed in as the G2-C educator on a fresh copy):
  - 48 "Approve…" buttons on Approve the skills and one on every skill page, each landing on "Nothing was changed";
  - Today listed "46 Skills to approve" and every role's drafted questions, so its badge read 126 where about 50 were
    theirs;
  - a worksheet's "Print for children" listed 49 children from 6 classes.
- **Causes, fixed where they are:**
  - Today's lines carried no decision: each now names its kind (`people.decides`), and `needsYou(me)` keeps only the
    person's own, with the questions drafted for their role. The menu counts the same list.
  - `childrenOnRoll` read the whole roll through `pii.read_child`, logging a name read for every child, for anyone; it
    now takes the reader's classes. `childHeader` read the whole roll to find one child; it now reads that child alone.
  - The skill page, Approve the skills and Curriculum's banner offered approval to anyone; they now ask `mayDecide`
    and tell anyone else the approval is the coordinator's. Changing a skill's words stays the educator's (N1).
- **u27** still proves the server's refusal: the form the coordinator is offered is sent by hand from the educator's
  page.
- **A child's page is twice as fast,** since it reads one name, not the roll's: 0.47–0.69 s against 1.1–1.4 s on main
  (three loads each, same copy). It now paints its frame first and streams in about 200 ms later, so u20, which read
  the page's parts the instant it loaded, waits for the page first; m5 reads the library the same way and got the same
  guard.
- **Checks:**
  - UX1's spec failed first on main's pages, for its reasons: Today showed the educator "46 Skills to approve" and 31
    questions; a skill page offered "Approve as written"; the print list named every class's children.
  - Then u32, u27, u15 and u26: 16 passed. The whole website suite on the migrated copy: 236 of 237, the one u20
    above, then u20 and m5: 4 passed. tsc and eslint clean; `bin/check` passed.
  - The whole engine suite on the migrated copy: 2531 passed, 2 skipped.

## UX2 — one count for one thing (2026-10-15, goals/ux2-one-count-one-thing.yaml)

- **Measured first.** On live (the audit): "Grade 1 · G2-C"; class papers to approve 12 on Today and 18 on
  Assessments; the bank 21,250, 28,705 and 28,717 on three pages; worksheets 1,872 above the list and 2,738 in the pager.
  On a fresh copy: the bank 19,638 / 28,696 / 28,746; worksheets 1,710 / 2,736.
- **Causes, each fixed where it is:**
  - A class's grade was taken three ways. It is one database function now, `class_band(tenant, section)` (migration
    20261115090000): the grade most of its active children are in, the lower on a tie. `roster.class_band` asks it;
    so do Today, Make, the topics, the class page and Assessments.
  - A spare copy has no child, so it took its worksheet's grade, and its class's group took the lowest. It takes its
    class's now. A spare not yet written on is counted apart ("and 1 spare"), never as a paper to approve; once read,
    it counts like any paper.
  - "The bank" is the questions the engine can draw: made by it, active, of a skill at one of its levels. Curriculum,
    a skill's page and the workflow map counted the old papers' questions too, which no paper draws. The Question bank
    page shows the taught part and says the whole: "N questions ready to print for the skills taught, of the bank's M".
  - The worksheet pager counted worksheets of untaught skills and of replaced skills, which its list never shows. The
    pager and the list count what the header counts, and the header names the library's whole.
- **Checks:** UX2's four tests failed first on main's pages, each for its reason ("Grade 1 · U33-CLASS"; "3 to
  approve" for two children's copies; the map's 28,746; "of 2736" under 1,710), then passed. `class_band` and
  `roster.class_band` agree in every case (`test_a_class_has_one_grade_and_the_database_says_it`); roster and week
  tests: 17 passed.

## UX3: Children grouped by class (2026-10-15)

- **Asked:** Nimish, on live's Children page: "Most of the pages just have a long list for no reason. All these things
  should be expandable and collapsible. They should have the right set of columns which are important. It should be
  teacher-specific." The same evening he saw no change from UX1 and UX2, and moved UX3–UX5 ahead of SF2.
- **Before (the audit's screenshots):** the coordinator's Grade 2 was one table of 27 children from 4 classes, roll
  numbers 1–12 repeating; Grade and Class were columns inside a "Grade 2" panel; "To write" filled the Parent report
  column; nothing collapsed; the full colour legend sat under every grade; at 400 px "Needs help on" began at x = 312.
- **Now (`goals/ux3-children-grouped.yaml`, `tests/u35-children-grouped.spec.ts`):**
  - one group per class under its grade. An educator's own classes are open; the coordinator's are closed, each one
    line saying only what waits ("3 children · 1 needs help · 2 answers waiting · 1 parent report waiting", or
    "nothing waiting"), opened in place. A class sorted stays open (`?open=`).
  - columns: Roll · Child · Needs help on (the skill, and the mistake repeated there, `mistake_name`) · Needs help ·
    Practising · Secure · Waiting on you (the papers pages' rule: unreadable or needs a person, on papers not replaced
    or voided) · Parent report (only "to approve" or "out of date", `reportWaits`). Grade, Class and Last paper read
    are gone. Children who need help come first.
  - the colour key is one line (`ColourKeyLine`) that opens to the whole key.
  - on a phone the counts fold away; the child and what they need help on stay on screen, and no page scrolls sideways.
  - the search opens the classes holding a match and puts the rest away; clearing puts every class back as it was.
- **Checks:** u35 failed first on the old page (no class groups), then 4 passed. The specs that pinned the old table were
  moved to the new one, each keeping its promise: u8 (the table, now per class; its goal names the new test), u2, u10,
  u11 (the key opened first), u18 (the search), u21, u26. The goal's criteria, 12 specs: 74 passed. `tsc`, eslint and
  `bin/check` clean.

## UX4: a class and a child, said once (2026-10-15)

- **Before (the audit's screenshots `12-growth-class-section`, `09-growth-id`):** a class showed where each child stands
  twice, by topic and then every skill of every topic; "Make this check" sat past a sideways scroll at 1440 px, behind a
  column of names; the full colour legend under it. A child's standing was said three times (four tiles, a by-topic
  table, the skills by topic); a child with no answers got tiles of zeros, a table of dashes, nine check rows, the
  legend, an empty mistakes panel and a parent report with nothing to report.
- **Now (`goals/ux4-class-and-child.yaml`, `tests/u36-class-and-child.spec.ts`):**
  - a class: one table of standing — by topic, or a topic opened (its name, or the topic line above) to its skills in
    the same place. No view of every skill of every topic. The heading says the grade.
  - checks, on a class and a child: one line each — skill · how many children (names folded) · size and level · Make
    this check. The skills no one has answered are folded under one line that counts them.
  - a child: the one sentence, a line to what waits on you when something does, then each topic a group whose line
    counts its skills (`byTopic`), open where a skill needs help. Tiles and the by-topic table are gone.
  - a child with nothing signed off, no graph and nothing waiting: one sentence and one action. The paper made for them
    that waits to be approved or read (`Open paper CS… →`); several, all of them on Assessments (`See <name>’s n
    papers →`); else their first check (`Make <name>’s first check →`): up to three skills, the class's latest answered
    first (`classLatest`), then the grade's order, at the check's level and size, for them alone.
  - the colour key is one line on both pages.
  - the parent report's state is a sentence edged in its colour. It was a pill, which does not wrap, and the longest
    ("Nothing to report yet: none of their answers is signed off") ran past the panel; u36 checks that no panel's
    content is wider than the panel, and failed on the pill.
- **Checks:** u36 failed first on the old pages (4 of 4, each for its reason), then passed. The specs that pinned the
  old layout keep their promises on the new one: u2 (the grid read a topic at a time; Bina's first step), u11 (the key
  opened; a topic opened for its cells; the folded checks), u20 (the topic groups; Mira has a waiting answer, so her
  page still says "Nothing to report yet"), u21 (back to every topic from the topic line), u24 (Esha has one signed-off
  answer, so her page lists her papers), screens. `ui4b2`'s goal sentence now says a topic opens in place. The goal's
  17 specs: 108 passed; `bin/check` 28 passed. tsc and eslint clean.

## UX3 and UX4 live; UX5a: Assessments by week, and the class's papers child by child (2026-10-15)

- **UX3 live:** #214 merged as `d3a948d`; main's CI passed, `migrate live` and `live database` 20:10 UTC, Vercel
  20:10:19. `bin/engine done ux3-children-grouped` on main's code, on the copy: 4/4 promises proved, 2/2 criteria.
- **UX4 live:** #215 merged as `1617165` (20:11 UTC); it was pushed to #214 a minute after that merged, so a new PR
  carried it. Main's CI passed, `migrate live` and `live database` 20:32:54 UTC, Vercel 20:32:55.
  `bin/engine done ux4-class-and-child` on main's code, on the copy: 4/4 promises proved, 2/2 criteria.
- **UX5 cut in two** (BUILD-ORDER): UX5a, Assessments and the class's papers to approve; UX5b, Make and Marking.
- **Before (the audit's 03-papers and 23-papers-approve):** Assessments stacked three rows of chips over four selects; "Each
  paper" was 27 rows in no roll order; spares sat among the papers. A class assessment made in the maker was one row a
  child, titled by a QR code: each child's copy is drawn on a worksheet of its own, with no skill set to group on. The
  class's papers to approve showed roll numbers and no names, two columns the same on every row, and a child the week's
  assembly could not dress appeared nowhere: `assemble.for_week` returned the reason and nothing kept it.
- **Now (`goals/ux5-papers-grouped.yaml`, `tests/u37-papers-grouped.spec.ts`):**
  - Assessments: weeks newest first, the newest open, each one line ("1 assessment · 1 to approve · 1 to check", or
    "nothing waiting"). An assessment is a line that opens in place (`?open=`) to its copies in roll order — Roll, Child,
    Level, Stage, Waiting, Score — the child opening the paper where its work is; the spares one line under them. One
    assessment left by the filters opens by itself (`open=none` closes it). Topic and stage stay at the top; class, child,
    kind and week fold under one line, open when one is chosen; a filter opens every week it leaves; a child chosen
    shows their copy under each assessment. The "By assessment / Each paper" switch is gone.
  - A maker's class paper is one assessment by the skills and levels every child's copy names (`si.key -> 'areas'`),
    titled by them.
  - Class papers to approve: Roll · Child · Level and why · Paper · Change level; under the table, every child of the class
    with no paper and why — the assembly's reason, now kept on their plan (migration 20261118090000,
    `prescription.no_paper`, written by `assemble.for_week`, cleared when a paper is handed out), or "joined the class
    after this week was planned". The button says what one tap approves: "Approve 2 papers and 1 spare", the children's
    papers counted as Today counts them. Its queries moved to `lib/queries-approve.ts` (queries.ts 374 → 318 lines).
- **Checks:** u37 failed first, 4 of 4, then passed; `test_the_reason_a_child_has_no_paper_is_kept_on_their_plan` failed
  on the missing column, then passed (with test_week, 21 passed). The specs that pinned the old layout keep their
  promises on the new one: u9, u16, u22, u24, u26, u33, u36, m4 (it found the maker split), s7 and u27 (the counted
  button; u27's classes now have papers to approve, so the refused approval is a real one).

## L5: a paper drawn for a child holds the 21-day window, as the week does (2026-10-16)

- **Seen on live:** Neha, Grade 1's educator, asked the maker for one Class assessment for her 13 children: Equal groups
  (repeated addition), Medium, 12 questions, one paper for all. It was refused: "only 4 questions none of these 13
  children has been given …; ask for 4 or fewer".
- **Cause:** Medium Equal groups (four or five groups of 2 to 6, as a sum or a picture) can make 20 questions; the bank
  holds 16 (`min_items`). ADR 0011 allowed so small a level because of the 21-day window (`exposure.days`, a threshold
  row; SPEC: "exclude any item that child has seen in the last 21 days"). The week's assembly reads it.
  `focus_paper._draw`, which draws every maker paper and home assessment, refused any question a child had *ever* been
  given. A small level ran dry for a class for good.
- **Fix (ADR 0079, `goals/l5-seen-means-the-last-21-days.yaml`):** `settings.exposure_days` is the window's one reader.
  The week's assembly, `focus_paper._draw` (so the maker and home assessments), and the week's scenario check (which read
  it from `config`, where no such row is) all use it. The refusal names the window: "only 4 questions in Equal groups
  (repeated addition) at Medium that none of these 13 children has been given in the last 21 days; ask for 4 or fewer".
  A child's page says "none Asha has been given in the last 21 days", read from the row.
- **Not checked from here:** how many of Grade 1's Medium Equal groups questions the class was given in the last 21 days.
  Live's database does not answer from this container. If fewer than 12 are left inside the window, Neha's paper is
  still refused, now saying why; then a second line at another level fills it.
- **Checks:** `test_a_question_given_before_the_window_comes_back_and_one_given_inside_it_does_not` failed first (a
  question given 22 days ago refused), then passed. Engine: test_maker, test_focus_paper, test_paper_from_library,
  test_week, test_focus and the scenario tests, 62 passed. Web: m2, m4, u38, s11, u2, 23 passed (m2's refusal words
  updated). `bin/check` 28 passed.

## L6: a paper is always made, repeating the questions seen longest ago (2026-10-16)

- **Asked:** after L5, a line the 21-day window could not fill was still refused. Nimish: "I don't want teachers to have
  this many complications. Can we just make it simplified". He chose: always make the paper, repeating the oldest.
- **Now (ADR 0080, `goals/l6-a-paper-is-always-made.yaml`):** `focus_paper._draw` (the maker, home assessments) takes
  the questions fresh to the paper's children in the window, then those they were given longest ago, then those another
  paper of the batch holds; never one twice on a paper. Each line reports `seen_before`; the maker's preview says it in
  one line ("5 of these questions were seen before: the bank had no more fresh ones."). `assemble.for_week` gives a child
  who has sat every worksheet at a level the one sat longest ago (`_seen_longest_ago`). The only refusal left: more
  questions than the level holds ("… holds 16 questions at Medium; ask for 16 or fewer"), or no worksheet at the level
  yet. The week's scenario `names_the_child_it_could_not_fill` became `gives_every_child_a_whole_paper`.
- **Checks:** the new tests failed first on the refusal, then passed. Web m2, m4, u37, u38: 19 passed.

## L7: each maker line is a topic, its skill, a level and how many; the educator's choice decides (2026-10-16)

- **Asked (Achal, through Nimish, an educator waiting):** 2-digit × 2-digit and multiples & factors were not in the
  maker; choosing Multiplication still listed every skill; he wants one paper from several topics.
- **Cause:** the maker listed only skills taught in the class (F1f) and levels of its grade or below (F1e);
  2-digit × 2-digit is Grade 4 at every level, multiples not switched on in the school's rows. The Topic box only
  filled the lines; each line's list held every skill. `focus_paper._asked` refused both too.
- **Now (ADR 0081, `goals/l7-a-line-is-topic-skill-level-number.yaml`):** each line of `/papers/make` and
  `/make/custom` is Topic → Skill (that topic's only) → Level → how many (`app/(app)/make/lines.tsx`,
  `lib/maker.ts:lineTopics`). Every skill is offered; the class's grade's first; "· Grade 4", "· not taught yet" and a
  level's grade said on the option. "Start from a topic" fills the lines at once. `_asked` checks only that the skill
  and level exist (`shelf.catalog(every=True)`). A child's own next step, the week, and the per-child change on the
  maker keep to the class's grade and what it was taught. F1e's and F1f's tests now prove that boundary.
- **Checks:** the engine tests failed first on the refusals, then 79 passed (maker, taught_per_class, focus_paper,
  paper_from_library, week, focus, topics). Web: u39 (new), m2, m4, u16, u29, u30, 20 passed. u39 was written before
  the page but not run red first; the labels it reads did not exist before.
- **Main's CI red on 9ed8de4:** `test_a_skill_set_is_read_as_itself` called `shelf._catalog(conn, None)` with the old
  two arguments. `every` now defaults to False; that test and its neighbours, 44 passed.

## L9: "not taught yet" is said where it shows (2026-10-16)

- **Seen on live:** Nimish, on Curriculum's table: "while this is showing not taught; on the tip i am not even having an
  option to mark these as taught". The switch was in a panel above the table for a whole topic, and for one skill three
  clicks deep in a closed "Taught" fold; the row that said "not taught yet" offered nothing.
- **Now (`goals/l9-not-taught-is-said-where-it-shows.yaml`):** a topic's or a skill's row that says "not taught yet"
  carries the switch for a person who may say it (`mayDecide(me, "topics")`): one button when one class of the grade
  waits ("Mark taught in G2"), else a choice of those classes and "Mark taught". `lib/taught.ts:untaughtByGrade` names
  them. Said of a topic's row, every skill in it; of a skill's row, that skill alone (`switchTopic`, unchanged).
- **Since L7 "taught" does not gate a paper an educator builds**; it decides what the engine picks by itself and what a
  class's pages show.
- **Checks:** u40 failed first (no button on the row), then passed; with u12, u17, u19, u24, u30, u31: 24 passed.

## B0c — the four levels are read from `difficulty` everywhere (2026-10-20, ADR 0084)

- **Built (`goals/b0c-levels-from-the-table.yaml`, PR #228):** every reader outside the maths library takes the levels'
  names and order from `difficulty`: the engine (`vocabulary.levels` / `letters`: prescribe, library codes, the bank's
  coverage, rehome, the home paper's level via `shelf.rule`), the website (`lib/levels.ts`; a skill's own levels as
  `levels`, ordered in SQL; every page, form and query that listed or ordered them) and `next_difficulty` (steps along
  the table's order, so a fifth level is reachable). Migration 20261121090000: `difficulty.letter` (E, M, H, A from the
  seed, unique per school) and the config row `level.usual` ("Medium", where four files each wrote it).
  `assess/placing.py` still names levels: the maths library's own rule, outside the test.
- **Rejected:** the letter computed as the level's initial; B0a's test adding "Expert" failed on it (clashes with Easy).
- **Checks:** `tests/test_levels.py` failed first (every file and `next_difficulty` listed; no `vocabulary.levels`; no
  `letter`); the ten next-level cases passed before and after. CI on 55bef20: engine (whole suite), web and browser
  green. Rehearsal run 39471842250: the migration applied on 160,215 of live's rows, `library build` made 0 and retired
  0; it then stopped at `live data` on the 16 Oct papers (main fails the same way). L13's check (d96972f) ported in
  55bef20; rehearsal run 39473436188 green end to end.
- **`bin/engine done b0c-levels-from-the-table`** (local copy): all six sentences PROVED; criteria 1 and 3 PASSED; the
  whole-suite criterion timed out at 1800 s in this container; run directly here it is 2571 passed, 2 skipped
  in 1884 s (the slowest are the reader's and the invariants', untouched here), and green on CI in 20 min; NOT DONE
  also for not being on main or live.
- **Merged with B0b (63f35e5):** main's grades (`grades()`) and this branch's levels (`levels()`) both kept; `topicLines`
  / `lineTopics` take the grades and the usual level; the curriculum walks `grade`'s rows in `difficulty`'s order. A
  fresh database from all 82 migrations (B0b's 20261120090000, then B0c's 20261121090000) applied cleanly; `engine
  live rules --write` on it gave the merged rules.json unchanged (271 rules). `bin/check` 28 passed; web `tsc` and
  eslint clean; level/grade/library/rules tests 155 passed. Rehearsal run 39491988653 on 63f35e5 green: copied 160,215
  rows; live already holds B0b's migration, so only 20261121090000 applied; `library build` made 0, retired 0; the copy
  after clean. `bin/engine done` again: six sentences PROVED, criteria 1 and 3 PASSED, the whole suite timed out at
  1800 s here (CI runs it).
- **Merged with #232 (main, 37683c3) at 80aebcf:** the marking check (`live_data._marking`) and its test are main's; this
  branch's port of L13's check is gone. Main added no migration; a fresh database from all 82 migrations (B0c's
  20261121090000 last) built cleanly; rules.json unchanged. `bin/check` 28 passed; level, grade, rules, live-data,
  copies, vocabulary and library tests 86 passed. `bin/engine done b0c-levels-from-the-table`: six sentences PROVED; all
  three criteria PASSED, the whole suite 2577 passed, 2 skipped in 1673 s; NOT DONE for not being on main or live.
  Rehearsal run 39531106626 on 80aebcf green: 160,215 rows copied; live at 20261120090000, so only 20261121090000
  applied; `library build` made 0, retired 0; the copy after: 19 invariants, 0 violations; `ok Marking counts each
  printed question once`.

## Marking counts each answer once: the check counted questions, not answers (2026-10-20, W3)

- **Which reading:** the check was wrong; no answer was counted twice. Measured on live through the engine's API
  (`GET /read/scan/2026-10-16.pdf/copies`, `/capture/{id}/readings`): each of the five papers has one live reading.
  CS2A6B23, CSCE3E2C, CSA4999D, CSB8ACB3 print 13 questions, two of them grids asking five answers each (`ans`,
  `s1`–`s4`): 11 + 10 = 21 results, every one a different question and answer. CS6A1049 (roll 1, page 1 not scanned):
  one grid and 4 others, 9 results. `_marking` compared results with distinct *questions* (13), so each grid's four
  extra cells read as "counted twice". No child's score or map was affected.
- **Fixed (`goals/l13-marking-counts-each-answer-once.yaml`):** `live_data._marking` counts the answers each printed
  question asks for (its `responses`, at least one) and calls twice only the same question *and* answer (`rid`) on two
  live readings of one paper. `test_each_answer_of_a_grid_question_counts_once_and_is_not_counted_twice` failed first
  with live's own words ("5 answers counted for 1 questions printed, 4 counted twice"), then passed; the page scanned
  twice still fails.
- **Seen on the way, fixed too:** a copy's score (`copy_scores.tally`) counted an answer read wrong or blank that a
  person then judged right as right *and* wrong: roll 1 of that scan showed 6 right, 5 wrong of 9 answers.
  `test_an_answer_read_wrong_and_judged_right_by_a_person_counts_once_as_right` failed first (wrong 2, blank 2), then
  passed.
- **`bin/engine done l13-marking-counts-each-answer-once`:** three sentences PROVED, criteria PASSED (7 passed, 1 skipped;
  bin/check 28 passed); NOT DONE for the manual rehearsal line and not being live.
- **Rehearsed on a copy of live (run 39480469879, 784f54b):** "copied: 63 tables, 160215 rows, every count equal to
  live"; `engine live data` before the update: `ok    Marking counts each printed question once`, and again after
  `bin/update-live`'s steps (the copy after, must be clean: every check ok).

## B1 — a skill's levels are rows (`skill_level`), kept equal to the blob; the first readers moved (2026-10-21, ADR 0087)

- **Built (`goals/b1-levels-are-rows.yaml`, scope not yet locked):** migration 20261123090000 makes `skill_level`, one
  row per skill and level, keyed into `skill_set`, `difficulty` and `grade`, holding the level's words (`looks_like`),
  its rule (everything else of the blob entry), its grade (named in `level_band`, else its rung's) and who approved it
  and when; `skill_level_version` files a level's earlier words and rule, only that level's, and the migration carries
  each level's history out of `skill_set_version` once. A trigger on `skill_set` (and on a rung's grade) keeps the rows
  equal to the blob whoever writes; nobody else may write them. `learning_objective` waits empty (the split is B3's).
- **Measured on the seed:** 178 levels, 178 rows · G1 16 · G2 63 · G3 55 · G4 44 · approved 0 and 0 (a fresh build has
  no approvals). `bin/engine levels check`: words, rule, grade and approval equal on every level, and 4 questions drawn
  from each of the 178 levels on seed 1 from rows and blob, identical.
- **Readers moved:** the generator's spec (`spec.row`, `spec.read`, so `bank.fill`, `fill_native`, `refill`, the mistake
  list), `cases.holds`/`placed`, `review`, `story_shape.placed`, `week_note.options`, `audit`, `references`, `legacy`, the
  item_generate eval; on the website the bank's totals, a question's level words, the home counts and the people page's
  "reaches". After B0c (#228) merged into main (861e624), main was merged in here (cc2144f, a merge commit) and
  `inventory.coverage`, `rehome.shaped` and the worksheet library's level list moved too. **Left for after B0d merges**
  (PR #231 rewrites them): `prescribe`, `shelf`, `focus_paper`, `focus`, `loaders`' counts, and the website's
  `queries.ts` with the curriculum, children, worksheets, papers/approve and skill-set pages that read through it. The writers (the site's edit, approval and move, the loader,
  `engine ratify`, `cases` bringing levels to the seed) still write the blob, by design (ADR 0087).
- **A fresh build from this branch and one from main differ by one level, by chance:** 28,698 questions and 2,737
  worksheets here, 28,696 and 2,736 on main, all on SUB.3D2D Advance's case S33 (9 questions here, 7 on main; every
  other case of every level equal). S33 has few questions left once Hard has taken its 44, and the bank looks for them
  with fresh randomness each build: main's own code on main's own database finds 6 on seed 0 and none on seeds 1–7.
  The level's rule is the same from rows and blob (`engine levels check`), so this is the bank's chance, not B1.
- **Checks:** `tests/test_skill_level.py` failed first (no `engine.checks.levels`), then 6 passed: keys refuse a level
  or grade that is no row; the rows give back the blob; same draws; a blob write reaches the rows; a level's own
  history, carried on first run; a moved reader reads the row even where the blob says otherwise.

## B0b — grades are read from the `grade` table; every grade a row holds is a key; "G2+" is Grade 2 (2026-10-20, ADR 0085)

- **Built (`goals/b0b-grades-from-the-table.yaml`, PR #229):** the website reads the grades once a request (`grades()`,
  `lib/queries.ts`); SQL orders and compares by `grade_ord(tenant, code)` or a join to `grade`; the engine likewise
  (`shelf._read_levels`, `week_note.options`, `parent_facts`, `every_report`). Migration 20261120090000: "G2+" → G2 on
  rung, sheet_template, blueprint, level_rule and `level_band`; a key on (tenant_id, band) into `grade` on ten tables;
  `level_band` checked on every write (`level_band_is_keyed`) and a grade a level names kept (`grade_held_by_a_level`);
  `class_band` breaks a tie by the grades' order. Seed: X1, X2 are G2.
- **Checks:** `tests/test_grades.py` failed first for the right reasons (the scan listed every site; "rung.band is no
  key into grade"; "rung.band still holds a '+' grade"; a Grade 9 + Grade 10 class read as G10), then 5 passed.
  `apps/web/tests/u34-grades-from-the-table.spec.ts`: a level moved to Grade 10 shows under Grade 10, last; reasoning
  under Grade 2 — 20 passed locally with s2, u12, u19, u20, u33.
- **No paper moved but the decided word:** every library worksheet drawn as HTML with main's code before the migration
  and this branch's after it, on one copy: 2,593 of 2,737 identical to the byte; the 144 reasoning worksheets differ
  only in "Grade 2+" → "Grade 2" (header and footer). The child's map already drew reasoning under Grade 2
  (`left(band, 2)`); its columns now come from `grade` in the same order.
- **What a person sees change:** reasoning's two skills under Grade 2 (the "Reasoning · Grade 2 and up" group gone);
  a Grade 2 child's profile counts the taught reasoning skill among the grade's; a Grade 3 or 4 class's week no longer
  offers the two reasoning skills (the week keeps to a class's own grade, test_week_note); a level's grade can be any
  grade the table holds; the menu reads "Grade 1–Grade 4 · Maths".
- **Rehearsed on a copy of live** (run 39467290221 on 6fbd2f6): "copied: 63 tables, 160215 rows"; live held G2+ on 2
  rungs and 337 worksheets, every other grade a row of `grade`; `applying 20261120090000_grades_from_the_table.sql`
  with no error; the update sequence ran after it. Its last step fails only on "Marking counts each printed question
  once" (the 5 papers of B0a below), as main does. Run 39466319322 met live mid-deploy of B0a ("relation grade does
  not exist"): live recorded 20261119 between the copy's schema step and its migration step.

## B0a — grades, levels and a child's states are tables, every link to them a key (2026-10-20, ADR 0084)

- **Built (`goals/b0a-the-vocabulary-is-tables.yaml`):** `grade` (14 rows, PG → G10), `difficulty` (4) and
  `child_state` (6, with words, colour, needs_work), from `supabase/seed/vocabulary.json`, made for every school by
  migration 20261119090000. Keys on (tenant_id, code): topic → subject, skill_set → topic, item / prescription /
  sheet_template / item_review difficulty → difficulty, child_skill_state.state → child_state; the four CHECKs they
  replace are gone (`rules.json` rewritten from a database built from the migrations). Nothing reads the new tables yet.
- **Checks:** `tests/test_vocabulary.py` failed first (`relation "grade" does not exist`; topic.subject_code no key),
  then 4 passed with test_loaders and test_rules (19 passed). CI on 899891c: web and browser (every spec) green.
- **A school added later gets its words too** (CI, 2026-10-20: `test_live_data` made a school with no states and its
  child's map could not be rebuilt): `internal.school_vocabulary()` makes them for every school there, and a trigger on
  `tenant` for any added later. `bin/engine done b0a-the-vocabulary-is-tables` on 7568a7d: all four sentences PROVED;
  criteria PASSED (19 passed; whole suite 2555 passed, 2 skipped; bin/check 28 passed); NOT DONE only for the manual
  rehearsal line and not being live.
- **The rehearsal now meets live's rows** (`rehearse-update-live.yml`): migrations live has not applied run after
  live's rows are restored. Run 39447048331 (and 39454151982 on 7568a7d): "copied: 60 tables, 160191 rows", then
  `applying 20261119090000_the_vocabulary_is_tables.sql` with no error, so every live row satisfies every new key;
  `bin/engine load` and the whole update sequence ran after it.
- **Not this change, seen by it:** `engine live data` on the copy: "Marking counts each printed question once" FAILs on
  5 papers (CS2A6B23, CSCE3E2C, CSA4999D, CSB8ACB3: 21 answers for 13 printed; CS6A1049: 9, 4 twice), already in the
  step before any update ran. Main fails identically (run 39449844559 on 1d92306), so it is in live's data, not this
  change; the last green rehearsal (2026-10-15) was before the 16 Oct scan was read.

## L12b live; 2026-10-16.pdf read at 0.76; each reading's line returned by the API (2026-10-16)

- **L12b live by hand, at Nimish's word:** #223 merged as 945adb2 (16:08 UTC). `deploy engine` (run 38929617532,
  with its step loading thresholds from the seed) and `migrate live` (run 38929621227) both succeeded; `/health` 200.
- **2026-10-16.pdf read again on live (`again`, run 6bfbd6a3, 16:18–16:20 UTC):**
  - read right 73 → 74, wrong 11 → 11, unclear 9 → 8; all 93 still wait for a person.
  - The only answer that moved is roll 4's "862" (MUL.1D3D): 2 boxes held ink at 0.72, 3 at 0.76, now read right
    (99.9%). The other four copies total the same as at 10:13.
  - The earlier claim here, that this 6 needed about 0.78 and still waits at 0.76, was wrong. It came from a rough
    check on the photograph, not from the reader's own boxes.
  - The 8 still unclear: 7 under the confidence floor (71–90%), and roll 5's 9000 seen as "900" in four inked boxes,
    held rightly. None waits on ink.
- **The line each reading was read at was not returned by `/capture/{id}/readings`** (`copy_scores.readings` kept a
  fixed list without `ink_line`), so 0.76 on live could be inferred only from the 862's count moving. Now returned;
  `test_ink_line.py::test_a_read_copy_a_person_settled_is_measured_as_the_reader_found_its_boxes` proves it.
- **`reader ink` on live (run 38931391155, from 945adb2, 16:22–16:56 UTC):** 328 settled answers; 312 count, at the
  line each was read at, as their reading stored (309 at 14:31).

  | line | agree | lose ink | gain ink | settled blanks given ink |
  |---|---|---|---|---|
  | 0.72 | 284 | 40 | 4 | 0 |
  | 0.74 | 290 | 33 | 5 | 0 |
  | 0.76 | 294 | 28 | 6 | 0 |
  | 0.78 | 295 | 26 | 7 | 0 |
  | 0.80 | 293 | 26 | 9 | 0 |
  | 0.84 | 290 | 25 | 13 | 0 |
  | 0.88 | 287 | 23 | 18 | 0 |

  - **The line stays 0.76.** 0.78 agrees on one more answer of 328, and gains ink on one more. Between the two runs
    each line moved by 3 or 4, so a gap of 1 is not a measured difference. ADR 0083 asks for the next decision once 16 Oct
    is settled, and it is not yet.
  - **The measure reproduces.** The 36 answers both runs list as counted differently by a fainter line have the same
    count at every line in both. What moved is which answers count as settled: copy dfca69a5's ADD.2D2D answer left
    the list, and the total stayed 328. Live's database does not answer this container, so which answers were
    settled or judged between 14:31 and 16:22 is unchecked.

## L12a live and measured on live; L12b: the ink line is a row, 0.76 (2026-10-16)

- **L12a live by hand, at Nimish's word:** #222 merged as 912290e (13:19 UTC). `deploy engine` (run 38907244418) and
  `migrate live` (run 38907249370) dispatched; engine on 912290e at 13:26 UTC.
- **`reader ink` on live:**
  - First run (38908115501): ssh dropped after 4m41s, silent. `engine logs` (38908838068) showed `engine read ink`
    still measuring (5m35s, 146% CPU, 604 MB, no out-of-memory kill, 0 restarts).
  - Fixed with keepalives (#223), and run again from the branch (38909176094): 55 minutes, 328 settled answers.
    309 of them count, at the line they were read at, as their reading stored.

  | line | agree | lose ink | gain ink | settled blanks given ink |
  |---|---|---|---|---|
  | 0.72 | 281 | 40 | 7 | 0 |
  | 0.76 | 291 | 28 | 9 | 0 |
  | 0.80 | 289 | 26 | 13 | 0 |
  | 0.84 | 286 | 25 | 17 | 0 |
  | 0.88 | 283 | 23 | 22 | 0 |

- **The 16 Oct scan at 13:21 UTC:** 93 answers, all waiting for a person (73 read right, 11 wrong, 9 unclear); none
  checked yet.
- **L12b (`goals/l12b-the-ink-line-is-a-row.yaml`, ADR 0083):** the line is the row `read.ink_line`, 0.76.
  - `digits.settings` carries it to `boxes.read_page`, and each reading records `ink_line` beside `inked`.
  - `engine read ink` also counts at 0.74 and 0.78, and compares each stored count at the line it was read at.
  - The 16 Oct "862" measured about 0.78 on its photograph (a rough check, not the reader's own boxes). On live it
    reads right at 0.76: see "L12b live" above.

## L10 + L11 live; L12a: where a pencil mark is told from the paper, measured (2026-10-16)

- **Live by hand, at Nimish's word:** #221 merged as 387c20e (10:04 UTC). `deploy engine` (run 38884830849) and
  `migrate live` (run 38884834073) dispatched; site live 10:05:13, engine on 387c20e at 10:11 UTC.
- **2026-10-16.pdf read again on live (`again`, run 9626d44d, 10:13 UTC):**
  - read right 65 → 73, wrong 11 → 11, unclear 17 → 9;
  - roll 4 is one copy of 21 answers, its first page no longer read twice.
- **The 9 still unclear:**
  - 7 under the confidence floor (71–90%), one of them a real misread ("36" for 30);
  - 1 held rightly (roll 5's 9000 seen as "900" in four inked boxes);
  - 1 lost to faint pencil: roll 4's "862", its 6 at most 21% darker than the paper where `boxes.dark` asks 28%.
- **Not checked from here:** the "page 1 of 2 is not in this file" line on the run and under Read a scan. No route
  returns `flow_run.result`, and live's database does not answer this container.
- **`bin/engine done` on main's code** (after this container's database came back from a restart):
  - L10: 1/1 proved, 2/2 criteria;
  - L11: 4/4 proved, 3/3 criteria;
  - each NOT DONE only on the live database and its manual step.
- **L12a (`goals/l12a-where-pencil-is-told-from-paper.yaml`):** `engine read ink` (`w3_read/ink_line.py`) takes every
  answer a person settled on a copy read in its boxes, typed or signed off as read.
  - It finds each answer's boxes again as the reader did and counts the boxes holding ink at lines 0.72–0.88, against
    the digits the answer was settled with.
  - It says per line how many answers agree, lose ink, gain ink, and how many settled blanks are given ink.
  - It writes nothing and names no child. It runs on the server by hand (`.github/workflows/reader-ink.yml`).
  - `boxes.dark` takes the line, default 0.72, so the reader is unchanged.
  - `tests/test_ink_line.py`: 4 passed, all failing first. A faint 6 is ink at 0.88 and not at 0.72, and an empty box
    is ink at neither. A worksheet printed for a child, written in, scanned, read by the box reader and signed off
    measures 12/12 agreeing, its count at 0.72 the one stored with each reading.
  - `bin/check`: 28 passed.

## L11: a child's pages anywhere in a scan are one copy, and what a scan lacks is said (2026-10-16)

- **Measured on the 2026-10-16 Grade 3 scan** (10 pages, contact sheet of every page, kept out of git): roll 1's
  "missing" first page was never in the file. Roll 4's first page is in it twice, as pages 1 and 9. Pages were one copy
  only where they lay together (`sorting.group`), so page 1 was read as a copy of its own. Pages 9–10's reading then
  replaced it (`copies._replaces`). Nothing on the run or the site said a page was missing: `inbox.read` threw away
  what `copies.read` returned.
- **What the old code dropped, run before the fix** (stand-in reader, a 4-page worksheet of 12 questions):
  - one child's pages apart in the file: 9 of 12 answers kept;
  - a whole copy, then its first page again: 3 of 12 kept;
  - 16 Oct escaped only because the lone page came first.
- **L11 (`goals/l11-a-scan-is-read-whole.yaml`):**
  - `sorting.gather` makes a child's own code (`OURS`) one copy wherever its pages lie; a library worksheet's copies
    stay apart.
  - `copies._placing` places each run alone, and each photograph alone where a run is longer than its paper. A page
    photographed twice is read from its later photograph.
  - Each copy's line carries `missing`, `twice` and `lacks`. The `lacks` words are the engine's, e.g. "page 1 of 2 is
    not in this file: scan it and send it to be read".
  - `inbox.read` keeps the lines on `flow_run.result`, by child id, never a name. Marking and Papers show the last
    three files under Read a scan, by class and roll, to the people whose classes they are.
- **Proved here:**
  - `tests/test_a_scan_read_whole.py`: 5 passed (all 5 failed first, for the reasons above).
  - The reading tests (sorting, copies, handout, inbox, read_back, every_answer): 54 passed.
  - `u41-what-a-scan-lacks.spec.ts` + `u3-marking.spec.ts`: 7 passed.
  - `bin/check`: 28 passed.

## L6, L7 and L9 live; L10: a small zero is a digit (2026-10-16)

- **Live by hand, at Nimish's word:** L6 + L7 on 2eb105c (Vercel 05:56, engine 06:00 UTC), L9 on 3b2abc3 (Vercel
  06:36:47); `deploy engine` and `migrate live` dispatched before main's CI finished. Main's CI then passed on both
  (2eb105c 06:28, 3b2abc3 07:03). `bin/engine done` on main's code: L7 4/4 + 3/3, L9 2/2 + 2/2, L6 3/3 proved and
  3 of 4 criteria (the week goal's suite fails here on two `test_rules` tests: the local copy carries SF2a's parked
  migration, which main's migrations do not; CI is green). Each says NOT DONE only because live's database does not
  answer from here.
- **The 2026-10-16 Grade 3 scan** (Drive folder `1A3vNmSQ…`, not read by the n8n flow; read by hand at 08:02): 5
  copies, 93 answers, 65 right, 11 wrong, 17 unclear. Of the 17, 15 were read right: 9 waited on "N boxes hold ink but
  the reader saw …" (zeros written 40–44% of the box, under DIGIT_TALL 0.45), 6 under the confidence floor (71–90%).
  Roll 1's first page matched no child (9 of 21 answers read).
- **L10 (`goals/l10-a-small-zero-is-a-digit.yaml`):** DIGIT_TALL 0.45 → 0.33, between a tick (23%) and the smallest
  digit measured (40%). `test_a_zero_written_small_is_a_digit_and_a_tick_is_not` failed on 0.45, passes on 0.33;
  test_boxes 24 passed; the reader's tests (boxes, copies, inbox, lineup, ocr, digits, read_again, read_back,
  read_eval, second_reader) 153 passed before the test's tick was sized as measured.

## UX5a live; UX5b: Home assessments and Marking open on the educator's class, a next step per child (2026-10-16)

- **UX5a live:** #216 merged as `9a87004` (02:38 UTC). Main's CI passed; `migrate live` (run 38844303957) applied
  20261118090000 and set `live database` at 03:12:09 UTC; Vercel 03:12:10. `bin/engine done ux5-papers-grouped` on main's
  code, on the copy: 4/4 promises proved, 3/3 criteria (85 browser tests, 21 engine tests, `bin/check` 28). It says NOT
  DONE only because the live database does not answer from this container; the migrate run is the live check.
- **Before (the audit's edu-laptop-make, edu-laptop-make-class, edu-laptop-capture, coord-laptop-capture):** an educator
  with one class met a table of one class and an "Open" link. A class's home assessments ran their why to 7–9 lines in a
  column squeezed by three action links a row and a "12 questions" every row repeated. Marking stacked a banner over five
  tiles; its children sat in eight bookkeeping columns; the coordinator got every class open.
- **Now (`goals/ux5b-make-and-marking.yaml`, `tests/u38-make-and-marking.spec.ts`):**
  - Home assessments: an educator who teaches one class opens on it (`/make` redirects). Each child still waiting is one
    line — Roll, Child, Works on, Why, Next step. What it works on opens the paper as it will print; the count every
    paper shares is said once ("12 questions each"). The next step is one: Approve (with "or choose another" under it),
    or "Choose one" where the engine has nothing to go on. Children already approved fold under one line ("1 approved
    this week"). A class paper waiting for the class is one line above the table, as the class list used to show it.
  - The why is the engine's sentence, never cut: the audit asked for one line, but mistake names run to 84 characters
    (M_SMALL_FROM_LARGE), so the longest why is about 130. The bar is two lines at 1280 px, measured by the browser's
    line boxes; a why column squeezed as before measured 7 lines and failed.
  - Marking: one sentence says what is in and what waits ("3 papers in: 5 answers settled by the engine, 0 checked by a
    person, 2 waiting for you to check; 2 papers to sign off."), the queue one tap away. By child, each class is one
    line saying what waits in it, open for the educator who teaches it, closed for the coordinator, opened by
    `?class=`. Open, its children: Roll, Child, Paper, Waiting, Next step — check the answers waiting (on the one paper
    that holds them, or the child's papers when several do), sign off, look at a paper that came back with nothing, or
    "Signed off". By class and by worksheet keep every count.
  - On a phone the why (Make) and the paper (Marking) fold away, so the next step is on screen.
  - The plural rule (`many`) is one helper in `lib/needs-you.ts`, used by Children and Marking.
- **Checks:** u38 failed first, 5 of 5 (each at its first new assertion), then passed. The specs that pinned the old
  pages keep their promises on the new ones: m2 (an approved child folds; Chetan's step is "Choose one"), u3 (the
  sentence holds the counts the tiles held; a child's row its answers waiting), u1 (the sentence's papers to sign off),
  s4 and screens (a class opened by `?class=`), u10 (alignment read inside a closed class line). The goal's 17 specs:
  110 passed; `bin/check` 28 passed; tsc and eslint clean.

## A copy photographed from its second page was read in the wrong layout (2026-10-15)

- **Seen:** PR #213's engine job on `2cbd41d`, which changed no engine code. Two `test_copies` tests failed: a copy
  holding its paper's pages 2–4 had answers on questions 1 to 8. The same code passed on three other heads.
- **Why only sometimes:** `bank refill` draws unseeded, so each CI database holds different word problems. The test
  worksheet is the bank's first twelve. When their stems are short, the layout before L3 (2026-09-21, smaller working
  boxes) draws them in 3 pages, where today's draws 4.
- **Cause:** `boxes.as_printed` chose a layout by keeping only those with as many pages as the copy's photographs,
  and took the only one left unmeasured. A copy split across two files holds fewer pages than its paper, so a
  3-photograph copy of a 4-page paper matched the 3-page old layout. Placement then took its pages as 1–3 without
  measuring, and the answers were read against the wrong questions and keys. Reproduced on the copy with the twelve
  shortest word problems ({'2026-10-10': 4, …, '2026-09-21': 3}).
- **Fix:** every layout long enough to hold the photographs is measured alike (`boxes._runs`: the best run of its
  pages the photographs fit), and the page count no longer chooses. `agreement` and `_agreeing` went with it.
  `test_a_copy_holding_its_later_pages_is_read_in_its_own_layout_whatever_another_layout_draws` builds the case from
  36 fixed sums (today's layout 3 pages, the old one 2); it failed before the fix, picking the old layout.

## `/growth` "could not load" on CI: a function's row guess made Postgres compile the query (2026-10-15)

- **Seen:** main's browser job on `3d07f66`, and once on T1's PR: the first load of `/growth` hit the page's 8 s limit.
  The query ran 3.97 s planning and 4.17 s executing on CI; 25 ms of work.
- **Cause, reproduced on a copy built as CI builds it:** `pii.read_child` returns one row but was declared with
  Postgres's default guess of 1,000, so the Children page's query (one name per child) was planned at 24,000 rows for
  24 children, cost 653,786: above `jit_above_cost`, and above the inlining and optimisation thresholds. Postgres
  compiled it before running it: 2,057 ms of compiling for 25 ms of work here, past 8 s on CI's slower runner.
  Earlier I put this down to a checkpoint (the `checkpoint` in `bin/testdb`, T1); that was not it.
- **Fix:** migration 20261116090000 declares `pii.read_child` and `next_difficulty` one row each. The same query: cost
  671, no compiling, 4.5 ms (was 2,081 ms). `tests/test_db_plans.py` holds both the declaration and the plan.
- **The same cause, a second time, where no declaration can reach it:** PR #213's browser job on `3135c85`. A skill's
  page (`e2e.spec.ts` "a skill on the map opens its own page") missed its heading's 5 s. Its query counting the
  mistakes reads `jsonb_array_elements` and `jsonb_object_keys`, Postgres's own functions, each guessed at 100 rows:
  8,730,000 guessed for 3,530 read, cost 1,723,004. On the CI-built copy it compiled for 366 ms of 406 ms; CI's log
  shows 4,061 ms. Our functions can say how many rows they return; Postgres's own cannot be told.
- **Fix at the cause:** migration 20261117090000 turns compiling off for the website's role, `app_web`. Every page
  query takes milliseconds, so compiling never pays for one. The engine's batch work keeps Postgres's choice. As
  `app_web` on the copy: `show jit` → off; the same query 8.8 ms (was 406 ms).
  `test_the_websites_role_never_compiles_a_query` failed before the migration and passes after it.
- **On live this holds only once the website connects as `app_web`.** That switch is Nimish's (the roles section
  above: "Live switches by Nimish's hand"). I do not know whether it has been made. Until it is, live's pages run as
  the owner and may still compile.
