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
  `G3/1. Kabir/Assessment 0/WhatsApp Image 2026-08-16 at 18.02.42.jpeg`.

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
  through the screen, by hand: Kabir's question 6, where Textract read `363` at 79.8% and the child
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
  counted on the screen rather than averaged away. Kabir's paper opens at `12 read and marked · 6
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
  --child Kabir --section G3 --pages 1` → `16 answers read, 7 for a person`, and `--pages 2` on the
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
  38 photographs placed, and **Kabir's four are in a different order from every other child's**, so
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
  - **red ink is the educator's and is inpainted out before the page is read.** Kabir's 5147 under
    a red circle came back `147` at 95%, his 533 as `53`. Inpainted rather than whited out: a white
    gap through a 7 leaves a 1. Measured both ways on the gold — same 78.0% exact, and silently
    wrong 3 → 1. It is a row (`ocr.red_pen_mask`), so it can be turned off for a school that marks
    in pencil.
  - a word on the question's own printed line belongs to it, by geometry — Textract gives a child's
    large digits a line of their own, and 5147 sat a hair above the region's top edge

- **`engine read eval --reader ocr --runs 2` → 78.0% exact (64/82), 100% given a row, 1.2%
  silently wrong (1), spread 78.0–78.0%.** The gold grew from 63 to 82 with Kabir's Grade 3–4 quiz,
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

- **Why.** Kabir's quiz prints "24,568 + 37,845 =" and Textract returned the printed `37,845` a
  second time, tagged as handwriting, on top of where it is printed — and the engine stood behind
  it as his answer at 94%. The rule added to stop that dropped **any** number the question
  mentions. But the answer to "15 + ___ = 30" IS 15, and the answer to "52 birds, 26 flew away"
  IS 26. The rule threw away correct answers, at 97% confidence, across two whole papers.

- **The fix is position, not value.** A number is the paper's only where a printed word of the same
  value **overlaps it on the page** — the same mark found twice. Kabir's duplicate overlaps its
  printed original and is dropped; a child's answer written in a blank, or below their working,
  overlaps nothing and is kept. The "unless the child declared it with a label or a sentence"
  escape hatch is gone: it was a patch over the wrong test, and it only saved the children who
  happened to write `ans=`.

- **Measured.** `bin/engine read eval --reader ocr --runs 2` → **79.3% exact (65/82)**, 100% given
  a row, **1.2% silently wrong (1)**, spread 79.3–79.3%. Kabir's quiz sheet is unharmed at 15/19
  with 0 silent errors, which is what the rule was written to protect.

- **Across the corpus**, re-read in full: **242 waiting for a person, down from 261**, and the
  engine now settles **625 of 867 (72%)** — Grade 2 **79%**, Grade 3 **64%**.

- **The lesson worth keeping.** Both defects were in the same rule, one day apart, and the gold set
  caught neither: Kabir's duplicate because his quiz was not yet in the gold, and this one because
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
corrected and signed off Kabir's Grade 3–4 quiz. **16 corrections, every `POST /capture/correct`
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
- **A re-read had taken six of Nimish's corrections** (Kabir's quiz p2, q11–16) and one from
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
