-- A class is taught skill by skill (goals/t1-topics-are-operations.yaml, ADR 0076). Nimish, 2026-10-15: "These are
-- types of problems. The topics are core addition, subtraction, multiplication, division, and factors." The topics
-- become six, by operation, and one of them now holds what were several: Multiplication holds equal groups (taught
-- in Grade 1) and columns (not yet taught in Grade 3). So the word "taught" moves from the topic to the skill:
--
--   the school's word on a skill   skill_set.taught, with who said it (null: the rows', which every load says again)
--   a class's word on a skill      class_skill, with who said it and when
--
-- `skill_taught_in` is the one rule: the class's word, else the school's. A topic is taught in a class when any of
-- its skills is (`taught_in`, the same name and arguments as before). Switching a topic for a class says it of every
-- skill in the topic; a person can then say one skill otherwise (`say_taught`).
--
-- Nothing on a paper changes on the day. Before any skill moves topic (the load after this migration moves them),
-- every word said on a topic is written onto each skill the topic holds now: the school's (`topic.taught`) and each
-- class's (`class_topic`). `class_topic` and `topic.taught` are then read by nothing; they stay for the website still
-- live until this commit's is, and go with the next migration.
--
-- Written to run twice.

alter table skill_set add column if not exists taught boolean not null default false;
alter table skill_set add column if not exists taught_by text;
alter table skill_set add column if not exists taught_at timestamptz;
alter table skill_set drop constraint if exists skill_set_taught_by_a_person;
alter table skill_set add constraint skill_set_taught_by_a_person check ((taught_by is null) = (taught_at is null));

create table if not exists class_skill (
  tenant_id       uuid not null references tenant(id) on delete cascade,
  section         text not null,
  skill_set_code  text not null,
  taught          boolean not null,
  taught_by       text not null,
  taught_at       timestamptz not null default now(),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  primary key (tenant_id, section, skill_set_code),
  foreign key (tenant_id, skill_set_code) references skill_set (tenant_id, code) on delete cascade
);

-- every word said on a topic, onto each skill it holds: the school's (a person's stays theirs; the rows' stays the
-- rows', said again by the next load) and each class's, unless a word is already said of the skill itself
create or replace function internal.topic_words_to_skills() returns void
language sql security definer set search_path = public as $$
  update skill_set s set taught = t.taught, taught_by = t.taught_by, taught_at = t.taught_at
  from topic t
  where t.tenant_id = s.tenant_id and t.code = s.topic_code and s.taught_by is null;

  insert into class_skill (tenant_id, section, skill_set_code, taught, taught_by, taught_at)
  select ct.tenant_id, ct.section, s.code, ct.taught, ct.taught_by, ct.taught_at
  from class_topic ct
  join skill_set s on s.tenant_id = ct.tenant_id and s.topic_code = ct.topic_code
  on conflict (tenant_id, section, skill_set_code) do nothing;
$$;

select internal.topic_words_to_skills();

-- this class's word on the skill, else the school's
create or replace function public.skill_taught_in(tenant uuid, skill text, section text) returns boolean
language sql stable as $$
  select coalesce(
    (select cs.taught from class_skill cs where cs.tenant_id = $1 and cs.skill_set_code = $2 and cs.section = $3),
    (select s.taught from skill_set s where s.tenant_id = $1 and s.code = $2),
    false)
$$;

-- a topic is taught in a class when any of its skills is
create or replace function public.taught_in(tenant uuid, topic text, section text) returns boolean
language sql stable as $$
  select exists (
    select 1 from skill_set s
    where s.tenant_id = $1 and s.topic_code = $2 and public.skill_taught_in($1, s.code, $3))
$$;

-- a person says a class has (or has not) been taught a topic — every skill in it — or, with `skill`, one skill of it.
-- A class no active child is in is no class: nothing is said. Returns how many skills were said.
create or replace function public.say_taught(tenant uuid, section text, topic text, skill text, taught boolean,
                                             said_by text) returns integer
language sql security definer set search_path = public as $$
  with said as (
    insert into class_skill (tenant_id, section, skill_set_code, taught, taught_by, taught_at)
    select s.tenant_id, $2, s.code, $5, $6, now()
    from skill_set s
    where s.tenant_id = $1 and s.topic_code = $3 and ($4 is null or s.code = $4)
      and exists (select 1 from child c where c.tenant_id = $1 and c.section = $2 and c.active)
    on conflict (tenant_id, section, skill_set_code)
    do update set taught = excluded.taught, taught_by = excluded.taught_by, taught_at = excluded.taught_at,
                  updated_at = now()
    returning 1)
  select count(*)::int from said
$$;

-- the website says a word only through `say_taught`; the old table is no longer its to write
revoke insert, update on class_topic from app_web;
grant execute on function public.skill_taught_in(uuid, text, text) to app_web;
grant execute on function public.taught_in(uuid, text, text) to app_web;
grant execute on function public.say_taught(uuid, text, text, text, boolean, text) to app_web;

select internal.apply_conventions();
