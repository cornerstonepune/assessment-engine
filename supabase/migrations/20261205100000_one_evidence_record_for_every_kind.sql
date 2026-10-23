-- One evidence record for every kind (goals/c2-one-evidence-record-for-every-kind.yaml, the locked scope of 22 Oct,
-- slice C2): written, observed, voice, project, performance; who saw it, where, which registry skill, its scale
-- (right / wrong / blank, or yes / sometimes / not yet) and its source. Past rows untouched (rule 4).
--
-- `evidence_event` held one kind, a written answer, and stays the one table: a record now says its kind, its mark on
-- its kind's scale, who saw it, where and what it came from. The kinds, scales and marks are rows (rule 1), the same
-- for every school (supabase/seed/vocabulary.json; tests/test_evidence_every_kind.py keeps the two equal).
--   * A written answer is what it was: its mark follows `correct` (right, wrong, blank: three signals, never two),
--     written by the database itself, so the sign-off and the correction are unchanged. Its who is its sign-off
--     (`confirmed_by`), its where the paper and its source the answer (`item_result_id`).
--   * Every other kind needs who saw it, where and its source, and a mark on its own scale; nothing writes one yet
--     (the observation engine is the next build). The maths graph reads written answers alone (`evidence_placed`).
--   * `skill_code` is a registry skill: every written answer's already is (a question's skill, C1); a new record of
--     any kind is refused unless it names one. Past rows are not re-checked (`not valid`), and not touched: adding a
--     column with a constant default rewrites no row and fires no trigger.
--
-- Written to run twice.

create table if not exists evidence_scale (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  words       text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists evidence_mark (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  scale       text not null,
  code        text not null,
  ord         int not null,
  words       text not null,
  correct     boolean,          -- what the maths graph reads for an answer: right true, wrong false, blank none
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, scale, code),
  foreign key (tenant_id, scale) references evidence_scale (tenant_id, code) on update cascade
);

create table if not exists evidence_kind (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  ord         int not null,
  words       text not null,
  scale       text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code),
  foreign key (tenant_id, scale) references evidence_scale (tenant_id, code) on update cascade
);

create or replace function internal.evidence_vocabulary(p_tenant uuid) returns void
language plpgsql as $$
begin
  insert into evidence_scale (tenant_id, code, words)
  select p_tenant, v.code, v.words
  from (values ('answer', 'right, wrong or blank'), ('seen', 'yes, sometimes or not yet')) v (code, words)
  on conflict (tenant_id, code) do nothing;

  insert into evidence_mark (tenant_id, scale, code, ord, words, correct)
  select p_tenant, v.scale, v.code, v.ord, v.words, v.correct
  from (values
    ('answer', 'right', 0, 'right', true), ('answer', 'wrong', 1, 'wrong', false),
    ('answer', 'blank', 2, 'blank', null::boolean),
    ('seen', 'yes', 0, 'yes', null), ('seen', 'sometimes', 1, 'sometimes', null),
    ('seen', 'not_yet', 2, 'not yet', null)
  ) v (scale, code, ord, words, correct)
  on conflict (tenant_id, scale, code) do nothing;

  insert into evidence_kind (tenant_id, code, ord, words, scale)
  select p_tenant, v.code, v.ord, v.words, v.scale
  from (values
    ('written', 0, 'written', 'answer'), ('observed', 1, 'observed', 'seen'), ('voice', 2, 'voice', 'answer'),
    ('project', 3, 'project', 'seen'), ('performance', 4, 'performance', 'seen')
  ) v (code, ord, words, scale)
  on conflict (tenant_id, code) do nothing;
end $$;

create or replace function internal.evidence_vocabulary_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.evidence_vocabulary(new.id);
  return new;
end $$;

drop trigger if exists evidence_vocabulary on tenant;
create trigger evidence_vocabulary after insert on tenant
  for each row execute function internal.evidence_vocabulary_on_new_school();

select internal.evidence_vocabulary(id) from tenant;

-- The record: its kind, its mark, who saw it, where, its source. Past rows read as the written answers they are.
alter table evidence_event add column if not exists kind text not null default 'written';
alter table evidence_event add column if not exists mark text;
alter table evidence_event add column if not exists seen_by text check (btrim(seen_by) <> '');
alter table evidence_event add column if not exists place text check (btrim(place) <> '');
alter table evidence_event add column if not exists source text check (btrim(source) <> '');
alter table evidence_event alter column rung_code drop not null;

alter table evidence_event drop constraint if exists evidence_event_tenant_id_kind_fkey;
alter table evidence_event add constraint evidence_event_tenant_id_kind_fkey
  foreign key (tenant_id, kind) references evidence_kind (tenant_id, code);
alter table evidence_event drop constraint if exists evidence_event_tenant_id_skill_code_fkey;
alter table evidence_event add constraint evidence_event_tenant_id_skill_code_fkey
  foreign key (tenant_id, skill_code) references registry_skill (tenant_id, code) not valid;
alter table evidence_event drop constraint if exists evidence_event_written_has_rung;
alter table evidence_event add constraint evidence_event_written_has_rung
  check (kind <> 'written' or rung_code is not null);
alter table evidence_event drop constraint if exists evidence_event_channel_check;
alter table evidence_event add constraint evidence_event_channel_check
  check (channel in ('item', 'teacher_override', 'educator'));

-- A new record's mark sits on its kind's scale and agrees with `correct`; a written answer's is written for it.
create or replace function internal.evidence_event_record() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  k_scale text;
  m record;
begin
  select scale into k_scale from evidence_kind where tenant_id = new.tenant_id and code = new.kind;
  if new.mark is null and new.kind = 'written' then
    select code into new.mark from evidence_mark
    where tenant_id = new.tenant_id and scale = k_scale and correct is not distinct from new.correct;
  end if;
  select * into m from evidence_mark where tenant_id = new.tenant_id and scale = k_scale and code = new.mark;
  if not found then
    raise exception 'a % record is marked on its scale (%), not %', new.kind, k_scale, coalesce(new.mark, 'nothing')
      using errcode = 'check_violation';
  end if;
  if exists (select 1 from evidence_mark where tenant_id = new.tenant_id and scale = k_scale and correct is not null)
  then
    if new.correct is not null and new.correct is distinct from m.correct then
      raise exception 'a % record marked % is not correct = %', new.kind, new.mark, new.correct
        using errcode = 'check_violation';
    end if;
    new.correct := m.correct;
  elsif new.correct is not null then
    raise exception 'a % record says yes, sometimes or not yet, never right or wrong', new.kind
      using errcode = 'check_violation';
  end if;
  if new.kind <> 'written' and (new.seen_by is null or new.place is null or new.source is null) then
    raise exception 'a % record says who saw it, where and its source', new.kind using errcode = 'check_violation';
  end if;
  return new;
end $$;

drop trigger if exists evidence_event_record on evidence_event;
create trigger evidence_event_record before insert on evidence_event
  for each row execute function internal.evidence_event_record();

-- The maths graph reads written answers alone; every other kind waits for the observation engine. Same columns.
create or replace view evidence_placed with (security_invoker = true) as
select e.id, e.tenant_id, e.child_id, e.skill_code, e.rung_code, e.correct, e.misconception_codes, e.channel,
       e.item_result_id, e.observed_at, e.stored_at, e.confirmed_by, e.created_at, e.updated_at,
       coalesce(i.rung_code, e.rung_code) as placed_rung
from evidence_event e
left join item_result r on r.id = e.item_result_id
left join item i on i.id = r.item_id
where e.kind = 'written'
  and (e.item_result_id is null
   or e.created_at = (select max(e2.created_at) from evidence_event e2 where e2.item_result_id = e.item_result_id));

select internal.apply_conventions();
