-- The curriculum published as numbered versions (goals/c3-the-curriculum-in-numbered-versions.yaml, the locked scope of
-- 22 Oct, slice C3): every new result names its version; an edit takes effect from the next week.
--
-- A skill already keeps its own history (`skill_set_version`, one row for each rule it has had, its `version` the
-- current one). What the school had not was the curriculum as a whole, at a moment: "version 7" meaning these skills
-- at these versions. Now:
--   curriculum_version        one row a publish, numbered 1, 2, 3 … for a school; who published it, when, and the
--                             Monday it takes effect: the week after it was published, in the school's own day
--   curriculum_version_skill  every skill and the version it was at when published
-- Both are a record, never edited (rule 4's way). `publish_curriculum` makes one; `curriculum_in_force` says which is
-- in force on a day: the newest whose Monday has come. A scored answer and an evidence record name the version in
-- force when they were written, by themselves; a past row names none, and is not touched.
--
-- Version 1 is the curriculum as it stands when this runs, in force from this week's Monday, so a result written from
-- today names it and nothing a child is given this week changes. A school with no skill yet begins at its first load.
--
-- The school's time zone is a row (`config` school.time_zone), as its week begins on its own Monday.
--
-- Written to run twice.

create table if not exists curriculum_version (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  number        int not null check (number > 0),
  published_by  text not null check (btrim(published_by) <> ''),
  published_at  timestamptz not null default now(),
  takes_effect  date not null,             -- a Monday: the week after it was published
  note          text not null default '',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (tenant_id, number),
  check (extract(isodow from takes_effect) = 1)
);

create table if not exists curriculum_version_skill (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references tenant(id) on delete cascade,
  curriculum_version_id  uuid not null references curriculum_version (id) on delete cascade,
  skill_code             text not null,
  skill_version          int not null,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  unique (curriculum_version_id, skill_code)
);
create index if not exists curriculum_version_skill_skill_idx on curriculum_version_skill (tenant_id, skill_code);

drop trigger if exists curriculum_version_kept on curriculum_version;
create trigger curriculum_version_kept before update or delete on curriculum_version
  for each statement execute function internal.forbid_change();
drop trigger if exists curriculum_version_skill_kept on curriculum_version_skill;
create trigger curriculum_version_skill_kept before update or delete on curriculum_version_skill
  for each statement execute function internal.forbid_change();

-- The school's own day at a moment, by its own clock.
create or replace function internal.school_day(p_tenant uuid, p_at timestamptz) returns date
language sql stable security definer set search_path = public as $$
  select (p_at at time zone (select value #>> '{}' from config where tenant_id = p_tenant and key = 'school.time_zone'))::date
$$;

-- Publish the curriculum as it stands: the next number, every skill at its version, in force from next Monday.
create or replace function public.publish_curriculum(p_tenant uuid, p_by text, p_note text default '',
                                                     p_at timestamptz default now())
returns int language plpgsql security definer set search_path = public as $$
declare
  n int;
  v uuid;
begin
  perform pg_advisory_xact_lock(hashtext('publish_curriculum'), hashtext(p_tenant::text));
  select coalesce(max(number), 0) + 1 into n from curriculum_version where tenant_id = p_tenant;
  insert into curriculum_version (tenant_id, number, published_by, published_at, takes_effect, note)
  values (p_tenant, n, p_by, p_at, date_trunc('week', internal.school_day(p_tenant, p_at))::date + 7, p_note)
  returning id into v;
  insert into curriculum_version_skill (tenant_id, curriculum_version_id, skill_code, skill_version)
  select p_tenant, v, s.code, s.version from skill s where s.tenant_id = p_tenant;
  return n;
end $$;

-- The version in force on a moment's day: the newest whose Monday has come.
create or replace function public.curriculum_in_force(p_tenant uuid, p_at timestamptz default now()) returns int
language sql stable security definer set search_path = public as $$
  select max(number) from curriculum_version
  where tenant_id = p_tenant and takes_effect <= internal.school_day(p_tenant, p_at)
$$;

-- A school's clock, and its version 1: the curriculum as it stands, in force from this week's Monday. For every
-- school, there now or added later.
create or replace function public.curriculum_begins(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
declare
  v uuid;
begin
  insert into config (tenant_id, key, value, description)
  values (p_tenant, 'school.time_zone', '"Asia/Kolkata"',
          'The school''s own clock: its day and its week, which a published curriculum takes effect from (C3).')
  on conflict (tenant_id, key) do nothing;
  -- a school with no skill yet (one just added, a database just built) begins at its first load (`engine load`)
  if exists (select 1 from curriculum_version where tenant_id = p_tenant)
     or not exists (select 1 from skill where tenant_id = p_tenant) then
    return;
  end if;
  insert into curriculum_version (tenant_id, number, published_by, takes_effect, note)
  values (p_tenant, 1, 'the curriculum as it stood (C3)', date_trunc('week', internal.school_day(p_tenant, now()))::date,
          'Every skill as it stood when versions began.')
  returning id into v;
  insert into curriculum_version_skill (tenant_id, curriculum_version_id, skill_code, skill_version)
  select p_tenant, v, s.code, s.version from skill s where s.tenant_id = p_tenant;
end $$;

create or replace function internal.curriculum_begins_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform public.curriculum_begins(new.id);
  return new;
end $$;

drop trigger if exists curriculum_begins on tenant;
create trigger curriculum_begins after insert on tenant
  for each row execute function internal.curriculum_begins_on_new_school();

select public.curriculum_begins(id) from tenant;

-- Every new result names the version in force when it was written; a past row names none.
alter table item_result add column if not exists curriculum_version int;
alter table evidence_event add column if not exists curriculum_version int;
alter table item_result drop constraint if exists item_result_tenant_id_curriculum_version_fkey;
alter table item_result add constraint item_result_tenant_id_curriculum_version_fkey
  foreign key (tenant_id, curriculum_version) references curriculum_version (tenant_id, number);
alter table evidence_event drop constraint if exists evidence_event_tenant_id_curriculum_version_fkey;
alter table evidence_event add constraint evidence_event_tenant_id_curriculum_version_fkey
  foreign key (tenant_id, curriculum_version) references curriculum_version (tenant_id, number);

create or replace function internal.result_names_its_curriculum() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.curriculum_version := coalesce(new.curriculum_version, curriculum_in_force(new.tenant_id, now()));
  return new;
end $$;

drop trigger if exists item_result_curriculum on item_result;
create trigger item_result_curriculum before insert on item_result
  for each row execute function internal.result_names_its_curriculum();
drop trigger if exists evidence_event_curriculum on evidence_event;
create trigger evidence_event_curriculum before insert on evidence_event
  for each row execute function internal.result_names_its_curriculum();

select internal.apply_conventions();
