-- Ring A — source of truth. Append or approve; a batch job never edits it.
-- Every table: id uuid, tenant_id, created_at, updated_at, RLS enabled and forced.
-- Registry and ladder references are by code with composite foreign keys;
-- everything else references by uuid.
--
-- The full schema is created in this migration and 20260917090100_ring_b.sql so
-- that no later phase needs DDL. Phases 1 to 4 add rows, never tables. Tables the
-- Phase 0 loader does not fill are created empty and say so at their definition.

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

-- Called at the end of every migration. 30 tables by hand is 30 chances to
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

-- Empty until Phase 2. BLUEPRINTS in the prototype is a dict of Python lambdas;
-- turning it into declarative slot rows is generation work, and Phase 2 is the
-- first phase that reads this table.
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

-- ------------------------------------------------------------- case tags (SPEC 3.3)

-- The eighteen dimensions: the seventeen of the taxonomy's section 12 master
-- tagging matrix plus word_structure. Named case codes (A01-A72 and the rest)
-- are deliberately NOT rows — they are combinations of these values, and the
-- taxonomy's own instruction is to store dimensions as tags and derive the
-- combinations. Empty until the dimension seed lands; Phase 2's picker and the
-- coverage report are the first readers.
create table case_dimension (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  code            text not null,                    -- op, d1, d2, presentation, ... word_structure
  name            text not null,
  description     text not null default '',
  allowed_values  text[] not null default '{}',     -- the values item.tags may carry for this code
  dimension_order integer,
  source          text not null default '',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (tenant_id, code)
);

-- Per rung, which dimension values must appear before that rung counts as
-- assessed. The coverage report is then one query: for each target, which have
-- no approved item, and which have items but no evidence. Empty until Phase 2.
create table coverage_target (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references tenant(id) on delete cascade,
  rung_code        text not null,
  dimension_code   text not null,
  required_values  text[] not null default '{}',
  min_items        integer not null default 1,
  note             text not null default '',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (tenant_id, rung_code, dimension_code),
  foreign key (tenant_id, rung_code) references rung (tenant_id, code) on delete cascade,
  foreign key (tenant_id, dimension_code) references case_dimension (tenant_id, code) on delete cascade
);
create index coverage_target_rung_idx on coverage_target (tenant_id, rung_code);
create index coverage_target_dimension_idx on coverage_target (tenant_id, dimension_code);

-- ------------------------------------------------------------- numbers and config

-- Empty until Phase 2. Every number it will hold (80 %, 50 %, 21 days,
-- 0.2 / 0.95, the auto-confirm confidence) is first read by the prescribe step;
-- seeding them now would be guessing at their units before anything consumes them.
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

-- Empty until Phase 2, which is the first reader of the weekly matrix row.
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

-- ------------------------------------------------------------------ children

-- Empty until the Phase 1 roster loader. No name here — SPEC 13.
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
-- Empty until Phase 1 (legacy templates and results) and Phase 2 (generation).

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
-- Empty until Phase 1 (legacy import) and Phase 3 (the QR path).

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
create index narrative_observation_tenant_idx on narrative_observation (tenant_id);

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
create index evidence_event_tenant_idx on evidence_event (tenant_id);

-- CLAUDE.md rule 4. Statement-level so it fires even when the statement would
-- match no rows, which is what makes it testable on an empty table.
create trigger evidence_event_append_only
  before update or delete on evidence_event
  for each statement execute function internal.forbid_change();

-- ------------------------------------------------------------- outputs and runs
-- Empty until Phase 4 (home_sheet, parent_note) and Phase 1 (gold).

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
create index home_sheet_tenant_idx on home_sheet (tenant_id);

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
create index parent_note_tenant_idx on parent_note (tenant_id);

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
create index gold_tenant_idx on gold (tenant_id);

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
create index access_log_tenant_idx on access_log (tenant_id);

-- ------------------------------------------------------------------ names

-- SPEC 13: children's names live here and on the printed page, nowhere else.
-- Empty until the Phase 1 roster loader.
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
