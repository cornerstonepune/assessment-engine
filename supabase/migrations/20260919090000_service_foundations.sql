-- Foundations for running the engine as a service instead of a person typing commands:
-- idempotent capture (a duplicate import stops counting, never deletes), a cost the adapter can
-- refuse against, a subject a prompt can be scoped to, and the two tables a teacher's correction
-- writes to so reading can improve from what it got wrong. Plan: docs/superpowers/plans/
-- 2026-09-18-spine.md. ADR 0007 (learning loop), 0008 (engine service), 0009 (subject plugins).

-- ------------------------------------------------------------- capture: a re-read supersedes

-- A duplicate `engine legacy import` of the same file for the same sheet is no longer a second
-- row that doubles a child's evidence (STATE.md N3): file_sha256 identifies the content,
-- superseded_by points a voided capture at the one that stands. Nothing is deleted — rule 4 — a
-- superseded capture's item_result rows stay exactly where they are; they simply stop being read.
alter table capture add column file_sha256 text;
alter table capture add column superseded_by uuid references capture(id);

create unique index capture_live_content_idx
  on capture (tenant_id, sheet_instance_id, file_sha256)
  where (superseded_by is null);
create index capture_superseded_by_idx on capture (superseded_by);

-- ------------------------------------------------------------- flow_run: cost, and a repeat call

alter table flow_run add column idempotency_key text;
alter table flow_run add column request jsonb not null default '{}'::jsonb;  -- ids and counts only — never a name or an image (rule 6)
alter table flow_run add column model text;         -- which model actually answered, after fallback
alter table flow_run add column tokens_in integer;
alter table flow_run add column tokens_out integer;

create unique index flow_run_idempotency_idx
  on flow_run (tenant_id, flow, idempotency_key)
  where (idempotency_key is not null);

-- ------------------------------------------------------------- prompt: scoped to a subject

-- Null subject is the shared default; a subject-specific row wins when both exist for a purpose.
-- The old unique constraints treated every subject's prompt as competing for one (purpose,
-- version) slot; the new index lets NUM and, later, a second subject each version their own.
alter table prompt add column subject text;
alter table prompt drop constraint prompt_tenant_id_purpose_version_key;
create unique index prompt_purpose_version_idx
  on prompt (tenant_id, purpose, coalesce(subject, ''), version);
drop index prompt_one_active_idx;
create unique index prompt_one_active_idx
  on prompt (tenant_id, purpose, coalesce(subject, ''))
  where (active);

-- ------------------------------------------------------------- subject: what a topic plugs into

-- A row is enough for a subject whose questions and marking a model plus a person can handle
-- ("rubric"); a row naming a verifier module is what makes maths' numbers exact (ADR 0005, 0009).
create table subject (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                        -- NUM, and later SCI, ENG, ...
  name        text not null,
  verifier    text,                                  -- engine.subjects.<verifier>, or null
  mark_mode   text not null default 'lookup' check (mark_mode in ('lookup', 'rubric')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

-- ------------------------------------------------------------- the learning loop's own rows

-- Every time a person edits what a model read, that edit is both a fact about this child's
-- handwriting and a labelled example: chunk 6 builds child_reading_profile from these rows, and
-- `engine eval` scores a prompt version against them once they are promoted to `gold`.
create table read_correction (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  child_id             uuid not null references child(id) on delete cascade,
  capture_id           uuid not null references capture(id) on delete cascade,
  item_result_id       uuid not null references item_result(id) on delete cascade,
  model_read           text not null default '',
  human_read           text not null,
  misconception_codes  text[] not null default '{}',
  by                   text not null,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index read_correction_child_idx on read_correction (tenant_id, child_id);
create index read_correction_item_result_idx on read_correction (item_result_id);

-- Ring B: rebuilt from read_correction, truncatable at any time. Notes are code-computed tallies
-- (a digit confusion, a habit), not model output — rule 1, nothing structural is a guess.
create table child_reading_profile (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  child_id    uuid not null references child(id) on delete cascade,
  notes       jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now(),
  unique (tenant_id, child_id)
);

-- ------------------------------------------------------------- the graph reads only live captures

create or replace function public.rebuild_child_skill_state(p_child_id uuid) returns integer
language plpgsql security definer set search_path = public as $$
declare
  min_events numeric := coalesce((select value from threshold where key = 'state.min_events'), 3);
  min_obs    numeric := coalesce((select value from threshold where key = 'state.min_observers'), 2);
  promote    numeric := coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5);
  n integer;
begin
  delete from child_skill_state where child_id = p_child_id;
  with live as (
    -- A superseded capture's evidence rows stay (rule 4) but stop counting: a duplicate import
    -- must not inflate a child's evidence twice. Evidence with no item_result behind it (none
    -- exists yet, but the column is nullable) is never superseded by construction.
    select e.* from evidence_event e
    left join item_result r on r.id = e.item_result_id
    left join capture c on c.id = r.capture_id
    where e.child_id = p_child_id and e.confirmed_by is not null
      and (c.id is null or c.superseded_by is null)
  )
  insert into child_skill_state
    (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, repeating_misconception, last_seen)
  select s.tenant_id, s.child_id, s.skill_code, s.rung_code,
         case when s.n_events < min_events                     then 'not_enough_yet'
              when s.repeating is not null                     then 'patterned_error'
              when s.share < demote                            then 'emerging'
              when s.share < promote or s.observers < min_obs  then 'practising'
              when s.n_events >= 2 * min_events                then 'stretch_ready'
              else 'secure' end,
         s.n_events, s.n_correct, s.repeating, s.last_seen
  from (
    select e.tenant_id, e.child_id, e.skill_code, e.rung_code,
           count(*) filter (where e.correct is not null)                        as n_events,
           count(*) filter (where e.correct)                                    as n_correct,
           (count(*) filter (where e.correct))::numeric
             / nullif(count(*) filter (where e.correct is not null), 0)          as share,
           count(distinct coalesce(r.capture_id::text, e.id::text))             as observers,
           max(e.observed_at)                                                   as last_seen,
           (select m.code from live e2, unnest(e2.misconception_codes) as m(code)
             where e2.child_id = e.child_id and e2.skill_code = e.skill_code
               and e2.rung_code = e.rung_code
             group by m.code having count(*) > 1
             order by count(*) desc, m.code limit 1)                            as repeating
    from live e
    left join item_result r on r.id = e.item_result_id
    group by e.tenant_id, e.child_id, e.skill_code, e.rung_code
  ) s;
  get diagnostics n = row_count;
  return n;
end $$;

create or replace function public.confirm_results(p_child_id uuid, p_by text) returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with pending as (
    select r.id, r.tenant_id, r.status, r.misconception_codes, i.rung_code, i.spec, i.skill_codes,
           coalesce((t.key ->> 'date')::timestamptz, c.created_at) as observed_at
    from item_result r
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    join item i on i.id = r.item_id
    where si.child_id = p_child_id and r.state = 'candidate'
      and r.status in ('correct', 'wrong', 'blank')
      and c.superseded_by is null
  ), ev as (
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct,
                                misconception_codes, channel, item_result_id, observed_at, confirmed_by)
    select tenant_id, p_child_id, coalesce(spec ->> 'skill', skill_codes[1]), rung_code,
           case status when 'correct' then true when 'wrong' then false else null end,
           misconception_codes, 'item', id, observed_at, p_by
    from pending
    returning item_result_id
  )
  update item_result r set state = 'confirmed', confirmed_by = p_by, confirmed_at = now()
  from ev where r.id = ev.item_result_id;
  get diagnostics n = row_count;
  perform rebuild_child_skill_state(p_child_id);
  return n;
end $$;

select internal.apply_conventions();
