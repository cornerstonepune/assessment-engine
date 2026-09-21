# Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the repository, the full Supabase schema, the four Phase 0 seed files and the `engine load` CLI, with the validated prototype `assess/` moved in under tests, so that every structural fact the engine needs is a row in Postgres and loading it twice changes nothing.

**Architecture:** One hosted Supabase Postgres (`ruznbyngtfjsaymuylhm`, ap-south-1) holds Ring A truth, Ring B derived shells, and a separate `pii` schema; every table carries `tenant_id`, has RLS enabled *and* forced, and a `service_role` policy. A Python package `packages/engine/engine/` holds the moved prototype (`assess/`, deterministic, no I/O), one connection helper (`db.py`), pure row builders plus one generic idempotent upsert (`loaders.py`), and a Typer CLI (`cli.py`). Structural content — skills, milestones, rungs, levels, misconceptions, prompts — lives in `supabase/seed/*.json`, never in Python.

**Tech Stack:** Python 3.12 in a `uv`-managed venv (typer, psycopg 3, python-dotenv, pytest, pytest-cov) · PostgreSQL 15 on hosted Supabase, changed only by numbered migrations applied with `supabase db push` · JSON seed files · Anthropic model id `claude-opus-5` recorded on every `prompt` row.

---

## Scope

Phase 0 of SPEC §11 only: repo scaffolding, the schema, the seeds, the prototype move with tests, the loader, the `engine load` CLI.

**Phase 0's gate** (all four must hold):

1. `uv run engine load` run twice changes nothing — the second run reports `changed 0` for every table, and `uv run engine load --check` exits 0.
2. The expected row counts are present: `tenant` 1, `skill` 37, `milestone` 162, `rung` 16, `level_rule` 12, `misconception` 24, `prompt` 5.
3. `uv run pytest` green, with at least 80 % coverage on the code this phase writes (`engine/db.py`, `engine/loaders.py`, `engine/cli.py`).
4. Zero rungs reference a skill id absent from the registry.

Phase 1 and later are **not** planned here. A separate plan covers legacy import once the school's scanned assessments arrive.

---

## Deliberate decisions this plan makes

Each of these is a place where the plan departs from a literal reading of SPEC or of a global convention. Task 12 records them in `DECISIONS-LOG.md`.

| Decision | Why | Alternative rejected |
|---|---|---|
| Every table gets `id uuid primary key`; registry and ladder ids live in a `code` column with `unique (tenant_id, code)`. | SPEC §4 says `skill.id` *is* `NUM.OPS.01` and `rung.id` *is* `R5`. With `tenant_id` on every table those are not globally unique, so a second school would collide on the primary key — exactly the "second school is a row, not a rewrite" rule breaking. | Composite `(tenant_id, id)` primary keys everywhere. Correct, but every foreign key becomes two columns. |
| Array columns are named `skill_codes` / `rung_codes`, not `skill_ids` / `rung_ids`. | They hold registry and ladder codes (`NUM.OPS.01`, `R5`), never uuids. Calling them `_ids` next to uuid foreign keys named `_id` is the kind of ambiguity that produces a silent join on the wrong column. | SPEC's literal `skill_ids[]`. |
| Ladder and registry references are **by code** with composite foreign keys (`milestone.skill_code`, `item.rung_code`); everything else references by uuid. | The loader never has to resolve a code to a uuid mid-load, so the generic upsert stays one function. The database still enforces the reference. | Resolving codes to uuids in the loader with per-table sub-selects. |
| psycopg 3 with hand-written SQL, not SQLAlchemy async. | The global Python convention assumes an ORM owns the schema. Here migrations own the schema (CLAUDE.md rule 9) and the engine's database work is bulk upserts and count queries. An ORM would add a second, drifting definition of every table. | SQLAlchemy 2.0 `mapped_column()`. |
| Prompt text lives in `supabase/seed/prompts/<purpose>.v<n>.txt`; `prompts.json` holds purpose, version, model, active flag, the JSON schema, and a `text_file` pointer. | Prompt text is 20 to 40 lines with real newlines. Inside a JSON string it becomes one escaped line, which is unreviewable in a pull request — and CLAUDE.md rule 7 makes prompt changes a reviewed event. The text still lands as a `prompt` row; the seed is only its source. | One `prompts.json` with escaped text. |
| Prompt guardrail tests assert the **prohibition is present**, not that the word is absent. | The prompts must contain the sentence `Never use the word "borrow"; the school says "exchange".` — so a test asserting the token is absent would fail on the very sentence that enforces the rule. | Absence tests. |
| `internal.apply_conventions()` is one function that enables and forces RLS, creates the `service_role` policy, and attaches the `updated_at` trigger on every table in `public` and `pii`. Every migration calls it last. | 28 tables times 3 statements written by hand is 84 chances to forget one. `tests/test_schema.py` then proves the invariant holds rather than trusting the author. | Per-table `alter table … enable row level security` lines. |
| `evidence_event` append-only is enforced by a **statement-level** trigger that raises. | CLAUDE.md rule 4. Statement-level fires even when the `UPDATE` matches no rows, which is what makes it testable without inserting evidence. | A row-level trigger (invisible on an empty table), or a `RULE` (silently swallows the write). |
| `access_log` is written by `pii.read_child(child_id, actor)`, a `security definer` function; direct `SELECT` on `pii.child` is revoked from `anon` and `authenticated`. | SPEC §4 says "trigger on `pii`". PostgreSQL has no `SELECT` trigger, so a read cannot be logged by a trigger. A logging accessor is the honest implementation of the same promise. | Leaving `access_log` as an empty table nothing writes to. |
| `M005` (conceptual "always subtract the smaller digit from the larger") is seeded as its own row with code `M_SMALLER_FROM_LARGER_CONCEPT`, distinct from the procedural `M_SMALL_FROM_LARGE`. | They are the same classroom error but different evidence: one is detectable from the wrong number alone, one only from the working. `unique (tenant_id, code, op)` cannot hold both under one code. | Folding `M005` into the procedural row as an `external_ref`. |
| The seed files are the source of truth and the tests pin them to the prototype constants — not the other way round. | `ladder.py` still holds `RUNGS` and `LEVELS` because `items.py` and `blueprints.py` import them, and CLAUDE.md rule 10 forbids rewriting the prototype. The parity tests in Task 5 and Task 6 mean the two cannot drift while both exist. | Deleting the constants now, which breaks `_item()` and every blueprint. |

### Not in Phase 0, deliberately

- **`blueprint` rows.** The table is created; it stays empty. `BLUEPRINTS` in the prototype is a dict of Python lambdas; turning it into declarative slot rows is generation work and belongs with Phase 2, which is the first phase that reads it.
- **`threshold` and `config` rows.** The tables are created; they stay empty. Every number they will hold (80 %, 50 %, 21 days, 0.2 / 0.95, auto-confirm confidence, the weekly matrix) is first read by Phase 2's prescribe step. Seeding them now would be guessing at their units before anything consumes them.
- **`opencv-python`, `playwright`, `segno`, `anthropic`, `fastapi`, `uvicorn`.** Declared as `media` and `api` extras in `pyproject.toml` so the dependency set is pinned, but not installed. Nothing in Phase 0 imports them; `assess/mark.py`, `assess/render.py` and `assess/build.py` are moved in unchanged and are not imported until Phase 1 and Phase 3. Installing a browser runtime to load 256 rows is a 400 MB no-op.
- **Coverage on `assess/`.** The gate is "at least 80 % on changed code". `assess/` is moved verbatim, not changed; it enters the coverage denominator in Phase 1, the first phase that edits it. The tests written in Task 2 still run on every commit.

### One SPEC inconsistency, resolved

SPEC §11 gives Phase 0's gate as "3 prompts present"; SPEC §8 defines five prompts. This plan seeds all five (`read_cells`, `read_page`, `legacy_extract`, `word_context`, `parent_note`), which satisfies both readings. Task 12 corrects the §11 row.

---

## File Structure

| Path | Responsibility |
|---|---|
| `.env.example` | Committed template of what the environment `.env` holds. Placeholders only, never a value. |
| `supabase/config.toml` | Supabase CLI project config, written by `supabase init`. |
| `supabase/migrations/20260917090000_ring_a.sql` | Schemas, `internal.apply_conventions()`, `internal.touch_updated_at()`, `internal.forbid_change()`, all 24 Ring A tables, `pii.child`, `pii.read_child()`. |
| `supabase/migrations/20260917090100_ring_b.sql` | The three derived tables: `child_skill_state`, `class_card`, `item_stat`. |
| `supabase/seed/registry-num.json` | Already present. The school's 37 NUM skills and their 162 milestones, exported from the Skill Map. Not modified. |
| `supabase/seed/rungs.json` | The 16 ladder rungs (R1–R14, X1, X2): band, order, descriptor, skill codes. |
| `supabase/seed/levels.json` | 12 level rules: four bands times `Lm`/`L0`/`Lp`, each naming its rungs, its foundational rung and its probe rung. |
| `supabase/seed/misconceptions.json` | 24 rows: 14 procedural predictors (`answer_lookup`) and 10 conceptual ones (`working` / `explanation` / `teacher`). |
| `supabase/seed/prompts.json` | The five prompts of SPEC §8: purpose, version 1, model, active flag, JSON schema, text file pointer. |
| `supabase/seed/prompts/*.v1.txt` | The actual prompt text, one file per purpose. |
| `packages/engine/pyproject.toml` | Package metadata, dependencies, the `engine` console script, pytest and coverage config. |
| `packages/engine/engine/__init__.py` | Package marker and `__version__`. |
| `packages/engine/engine/assess/` | The validated prototype, moved verbatim: `ladder`, `items`, `blueprints`, `pick`, `render`, `mark`, `misconceptions`, `build`. |
| `packages/engine/engine/db.py` | The only place the engine opens a database connection. Reads `DATABASE_URL`, refuses placeholders. |
| `packages/engine/engine/loaders.py` | Pure row builders per seed file, one generic idempotent upsert, `load_all`, row counts, the orphan-rung query. |
| `packages/engine/engine/cli.py` | Typer app: `engine load`, `engine load --check`. |
| `packages/engine/tests/conftest.py` | The `db` marker and the session connection fixture that skips when `DATABASE_URL` is unusable. |
| `packages/engine/tests/assess/test_misconceptions.py` | Every documented worked example of every predictor. |
| `packages/engine/tests/assess/test_items.py` | Operand samplers and `bare_sum` behaviour. |
| `packages/engine/tests/seed/test_ladder_seeds.py` | `rungs.json` and `levels.json` against `ladder.py` and against the registry. |
| `packages/engine/tests/seed/test_misconception_seed.py` | `misconceptions.json` procedural rows against `misconceptions.catalogue()`. |
| `packages/engine/tests/seed/test_prompt_seed.py` | Five prompts, schemas strict, guardrail sentences present, model id correct. |
| `packages/engine/tests/test_db.py` | `database_url()` refuses missing and placeholder values. |
| `packages/engine/tests/test_loaders.py` | The generated SQL, and every row builder, without a database. |
| `packages/engine/tests/test_schema.py` | `db`-marked: RLS on every table, `tenant_id` on every table but `tenant`, the three signals, append-only evidence. |
| `packages/engine/tests/test_cli.py` | `engine load` exit codes and output, with the database stubbed. |

---

## Task 1 — Python workspace

The one task that is not test-first: pytest does not exist yet. Its check is that the toolchain runs.

**Files:**
- Create `packages/engine/pyproject.toml`
- Create `packages/engine/engine/__init__.py`
- Create `.env.example`

- [ ] **Step 1: Branch off main.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && git checkout -b phase-0-foundations
```

Expected output: `Switched to a new branch 'phase-0-foundations'`

- [ ] **Step 2: Create the package directories.**

```bash
mkdir -p /Users/nimishshah/cornerstone/assessment-engine/packages/engine/engine \
         /Users/nimishshah/cornerstone/assessment-engine/packages/engine/tests/assess \
         /Users/nimishshah/cornerstone/assessment-engine/packages/engine/tests/seed \
         /Users/nimishshah/cornerstone/assessment-engine/supabase/migrations \
         /Users/nimishshah/cornerstone/assessment-engine/supabase/seed/prompts && \
  find /Users/nimishshah/cornerstone/assessment-engine/packages \
       /Users/nimishshah/cornerstone/assessment-engine/supabase -type d | sort
```

Expected output: eight directory paths, ending `.../supabase/seed/prompts`.

- [ ] **Step 3: Write `packages/engine/pyproject.toml`.**

```toml
[project]
name = "cornerstone-engine"
version = "0.1.0"
description = "Cornerstone assessment engine: item generation, marking, and the child skill graph."
requires-python = ">=3.12,<3.13"
dependencies = [
    "typer>=0.12",
    "psycopg[binary]>=3.2",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-cov>=5.0"]
# Installed by the phase that first imports them, not before.
media = ["opencv-python>=4.10", "playwright>=1.47", "segno>=1.6"]
api = ["fastapi>=0.115", "uvicorn>=0.30", "pydantic>=2.9", "anthropic>=0.40"]

[project.scripts]
engine = "engine.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["engine"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
markers = ["db: needs a reachable DATABASE_URL (hosted Supabase)"]

[tool.coverage.run]
source = ["engine"]
# assess/ is moved in verbatim this phase, not written. It enters the coverage
# gate in Phase 1, the first phase that changes it.
omit = ["*/engine/assess/*"]

[tool.coverage.report]
show_missing = true
```

- [ ] **Step 4: Write `packages/engine/engine/__init__.py`.**

```python
"""Cornerstone assessment engine.

Structural facts (bands, rungs, levels, blueprints, misconceptions, thresholds,
prompts) are rows in Postgres, seeded from supabase/seed/. Nothing structural
lives in this package.
"""

__version__ = "0.1.0"
```

- [ ] **Step 5: Create the venv on Python 3.12 and install.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv venv --python 3.12 && \
  /Users/nimishshah/.local/bin/uv pip install -e ".[dev]"
```

Expected output: `Using CPython 3.12.x`, `Creating virtual environment at: .venv`, then an install summary whose package list includes `cornerstone-engine`, `psycopg`, `pytest`, `pytest-cov`, `python-dotenv`, `typer`. If 3.12 is not on the machine, `uv` downloads a managed build first; that is expected and takes about a minute.

- [ ] **Step 6: Prove the toolchain runs.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run python -c "import engine, psycopg, typer; print(engine.__version__)" && \
  /Users/nimishshah/.local/bin/uv run pytest --version
```

Expected output:

```
0.1.0
pytest 8.3.x
```

- [ ] **Step 7: Write `.env.example`.**

The pre-write hook blocks real credentials. Every secret value here is the literal string `CHANGE_ME`.

```bash
# Cornerstone Cloud — Supabase (project cornerstone-cloud, ap-south-1 Mumbai).
# Copy to .env and fill in. .env is gitignored and never committed.

SUPABASE_PROJECT_REF=ruznbyngtfjsaymuylhm
SUPABASE_URL=https://ruznbyngtfjsaymuylhm.supabase.co

# Session pooler, ap-south-1. Percent-encode any ! # @ : / in the password.
DATABASE_URL=postgresql://postgres.ruznbyngtfjsaymuylhm:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres

# Dashboard > Settings > API Keys. The service_role key is server-side only.
SUPABASE_ANON_KEY=CHANGE_ME
SUPABASE_SERVICE_ROLE_KEY=CHANGE_ME

# console.anthropic.com, on the Cornerstone account.
ANTHROPIC_API_KEY=CHANGE_ME

# The single tenant for the pilot.
TENANT_SLUG=cornerstone
TENANT_NAME=Cornerstone School, Pune
```

- [ ] **Step 8: Confirm the venv is ignored by git.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git status --porcelain --untracked-files=all | grep -c "\.venv"
```

Expected output: `0` — `.gitignore` already carries `.venv/`, which matches at any depth. (`grep -c` exits 1 when it counts nothing; the `0` on stdout is the answer.)

- [ ] **Step 9: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/pyproject.toml packages/engine/engine/__init__.py .env.example && \
  git commit -m "Phase 0: Python workspace, uv venv on 3.12, .env template" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `3 files changed`.

---

## Task 2 — Move the prototype in, driven by its tests

CLAUDE.md rule 10: the prototype `assess/` **is** the engine. It is copied unchanged. The tests are written first and fail on the missing module; the copy is what makes them pass.

**Files:**
- Create `packages/engine/tests/assess/test_misconceptions.py`
- Create `packages/engine/tests/assess/test_items.py`
- Create `packages/engine/engine/assess/` (copied from `/Users/nimishshah/Downloads/assessment-engine-prototype/assess/`)

- [ ] **Step 1: Write the failing predictor tests.**

Create `packages/engine/tests/assess/test_misconceptions.py`. Every number here is the worked example from the predictor's own docstring, recomputed by hand against the code.

```python
"""Every misconception predictor reproduces its documented worked example.

These are the numbers a marker looks a wrong answer up in. If one of them moves,
a child's mistake stops being classified and silently becomes `unclassified`.
"""

from engine.assess import misconceptions as M


def test_digits_indexes_from_the_ones_column():
    assert M.digits(302, 3) == [2, 0, 3]


def test_from_digits_is_the_inverse_of_digits():
    assert M.from_digits(M.digits(302, 3)) == 302


def test_add_nocarry_47_38_returns_75():
    assert M.add_nocarry(47, 38) == 75


def test_add_nocarry_returns_none_when_there_is_no_carry():
    assert M.add_nocarry(23, 45) is None


def test_add_carry_skips_column_47_38_returns_175():
    assert M.add_carry_skips_column(47, 38) == 175


def test_add_concat_47_38_returns_715():
    assert M.add_concat(47, 38) == 715


def test_add_concat_returns_none_when_no_column_exceeds_nine():
    assert M.add_concat(23, 45) is None


def test_add_drop_carry_out_76_54_returns_30():
    assert M.add_drop_carry_out(76, 54) == 30


def test_sub_smaller_from_larger_62_27_returns_45():
    assert M.sub_smaller_from_larger(62, 27) == 45


def test_sub_no_decrement_62_27_returns_45():
    assert M.sub_no_decrement(62, 27) == 45


def test_sub_across_zero_lender_not_decremented_302_178_returns_224():
    assert M.sub_across_zero_lender_not_decremented(302, 178) == 224


def test_sub_across_zero_zero_not_reduced_302_178_returns_134():
    assert M.sub_across_zero_zero_not_reduced(302, 178) == 134


def test_sub_across_zero_predictors_return_none_without_an_interior_zero():
    assert M.sub_across_zero_lender_not_decremented(342, 178) is None
    assert M.sub_across_zero_zero_not_reduced(342, 178) is None


def test_predict_never_offers_the_correct_answer_as_a_wrong_one():
    for a, b in ((47, 38), (76, 54), (23, 45)):
        assert a + b not in M.predict("+", a, b).values()
    for a, b in ((62, 27), (302, 178), (95, 43)):
        assert a - b not in M.predict("-", a, b).values()


def test_predict_never_offers_a_negative_wrong_answer():
    assert all(v >= 0 for v in M.predict("-", 302, 178).values())


def test_two_subtraction_misconceptions_collide_on_62_minus_27():
    # Both "smaller from larger" and "exchanged but did not decrement" write 45.
    # The marker must tag both codes, not pick one.
    predicted = M.predict("-", 62, 27)
    assert {c for c, v in predicted.items() if v == 45} >= {
        "M_SMALL_FROM_LARGE",
        "M_NO_DECREMENT",
    }


def test_catalogue_has_fourteen_rows_keyed_by_code_and_operation():
    rows = M.catalogue()
    assert len(rows) == 14
    assert len({(r["code"], r["op"]) for r in rows}) == 14
    assert {r["op"] for r in rows} == {"+", "-"}


def test_catalogue_rows_all_carry_a_name_and_a_repair_hint():
    for row in M.catalogue():
        assert row["name"].strip()
        assert row["repair"].strip()
```

- [ ] **Step 2: Write the failing generator tests.**

Create `packages/engine/tests/assess/test_items.py`.

```python
"""The operand samplers honour their constraints and bare_sum answers correctly.

A generator that quietly drifts off its rung is a child sent the wrong sheet.
"""

import random

import pytest

from engine.assess import items as I
from engine.assess import misconceptions as M


def test_regroup_count_add_counts_carries():
    assert I._regroup_count_add(47, 38) == 1
    assert I._regroup_count_add(23, 45) == 0
    # 76 + 54 carries out of the ones AND out of the tens: the carry-out counts.
    # A blueprint slot asking for regroups={1} will never be given this pair.
    assert I._regroup_count_add(76, 54) == 2


def test_regroup_count_sub_counts_exchanges():
    assert I._regroup_count_sub(62, 27) == 1
    assert I._regroup_count_sub(95, 43) == 0


def test_sample_add_returns_two_digit_operands_with_one_carry():
    a, b = I.sample_add(random.Random(7), 2, 2, {1})
    assert 10 <= a <= 99 and 10 <= b <= 99
    assert I._regroup_count_add(a, b) == 1


def test_sample_add_honours_a_maximum_total():
    a, b = I.sample_add(random.Random(11), 1, 1, {1}, max_total=18)
    assert a + b <= 18


def test_sample_add_raises_when_no_operands_can_satisfy_the_request():
    with pytest.raises(RuntimeError, match="no add sample"):
        I.sample_add(random.Random(1), 1, 1, {5})


def test_sample_sub_never_returns_a_negative_difference():
    a, b = I.sample_sub(random.Random(3), 2, 2, {1})
    assert a > b


def test_sample_sub_across_zero_puts_a_zero_inside_the_minuend():
    a, b = I.sample_sub(random.Random(5), 3, 3, {1, 2}, across_zero=True)
    assert 0 in M.digits(a, 3)[1:]
    assert a > b


def test_bare_sum_answer_matches_its_own_operands():
    item = I.bare_sum(random.Random(13), "R5", "Procedural", "+", 2, 2, {1})
    assert item.responses[0].answer == str(item.spec["a"] + item.spec["b"])


def test_bare_sum_subtraction_answer_matches_its_own_operands():
    item = I.bare_sum(random.Random(17), "R6", "Procedural", "-", 2, 2, {1}, layout="column")
    assert item.responses[0].answer == str(item.spec["a"] - item.spec["b"])


def test_bare_sum_response_is_a_digit_run_with_predictions():
    item = I.bare_sum(random.Random(13), "R5", "Procedural", "+", 2, 2, {1})
    response = item.responses[0]
    assert response.kind == "digits"
    assert response.cells >= len(response.answer)
    assert response.misconceptions
    assert str(item.spec["a"] + item.spec["b"]) not in {
        str(v) for v in response.misconceptions.values()
    }


def test_bare_sum_takes_its_skills_from_the_rung():
    item = I.bare_sum(random.Random(13), "R5", "Procedural", "+", 2, 2, {1})
    assert item.skills == I.RUNGS["R5"]["skills"]
    assert item.rung == "R5"


def test_bare_sum_is_deterministic_for_the_same_seed():
    first = I.bare_sum(random.Random(29), "R5", "Procedural", "+", 2, 2, {1})
    second = I.bare_sum(random.Random(29), "R5", "Procedural", "+", 2, 2, {1})
    assert first.item_id == second.item_id
    assert first.spec == second.spec


def test_column_layout_leaves_no_working_lines():
    item = I.bare_sum(random.Random(31), "R6", "Procedural", "-", 2, 2, {1}, layout="column")
    assert item.fmt == "column_grid"
    assert item.working_lines == 0
```

- [ ] **Step 3: Run both test files and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/assess
```

Expected failure: two collection errors, `ModuleNotFoundError: No module named 'engine.assess'`, summary line `2 errors`.

- [ ] **Step 4: Copy the prototype in, unchanged.**

```bash
cp -R /Users/nimishshah/Downloads/assessment-engine-prototype/assess \
      /Users/nimishshah/cornerstone/assessment-engine/packages/engine/engine/assess && \
  rm -rf /Users/nimishshah/cornerstone/assessment-engine/packages/engine/engine/assess/__pycache__ && \
  ls /Users/nimishshah/cornerstone/assessment-engine/packages/engine/engine/assess
```

Expected output, nine files:

```
__init__.py
blueprints.py
build.py
items.py
ladder.py
mark.py
misconceptions.py
pick.py
render.py
```

- [ ] **Step 5: Confirm the copy is byte-identical to the prototype.**

```bash
diff -r /Users/nimishshah/Downloads/assessment-engine-prototype/assess \
        /Users/nimishshah/cornerstone/assessment-engine/packages/engine/engine/assess \
        --exclude=__pycache__ && echo IDENTICAL
```

Expected output: `IDENTICAL`

- [ ] **Step 6: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/assess
```

Expected output: `31 passed`.

- [ ] **Step 7: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/engine/assess packages/engine/tests/assess && \
  git commit -m "Phase 0: move the validated prototype assess/ in, under tests" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `11 files changed`.

---

## Task 3 — Ring A migration

Written test-first: `tests/test_schema.py` asserts the invariants CLAUDE.md demands, fails because the tables do not exist, and the migration is what makes it pass. The full schema is created in this task and Task 4 so that **no later phase needs DDL** — Phases 1 to 4 add rows, never tables.

**Files:**
- Create `packages/engine/tests/conftest.py`
- Create `packages/engine/tests/test_schema.py`
- Create `supabase/config.toml` (via `supabase init`)
- Create `supabase/migrations/20260917090000_ring_a.sql`

- [ ] **Step 1: Fill in the real `.env` (human, once).**

Open `/Users/nimishshah/cornerstone/assessment-engine/.env` and replace the `DATABASE_URL` password with the real session-pooler password from the Supabase dashboard (Settings → Database → Connection string → Session pooler). Percent-encode `! # @ : /` if present. Do not paste the value into a terminal, a commit, or this plan.

Then verify — the password is never printed:

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  psql "$DATABASE_URL" -Atc "select current_database(), current_user"
```

Expected output: `postgres|postgres.ruznbyngtfjsaymuylhm`

- [ ] **Step 2: Write `packages/engine/tests/conftest.py`.**

```python
"""Shared fixtures. Database tests skip cleanly when no database is reachable.

`engine.db` is imported inside the fixtures, not at module level: a conftest that
fails to import aborts the entire run, and this file is written one task before
`engine/db.py` exists.
"""

import pytest


@pytest.fixture(scope="session")
def database_url() -> str:
    from engine import db

    try:
        return db.database_url()
    except db.ConfigError as exc:  # no .env yet, or still a placeholder
        pytest.skip(str(exc))


@pytest.fixture(scope="session")
def conn(database_url):
    from engine import db

    with db.connect() as connection:
        yield connection
        connection.rollback()
```

- [ ] **Step 3: Write the failing schema tests.**

Create `packages/engine/tests/test_schema.py`.

```python
"""The invariants CLAUDE.md makes non-negotiable, asserted against the real schema.

RLS on every table, tenant_id on every table but `tenant`, blank/wrong/unreadable
never collapsed, evidence append-only.
"""

import psycopg
import pytest

pytestmark = pytest.mark.db

EXPECTED_TABLE_COUNT = 28


def _tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where c.relkind = 'r' and n.nspname in ('public', 'pii')
            order by 1, 2
            """
        )
        return cur.fetchall()


def test_the_whole_schema_is_present(conn):
    assert len(_tables(conn)) == EXPECTED_TABLE_COUNT


def test_every_table_has_row_level_security_enabled_and_forced(conn):
    missing = [(s, t) for s, t, enabled, forced in _tables(conn) if not (enabled and forced)]
    assert missing == []


def test_every_table_has_a_service_role_policy(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select schemaname, tablename
            from pg_policies
            where schemaname in ('public', 'pii') and policyname = 'service_role_all'
            """
        )
        with_policy = set(cur.fetchall())
    assert {(s, t) for s, t, _, _ in _tables(conn)} == with_policy


def test_every_table_except_tenant_carries_tenant_id(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select table_schema, table_name
            from information_schema.columns
            where table_schema in ('public', 'pii') and column_name = 'tenant_id'
            """
        )
        with_tenant = set(cur.fetchall())
    all_tables = {(s, t) for s, t, _, _ in _tables(conn)}
    assert all_tables - with_tenant == {("public", "tenant")}


def test_every_table_has_created_at_and_updated_at(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select table_schema, table_name, count(*)
            from information_schema.columns
            where table_schema in ('public', 'pii')
              and column_name in ('created_at', 'updated_at')
            group by 1, 2
            having count(*) <> 2
            """
        )
        assert cur.fetchall() == []


def test_item_result_keeps_blank_wrong_and_unreadable_apart(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select pg_get_constraintdef(oid)
            from pg_constraint
            where conrelid = 'item_result'::regclass
              and conname = 'item_result_status_check'
            """
        )
        definition = cur.fetchone()[0]
    for value in ("correct", "wrong", "blank", "unreadable", "needs_teacher"):
        assert f"'{value}'" in definition
    assert "'incorrect'" not in definition


def test_working_shown_keeps_wrong_with_working_apart_from_wrong(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select pg_get_constraintdef(oid)
            from pg_constraint
            where conrelid = 'item_result'::regclass
              and conname = 'item_result_working_shown_check'
            """
        )
        definition = cur.fetchone()[0]
    for value in ("none", "partial", "full"):
        assert f"'{value}'" in definition


def test_evidence_event_refuses_an_update(conn):
    with conn.cursor() as cur:
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            cur.execute("update evidence_event set correct = true where false")
    conn.rollback()


def test_evidence_event_refuses_a_delete(conn):
    with conn.cursor() as cur:
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            cur.execute("delete from evidence_event where false")
    conn.rollback()


def test_only_one_prompt_version_per_purpose_can_be_active(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select indexdef from pg_indexes
            where tablename = 'prompt' and indexname = 'prompt_one_active_idx'
            """
        )
        assert "WHERE (active)" in cur.fetchone()[0]
```

- [ ] **Step 4: Run the schema tests and watch them fail.**

`engine/db.py` does not exist yet, so the `conn` fixture cannot resolve. That is the expected first failure; Task 8 writes `db.py` and these tests go from *error* to *pass*. Run it anyway to record the state:

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_schema.py
```

Expected failure: `10 errors`, each one `ModuleNotFoundError: No module named 'engine.db'` raised inside the `database_url` fixture. Collection itself succeeds — that is what the lazy import in `conftest.py` buys.

- [ ] **Step 5: Initialise the Supabase CLI project.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && supabase init
```

Expected output: `Finished supabase init.` If it asks about generating editor settings, answer `N`. It creates `supabase/config.toml` and leaves the existing `supabase/seed/` and `supabase/migrations/` alone.

- [ ] **Step 6: Log in and link to the hosted project (human, once).**

```bash
supabase login
```

Expected: a browser tab opens; after approval the terminal prints `Finished supabase login.`

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  supabase link --project-ref ruznbyngtfjsaymuylhm
```

Expected output: a database-password prompt (type it; it is not echoed and never written to a file), then `Finished supabase link.` This is a hosted project — never run `supabase start` or `supabase db reset`, which target a local Docker stack that does not exist here.

- [ ] **Step 7: Write the schema helpers and the registry tables.**

Create `supabase/migrations/20260917090000_ring_a.sql` with this first section:

```sql
-- Ring A — source of truth. Append or approve; a batch job never edits it.
-- Every table: id uuid, tenant_id, created_at, updated_at, RLS enabled and forced.
-- Registry and ladder references are by code with composite foreign keys;
-- everything else references by uuid.

create schema if not exists pii;
create schema if not exists internal;

-- ------------------------------------------------------------------ helpers

create or replace function internal.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

create or replace function internal.forbid_change() returns trigger
language plpgsql as $$
begin
  raise exception '% is append-only: % is not allowed', tg_table_name, tg_op;
end $$;

-- Called at the end of every migration. 28 tables by hand is 28 chances to
-- forget one; tests/test_schema.py proves the invariant instead of trusting it.
create or replace function internal.apply_conventions() returns void
language plpgsql as $$
declare t record;
begin
  for t in
    select n.nspname as s, c.relname as r
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relkind = 'r' and n.nspname in ('public', 'pii')
  loop
    execute format('alter table %I.%I enable row level security', t.s, t.r);
    execute format('alter table %I.%I force row level security', t.s, t.r);
    execute format('drop policy if exists service_role_all on %I.%I', t.s, t.r);
    execute format(
      'create policy service_role_all on %I.%I for all to service_role using (true) with check (true)',
      t.s, t.r);
    execute format('drop trigger if exists touch_updated_at on %I.%I', t.s, t.r);
    execute format(
      'create trigger touch_updated_at before update on %I.%I '
      'for each row execute function internal.touch_updated_at()',
      t.s, t.r);
  end loop;
end $$;

-- ------------------------------------------------------------------ tenancy

create table tenant (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique,
  name        text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ------------------------------------------------------------- registry and ladder

create table skill (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,                       -- NUM.OPS.01, as issued
  domain       text not null,                       -- NUM
  strand       text not null,                       -- NUM.OPS
  name         text not null,
  description  text not null default '',
  source       text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

create table milestone (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  skill_code   text not null,
  band         text not null,                       -- PG, N, K1, K2, G1..G4
  descriptor   text not null,
  scale        text not null,                       -- score_10, yes_sometimes_no_na, none
  source       text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, skill_code, band),
  foreign key (tenant_id, skill_code) references skill (tenant_id, code) on delete cascade
);

create table rung (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  code          text not null,                      -- R1..R14, X1, X2
  band          text not null,                      -- G1..G4, G2+
  ladder_order  integer,                            -- null for X1 / X2, off the ordered strand
  descriptor    text not null,
  skill_codes   text[] not null default '{}',       -- registry codes, checked by `engine load`
  milestone_id  uuid references milestone(id),      -- nullable: ADR 0002, registry gaps
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (tenant_id, code)
);
create index rung_milestone_id_idx on rung (milestone_id);

create table level_rule (
  id                      uuid primary key default gen_random_uuid(),
  tenant_id               uuid not null references tenant(id) on delete cascade,
  band                    text not null,
  level                   text not null check (level in ('Lm', 'L0', 'Lp')),
  rung_codes              text[] not null default '{}',
  foundational_rung_code  text,
  probe_rung_code         text,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (tenant_id, band, level)
);

create table blueprint (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  band        text not null,
  level       text not null check (level in ('Lm', 'L0', 'Lp')),
  slots       jsonb not null default '[]'::jsonb,   -- [{label, generator, args, rung, signal, tags?}]
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, band, level)
);

create table misconception (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  code           text not null,                     -- M_NOCARRY, M_SMALL_FROM_LARGE, ...
  op             text not null check (op in ('+', '-', 'any')),
  name           text not null,
  description    text not null default '',
  repair_hint    text not null default '',
  detectable_by  text not null
                 check (detectable_by in ('answer_lookup', 'working', 'explanation', 'teacher')),
  source         text not null default '',
  external_ref   text,                              -- M001..M010 from the adaptive spec
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (tenant_id, code, op)
);

create table threshold (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  key          text not null,
  value        numeric(20, 4) not null,
  unit         text not null default '',
  description  text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, key)
);

create table config (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  key          text not null,
  value        jsonb not null,
  description  text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, key)
);

create table prompt (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  purpose      text not null,
  version      integer not null,
  text         text not null,
  model        text not null,
  json_schema  jsonb not null,
  active       boolean not null default true,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, purpose, version)
);
create unique index prompt_one_active_idx on prompt (tenant_id, purpose) where (active);
```

- [ ] **Step 8: Append the children, items, sheets and capture tables.**

Continue the same file:

```sql
-- ------------------------------------------------------------------ children

create table child (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  roll_no     text not null,
  band        text not null,
  section     text not null,
  active      boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, section, roll_no)
);

-- ------------------------------------------------------------- items and sheets

create table item (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  item_key     text not null,                       -- assess.items.Item.item_id
  template     text not null,
  rung_code    text not null,
  skill_codes  text[] not null default '{}',
  signal       text not null,
  fmt          text not null,
  stem         text not null default '',
  spec         jsonb not null,
  responses    jsonb not null,                      -- [{rid, kind, answer, cells, ...}]
  tags         jsonb not null default '{}'::jsonb,  -- taxonomy 12 case tags, derived by code
  source       text not null default 'generated' check (source in ('generated', 'legacy')),
  status       text not null default 'active' check (status in ('draft', 'active', 'retired')),
  times_used   integer not null default 0,
  p_correct    numeric(5, 4),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, item_key),
  foreign key (tenant_id, rung_code) references rung (tenant_id, code)
);
create index item_rung_idx on item (tenant_id, rung_code);

create table sheet_template (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  band          text not null,
  level         text not null check (level in ('Lm', 'L0', 'Lp')),
  variant       integer not null default 1,
  week          text not null,
  batch_id      text,
  blueprint_id  uuid references blueprint(id),
  item_ids      uuid[] not null default '{}',
  key           jsonb not null default '{}'::jsonb, -- answers + cell geometry in mm
  html_path     text,
  source        text not null default 'generated' check (source in ('generated', 'legacy')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index sheet_template_blueprint_idx on sheet_template (blueprint_id);
create index sheet_template_week_idx on sheet_template (tenant_id, week);

create table sheet_instance (
  id                 uuid primary key default gen_random_uuid(),
  tenant_id          uuid not null references tenant(id) on delete cascade,
  qr_code            text not null,                -- CS + 6 hex, printed on the page
  sheet_template_id  uuid not null references sheet_template(id) on delete cascade,
  child_id           uuid references child(id),    -- null until a coordinator names it
  print_status       text not null default 'new'
                     check (print_status in ('new', 'printed', 'with_teacher', 'returned', 'void')),
  pdf_path           text,
  printed_at         timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (tenant_id, qr_code)
);
create index sheet_instance_template_idx on sheet_instance (sheet_template_id);
create index sheet_instance_child_idx on sheet_instance (child_id);

create table prescription (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references tenant(id) on delete cascade,
  child_id               uuid not null references child(id) on delete cascade,
  week                   text not null,
  strand                 text not null,
  level                  text not null check (level in ('Lm', 'L0', 'Lp')),
  rung_codes             text[] not null default '{}',
  rule_fired             text not null,             -- which clause of SPEC 5 chose this
  misconception_targets  text[] not null default '{}',
  sheet_instance_id      uuid references sheet_instance(id),
  override_by            text,
  override_reason        text,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create index prescription_child_idx on prescription (child_id);
create index prescription_sheet_instance_idx on prescription (sheet_instance_id);
create index prescription_week_idx on prescription (tenant_id, week);

-- ------------------------------------------------------------- capture and marking

create table capture (
  id                 uuid primary key default gen_random_uuid(),
  tenant_id          uuid not null references tenant(id) on delete cascade,
  drive_file_id      text,
  path               text not null,
  pages              integer not null default 0,
  qr_read            text,
  sheet_instance_id  uuid references sheet_instance(id),
  status             text not null default 'new'
                     check (status in ('new', 'resolved', 'needs_rephoto', 'processed', 'error')),
  error              text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create index capture_sheet_instance_idx on capture (sheet_instance_id);
create index capture_status_idx on capture (tenant_id, status);

create table item_result (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  capture_id           uuid not null references capture(id) on delete cascade,
  item_id              uuid not null references item(id),
  rid                  text not null,
  raw_read             text,
  read_confidence      numeric(5, 4),
  -- Three signals, never two: blank, wrong and unreadable stay distinct here,
  -- and wrong-with-working stays distinct through working_shown.
  status               text not null
                       check (status in ('correct', 'wrong', 'blank', 'unreadable', 'needs_teacher')),
  misconception_codes  text[] not null default '{}',
  working_shown        text not null default 'none'
                       check (working_shown in ('none', 'partial', 'full')),
  state                text not null default 'candidate'
                       check (state in ('candidate', 'confirmed', 'rejected')),
  confirmed_by         text,
  confirmed_at         timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (capture_id, item_id, rid)
);
create index item_result_capture_idx on item_result (capture_id);
create index item_result_item_idx on item_result (item_id);
create index item_result_state_idx on item_result (tenant_id, state);

create table narrative_observation (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  capture_id      uuid not null references capture(id) on delete cascade,
  text            text not null,
  signals         jsonb not null default '{}'::jsonb,
  prompt_version  integer,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (capture_id)
);

create table evidence_event (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  child_id             uuid not null references child(id) on delete cascade,
  skill_code           text not null,
  rung_code            text not null,
  correct              boolean,
  misconception_codes  text[] not null default '{}',
  channel              text not null check (channel in ('item', 'teacher_override')),
  item_result_id       uuid references item_result(id),
  observed_at          timestamptz not null,
  stored_at            timestamptz not null default now(),
  confirmed_by         text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index evidence_event_child_idx on evidence_event (child_id, observed_at);
create index evidence_event_item_result_idx on evidence_event (item_result_id);

-- CLAUDE.md rule 4. Statement-level so it fires even when the statement would
-- match no rows, which is what makes it testable on an empty table.
create trigger evidence_event_append_only
  before update or delete on evidence_event
  for each statement execute function internal.forbid_change();

-- ------------------------------------------------------------- outputs and runs

create table home_sheet (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  child_id            uuid not null references child(id) on delete cascade,
  week                text not null,
  target_skill_codes  text[] not null default '{}',
  item_ids            uuid[] not null default '{}',
  pdf_path            text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index home_sheet_child_idx on home_sheet (child_id);

create table parent_note (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  child_id        uuid not null references child(id) on delete cascade,
  week            text not null,
  body            text not null,
  prompt_version  integer,
  approved_by     text,
  sent_at         timestamptz,
  channel         text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index parent_note_child_idx on parent_note (child_id);

create table gold (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  capture_id  uuid not null references capture(id) on delete cascade,
  item_id     uuid references item(id),
  rid         text,
  truth       jsonb not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index gold_capture_idx on gold (capture_id);
create index gold_item_idx on gold (item_id);

create table flow_run (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  flow         text not null,
  trigger      text,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  status       text not null default 'running' check (status in ('running', 'ok', 'error')),
  error        text,
  tokens       integer,
  cost_inr     numeric(20, 4),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index flow_run_flow_idx on flow_run (tenant_id, flow, started_at desc);

create table access_log (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  actor        text not null,
  child_id     uuid,
  action       text not null,
  occurred_at  timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index access_log_child_idx on access_log (child_id, occurred_at desc);
```

- [ ] **Step 9: Append the `pii` schema and the logging accessor.**

Continue the same file:

```sql
-- ------------------------------------------------------------------ names

-- SPEC 13: children's names live here and on the printed page, nowhere else.
create table pii.child (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references public.tenant(id) on delete cascade,
  child_id        uuid not null references public.child(id) on delete cascade,
  first_name      text not null,
  last_name       text not null default '',
  home_languages  text[] not null default '{}',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (tenant_id, child_id)
);
create index pii_child_child_idx on pii.child (child_id);

-- PostgreSQL has no SELECT trigger, so a read cannot be logged by one. Reads go
-- through this accessor, which writes access_log before returning the row.
create or replace function pii.read_child(p_child_id uuid, p_actor text)
returns table (first_name text, last_name text, home_languages text[])
language plpgsql
security definer
set search_path = pii, public
as $$
begin
  insert into public.access_log (tenant_id, actor, child_id, action)
  select c.tenant_id, p_actor, p_child_id, 'read_pii_child'
  from pii.child c
  where c.child_id = p_child_id;

  return query
  select c.first_name, c.last_name, c.home_languages
  from pii.child c
  where c.child_id = p_child_id;
end $$;

revoke all on pii.child from anon, authenticated;
revoke all on schema pii from anon, authenticated;

-- ------------------------------------------------------------------ conventions

select internal.apply_conventions();
```

- [ ] **Step 10: Apply the migration to the hosted project.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  supabase db push --db-url "$DATABASE_URL"
```

Expected output:

```
Applying migration 20260917090000_ring_a.sql...
Finished supabase db push.
```

- [ ] **Step 11: Verify the table count directly.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii')"
```

Expected output: `25` — 24 Ring A tables plus `pii.child`. Ring B in Task 4 brings it to 28.

- [ ] **Step 12: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add supabase/config.toml supabase/migrations/20260917090000_ring_a.sql \
          packages/engine/tests/conftest.py packages/engine/tests/test_schema.py && \
  git commit -m "Phase 0: Ring A schema, pii schema, RLS conventions, append-only evidence" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `4 files changed`.

---

## Task 4 — Ring B migration

Ring B is derived and TRUNCATE-able. The shells are created now so Phase 1's graph rebuild adds no DDL.

**Files:**
- Create `supabase/migrations/20260917090100_ring_b.sql`
- Modify `packages/engine/tests/test_schema.py`

- [ ] **Step 1: Add the Ring B assertions that do not yet hold.**

`EXPECTED_TABLE_COUNT` is already 28 as written in Task 3, which is the count *after* this migration. Append to `packages/engine/tests/test_schema.py`:

```python
def test_ring_b_tables_exist(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.relname
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public'
              and c.relname in ('child_skill_state', 'class_card', 'item_stat')
            order by 1
            """
        )
        assert [r[0] for r in cur.fetchall()] == ["child_skill_state", "class_card", "item_stat"]


def test_child_skill_state_names_all_six_states(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select pg_get_constraintdef(oid)
            from pg_constraint
            where conrelid = 'child_skill_state'::regclass
              and conname = 'child_skill_state_state_check'
            """
        )
        definition = cur.fetchone()[0]
    for value in (
        "not_enough_yet",
        "patterned_error",
        "emerging",
        "practising",
        "secure",
        "stretch_ready",
    ):
        assert f"'{value}'" in definition
```

- [ ] **Step 2: Run the schema tests and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_schema.py
```

Expected failure: `12 errors`, still `ModuleNotFoundError: No module named 'engine.db'` from the fixture (Task 8 supplies it) — two more than before, which is the two tests just added. The Ring B tables they need are what Step 3 creates; the whole module comes green in Task 8 Step 5.

- [ ] **Step 3: Write `supabase/migrations/20260917090100_ring_b.sql`.**

```sql
-- Ring B — derived. TRUNCATE-able at any time; a pure function of Ring A,
-- rebuilt nightly by `engine graph` from confirmed evidence only.

create table child_skill_state (
  id                       uuid primary key default gen_random_uuid(),
  tenant_id                uuid not null references tenant(id) on delete cascade,
  child_id                 uuid not null references child(id) on delete cascade,
  skill_code               text not null,
  rung_code                text not null,
  state                    text not null
                           check (state in ('not_enough_yet', 'patterned_error', 'emerging',
                                            'practising', 'secure', 'stretch_ready')),
  n_events                 integer not null default 0,
  n_correct                integer not null default 0,
  repeating_misconception  text,
  last_seen                timestamptz,
  computed_at              timestamptz not null default now(),
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (tenant_id, child_id, skill_code, rung_code)
);
create index child_skill_state_child_idx on child_skill_state (child_id);

create table class_card (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  section      text not null,
  week         text not null,
  rung_code    text not null,
  secure       uuid[] not null default '{}',          -- child ids
  reteach      jsonb not null default '{}'::jsonb,    -- {misconception_code: [child_id, ...]}
  move_up      uuid[] not null default '{}',
  computed_at  timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, section, week, rung_code)
);

create table item_stat (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  item_id              uuid not null references item(id) on delete cascade,
  n                    integer not null default 0,
  p_correct            numeric(5, 4),
  flagged_mislevelled  boolean not null default false,
  computed_at          timestamptz not null default now(),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (tenant_id, item_id)
);
create index item_stat_item_idx on item_stat (item_id);

select internal.apply_conventions();
```

- [ ] **Step 4: Apply it.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  supabase db push --db-url "$DATABASE_URL"
```

Expected output:

```
Applying migration 20260917090100_ring_b.sql...
Finished supabase db push.
```

- [ ] **Step 5: Verify the full table count and the RLS invariant in SQL.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii')" && \
  psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not (c.relrowsecurity and c.relforcerowsecurity)"
```

Expected output:

```
28
0
```

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add supabase/migrations/20260917090100_ring_b.sql packages/engine/tests/test_schema.py && \
  git commit -m "Phase 0: Ring B derived tables, truncatable, rebuilt from Ring A" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 5 — Ladder seeds: `rungs.json` and `levels.json`

**Files:**
- Create `packages/engine/tests/seed/test_ladder_seeds.py`
- Create `supabase/seed/rungs.json`
- Create `supabase/seed/levels.json`

- [ ] **Step 1: Write the failing parity tests.**

Create `packages/engine/tests/seed/test_ladder_seeds.py`. These tests are what stop `ladder.py` and the seed files drifting while both exist.

```python
"""The ladder seeds match ladder.py exactly, and every skill they name is real.

ladder.py still holds RUNGS and LEVELS because items.py and blueprints.py import
them (CLAUDE.md rule 10: do not rewrite the prototype). The seed files are the
source of truth for the database. These tests pin the two together.
"""

import json
from pathlib import Path

import pytest

from engine.assess import ladder

# tests/seed/test_ladder_seeds.py -> packages/engine -> packages -> repository root
SEED = Path(__file__).resolve().parents[2].parent.parent / "supabase" / "seed"


def _read(name):
    return json.loads((SEED / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rungs():
    return _read("rungs.json")["rungs"]


@pytest.fixture(scope="module")
def levels():
    return _read("levels.json")["levels"]


@pytest.fixture(scope="module")
def registry_skill_codes():
    return set(_read("registry-num.json")["skills"])


def test_there_are_sixteen_rungs(rungs):
    assert len(rungs) == 16


def test_every_rung_in_the_ladder_is_in_the_seed(rungs):
    assert {r["code"] for r in rungs} == set(ladder.RUNGS)


def test_each_rung_carries_the_ladders_band_descriptor_and_skills(rungs):
    for row in rungs:
        source = ladder.RUNGS[row["code"]]
        assert row["band"] == source["band"]
        assert row["descriptor"] == source["desc"]
        assert row["skill_codes"] == source["skills"]


def test_ladder_order_follows_ORDER_and_is_null_off_the_strand(rungs):
    for row in rungs:
        expected = ladder.ORDER.index(row["code"]) + 1 if row["code"] in ladder.ORDER else None
        assert row["ladder_order"] == expected


def test_the_ordered_rungs_are_r1_to_r14_with_no_gaps(rungs):
    ordered = sorted(
        (r["ladder_order"], r["code"]) for r in rungs if r["ladder_order"] is not None
    )
    assert [n for n, _ in ordered] == list(range(1, 15))
    assert [code for _, code in ordered] == ladder.ORDER


def test_no_rung_names_a_skill_the_registry_does_not_have(rungs, registry_skill_codes):
    unknown = {
        (r["code"], code)
        for r in rungs
        for code in r["skill_codes"]
        if code not in registry_skill_codes
    }
    assert unknown == set()


def test_there_are_twelve_level_rules(levels):
    assert len(levels) == 12
    assert {(row["band"], row["level"]) for row in levels} == {
        (band, level) for band in ladder.LEVELS for level in ("Lm", "L0", "Lp")
    }


def test_each_level_rule_carries_the_ladders_rungs(levels):
    for row in levels:
        assert row["rung_codes"] == ladder.LEVELS[row["band"]][row["level"]]


def test_foundational_is_the_first_rung_of_lm_and_probe_the_first_of_lp(levels):
    for row in levels:
        source = ladder.LEVELS[row["band"]]
        assert row["foundational_rung_code"] == source["Lm"][0]
        assert row["probe_rung_code"] == source["Lp"][0]


def test_every_rung_named_by_a_level_rule_exists_on_the_ladder(levels, rungs):
    known = {r["code"] for r in rungs}
    for row in levels:
        assert set(row["rung_codes"]) <= known
        assert row["foundational_rung_code"] in known
        assert row["probe_rung_code"] in known
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_ladder_seeds.py
```

Expected failure: `10 errors` — the module fixture raises `FileNotFoundError: [Errno 2] No such file or directory: '.../supabase/seed/rungs.json'` for every test.

- [ ] **Step 3: Write `supabase/seed/rungs.json`.**

```json
{
  "rungs": [
    {"code": "R1", "band": "G1", "ladder_order": 1, "descriptor": "Adds within 10 by combining two sets; reads + and =", "skill_codes": ["NUM.OPS.01"]},
    {"code": "R2", "band": "G1", "ladder_order": 2, "descriptor": "Adds within 20 (crossing 10); part-part-whole; +1/+10 patterns", "skill_codes": ["NUM.OPS.01"]},
    {"code": "R3", "band": "G1", "ladder_order": 3, "descriptor": "Subtracts within 20 as take-away and 'how many more'", "skill_codes": ["NUM.OPS.02"]},
    {"code": "R4", "band": "G2", "ladder_order": 4, "descriptor": "2-digit ± without regrouping in place-value columns", "skill_codes": ["NUM.OPS.01", "NUM.OPS.02"]},
    {"code": "R5", "band": "G2", "ladder_order": 5, "descriptor": "2-digit addition with one regrouping", "skill_codes": ["NUM.OPS.01"]},
    {"code": "R6", "band": "G2", "ladder_order": 6, "descriptor": "2-digit subtraction with exchange", "skill_codes": ["NUM.OPS.02"]},
    {"code": "R7", "band": "G2", "ladder_order": 7, "descriptor": "Mental strategies: bridging, friendly numbers, missing numbers, equality", "skill_codes": ["NUM.OPS.05"]},
    {"code": "R8", "band": "G2", "ladder_order": 8, "descriptor": "One- and two-step word problems in ₹ / objects", "skill_codes": ["NUM.PRB.02", "NUM.MEAS.04"]},
    {"code": "R9", "band": "G3", "ladder_order": 9, "descriptor": "3-digit ± with one or two regroupings", "skill_codes": ["NUM.OPS.01", "NUM.OPS.02"]},
    {"code": "R10", "band": "G3", "ladder_order": 10, "descriptor": "Subtraction across zero", "skill_codes": ["NUM.OPS.02"]},
    {"code": "R11", "band": "G3", "ladder_order": 11, "descriptor": "Estimate first (round to 10), judge reasonableness", "skill_codes": ["NUM.PV.03", "NUM.PRB.03"]},
    {"code": "R12", "band": "G4", "ladder_order": 12, "descriptor": "4-digit addition with multiple addends; 4-digit subtraction across zeros", "skill_codes": ["NUM.OPS.01", "NUM.OPS.02"]},
    {"code": "R13", "band": "G4", "ladder_order": 13, "descriptor": "Chooses an efficient strategy; place-value reasoning under constraint", "skill_codes": ["NUM.OPS.05", "NUM.PRB.03"]},
    {"code": "R14", "band": "G4", "ladder_order": 14, "descriptor": "Multi-step ₹ problems under a budget constraint", "skill_codes": ["NUM.PRB.02", "NUM.MEAS.04"]},
    {"code": "X1", "band": "G2+", "ladder_order": null, "descriptor": "Explains the procedure / judges a claim", "skill_codes": ["NUM.PRB.03"]},
    {"code": "X2", "band": "G2+", "ladder_order": null, "descriptor": "Finds the mistake in a worked example", "skill_codes": ["NUM.PRB.03"]}
  ]
}
```

Every `descriptor` is copied character-for-character from `ladder.RUNGS[...]["desc"]`; Step 1's parity test is what proves it.

- [ ] **Step 4: Write `supabase/seed/levels.json`.**

```json
{
  "levels": [
    {"band": "G1", "level": "Lm", "rung_codes": ["R1"], "foundational_rung_code": "R1", "probe_rung_code": "R4"},
    {"band": "G1", "level": "L0", "rung_codes": ["R2", "R3"], "foundational_rung_code": "R1", "probe_rung_code": "R4"},
    {"band": "G1", "level": "Lp", "rung_codes": ["R4"], "foundational_rung_code": "R1", "probe_rung_code": "R4"},
    {"band": "G2", "level": "Lm", "rung_codes": ["R3", "R4"], "foundational_rung_code": "R3", "probe_rung_code": "R9"},
    {"band": "G2", "level": "L0", "rung_codes": ["R5", "R6", "R7"], "foundational_rung_code": "R3", "probe_rung_code": "R9"},
    {"band": "G2", "level": "Lp", "rung_codes": ["R9"], "foundational_rung_code": "R3", "probe_rung_code": "R9"},
    {"band": "G3", "level": "Lm", "rung_codes": ["R5", "R6", "R7"], "foundational_rung_code": "R5", "probe_rung_code": "R12"},
    {"band": "G3", "level": "L0", "rung_codes": ["R9", "R10", "R11"], "foundational_rung_code": "R5", "probe_rung_code": "R12"},
    {"band": "G3", "level": "Lp", "rung_codes": ["R12", "R13"], "foundational_rung_code": "R5", "probe_rung_code": "R12"},
    {"band": "G4", "level": "Lm", "rung_codes": ["R9", "R10", "R11"], "foundational_rung_code": "R9", "probe_rung_code": "R13"},
    {"band": "G4", "level": "L0", "rung_codes": ["R12", "R13", "R14"], "foundational_rung_code": "R9", "probe_rung_code": "R13"},
    {"band": "G4", "level": "Lp", "rung_codes": ["R13"], "foundational_rung_code": "R9", "probe_rung_code": "R13"}
  ]
}
```

- [ ] **Step 5: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_ladder_seeds.py
```

Expected output: `10 passed`.

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add supabase/seed/rungs.json supabase/seed/levels.json \
          packages/engine/tests/seed/test_ladder_seeds.py && \
  git commit -m "Phase 0: seed the 16 rungs and 12 level rules, pinned to ladder.py" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `3 files changed`.

---

## Task 6 — Misconception seed

24 rows: the 14 procedural predictors a marker looks answers up in, and the 10 conceptual ones from the school's adaptive subtraction spec, which no answer alone can reveal.

**Files:**
- Create `packages/engine/tests/seed/test_misconception_seed.py`
- Create `supabase/seed/misconceptions.json`

- [ ] **Step 1: Write the failing parity tests.**

Create `packages/engine/tests/seed/test_misconception_seed.py`.

```python
"""The procedural misconception rows are exactly what the predictors produce.

If a predictor is renamed or its repair hint is reworded and the seed is not
updated, a marker tags a code the database has never heard of.
"""

import json
from pathlib import Path

import pytest

from engine.assess import misconceptions as M

SEED = Path(__file__).resolve().parents[2].parent.parent / "supabase" / "seed"
DETECTABLE_BY = {"answer_lookup", "working", "explanation", "teacher"}


@pytest.fixture(scope="module")
def rows():
    return json.loads((SEED / "misconceptions.json").read_text(encoding="utf-8"))["misconceptions"]


def test_there_are_twenty_four_misconceptions(rows):
    assert len(rows) == 24


def test_code_and_operation_together_are_unique(rows):
    assert len({(r["code"], r["op"]) for r in rows}) == 24


def test_every_row_has_the_columns_the_loader_writes(rows):
    for row in rows:
        assert set(row) == {
            "code",
            "op",
            "name",
            "description",
            "repair_hint",
            "detectable_by",
            "source",
            "external_ref",
        }


def test_detectable_by_is_one_of_the_four_channels(rows):
    assert {r["detectable_by"] for r in rows} <= DETECTABLE_BY


def test_the_procedural_rows_are_exactly_the_prototype_catalogue(rows):
    seeded = {(r["code"], r["op"]): r for r in rows if r["detectable_by"] == "answer_lookup"}
    catalogue = {(r["code"], r["op"]): r for r in M.catalogue()}
    assert set(seeded) == set(catalogue)
    for key, source in catalogue.items():
        assert seeded[key]["name"] == source["name"]
        assert seeded[key]["repair_hint"] == source["repair"]


def test_there_are_fourteen_answer_lookup_rows(rows):
    assert sum(1 for r in rows if r["detectable_by"] == "answer_lookup") == 14


def test_the_ten_conceptual_rows_carry_their_external_reference(rows):
    conceptual = [r for r in rows if r["detectable_by"] != "answer_lookup"]
    assert len(conceptual) == 10
    assert sorted(r["external_ref"] for r in conceptual) == [f"M{n:03d}" for n in range(1, 11)]


def test_only_the_conceptual_rows_have_an_external_reference(rows):
    for row in rows:
        if row["detectable_by"] == "answer_lookup":
            assert row["external_ref"] is None


def test_every_code_uses_the_repositorys_prefix(rows):
    assert all(r["code"].startswith("M_") for r in rows)


def test_no_row_uses_the_word_the_school_does_not_use(rows):
    # CLAUDE.md, Language and naming: "exchange / regroup", never the other word.
    for row in rows:
        blob = f"{row['name']} {row['description']} {row['repair_hint']}".lower()
        assert "borrow" not in blob


def test_every_row_names_where_it_came_from(rows):
    for row in rows:
        assert row["source"].strip()
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_misconception_seed.py
```

Expected failure: `11 errors` — the module fixture raises `FileNotFoundError: ... supabase/seed/misconceptions.json` for every test.

- [ ] **Step 3: Write `supabase/seed/misconceptions.json`.**

The 14 `answer_lookup` rows reproduce `catalogue()` verbatim in `name` and `repair_hint`; their `description` is the worked example the predictor actually returns. The 10 conceptual rows are the adaptive spec's §12 list, reworded into the school's vocabulary — `M004` reads "exchange", not the source's word.

```json
{
  "misconceptions": [
    {"code": "M_NOCARRY", "op": "+", "name": "Forgets to carry", "description": "Writes each column sum mod 10 and never carries: 47 + 38 written as 75.", "repair_hint": "Place-value chart; exchange 10 ones for a ten with rods before recording", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_CARRY_SKIP", "op": "+", "name": "Carry placed one column too far left", "description": "The carry is added two columns left instead of one: 47 + 38 written as 175.", "repair_hint": "Column chart with the carry written above the correct column; two worked examples", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_CONCAT", "op": "+", "name": "Writes the whole column sum instead of regrouping", "description": "Writes the full column sums side by side: 47 + 38 written as 715.", "repair_hint": "Ten-frame / rods: 'only one digit fits in a column'", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_DROP_CARRYOUT", "op": "+", "name": "Drops the final carry-out (76+54 -> 30)", "description": "Drops the carry out of the last column: 76 + 54 written as 30.", "repair_hint": "Estimate first; 'can the answer be smaller than the bigger number?'", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_FACT_PM1", "op": "+", "name": "Fact off by one", "description": "The answer is one more than the correct total: 47 + 38 written as 86.", "repair_hint": "Number bonds; ten-frame fluency", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_FACT_PM10", "op": "+", "name": "Tens miscounted", "description": "The answer is ten more than the correct total: 47 + 38 written as 95.", "repair_hint": "Count in tens on a 100-square", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_WRONG_OP", "op": "+", "name": "Subtracted instead of adding", "description": "Writes the difference where the sum was asked: 47 + 38 written as 9.", "repair_hint": "Read the question aloud; identify the operation word", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_SMALL_FROM_LARGE", "op": "-", "name": "Subtracts the smaller digit from the larger regardless of row ('neeche wala number')", "description": "Takes the smaller digit from the larger in every column, whichever row it sits in: 62 - 27 written as 45.", "repair_hint": "Rods: show that the top number is the whole; act out the exchange", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_NO_DECREMENT", "op": "-", "name": "Exchanges but does not reduce the lender column", "description": "Adds ten to the column but leaves the lender column unchanged: 62 - 27 written as 45.", "repair_hint": "Cross out and rewrite the lender digit before subtracting", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_ZERO_LENDER", "op": "-", "name": "Across zero: zero lends but the column to its left is not reduced", "description": "The zero becomes 9 and lends, but the column left of it keeps its value: 302 - 178 written as 224.", "repair_hint": "Three-column rods; exchange a hundred for ten tens first", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_ZERO_NOT_NINE", "op": "-", "name": "Across zero: zero becomes 10 and stays 10 (should be 9)", "description": "Takes from the left column correctly but leaves the zero as 10: 302 - 178 written as 134.", "repair_hint": "Number line count-up as a check", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_FACT_PM1", "op": "-", "name": "Fact off by one", "description": "The answer is one less than the correct difference: 62 - 27 written as 34.", "repair_hint": "Number bonds; count-up on a number line", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_FACT_PM10", "op": "-", "name": "Tens miscounted", "description": "The answer is ten more than the correct difference: 62 - 27 written as 45.", "repair_hint": "Count back in tens on a 100-square", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_WRONG_OP", "op": "-", "name": "Added instead of subtracting", "description": "Writes the sum where the difference was asked: 62 - 27 written as 89.", "repair_hint": "Read the question aloud; identify the operation word", "detectable_by": "answer_lookup", "source": "assess/misconceptions.py (Neha S, Maths planning.docx, Aug 2026)", "external_ref": null},
    {"code": "M_MAKE_SMALLER", "op": "-", "name": "Subtraction means make smaller", "description": "Fails compare and missing-part situations, where the answer is found by counting up.", "repair_hint": "Probe with 5 total, 2 red, unknown blue.", "detectable_by": "explanation", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M001"},
    {"code": "M_DIGITS_INDEPENDENT", "op": "any", "name": "Digits are independent", "description": "Treats 43 as a 4 and a 3 with no relation between them.", "repair_hint": "Ask what the 4 represents in 43.", "detectable_by": "explanation", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M002"},
    {"code": "M_REGROUP_CHANGES_TOTAL", "op": "-", "name": "Regrouping changes the total", "description": "Thinks 42 becomes 3 + 12, or some other altered total, once it is regrouped.", "repair_hint": "Represent both decompositions with blocks.", "detectable_by": "explanation", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M003"},
    {"code": "M_EXCHANGE_UNEXPLAINED", "op": "-", "name": "Exchange is a rule without meaning", "description": "Can execute the rote steps of an exchange but cannot say what was traded or why the total is unchanged.", "repair_hint": "Ask what was traded and why the value stayed the same.", "detectable_by": "explanation", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M004"},
    {"code": "M_SMALLER_FROM_LARGER_CONCEPT", "op": "-", "name": "Always subtract the smaller digit from the larger", "description": "The conceptual reading of M_SMALL_FROM_LARGE: visible in the working on items such as 42 - 17 even when the final answer is corrected.", "repair_hint": "Use a symbol-free story and a directed quantity comparison.", "detectable_by": "working", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M005"},
    {"code": "M_ZERO_BLOCKS", "op": "-", "name": "Zero blocks regrouping", "description": "Stops or guesses when a zero must lend, as in 304 - 128.", "repair_hint": "Animate the exchange from hundreds through tens.", "detectable_by": "working", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M006"},
    {"code": "M_MISALIGNED_COLUMNS", "op": "any", "name": "Column misalignment", "description": "Places ones under tens when writing the numbers into columns.", "repair_hint": "Visual place-value columns with snap-to-grid.", "detectable_by": "working", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M007"},
    {"code": "M_COMPENSATION_SIGN", "op": "-", "name": "Compensation sign error", "description": "Adjusts in the wrong direction, doing 52 - 29 as 52 - 30 - 1.", "repair_hint": "Use an algebraic balance visualisation.", "detectable_by": "working", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M008"},
    {"code": "M_COUNTS_ONE_BY_ONE", "op": "any", "name": "Counts inefficiently", "description": "Can solve, but with excessive one-by-one counting marks.", "repair_hint": "Ask the learner to create the largest sensible jumps.", "detectable_by": "working", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M009"},
    {"code": "M_KEYWORD_OVERGENERALISED", "op": "any", "name": "Pattern overgeneralisation", "description": "Chooses subtraction because a keyword such as 'left' appears in the question.", "repair_hint": "Give a non-subtraction context containing the keyword.", "detectable_by": "teacher", "source": "docs/sources/adaptive-subtraction-learning-engine-spec.txt section 12", "external_ref": "M010"}
  ]
}
```

- [ ] **Step 4: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_misconception_seed.py
```

Expected output: `11 passed`.

- [ ] **Step 5: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add supabase/seed/misconceptions.json packages/engine/tests/seed/test_misconception_seed.py && \
  git commit -m "Phase 0: seed 24 misconceptions, 14 answer-lookup and 10 conceptual" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 7 — Prompt seed

The five prompts of SPEC §8, version 1, model `claude-opus-5`, each with a strict JSON schema. CLAUDE.md rule 2: a prompt string inside Python, TypeScript or an n8n node is a defect.

**Files:**
- Create `packages/engine/tests/seed/test_prompt_seed.py`
- Create `supabase/seed/prompts/read_cells.v1.txt`
- Create `supabase/seed/prompts/read_page.v1.txt`
- Create `supabase/seed/prompts/legacy_extract.v1.txt`
- Create `supabase/seed/prompts/word_context.v1.txt`
- Create `supabase/seed/prompts/parent_note.v1.txt`
- Create `supabase/seed/prompts.json`

- [ ] **Step 1: Write the failing prompt tests.**

Create `packages/engine/tests/seed/test_prompt_seed.py`.

```python
"""The five prompts of SPEC section 8 exist, are strict, and carry their guardrails.

The guardrail tests assert the prohibition SENTENCE is present, not that the
word is absent: the prompts must contain the sentence that forbids the word, so
an absence test would fail on the rule itself.
"""

import json
from pathlib import Path

import pytest

SEED = Path(__file__).resolve().parents[2].parent.parent / "supabase" / "seed"

PURPOSES = {"read_cells", "read_page", "legacy_extract", "word_context", "parent_note"}
SCHOOL_VOCABULARY = 'Never use the word "borrow"; the school says "exchange".'
TRANSCRIBE_ONLY = "Transcribe only. Do not compute, check, correct or complete any arithmetic."


@pytest.fixture(scope="module")
def prompts():
    return json.loads((SEED / "prompts.json").read_text(encoding="utf-8"))["prompts"]


@pytest.fixture(scope="module")
def texts(prompts):
    return {p["purpose"]: (SEED / p["text_file"]).read_text(encoding="utf-8") for p in prompts}


def test_all_five_purposes_are_seeded(prompts):
    assert {p["purpose"] for p in prompts} == PURPOSES
    assert len(prompts) == 5


def test_every_prompt_is_version_one_and_active(prompts):
    for prompt in prompts:
        assert prompt["version"] == 1
        assert prompt["active"] is True


def test_every_prompt_names_the_model(prompts):
    assert {p["model"] for p in prompts} == {"claude-opus-5"}


def test_every_prompt_has_a_text_file_that_exists_and_is_not_empty(texts):
    for purpose, text in texts.items():
        assert len(text.strip()) > 200, purpose


def test_every_schema_is_a_strict_object(prompts):
    for prompt in prompts:
        schema = prompt["json_schema"]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["required"]
        assert set(schema["required"]) <= set(schema["properties"])


def test_the_reading_prompts_forbid_computing(texts):
    assert TRANSCRIBE_ONLY in texts["read_cells"]
    assert TRANSCRIBE_ONLY in texts["legacy_extract"]


def test_every_language_prompt_carries_the_schools_vocabulary_rule(texts):
    for purpose in ("read_page", "legacy_extract", "word_context", "parent_note"):
        assert SCHOOL_VOCABULARY in texts[purpose], purpose


def test_the_parent_note_says_educator_not_teacher(texts):
    assert 'Say "educator", never "teacher".' in texts["parent_note"]


def test_the_word_context_prompt_forbids_changing_the_numbers(texts):
    assert "Do not change, round, add or remove a number." in texts["word_context"]


def test_no_reading_prompt_mentions_a_child_name(texts):
    # SPEC section 13: prompts receive crops and pages, not names.
    for purpose in ("read_cells", "read_page", "legacy_extract"):
        assert "name" not in texts[purpose].lower(), purpose


def test_read_cells_returns_one_character_per_cell(texts):
    assert "One character per cell." in texts["read_cells"]
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_prompt_seed.py
```

Expected failure: `11 errors` — the module fixture raises `FileNotFoundError: ... supabase/seed/prompts.json` for every test.

- [ ] **Step 3: Write `supabase/seed/prompts/read_cells.v1.txt`.**

```text
You are transcribing handwriting from a scanned Grade 1 to Grade 4 maths worksheet at Cornerstone School, Pune.

You will receive the answer-cell crops from one page, in order. Each crop is one cell a child has written a single character into. Each crop is labelled with its item number and its response id.

Transcribe only. Do not compute, check, correct or complete any arithmetic. You are not shown the question and you must not infer one. If the character the child wrote would make the answer wrong, transcribe it exactly as written anyway.

For every crop, return:
- item: the item number given with the crop
- rid: the response id given with the crop
- k: the cell index inside that response, counting from 0 at the left
- digit: the single character 0 to 9 the child wrote, or "" for an empty cell
- confidence: 0.00 to 1.00, your confidence in that character

Rules:
- One character per cell. Never two characters, never a word, never an operator.
- If a digit is crossed out and another is written, transcribe the one the child left standing.
- An empty cell, or a cell holding only a stray mark, is "" with a confidence of 1.00.
- A cell you genuinely cannot read is "" with a confidence below 0.30.
- Return exactly one object per crop, in the order the crops were given.

Return JSON only, matching the schema. No prose.
```

- [ ] **Step 4: Write `supabase/seed/prompts/read_page.v1.txt`.**

```text
You are reading one whole page of a completed Grade 1 to Grade 4 maths worksheet from Cornerstone School, Pune, in order to describe how the child worked.

You are not marking the page. Another part of the system has already decided which answers are right and which are wrong, and nothing you write changes that.

Report only what is visible on the page:
- self_correction: were answers or working crossed out and rewritten?
- guessed: are there answers standing alone with no working anywhere on the page, at items where working would normally appear?
- fatigue: do the writing, the working or the completeness fall away towards the end of the page?
- method_pattern: is one method repeated across items? For example counting marks, a hand-drawn number line, columns written out, an exchange recorded above the tens. Return null if no method repeats.

Then write two to four plain sentences an educator can read in ten seconds. Refer to items by their number. Say what you saw, not what it means about the child. No praise, no diagnosis, no advice, no score, no count of right answers.

Never use the word "borrow"; the school says "exchange".

Return JSON only, matching the schema. No prose outside it.
```

- [ ] **Step 5: Write `supabase/seed/prompts/legacy_extract.v1.txt`.**

```text
You are transcribing one page of a completed maths assessment from Cornerstone School, Pune. This page carries no machine-readable markers, so you are reading both the printed question and the child's writing.

You will be told how many items this page is expected to contain.

Transcribe only. Do not compute, check, correct or complete any arithmetic. If what the child wrote is wrong, transcribe the wrong value exactly as written. Never supply a value the child did not write.

For every item on the page, return:
- n: the printed item number
- question_as_printed: the question exactly as printed, on one line, for example "47 + 38 =" or "302 - 178"
- child_answer: exactly what the child wrote as the final answer, as a string, or "" if nothing was written
- attempted: true if there is any of the child's writing for this item, including working with no final answer
- working_summary: at most twelve words describing the visible working, or "" if there is none
- self_corrected: true if an answer or the working was crossed out and rewritten

Rules:
- Return one object per printed item, in printed order, including items the child left blank.
- If the page holds more or fewer items than expected, still return one object per item you can see, and use page_note to say what differs.
- Never use the word "borrow"; the school says "exchange".

Return JSON only, matching the schema. No prose outside it.
```

- [ ] **Step 6: Write `supabase/seed/prompts/word_context.v1.txt`.**

```text
You are writing the wording of one word problem for a maths worksheet at Cornerstone School, Pune.

You will be given: the numbers to use, in the order they must appear; the operation; the rung descriptor this item must stay inside, quoted verbatim; the maximum number of words; and the list of first names you may use.

Write the stem only. Every rule below is hard:
- Use the given numbers exactly, in the given order. Do not change, round, add or remove a number.
- Do not state, compute, or hint at the answer.
- Use only first names from the list you were given. Use no other person, brand, school or place name.
- Stay at or under the word cap.
- Indian context: rupees, metres, kilograms, litres, and everyday school, market, kitchen and playground situations. Write money as a number of rupees, for example 47 rupees.
- Plain present-day language a child of that grade reads without help. One or two sentences, then the question.
- Do not name the operation as an instruction: no "add", no "subtract", no "plus", no "minus", no "find the total of". Let the situation carry it.
- Stay inside the rung descriptor you were given. Do not introduce a second step, a second operation, or a unit the descriptor does not mention.
- Never use the word "borrow"; the school says "exchange".

Return JSON only, matching the schema. No prose outside it.
```

- [ ] **Step 7: Write `supabase/seed/prompts/parent_note.v1.txt`.**

```text
You are drafting a short note from Cornerstone School, Pune, to one child's parent about this week's maths.

You will be given the child's first name, and the one or two things the educators have flagged this week, each with its repair hint. You are given nothing else about the child, and you must not invent anything else.

Write four to six sentences, in this shape:
1. One sentence naming something the child is doing well, drawn from what you were given.
2. One or two sentences saying plainly what the child is still working on. Describe what happens on the page, not a label. For example: when the ones column needs an exchange, the tens column is sometimes left unchanged.
3. One or two sentences giving the parent one concrete thing to try at home this week, in five minutes, with things already in the house.
4. One closing sentence inviting the parent to reply or to speak to the educator.

Rules:
- Plain English. No jargon, no scores, no percentages, no grades, no ranking, no comparison with other children.
- Never use the word "borrow"; the school says "exchange".
- Say "educator", never "teacher".
- Never use the words weak, poor, behind, struggling, problem, or concern.
- Use the child's first name, and no other name.
- Warm, specific, unhurried. No exclamation marks.

Return JSON only, matching the schema. No prose outside it.
```

- [ ] **Step 8: Write `supabase/seed/prompts.json`.**

```json
{
  "prompts": [
    {
      "purpose": "read_cells",
      "version": 1,
      "model": "claude-opus-5",
      "active": true,
      "text_file": "prompts/read_cells.v1.txt",
      "json_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["cells"],
        "properties": {
          "cells": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["item", "rid", "k", "digit", "confidence"],
              "properties": {
                "item": {"type": "integer", "minimum": 1},
                "rid": {"type": "string", "minLength": 1},
                "k": {"type": "integer", "minimum": 0},
                "digit": {"type": "string", "pattern": "^[0-9]?$"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
              }
            }
          }
        }
      }
    },
    {
      "purpose": "read_page",
      "version": 1,
      "model": "claude-opus-5",
      "active": true,
      "text_file": "prompts/read_page.v1.txt",
      "json_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["narrative", "signals"],
        "properties": {
          "narrative": {"type": "string", "minLength": 1, "maxLength": 600},
          "signals": {
            "type": "object",
            "additionalProperties": false,
            "required": ["self_correction", "guessed", "fatigue", "method_pattern"],
            "properties": {
              "self_correction": {"type": "boolean"},
              "guessed": {"type": "boolean"},
              "fatigue": {"type": "boolean"},
              "method_pattern": {"type": ["string", "null"], "maxLength": 120}
            }
          }
        }
      }
    },
    {
      "purpose": "legacy_extract",
      "version": 1,
      "model": "claude-opus-5",
      "active": true,
      "text_file": "prompts/legacy_extract.v1.txt",
      "json_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["items", "page_note"],
        "properties": {
          "page_note": {"type": "string", "maxLength": 300},
          "items": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["n", "question_as_printed", "child_answer", "attempted", "working_summary", "self_corrected"],
              "properties": {
                "n": {"type": "integer", "minimum": 1},
                "question_as_printed": {"type": "string", "minLength": 1, "maxLength": 200},
                "child_answer": {"type": "string", "maxLength": 40},
                "attempted": {"type": "boolean"},
                "working_summary": {"type": "string", "maxLength": 120},
                "self_corrected": {"type": "boolean"}
              }
            }
          }
        }
      }
    },
    {
      "purpose": "word_context",
      "version": 1,
      "model": "claude-opus-5",
      "active": true,
      "text_file": "prompts/word_context.v1.txt",
      "json_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["stem", "numbers_used", "word_count"],
        "properties": {
          "stem": {"type": "string", "minLength": 10, "maxLength": 400},
          "numbers_used": {"type": "array", "items": {"type": "integer"}},
          "word_count": {"type": "integer", "minimum": 1, "maximum": 80}
        }
      }
    },
    {
      "purpose": "parent_note",
      "version": 1,
      "model": "claude-opus-5",
      "active": true,
      "text_file": "prompts/parent_note.v1.txt",
      "json_schema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["body", "sentence_count"],
        "properties": {
          "body": {"type": "string", "minLength": 40, "maxLength": 1200},
          "sentence_count": {"type": "integer", "minimum": 4, "maximum": 6}
        }
      }
    }
  ]
}
```

- [ ] **Step 9: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/seed/test_prompt_seed.py
```

Expected output: `11 passed`.

- [ ] **Step 10: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add supabase/seed/prompts.json supabase/seed/prompts \
          packages/engine/tests/seed/test_prompt_seed.py && \
  git commit -m "Phase 0: seed the five SPEC section 8 prompts at version 1 with strict schemas" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `7 files changed`.

---

## Task 8 — `engine/db.py`, the one connection helper

**Files:**
- Create `packages/engine/tests/test_db.py`
- Create `packages/engine/engine/db.py`

- [ ] **Step 1: Write the failing tests.**

Create `packages/engine/tests/test_db.py`.

```python
"""The connection helper refuses to run against a missing or placeholder URL.

A placeholder that reaches psycopg produces a connection error forty lines deep.
Catching it here names the file the user has to fix.
"""

import pytest

from engine import db


def test_database_url_raises_when_it_is_not_set(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "absent.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(db.ConfigError, match="is not set"):
        db.database_url()


def test_database_url_raises_when_it_is_still_a_placeholder(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "absent.env")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:CHANGE_ME@localhost:5432/postgres")
    with pytest.raises(db.ConfigError, match="placeholder"):
        db.database_url()


def test_database_url_returns_a_real_value(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "absent.env")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@example.invalid:5432/postgres")
    assert db.database_url() == "postgresql://u:p@example.invalid:5432/postgres"


def test_database_url_strips_surrounding_whitespace(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "absent.env")
    monkeypatch.setenv("DATABASE_URL", "  postgresql://u:p@example.invalid:5432/postgres \n")
    assert db.database_url() == "postgresql://u:p@example.invalid:5432/postgres"


def test_the_error_names_the_file_to_fix(monkeypatch, tmp_path):
    env = tmp_path / "absent.env"
    monkeypatch.setattr(db, "ENV_PATH", env)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(db.ConfigError, match=str(env)):
        db.database_url()


def test_load_env_reads_the_repository_env_file(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_URL=postgresql://u:p@example.invalid:5432/postgres\n", encoding="utf-8"
    )
    monkeypatch.setattr(db, "ENV_PATH", env)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.database_url() == "postgresql://u:p@example.invalid:5432/postgres"


def test_an_environment_value_wins_over_the_env_file(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "DATABASE_URL=postgresql://fromfile@example.invalid:5432/postgres\n", encoding="utf-8"
    )
    monkeypatch.setattr(db, "ENV_PATH", env)
    monkeypatch.setenv("DATABASE_URL", "postgresql://fromshell@example.invalid:5432/postgres")
    assert "fromshell" in db.database_url()
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_db.py
```

Expected failure: `ModuleNotFoundError: No module named 'engine.db'`, summary `1 error`.

- [ ] **Step 3: Write `packages/engine/engine/db.py`.**

```python
"""The only place this engine opens a database connection.

One hosted Supabase project, reached through the ap-south-1 session pooler.
Callers commit or roll back; this module never decides that for them.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# packages/engine/engine/db.py -> repository root
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
PLACEHOLDER = "CHANGE_ME"


class ConfigError(RuntimeError):
    """DATABASE_URL is missing, or still holds a placeholder."""


def load_env() -> None:
    """Read the repository .env. A value already in the environment wins."""
    load_dotenv(ENV_PATH, override=False)


def database_url() -> str:
    load_env()
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ConfigError(f"DATABASE_URL is not set. Copy .env.example and fill it in: {ENV_PATH}")
    if PLACEHOLDER in url:
        raise ConfigError(f"DATABASE_URL is still a placeholder. Fill it in: {ENV_PATH}")
    return url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Open one connection with autocommit off. The caller commits or rolls back."""
    with psycopg.connect(database_url(), autocommit=False) as conn:
        yield conn
```

- [ ] **Step 4: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_db.py
```

Expected output: `7 passed`.

- [ ] **Step 5: Run the schema tests, which can now import, and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_schema.py
```

Expected output: `12 passed` — the Ring A and Ring B migrations from Tasks 3 and 4 satisfy every invariant. If `.env` is not filled in, the output is `12 skipped` with the reason printed; it must be filled in before the gate in Task 12.

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/engine/db.py packages/engine/tests/test_db.py && \
  git commit -m "Phase 0: one connection helper that refuses placeholder credentials" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 9 — `engine/loaders.py`: the pure row builders

Each builder turns one seed file into rows. They take no connection, so they are tested without a database — and that is most of the loader's logic.

**Files:**
- Create `packages/engine/tests/test_loaders.py`
- Create `packages/engine/engine/loaders.py`

- [ ] **Step 1: Write the failing builder tests.**

Create `packages/engine/tests/test_loaders.py`.

```python
"""The row builders, and the SQL the generic upsert produces, without a database."""

import pytest

from engine import loaders

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="module")
def registry():
    return loaders.read_seed("registry-num.json")


def test_read_seed_raises_a_named_error_for_a_missing_file():
    with pytest.raises(loaders.SeedError, match="seed file missing"):
        loaders.read_seed("there-is-no-such-seed.json")


def test_read_seed_raises_a_named_error_for_broken_json(tmp_path, monkeypatch):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(loaders, "SEED_DIR", tmp_path)
    loaders.read_seed.cache_clear()
    try:
        with pytest.raises(loaders.SeedError, match="not valid JSON"):
            loaders.read_seed("broken.json")
    finally:
        loaders.read_seed.cache_clear()


def test_require_names_every_missing_key():
    with pytest.raises(loaders.SeedError, match="missing b, c"):
        loaders.require({"a": 1}, ("a", "b", "c"), "row 3")


def test_upsert_sql_only_writes_when_a_column_actually_differs():
    table = loaders.Table(
        "thing", ("tenant_id", "code", "name"), ("tenant_id", "code"), lambda tenant_id: []
    )
    assert loaders._upsert_sql(table) == (
        "insert into thing (tenant_id, code, name) "
        "values (%(tenant_id)s, %(code)s, %(name)s) "
        "on conflict (tenant_id, code) do update set name = excluded.name "
        "where (thing.name) is distinct from (excluded.name)"
    )


def test_skill_rows_has_one_row_per_registry_skill(registry):
    rows = loaders.skill_rows(TENANT, registry)
    assert len(rows) == 37
    assert len({r["code"] for r in rows}) == 37


def test_skill_rows_take_domain_and_strand_from_the_registry_tree(registry):
    by_code = {r["code"]: r for r in loaders.skill_rows(TENANT, registry)}
    assert by_code["NUM.OPS.01"]["domain"] == "NUM"
    assert by_code["NUM.OPS.01"]["strand"] == "NUM.OPS"
    assert by_code["NUM.MEAS.04"]["strand"] == "NUM.MEAS"


def test_skill_rows_carry_the_tenant_and_the_registry_text(registry):
    rows = loaders.skill_rows(TENANT, registry)
    assert all(r["tenant_id"] == TENANT for r in rows)
    assert all(r["name"].strip() for r in rows)


def test_skill_rows_refuse_a_skill_the_tree_does_not_place():
    orphan = {"skills": {"NUM.ZZZ.99": {"name": "x", "desc": "y", "src": "z"}}, "tree": []}
    with pytest.raises(loaders.SeedError, match="not in tree"):
        loaders.skill_rows(TENANT, orphan)


def test_milestone_rows_match_the_registry_count(registry):
    rows = loaders.milestone_rows(TENANT, registry)
    assert len(rows) == 162
    assert len({(r["skill_code"], r["band"]) for r in rows}) == 162


def test_milestone_rows_carry_band_descriptor_and_scale(registry):
    rows = loaders.milestone_rows(TENANT, registry)
    assert all(r["band"].strip() and r["descriptor"].strip() and r["scale"].strip() for r in rows)


def test_rung_rows_are_the_sixteen_ladder_rungs():
    rows = loaders.rung_rows(TENANT, loaders.read_seed("rungs.json"))
    assert len(rows) == 16
    by_code = {r["code"]: r for r in rows}
    assert by_code["R6"]["band"] == "G2"
    assert by_code["R6"]["skill_codes"] == ["NUM.OPS.02"]
    assert by_code["R6"]["ladder_order"] == 6
    assert by_code["X1"]["ladder_order"] is None


def test_level_rule_rows_are_four_bands_by_three_levels():
    rows = loaders.level_rule_rows(TENANT, loaders.read_seed("levels.json"))
    assert len(rows) == 12
    assert {r["band"] for r in rows} == {"G1", "G2", "G3", "G4"}
    assert {r["level"] for r in rows} == {"Lm", "L0", "Lp"}


def test_misconception_rows_are_fourteen_procedural_and_ten_conceptual():
    rows = loaders.misconception_rows(TENANT, loaders.read_seed("misconceptions.json"))
    assert len(rows) == 24
    assert sum(1 for r in rows if r["detectable_by"] == "answer_lookup") == 14


def test_prompt_rows_read_their_text_from_disk():
    rows = loaders.prompt_rows(TENANT, loaders.read_seed("prompts.json"))
    assert len(rows) == 5
    assert all(len(r["text"]) > 200 for r in rows)
    assert all(r["model"] == "claude-opus-5" for r in rows)
    assert all(isinstance(r["json_schema"], dict) for r in rows)


def test_prompt_rows_raise_when_the_text_file_is_missing():
    seed = {
        "prompts": [
            {
                "purpose": "read_cells",
                "version": 1,
                "model": "claude-opus-5",
                "active": True,
                "text_file": "prompts/there-is-no-such-prompt.v1.txt",
                "json_schema": {},
            }
        ]
    }
    with pytest.raises(loaders.SeedError, match="text file missing"):
        loaders.prompt_rows(TENANT, seed)


def test_every_table_builder_produces_exactly_its_declared_columns():
    for table in loaders.TABLES:
        for row in table.build(TENANT):
            assert set(row) == set(table.columns), table.name


def test_every_conflict_column_is_one_of_the_tables_columns():
    for table in loaders.TABLES:
        assert set(table.conflict) <= set(table.columns), table.name
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_loaders.py
```

Expected failure: `ModuleNotFoundError: No module named 'engine.loaders'`, summary `1 error`.

- [ ] **Step 3: Write the seed reading and the row builders.**

Create `packages/engine/engine/loaders.py` with this first section:

```python
"""Idempotent seed loaders: supabase/seed/*.json into Ring A.

Every table is a pure row builder plus one generic upsert that writes only when a
column actually differs. That is what makes `engine load` safe to run twice: the
second run reports zero changed rows because no statement changed anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from psycopg.types.json import Jsonb

# packages/engine/engine/loaders.py -> repository root
SEED_DIR = Path(__file__).resolve().parents[3] / "supabase" / "seed"


class SeedError(RuntimeError):
    """A seed file is missing, malformed, or missing a key the loader needs."""


@lru_cache(maxsize=None)
def read_seed(name: str) -> Any:
    """Read and parse one seed file. Cached: registry-num.json is read twice."""
    path = SEED_DIR / name
    if not path.exists():
        raise SeedError(f"seed file missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError(f"{path} is not valid JSON: {exc}") from exc


def require(row: dict, keys: Iterable[str], where: str) -> None:
    missing = [key for key in keys if key not in row]
    if missing:
        raise SeedError(f"{where}: missing {', '.join(missing)}")


# ------------------------------------------------------------------ row builders


def skill_rows(tenant_id: str, registry: dict) -> list[dict]:
    placed = {
        code: (domain["code"], strand["code"])
        for domain in registry.get("tree", [])
        for strand in domain.get("strands", [])
        for code in strand.get("skills", [])
    }
    rows = []
    for code, skill in registry["skills"].items():
        require(skill, ("name", "desc", "src"), f"registry skill {code}")
        if code not in placed:
            raise SeedError(f"registry skill {code} is in skills but not in tree")
        domain, strand = placed[code]
        rows.append(
            dict(
                tenant_id=tenant_id,
                code=code,
                domain=domain,
                strand=strand,
                name=skill["name"],
                description=skill["desc"],
                source=skill["src"],
            )
        )
    return sorted(rows, key=lambda row: row["code"])


def milestone_rows(tenant_id: str, registry: dict) -> list[dict]:
    rows = []
    for code, skill in registry["skills"].items():
        for milestone in skill.get("ms", []):
            require(milestone, ("b", "d", "s", "src"), f"registry milestone on {code}")
            rows.append(
                dict(
                    tenant_id=tenant_id,
                    skill_code=code,
                    band=milestone["b"],
                    descriptor=milestone["d"],
                    scale=milestone["s"],
                    source=milestone["src"],
                )
            )
    return sorted(rows, key=lambda row: (row["skill_code"], row["band"]))


def rung_rows(tenant_id: str, seed: dict) -> list[dict]:
    rows = []
    for rung in seed["rungs"]:
        require(rung, ("code", "band", "ladder_order", "descriptor", "skill_codes"), "rungs.json")
        rows.append(
            dict(
                tenant_id=tenant_id,
                code=rung["code"],
                band=rung["band"],
                ladder_order=rung["ladder_order"],
                descriptor=rung["descriptor"],
                skill_codes=rung["skill_codes"],
            )
        )
    return rows


def level_rule_rows(tenant_id: str, seed: dict) -> list[dict]:
    rows = []
    for level in seed["levels"]:
        require(
            level,
            ("band", "level", "rung_codes", "foundational_rung_code", "probe_rung_code"),
            "levels.json",
        )
        rows.append(
            dict(
                tenant_id=tenant_id,
                band=level["band"],
                level=level["level"],
                rung_codes=level["rung_codes"],
                foundational_rung_code=level["foundational_rung_code"],
                probe_rung_code=level["probe_rung_code"],
            )
        )
    return rows


def misconception_rows(tenant_id: str, seed: dict) -> list[dict]:
    rows = []
    for row in seed["misconceptions"]:
        require(
            row,
            ("code", "op", "name", "description", "repair_hint", "detectable_by", "source",
             "external_ref"),
            "misconceptions.json",
        )
        rows.append(
            dict(
                tenant_id=tenant_id,
                code=row["code"],
                op=row["op"],
                name=row["name"],
                description=row["description"],
                repair_hint=row["repair_hint"],
                detectable_by=row["detectable_by"],
                source=row["source"],
                external_ref=row["external_ref"],
            )
        )
    return rows


def prompt_rows(tenant_id: str, seed: dict) -> list[dict]:
    rows = []
    for prompt in seed["prompts"]:
        require(
            prompt,
            ("purpose", "version", "model", "active", "text_file", "json_schema"),
            f"prompts.json entry {prompt.get('purpose', '?')}",
        )
        path = SEED_DIR / prompt["text_file"]
        if not path.exists():
            raise SeedError(
                f"prompt {prompt['purpose']} v{prompt['version']}: text file missing: {path}"
            )
        rows.append(
            dict(
                tenant_id=tenant_id,
                purpose=prompt["purpose"],
                version=prompt["version"],
                text=path.read_text(encoding="utf-8").strip(),
                model=prompt["model"],
                json_schema=prompt["json_schema"],
                active=prompt["active"],
            )
        )
    return rows
```

- [ ] **Step 4: Append the table declarations and the SQL builder.**

Continue the same file:

```python
# ------------------------------------------------------------------ table registry


@dataclass(frozen=True)
class Table:
    """One seeded table: where its rows come from, and how a re-run finds them."""

    name: str
    columns: tuple[str, ...]
    conflict: tuple[str, ...]
    build: Callable[[str], list[dict]]
    jsonb: tuple[str, ...] = ()


TABLES: tuple[Table, ...] = (
    Table(
        "skill",
        ("tenant_id", "code", "domain", "strand", "name", "description", "source"),
        ("tenant_id", "code"),
        lambda tenant_id: skill_rows(tenant_id, read_seed("registry-num.json")),
    ),
    Table(
        "milestone",
        ("tenant_id", "skill_code", "band", "descriptor", "scale", "source"),
        ("tenant_id", "skill_code", "band"),
        lambda tenant_id: milestone_rows(tenant_id, read_seed("registry-num.json")),
    ),
    Table(
        "rung",
        ("tenant_id", "code", "band", "ladder_order", "descriptor", "skill_codes"),
        ("tenant_id", "code"),
        lambda tenant_id: rung_rows(tenant_id, read_seed("rungs.json")),
    ),
    Table(
        "level_rule",
        ("tenant_id", "band", "level", "rung_codes", "foundational_rung_code", "probe_rung_code"),
        ("tenant_id", "band", "level"),
        lambda tenant_id: level_rule_rows(tenant_id, read_seed("levels.json")),
    ),
    Table(
        "misconception",
        ("tenant_id", "code", "op", "name", "description", "repair_hint", "detectable_by",
         "source", "external_ref"),
        ("tenant_id", "code", "op"),
        lambda tenant_id: misconception_rows(tenant_id, read_seed("misconceptions.json")),
    ),
    Table(
        "prompt",
        ("tenant_id", "purpose", "version", "text", "model", "json_schema", "active"),
        ("tenant_id", "purpose", "version"),
        lambda tenant_id: prompt_rows(tenant_id, read_seed("prompts.json")),
        jsonb=("json_schema",),
    ),
)


def _upsert_sql(table: Table) -> str:
    """Insert, or update only the columns that actually differ.

    The trailing WHERE is what makes a second run report zero changed rows:
    PostgreSQL reports 0 affected rows when it suppresses the update.
    Table and column names come from the TABLES constant, never from input.
    """
    updatable = [c for c in table.columns if c not in table.conflict]
    values = ", ".join(f"%({c})s" for c in table.columns)
    assignments = ", ".join(f"{c} = excluded.{c}" for c in updatable)
    current = ", ".join(f"{table.name}.{c}" for c in updatable)
    proposed = ", ".join(f"excluded.{c}" for c in updatable)
    return (
        f"insert into {table.name} ({', '.join(table.columns)}) "
        f"values ({values}) "
        f"on conflict ({', '.join(table.conflict)}) do update set {assignments} "
        f"where ({current}) is distinct from ({proposed})"
    )
```

- [ ] **Step 5: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_loaders.py
```

Expected output: `17 passed`.

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/engine/loaders.py packages/engine/tests/test_loaders.py && \
  git commit -m "Phase 0: seed row builders and the idempotent upsert SQL" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 10 — `engine/loaders.py`: writing, counting, and the orphan check

**Files:**
- Modify `packages/engine/engine/loaders.py`
- Modify `packages/engine/tests/test_loaders.py`

- [ ] **Step 1: Add the failing write-path tests.**

Append to `packages/engine/tests/test_loaders.py`. Every one of them rolls back, so the `cornerstone-test` tenant never persists.

```python
# ------------------------------------------------------------------ write path


@pytest.mark.db
def test_load_all_writes_every_expected_row(conn):
    report = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    assert report.seeded == {
        "skill": 37,
        "milestone": 162,
        "rung": 16,
        "level_rule": 12,
        "misconception": 24,
        "prompt": 5,
    }
    assert report.present == report.seeded
    conn.rollback()


@pytest.mark.db
def test_a_second_load_changes_nothing(conn):
    loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    second = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    assert sum(second.changed.values()) == 0
    assert second.clean
    conn.rollback()


@pytest.mark.db
def test_no_rung_references_a_skill_the_registry_does_not_have(conn):
    report = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    assert report.orphan_rung_skills == []
    conn.rollback()


@pytest.mark.db
def test_a_changed_seed_value_is_written_back(conn):
    report = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    with conn.cursor() as cur:
        cur.execute(
            "update rung set descriptor = 'drifted' where tenant_id = %s and code = 'R6'",
            (report.tenant_id,),
        )
    again = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    assert again.changed["rung"] == 1
    assert not again.clean
    conn.rollback()


@pytest.mark.db
def test_a_report_with_a_missing_row_is_not_clean(conn):
    report = loaders.load_all(conn, "cornerstone-test", "Cornerstone Test Tenant")
    stale = loaders.LoadReport(
        tenant_id=report.tenant_id,
        seeded=report.seeded,
        changed={name: 0 for name in report.seeded},
        present={**report.present, "prompt": 0},
        orphan_rung_skills=[],
    )
    assert not stale.clean
    conn.rollback()
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_loaders.py -m db
```

Expected failure: `AttributeError: module 'engine.loaders' has no attribute 'load_all'`, summary `5 failed`.

- [ ] **Step 3: Append the write path to `packages/engine/engine/loaders.py`.**

```python
# ------------------------------------------------------------------ writing


@dataclass(frozen=True)
class LoadReport:
    tenant_id: str
    seeded: dict[str, int]   # rows the seed files hold
    changed: dict[str, int]  # rows this run inserted or updated
    present: dict[str, int]  # rows now in the database for this tenant
    orphan_rung_skills: list[tuple[str, str]]

    @property
    def clean(self) -> bool:
        """True when this run wrote nothing, everything is present, and no rung dangles."""
        return (
            not self.orphan_rung_skills
            and sum(self.changed.values()) == 0
            and all(self.present[name] == count for name, count in self.seeded.items())
        )


def upsert(conn, table: Table, rows: list[dict]) -> int:
    """Write one table's rows. Returns how many rows actually changed."""
    sql = _upsert_sql(table)
    changed = 0
    with conn.cursor() as cur:
        for row in rows:
            params = {c: (Jsonb(row[c]) if c in table.jsonb else row[c]) for c in table.columns}
            cur.execute(sql, params)
            changed += cur.rowcount
    return changed


def upsert_tenant(conn, slug: str, name: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "insert into tenant (slug, name) values (%s, %s) "
            "on conflict (slug) do update set name = excluded.name "
            "where tenant.name is distinct from excluded.name "
            "returning id",
            (slug, name),
        )
        row = cur.fetchone()
        if row is None:
            # The conflict clause suppressed the update, so nothing was returned.
            cur.execute("select id from tenant where slug = %s", (slug,))
            row = cur.fetchone()
        return str(row[0])


def row_counts(conn, tenant_id: str) -> dict[str, int]:
    counts = {}
    with conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"select count(*) from {table.name} where tenant_id = %s", (tenant_id,))
            counts[table.name] = cur.fetchone()[0]
    return counts


def orphan_rung_skills(conn, tenant_id: str) -> list[tuple[str, str]]:
    """Rungs naming a skill code the registry does not have. Phase 0's gate wants zero."""
    with conn.cursor() as cur:
        cur.execute(
            "select r.code, s "
            "from rung r, unnest(r.skill_codes) as s "
            "where r.tenant_id = %s "
            "  and not exists (select 1 from skill k "
            "                  where k.tenant_id = r.tenant_id and k.code = s) "
            "order by 1, 2",
            (tenant_id,),
        )
        return [(code, skill) for code, skill in cur.fetchall()]


def load_all(conn, tenant_slug: str, tenant_name: str) -> LoadReport:
    """Load every seed file. Does not commit; the caller decides."""
    tenant_id = upsert_tenant(conn, tenant_slug, tenant_name)
    seeded: dict[str, int] = {}
    changed: dict[str, int] = {}
    for table in TABLES:
        rows = table.build(tenant_id)
        seeded[table.name] = len(rows)
        changed[table.name] = upsert(conn, table, rows)
    return LoadReport(
        tenant_id=tenant_id,
        seeded=seeded,
        changed=changed,
        present=row_counts(conn, tenant_id),
        orphan_rung_skills=orphan_rung_skills(conn, tenant_id),
    )
```

- [ ] **Step 4: Run the database tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_loaders.py -m db
```

Expected output: `5 passed`.

- [ ] **Step 5: Run the whole loader suite.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_loaders.py
```

Expected output: `22 passed`.

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/engine/loaders.py packages/engine/tests/test_loaders.py && \
  git commit -m "Phase 0: load_all, row counts, and the orphan rung-to-skill check" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 11 — the `engine load` CLI

**Files:**
- Create `packages/engine/tests/test_cli.py`
- Create `packages/engine/engine/cli.py`

- [ ] **Step 1: Write the failing CLI tests.**

Create `packages/engine/tests/test_cli.py`.

```python
"""engine load: exit codes and output, with the database stubbed out."""

from contextlib import contextmanager

import pytest
from typer.testing import CliRunner

from engine import cli, db, loaders

runner = CliRunner()


class FakeConnection:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _report(changed=0, present=None):
    seeded = {"skill": 37, "milestone": 162, "rung": 16,
              "level_rule": 12, "misconception": 24, "prompt": 5}
    return loaders.LoadReport(
        tenant_id="11111111-1111-1111-1111-111111111111",
        seeded=seeded,
        changed={name: changed for name in seeded},
        present=present or dict(seeded),
        orphan_rung_skills=[],
    )


@pytest.fixture
def stub(monkeypatch):
    connection = FakeConnection()

    @contextmanager
    def fake_connect():
        yield connection

    monkeypatch.setattr(cli.db, "connect", fake_connect)
    monkeypatch.setattr(cli.db, "load_env", lambda: None)
    monkeypatch.setenv("TENANT_SLUG", "cornerstone")
    monkeypatch.setenv("TENANT_NAME", "Cornerstone School, Pune")
    return connection


def test_help_names_the_load_command():
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "load" in result.output


def test_load_prints_one_line_per_table(stub, monkeypatch):
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: _report())
    result = runner.invoke(cli.app, ["load"])
    assert result.exit_code == 0
    for table in ("skill", "milestone", "rung", "level_rule", "misconception", "prompt"):
        assert table in result.output
    assert "37" in result.output and "162" in result.output


def test_load_commits(stub, monkeypatch):
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: _report())
    runner.invoke(cli.app, ["load"])
    assert stub.committed is True
    assert stub.rolled_back is False


def test_load_check_rolls_back(stub, monkeypatch):
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: _report())
    result = runner.invoke(cli.app, ["load", "--check"])
    assert result.exit_code == 0
    assert stub.rolled_back is True
    assert stub.committed is False
    assert "check: clean" in result.output


def test_load_check_fails_when_a_row_would_change(stub, monkeypatch):
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: _report(changed=3))
    result = runner.invoke(cli.app, ["load", "--check"])
    assert result.exit_code == 1
    assert "check: NOT clean" in result.output


def test_load_check_fails_when_a_count_is_short(stub, monkeypatch):
    short = _report(present={"skill": 37, "milestone": 162, "rung": 16,
                             "level_rule": 12, "misconception": 24, "prompt": 0})
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: short)
    result = runner.invoke(cli.app, ["load", "--check"])
    assert result.exit_code == 1


def test_load_check_fails_on_an_orphan_rung(stub, monkeypatch):
    base = _report()
    orphaned = loaders.LoadReport(
        tenant_id=base.tenant_id,
        seeded=base.seeded,
        changed=base.changed,
        present=base.present,
        orphan_rung_skills=[("R6", "NUM.OPS.99")],
    )
    monkeypatch.setattr(cli.loaders, "load_all", lambda conn, slug, name: orphaned)
    result = runner.invoke(cli.app, ["load", "--check"])
    assert result.exit_code == 1


def test_load_exits_two_when_the_database_url_is_missing(monkeypatch):
    @contextmanager
    def refusing_connect():
        raise db.ConfigError("DATABASE_URL is not set.")
        yield  # pragma: no cover

    monkeypatch.setattr(cli.db, "connect", refusing_connect)
    monkeypatch.setattr(cli.db, "load_env", lambda: None)
    result = runner.invoke(cli.app, ["load"])
    assert result.exit_code == 2


def test_load_exits_two_when_a_seed_file_is_broken(stub, monkeypatch):
    def broken(conn, slug, name):
        raise loaders.SeedError("seed file missing: rungs.json")

    monkeypatch.setattr(cli.loaders, "load_all", broken)
    result = runner.invoke(cli.app, ["load"])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_cli.py
```

Expected failure: `ModuleNotFoundError: No module named 'engine.cli'`, summary `1 error`.

- [ ] **Step 3: Write `packages/engine/engine/cli.py`.**

```python
"""engine — the Cornerstone assessment engine command line."""

from __future__ import annotations

import os

import typer

from . import db, loaders

app = typer.Typer(add_completion=False, help="Cornerstone assessment engine.")


@app.callback()
def main() -> None:
    """Cornerstone assessment engine."""
    # Present so Typer keeps `load` as a named subcommand rather than collapsing
    # a single-command app into the top level.


def _print_report(report: loaders.LoadReport, check: bool) -> None:
    typer.echo(f"tenant {report.tenant_id}")
    for name, seeded in report.seeded.items():
        typer.echo(
            f"{name:<14} seed {seeded:>4}   db {report.present[name]:>4}"
            f"   changed {report.changed[name]:>4}"
        )
    if report.orphan_rung_skills:
        for rung_code, skill_code in report.orphan_rung_skills:
            typer.secho(
                f"rung {rung_code} references unknown skill {skill_code}",
                fg=typer.colors.RED,
                err=True,
            )
    else:
        typer.echo("rung -> skill references: 0 unknown")
    if check:
        typer.echo("check: clean" if report.clean else "check: NOT clean")


@app.command()
def load(
    check: bool = typer.Option(
        False,
        "--check",
        help="Load into a transaction, roll it back, and fail if anything would change.",
    ),
) -> None:
    """Load supabase/seed/*.json into Ring A. Running it twice changes nothing."""
    db.load_env()
    slug = os.environ.get("TENANT_SLUG", "cornerstone")
    name = os.environ.get("TENANT_NAME", "Cornerstone School, Pune")
    try:
        with db.connect() as conn:
            report = loaders.load_all(conn, slug, name)
            if check:
                conn.rollback()
            else:
                conn.commit()
    except (db.ConfigError, loaders.SeedError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    _print_report(report, check)
    if check and not report.clean:
        raise typer.Exit(code=1)
```

- [ ] **Step 4: Run the tests and watch them pass.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest tests/test_cli.py
```

Expected output: `9 passed`.

- [ ] **Step 5: Confirm the console script is installed.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run engine --help
```

Expected output: Typer's help for "Cornerstone assessment engine.", listing `load` under `Commands`.

- [ ] **Step 6: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add packages/engine/engine/cli.py packages/engine/tests/test_cli.py && \
  git commit -m "Phase 0: engine load and engine load --check" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `2 files changed`.

---

## Task 12 — Run the gate and record it

Nothing here is a claim; every line is a command and its output. CLAUDE.md rule 8.

**Files:**
- Modify `STATE.md`
- Modify `HANDOFF.md`
- Modify `DECISIONS-LOG.md`
- Modify `SPEC.md`

- [ ] **Step 1: Gate criterion 1a — load, for real, the first time.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run engine load
```

Expected output (the tenant uuid differs on your machine):

```
tenant 8c1f7a2e-0000-0000-0000-000000000000
skill          seed   37   db   37   changed   37
milestone      seed  162   db  162   changed  162
rung           seed   16   db   16   changed   16
level_rule     seed   12   db   12   changed   12
misconception  seed   24   db   24   changed   24
prompt         seed    5   db    5   changed    5
rung -> skill references: 0 unknown
```

- [ ] **Step 2: Gate criterion 1b — load again; nothing changes.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run engine load
```

Expected output: the same block with `changed    0` on every one of the six table lines.

- [ ] **Step 3: Gate criterion 1c — `--check` exits 0.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run engine load --check ; echo "exit=$?"
```

Expected output: the same block, then `check: clean` and `exit=0`.

- [ ] **Step 4: Gate criterion 2 — the row counts, read straight from Postgres.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  psql "$DATABASE_URL" -Atc "select 'tenant', count(*) from tenant union all select 'skill', count(*) from skill union all select 'milestone', count(*) from milestone union all select 'rung', count(*) from rung union all select 'level_rule', count(*) from level_rule union all select 'misconception', count(*) from misconception union all select 'prompt', count(*) from prompt order by 1"
```

Expected output:

```
level_rule|12
milestone|162
misconception|24
prompt|5
rung|16
skill|37
tenant|1
```

- [ ] **Step 5: Gate criterion 4 — zero orphan rung-to-skill references, in SQL.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && set -a && . ./.env && set +a && \
  psql "$DATABASE_URL" -Atc "select count(*) from rung r, unnest(r.skill_codes) as s where not exists (select 1 from skill k where k.tenant_id = r.tenant_id and k.code = s)"
```

Expected output: `0`

- [ ] **Step 6: Gate criterion 3 — the whole suite with coverage.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest --cov --cov-report=term-missing --cov-fail-under=80
```

Expected output: `113 passed`, then a coverage table listing `engine/__init__.py`, `engine/cli.py`, `engine/db.py`, `engine/loaders.py`, with `TOTAL` at or above 80 %. `engine/assess/*` is absent from the table by design — it is moved, not changed, this phase.

- [ ] **Step 7: Rewrite the `Code` and `Environment` sections of `STATE.md`.**

Replace those two sections of `/Users/nimishshah/cornerstone/assessment-engine/STATE.md` with:

```markdown
## Code — Phase 0 complete 2026-09-17

- Schema: 28 tables across `public` and `pii`, all with RLS enabled and forced and a
  `service_role` policy. Check: the `pg_class` query in the plan's Task 4 step 5 → `28` then `0`.
- Seeds loaded: tenant 1, skill 37, milestone 162, rung 16, level_rule 12, misconception 24,
  prompt 5. Check: `uv run engine load` → the counts above.
- Loader is idempotent. Check: `uv run engine load --check` → `check: clean`, exit 0.
- No rung references a skill the registry lacks. Check: the `unnest(skill_codes)` query in the
  plan's Task 12 step 5 → `0`.
- Engine tests green with coverage on the code this phase wrote. Check:
  `uv run pytest --cov --cov-fail-under=80` → `113 passed`, TOTAL at or above 80 %.
- Prototype `assess/` moved in byte-identical. Check: `diff -r` against
  `~/Downloads/assessment-engine-prototype/assess --exclude=__pycache__` → no output.

## Environment

- Docker, Supabase CLI 2.109.0, psql, Node 24, Python 3.14 present; the engine runs on a
  uv-managed Python 3.12 venv at `packages/engine/.venv`.
- Supabase is the hosted project `ruznbyngtfjsaymuylhm` (ap-south-1). Migrations are applied
  with `supabase db push --db-url "$DATABASE_URL"`. There is no local stack: never
  `supabase start`, never `supabase db reset`.
- n8n not installed (Docker); `gh` authenticated as nimishshah1989, admin of `cornerstonepune`.
```

- [ ] **Step 8: Rewrite the `Done` and `Next` sections of `HANDOFF.md`.**

Replace those two sections of `/Users/nimishshah/cornerstone/assessment-engine/HANDOFF.md` with:

```markdown
## Done — Phase 0, 2026-09-17

- Branch `phase-0-foundations`. Python 3.12 venv under `packages/engine`, uv-managed.
- Two migrations applied to the hosted project: Ring A (24 tables plus `pii.child`) and Ring B
  (3 derived tables). The full schema exists now, so Phases 1 to 4 add rows, never DDL.
- `internal.apply_conventions()` enables and forces RLS, creates the `service_role` policy and
  attaches the `updated_at` trigger on every table. Every migration ends by calling it.
- Prototype `assess/` moved in byte-identical, with 31 tests over the predictors and generators.
- Four seed files written and loaded: 16 rungs, 12 level rules, 24 misconceptions, 5 prompts.
- `engine load` and `engine load --check` work; loading twice changes nothing.

## Next

1. Four Phase 0 shells are deliberately empty and Phase 2 is the first reader of each:
   `blueprint` rows, `threshold` rows, `config` rows (the weekly matrix), and
   `rung.milestone_id`, which is NULL for all 16 rungs pending the coverage report.
2. Phase 1: legacy import of the G2/G3 assessments Nimish uploads to `~/cornerstone/assessments/`
   → confirm queue → evidence → graph v0 → Child Growth. Its plan is written separately, once
   the scans arrive.
3. Before Phase 1's first vision call, `engine eval read_cells` needs `gold` rows. There are
   none yet; Aseem's hand-marking of three sheets is the input.
```

- [ ] **Step 9: Append the Phase 0 decisions to `DECISIONS-LOG.md`.**

Append to `/Users/nimishshah/cornerstone/assessment-engine/DECISIONS-LOG.md`:

```markdown
## 2026-09-17 — Phase 0 schema and loader

- **Surrogate uuid primary keys, natural keys as `code` columns.** SPEC section 4 gives
  `skill.id` as `NUM.OPS.01` and `rung.id` as `R5`. With `tenant_id` on every table those are
  not unique across schools, so they became `code` with `unique (tenant_id, code)` and a uuid
  primary key. Rejected: composite `(tenant_id, id)` primary keys, which double the width of
  every foreign key.
- **`skill_codes` / `rung_codes`, not `skill_ids` / `rung_ids`.** The arrays hold registry and
  ladder codes, never uuids. `_id` next to uuid foreign keys named `_id` is a join waiting to go
  to the wrong column.
- **psycopg 3 and hand-written SQL, not SQLAlchemy.** Migrations own the schema (CLAUDE.md
  rule 9) and the engine's database work is bulk upserts and counts. An ORM would be a second,
  drifting definition of every table.
- **Prompt text in `supabase/seed/prompts/*.txt`, pointed at from `prompts.json`.** Prompt text
  is 20 to 40 real lines. Inside a JSON string it is one escaped line, unreviewable in a pull
  request — and rule 7 makes a prompt change a reviewed event. The text still lands as a
  `prompt` row; the file is only its source.
- **`pii.read_child()` instead of a read trigger.** SPEC section 4 says `access_log` is written
  by a "trigger on `pii`". PostgreSQL has no `SELECT` trigger, so reads are logged by a
  `security definer` accessor and direct `SELECT` is revoked from `anon` and `authenticated`.
- **`ladder.py` keeps `RUNGS` and `LEVELS` for now.** CLAUDE.md rule 1 wants no structural
  constants in Python; rule 10 forbids rewriting the prototype, and `items.py` and
  `blueprints.py` import them. Parity tests pin the seeds to the constants so they cannot drift.
  They are deleted in the phase that moves generation onto blueprint rows.
- **`blueprint`, `threshold` and `config` created empty.** Nothing in Phase 0 reads them; the
  first reader is Phase 2's prescribe step, which is where their rows are written and reviewed.
- **M005 seeded as its own row.** `M_SMALL_FROM_LARGE` (answer-lookup) and
  `M_SMALLER_FROM_LARGER_CONCEPT` (working) are the same classroom error with different
  evidence. `unique (tenant_id, code, op)` cannot hold both under one code, and collapsing them
  would lose the working-only signal.
```

- [ ] **Step 10: Correct the SPEC section 11 prompt count.**

In `/Users/nimishshah/cornerstone/assessment-engine/SPEC.md`, the Phase 0 gate cell reads
``` `engine load` twice = zero diff; 37 NUM skills, 16 rungs, 14+ misconceptions, 3 prompts present ```
SPEC section 8 defines five prompts, not three. Replace that cell's text with:

``` `engine load` twice = zero diff; 37 NUM skills, 16 rungs, 24 misconceptions, 5 prompts present ```

- [ ] **Step 11: Run the whole suite once more, after the documentation edits.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine/packages/engine && \
  /Users/nimishshah/.local/bin/uv run pytest --cov --cov-report=term-missing --cov-fail-under=80
```

Expected output: `113 passed`, TOTAL at or above 80 %.

- [ ] **Step 12: Confirm nothing secret is staged.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git status --porcelain && git check-ignore -v .env
```

Expected output: modified `SPEC.md`, `STATE.md`, `HANDOFF.md`, `DECISIONS-LOG.md`, and a line
naming `.gitignore` as the source of the `.env` ignore rule — confirming `.env` is ignored and
unstaged.

- [ ] **Step 13: Commit.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git add STATE.md HANDOFF.md DECISIONS-LOG.md SPEC.md && \
  git commit -m "Phase 0: gate passed - record verified state, handoff, and decisions" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Expected output: `4 files changed`.

- [ ] **Step 14: Push the branch.**

```bash
cd /Users/nimishshah/cornerstone/assessment-engine && \
  git push -u origin phase-0-foundations
```

Expected output: a `remote: Create a pull request` URL for `cornerstonepune/assessment-engine`.

---

## Gate summary

| # | Criterion | Command | Expected |
|---|---|---|---|
| 1 | `engine load` twice changes nothing | Task 12 steps 1 to 3 | second run `changed 0` on every line; `--check` prints `check: clean`, exit 0 |
| 2 | Expected row counts present | Task 12 step 4 | tenant 1, skill 37, milestone 162, rung 16, level_rule 12, misconception 24, prompt 5 |
| 3 | pytest green, at least 80 % on changed code | Task 12 step 6 | `113 passed`, TOTAL at or above 80 % over `db.py`, `loaders.py`, `cli.py` |
| 4 | Zero rungs reference an absent skill | Task 12 step 5 | `0` |

Test counts per file, which together make the 113: `test_misconceptions.py` 18,
`test_items.py` 13, `test_ladder_seeds.py` 10, `test_misconception_seed.py` 11,
`test_prompt_seed.py` 11, `test_db.py` 7, `test_loaders.py` 22 (17 pure, 5 `db`),
`test_schema.py` 12, `test_cli.py` 9.

---

## Self-review: where each Phase 0 requirement is covered

| Requirement | Source | Task |
|---|---|---|
| Repo scaffolding, venv, package | SPEC §10 | 1 |
| Prototype `assess/` moved in with tests green | SPEC §11, CLAUDE.md rule 10 | 2 |
| Ring A: all 22 named tables plus `threshold` and `config` | SPEC §4, §5 | 3 |
| `pii` schema, `pii.child`, `access_log` | SPEC §4, §13 | 3 |
| `tenant_id`, RLS enabled and forced, service_role policy on every table | SPEC §2, auth rules | 3 (`internal.apply_conventions`), asserted in `tests/test_schema.py` |
| Evidence append-only | CLAUDE.md rule 4 | 3 (statement trigger), asserted in `tests/test_schema.py` |
| Blank / wrong / wrong-with-working never collapse | CLAUDE.md rule 5 | 3 (`item_result.status` plus `working_shown` checks), asserted in `tests/test_schema.py` |
| Ring B: `child_skill_state`, `class_card`, `item_stat` | SPEC §4 | 4 |
| 16 rungs seeded from `ladder.py` | brief, `ladder.RUNGS` | 5 |
| 12 level rules, four bands by Lm/L0/Lp | brief, `ladder.LEVELS` | 5 |
| 24 misconceptions: 14 `answer_lookup` plus M001–M010 | SPEC §3, brief | 6 |
| Five prompts, version 1, strict schema, `claude-opus-5` | SPEC §8 | 7 |
| "exchange" not the other word; "educator" not "teacher"; transcribe, never compute | CLAUDE.md naming, SPEC §8 | 7, asserted in `tests/seed/test_prompt_seed.py` |
| `engine/db.py`, the single connection helper | brief | 8 |
| `engine/loaders.py`, idempotent upserts | brief, SPEC §11 | 9, 10 |
| `engine/cli.py`: `engine load`, `engine load --check` | SPEC §5 step 1, CLAUDE.md Verify | 11 |
| `tests/` mirroring the modules | SPEC §10, testing conventions | 2, 5 to 11 |
| Migrations only, no manual DDL | CLAUDE.md rule 9 | 3, 4 |
| Every "works" is a command in `STATE.md` | CLAUDE.md rule 8 | 12 |

**Not covered in Phase 0, by design, with the phase that covers each:** `blueprint` rows
(Phase 2), `threshold` rows (Phase 2), `config` rows for the weekly matrix (Phase 2),
`rung.milestone_id` resolution and the registry coverage report (Phase 2), `gold` rows and
`engine eval` (Phase 1), `packages/engine/api/` and `adapters/` (Phases 1 and 3), `apps/web/`
(Phase 1), `n8n/workflows/` (Phases 2 and 3).
