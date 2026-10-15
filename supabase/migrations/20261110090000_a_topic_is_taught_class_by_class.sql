-- A topic is taught class by class (goals/f1f-taught-per-class.yaml, ADR 0073 D5). Nimish, 2026-10-14: "people who
-- are there for one thing like educator only see something that's relevant for their class and their students."
-- Whether a topic was taught was one switch for the school (`topic.taught`): switching multiplication on for Grade 3
-- switched it on for Grade 1.
--
-- Each class (a `child.section`) now has its own word on a topic, with who said it and when: an educator's for their
-- own classes, the coordinator's for any. A class no one has spoken for follows the school's switch — the rows', until
-- a person switched it — so nothing changes on the day, and a class the roll brings later starts where the school is.
-- `taught_in` is the one rule, read by the engine and the site alike.
--
-- Written to run twice.

create table if not exists class_topic (
  tenant_id   uuid not null references tenant(id) on delete cascade,
  section     text not null,
  topic_code  text not null,
  taught      boolean not null,
  taught_by   text not null,
  taught_at   timestamptz not null default now(),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (tenant_id, section, topic_code),
  foreign key (tenant_id, topic_code) references topic (tenant_id, code) on delete cascade
);
grant insert on class_topic to app_web;
grant update (taught, taught_by, taught_at) on class_topic to app_web;

-- this class's word on the topic, else the school's switch
create or replace function public.taught_in(tenant uuid, topic text, section text) returns boolean
language sql stable as $$
  select coalesce(
    (select ct.taught from class_topic ct where ct.tenant_id = $1 and ct.topic_code = $2 and ct.section = $3),
    (select t.taught from topic t where t.tenant_id = $1 and t.code = $2),
    false)
$$;
grant execute on function public.taught_in(uuid, text, text) to app_web;

select internal.apply_conventions();
