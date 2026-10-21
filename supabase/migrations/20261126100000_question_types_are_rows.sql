-- Question types are rows, one approval each (goals/b2-question-types-are-rows.yaml, ADR 0077, decisions B2-1, B2-2,
-- B2-4).
--
-- Nimish, 2026-10-20: "we need proper tables". A type is what ADR 0077 calls a format: the printed format where the
-- template is only the level's numbers written as a name (ADD.2D2D.REG1), else the template (EQ.TRUE_FALSE, MULT.NTH,
-- each card kind). Its words lived in the website's code, which types a level used in the skills' `formats` lists (out
-- of step with the bank in 11 skills), and nothing approved a type. Now:
--   question_type              one row per type: its words, how it reaches the child, how its questions are marked
--   question_type_of(fmt, t)   the one rule putting a question in a type: the template's row, else the printed format's
--   skill_level_question_type  the types each level's questions are in, kept by the bank's own writes
--   question_type_approval     the coordinator's approval, one per type, covering every skill and level using it
--   drawable_item              what a paper may draw: active, at a confirmed level, of an approved type
--
-- Live on the day (rehearsal 39560151627): 74 types in 394 level × type links, every level confirmed, every type on a
-- paper; so every type starts approved and no paper changes. A new type waits for the coordinator.
--
-- Written to run twice.

create table if not exists question_type (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                -- the template's name, or the printed format's (ADR 0077)
  fmt         text not null,                -- the printed format its questions carry (`item.fmt`)
  words       text not null,                -- the type in the school's words
  reaches     text not null default 'printed' check (reaches in ('printed', 'read_aloud', 'drawn')),
  marked      eval_type[] not null check (cardinality(marked) > 0),  -- the ways its questions are marked
  own_words   boolean not null default true,  -- false: its printed line is drawn from its numbers (render.DRAWN_FROM_NUMBERS)
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

-- One approval per type: given once, by the coordinator, and never edited (a correction is SF2a's withdrawal, later).
create table if not exists question_type_approval (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  question_type  text not null,
  approved_by    text not null check (btrim(approved_by) <> ''),
  approved_at    timestamptz not null default now(),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (tenant_id, question_type),
  foreign key (tenant_id, question_type) references question_type (tenant_id, code) on update cascade
);

-- `place`: where the type's kind prints on a library worksheet, as the skill's list placed it (`library._kind_rank`);
-- null prints after the placed ones, mixed by question.
create table if not exists skill_level_question_type (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  skill_code     text not null,
  difficulty     text not null,
  question_type  text not null,
  place          integer,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (tenant_id, skill_code, difficulty, question_type),
  foreign key (tenant_id, skill_code, difficulty) references skill_level (tenant_id, skill_code, difficulty)
    on delete cascade on update cascade,
  foreign key (tenant_id, question_type) references question_type (tenant_id, code) on update cascade
);

-- The one rule (ADR 0077): a question is in its template's type where the template is a type, else in its printed
-- format's. A template that is only a level's numbers is no row, so its questions fall to their printed format.
create or replace function public.question_type_of(fmt text, template text) returns text
language sql stable set search_path = public as $$
  select coalesce((select q.code from question_type q where q.code = $2 limit 1), $1)
$$;

-- One level's links made equal to its bank: a link for each type its active generated questions are in that is a row,
-- placed as the skill's list placed its printed format; a link no question holds any more goes.
create or replace function internal.skill_level_question_type_sync(p_tenant uuid, p_skill text, p_level text)
returns void language plpgsql security definer set search_path = public as $$
begin
  if p_skill is null or p_level is null then
    return;
  end if;
  with held as (
    select distinct q.code, q.fmt from item i join question_type q
      on q.tenant_id = i.tenant_id and q.code = question_type_of(i.fmt, i.template)
    where i.tenant_id = p_tenant and i.skill_set_code = p_skill and i.difficulty = p_level
      and i.status = 'active' and i.source = 'generated'
  ), gone as (
    delete from skill_level_question_type l
    where l.tenant_id = p_tenant and l.skill_code = p_skill and l.difficulty = p_level
      and not exists (select 1 from held h where h.code = l.question_type)
  )
  insert into skill_level_question_type as l (tenant_id, skill_code, difficulty, question_type, place)
  select p_tenant, p_skill, p_level, h.code, array_position(s.formats, h.fmt) - 1
  from held h join skill_level sl on sl.tenant_id = p_tenant and sl.skill_code = p_skill and sl.difficulty = p_level
  join skill_set s on s.tenant_id = p_tenant and s.code = p_skill
  on conflict (tenant_id, skill_code, difficulty, question_type) do update set place = excluded.place
    where l.place is distinct from excluded.place;
end $$;

create or replace function internal.skill_level_question_type_sync_all() returns void
language sql security definer set search_path = public as $$
  select internal.skill_level_question_type_sync(l.tenant_id, l.skill_code, l.difficulty) from skill_level l;
  delete from skill_level_question_type x where not exists (
    select 1 from skill_level l where l.tenant_id = x.tenant_id and l.skill_code = x.skill_code
      and l.difficulty = x.difficulty);
$$;

-- Whoever writes a question, its level's links follow; so do a skill's when its list's order changes, and every
-- level's when a type becomes a row.
create or replace function internal.skill_level_question_type_from_item() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op in ('UPDATE', 'DELETE') then
    perform internal.skill_level_question_type_sync(old.tenant_id, old.skill_set_code, old.difficulty);
  end if;
  if tg_op in ('INSERT', 'UPDATE')
     and (tg_op = 'INSERT' or row(new.skill_set_code, new.difficulty) is distinct from row(old.skill_set_code, old.difficulty)) then
    perform internal.skill_level_question_type_sync(new.tenant_id, new.skill_set_code, new.difficulty);
  end if;
  return null;
end $$;

drop trigger if exists skill_level_question_type_on_item on item;
create trigger skill_level_question_type_on_item after insert or delete or update of status, fmt, template, source,
  skill_set_code, difficulty on item for each row execute function internal.skill_level_question_type_from_item();

create or replace function internal.skill_level_question_type_from_skill_set() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_level_question_type_sync(l.tenant_id, l.skill_code, l.difficulty)
  from skill_level l where l.tenant_id = new.tenant_id and l.skill_code = new.code;
  return null;
end $$;

drop trigger if exists skill_level_question_type_on_skill_set on skill_set;
create trigger skill_level_question_type_on_skill_set after update of formats on skill_set
  for each row when (old.formats is distinct from new.formats)
  execute function internal.skill_level_question_type_from_skill_set();

-- A new level (B1's trigger made its row after the skill's) takes the links its questions already hold.
create or replace function internal.skill_level_question_type_from_skill_level() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_level_question_type_sync(new.tenant_id, new.skill_code, new.difficulty);
  return null;
end $$;

drop trigger if exists skill_level_question_type_on_skill_level on skill_level;
create trigger skill_level_question_type_on_skill_level after insert on skill_level
  for each row execute function internal.skill_level_question_type_from_skill_level();

create or replace function internal.skill_level_question_type_from_type() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_level_question_type_sync_all();
  return null;
end $$;

drop trigger if exists skill_level_question_type_on_type on question_type;
create trigger skill_level_question_type_on_type after insert or delete or update of code, fmt on question_type
  for each statement execute function internal.skill_level_question_type_from_type();

-- What a paper may draw: an active question, at a confirmed level, of an approved type. Every draw reads this.
create or replace view drawable_item with (security_invoker = true) as
  select i.*, question_type_of(i.fmt, i.template) as question_type
  from item i
  join skill_level l on l.tenant_id = i.tenant_id and l.skill_code = i.skill_set_code and l.difficulty = i.difficulty
  where i.status = 'active' and l.confirmed_at is not null
    and exists (select 1 from question_type_approval a
                where a.tenant_id = i.tenant_id and a.question_type = question_type_of(i.fmt, i.template));

-- The day B2 ships, no paper that can be made is refused (decided, 2026-10-21): every type already on a paper —
-- printed, or on a library worksheet in use — or at levels all already confirmed starts approved. A type in use nowhere
-- waits. Run once by this migration; the tests call it to check the rule.
create or replace function internal.question_types_start_approved() returns void
language sql security definer set search_path = public as $$
  with used as (
    select i.tenant_id, question_type_of(i.fmt, i.template) as code, i.skill_set_code, i.difficulty, i.id
    from item i where i.status = 'active' and i.source = 'generated'
  ), on_paper as (
    select distinct u.tenant_id, u.code from used u
    where exists (select 1 from sheet_template t where t.tenant_id = u.tenant_id and u.id = any(t.item_ids)
                  and (t.retired_at is null and t.source = 'library'
                       or exists (select 1 from sheet_instance si where si.sheet_template_id = t.id)))
  ), confirmed as (
    select u.tenant_id, u.code from used u
    left join skill_level l on l.tenant_id = u.tenant_id and l.skill_code = u.skill_set_code and l.difficulty = u.difficulty
    group by 1, 2 having bool_and(l.confirmed_at is not null)
  )
  insert into question_type_approval (tenant_id, question_type, approved_by)
  select x.tenant_id, x.code, 'in use before B2 (2026-10-21)'
  from (select * from on_paper union select * from confirmed) x
  join question_type q on q.tenant_id = x.tenant_id and q.code = x.code
  on conflict (tenant_id, question_type) do nothing
$$;

-- Live's types as its bank holds them, by ADR 0077's rule; `engine load` then gives each its words, how it reaches the
-- child, and adds the seed's. A fresh database holds no question yet, and takes its types from the seed alone.
insert into question_type (tenant_id, code, fmt, words, marked)
select i.tenant_id,
       case when i.template ~ '^(ADD|SUB|MUL|DIV)\.(\dD\dD(\.REG\w*)?|MULTI\d*)$' then i.fmt else i.template end,
       min(i.fmt), replace(min(i.fmt), '_', ' '), array_agg(distinct i.eval_type)
from item i where i.source = 'generated'
group by 1, 2
on conflict (tenant_id, code) do nothing;

select internal.skill_level_question_type_sync_all();
select internal.question_types_start_approved();

select internal.apply_conventions();

-- Approvals are given, never edited: the engine and the website may add one, not change or remove it.
do $$
begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    revoke update, delete, truncate on question_type_approval from app_web, app_engine;
    revoke insert, update, delete, truncate on skill_level_question_type from app_web, app_engine;
  end if;
end $$;
