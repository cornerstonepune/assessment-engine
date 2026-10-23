-- Every question names its skills in the registry, one or several; a mixed question says which step tests which skill
-- (goals/c1-questions-name-their-skills.yaml, the locked scope of 22 Oct, slice C1).
--
-- A question carried its registry skills as a list of words (`item.skill_codes`, a copy of its skill's list) and a
-- legacy one its own in `spec ->> 'skill'`; results count the first that is there (graph_functions: `coalesce(spec ->>
-- 'skill', skill_codes[1])`). Nothing checked either against the registry, and nothing could say that one question
-- tests two skills, or where. Now:
--   item_registry_skill   one row per skill a question tests, a real key to `registry_skill`; a mixed question's rows
--                         each name the step (its number and its words) that tests the skill
-- Every question starts with the one skill its results already count, so no result changes. A question written later
-- gets the same row by itself; whoever writes a mixed one writes its steps, and the database refuses, at commit, a
-- question with no skill, or with two skills and a row that names no step.
--
-- Also, at its cause, E0's named fragility (PR #284): writing any question type re-made every level's links from the
-- bank alone, so a level's kinds the curriculum names but the bank does not yet hold (English, all of it) vanished
-- until the next `engine load`. A link now says whether the curriculum declared it; the bank adds and removes only its
-- own.
--
-- And B4b's `skill_set` view, kept for the one deploy in which B4's code might still run, goes (B4b: "the next schema
-- slice drops it").
--
-- Written to run twice.

create table if not exists item_registry_skill (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  item_id         uuid not null references item (id) on delete cascade,
  registry_skill  text not null,
  step            smallint check (step > 0),            -- a mixed question's step that tests this skill
  step_words      text check (btrim(step_words) <> ''), -- that step, in the school's words
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check ((step is null) = (step_words is null)),
  foreign key (tenant_id, registry_skill) references registry_skill (tenant_id, code) on update cascade
);
create unique index if not exists item_registry_skill_one_skill on item_registry_skill (item_id, registry_skill)
  where step is null;
create unique index if not exists item_registry_skill_one_step on item_registry_skill (item_id, step)
  where step is not null;
create index if not exists item_registry_skill_item_idx on item_registry_skill (item_id);
create index if not exists item_registry_skill_registry_idx on item_registry_skill (tenant_id, registry_skill);

-- The skill a question's results already count: its own (a legacy question's), else its skill's first.
create or replace function internal.item_own_registry_skill(p_spec jsonb, p_skill_codes text[]) returns text
language sql immutable as $$
  select coalesce($1 ->> 'skill', $2[1])
$$;

insert into item_registry_skill (tenant_id, item_id, registry_skill)
select i.tenant_id, i.id, internal.item_own_registry_skill(i.spec, i.skill_codes)
from item i
where not exists (select 1 from item_registry_skill x where x.item_id = i.id);

-- A question written later names the same skill by itself; a mixed one's writer then writes its steps. A question
-- whose own skill is written again (a legacy question imported again) moves its row with it.
create or replace function internal.item_registry_skill_from_item() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    insert into item_registry_skill (tenant_id, item_id, registry_skill)
    values (new.tenant_id, new.id, internal.item_own_registry_skill(new.spec, new.skill_codes));
  elsif internal.item_own_registry_skill(new.spec, new.skill_codes)
        is distinct from internal.item_own_registry_skill(old.spec, old.skill_codes) then
    update item_registry_skill set registry_skill = internal.item_own_registry_skill(new.spec, new.skill_codes)
    where item_id = new.id and step is null
      and registry_skill = internal.item_own_registry_skill(old.spec, old.skill_codes);
  end if;
  return null;
end $$;

drop trigger if exists item_registry_skill_on_item on item;
create trigger item_registry_skill_on_item after insert or update of spec, skill_codes on item
  for each row execute function internal.item_registry_skill_from_item();

-- At commit: a question names at least one skill, and a mixed one names the step of every skill it tests.
create or replace function internal.item_registry_skill_check() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  q uuid := coalesce(new.item_id, old.item_id);
  n_skills int;
  n_unstepped int;
begin
  if not exists (select 1 from item where id = q) then
    return null;
  end if;
  select count(distinct registry_skill), count(*) filter (where step is null)
  into n_skills, n_unstepped from item_registry_skill where item_id = q;
  if n_skills = 0 then
    raise exception 'question % names no registry skill', q using errcode = 'check_violation';
  end if;
  if n_skills > 1 and n_unstepped > 0 then
    raise exception 'question % tests % registry skills, and % of its rows names no step', q, n_skills, n_unstepped
      using errcode = 'check_violation';
  end if;
  return null;
end $$;

drop trigger if exists item_registry_skill_checked on item_registry_skill;
create constraint trigger item_registry_skill_checked after insert or update or delete on item_registry_skill
  deferrable initially deferred for each row execute function internal.item_registry_skill_check();

-- E0's fragility, at its cause: the bank adds and removes only the links it holds; a declared one stays.
alter table skill_level_question_type add column if not exists declared boolean;
update skill_level_question_type l set declared = not exists (
  select 1 from item i where i.tenant_id = l.tenant_id and i.skill_set_code = l.skill_code
    and i.difficulty = l.difficulty and i.status = 'active' and i.source = 'generated'
    and question_type_of(i.fmt, i.template) = l.question_type)
where l.declared is null;
alter table skill_level_question_type alter column declared set default true;
alter table skill_level_question_type alter column declared set not null;

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
    where l.tenant_id = p_tenant and l.skill_code = p_skill and l.difficulty = p_level and not l.declared
      and not exists (select 1 from held h where h.code = l.question_type)
  )
  insert into skill_level_question_type as l (tenant_id, skill_code, difficulty, question_type, place, declared)
  select p_tenant, p_skill, p_level, h.code, array_position(s.formats, h.fmt) - 1, false
  from held h join skill_level sl on sl.tenant_id = p_tenant and sl.skill_code = p_skill and sl.difficulty = p_level
  join skill s on s.tenant_id = p_tenant and s.code = p_skill
  on conflict (tenant_id, skill_code, difficulty, question_type) do update set place = excluded.place
    where l.place is distinct from excluded.place;
end $$;

drop view if exists skill_set;

select internal.apply_conventions();
