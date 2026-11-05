-- M1-15: a prerequisite link between two skills holds its reason and who confirmed it, and nothing reads a link nobody
-- confirmed (goals/m1-15-skill-links.yaml). Nimish, approved 2026-11-04.
--
-- Two tables hold links, because there are two spaces of skills:
--   skill_link          between the BROAD skills (registry_skill: the ones evidence_event.skill_code points at and K2's
--                       observations use). New. Nothing is in it until a person's list is loaded.
--   skill_prerequisite  between the maths micro-steps (skill). Exists, 282 rows, drafted by a grade rule ("a skill after
--                       every skill of its topic on the nearest grade below") and the English foundation; no person has
--                       checked one. It gains the same words, and every row it holds is marked PROPOSED.
-- A link is proposed until a member of staff confirms it, and the confirmation keeps who and when. The two views
-- (skill_link_confirmed, skill_prerequisite_confirmed) show confirmed links only; every reader goes through them.
-- skill_prerequisite_audit and skill_link_audit show every row, whatever its status, for the checks that count them.
--
-- Strength (hard | soft) and status (proposed | confirmed) are vocabulary rows, not lists in a check, as the repo keeps its
-- other words (evidence_scale, approval_state). Written to run twice. No row is deleted; DELETE is revoked on the new
-- tables, and left as it was on skill_prerequisite (a test deletes from it).

create table if not exists link_strength (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  ord         int not null,
  words       text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

-- `confirmed` says whether a link in this state has been confirmed by a person: the views and the confirmation trigger
-- read it, so neither names a state.
create table if not exists link_status (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  ord         int not null,
  words       text not null,
  confirmed   boolean not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create or replace function internal.skill_link_vocabulary(p_tenant uuid) returns void
language plpgsql as $$
begin
  insert into link_strength (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values
    ('hard', 0, 'a child needs the first before the second'),
    ('soft', 1, 'the first helps with the second, but is not needed')
  ) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;

  insert into link_status (tenant_id, code, ord, words, confirmed)
  select p_tenant, v.code, v.ord, v.words, v.confirmed
  from (values
    ('proposed', 0, 'proposed, not yet checked by a person', false),
    ('confirmed', 1, 'confirmed by a member of staff', true)
  ) v (code, ord, words, confirmed)
  on conflict (tenant_id, code) do nothing;
end $$;

create or replace function internal.skill_link_vocabulary_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_link_vocabulary(new.id);
  return new;
end $$;

drop trigger if exists skill_link_vocabulary on tenant;
create trigger skill_link_vocabulary after insert on tenant
  for each row execute function internal.skill_link_vocabulary_on_new_school();

select internal.skill_link_vocabulary(id) from tenant;

-- The links between broad skills.
create table if not exists skill_link (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  skill_code    text not null,                       -- the skill that comes after
  before_code   text not null,                       -- the skill a child meets first
  strength      text not null default 'hard',
  reason        text not null check (btrim(reason) <> ''),   -- one line, in the school's words
  source        text not null check (btrim(source) <> ''),   -- where the link came from: a list, a person, a seed
  status        text not null default 'proposed',
  confirmed_by  uuid references staff(id),
  confirmed_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (tenant_id, skill_code, before_code),
  foreign key (tenant_id, skill_code) references registry_skill (tenant_id, code) on update cascade,
  foreign key (tenant_id, before_code) references registry_skill (tenant_id, code) on update cascade,
  foreign key (tenant_id, strength) references link_strength (tenant_id, code) on update cascade,
  foreign key (tenant_id, status) references link_status (tenant_id, code) on update cascade,
  constraint skill_link_not_itself check (skill_code <> before_code)
);

-- The micro-step prerequisites gain the same words. Every row already there was drafted, so each is proposed, from the
-- seed; none is confirmed (no person has checked one). Strength 'soft': a grade rule cannot say a step is needed.
alter table skill_prerequisite
  add column if not exists strength     text not null default 'soft',
  add column if not exists reason       text,
  add column if not exists source       text,
  add column if not exists status       text not null default 'proposed',
  add column if not exists confirmed_by uuid references staff(id),
  add column if not exists confirmed_at timestamptz;

update skill_prerequisite p
set source = 'seed rule',
    reason = case
      when exists (select 1 from skill s join topic o on o.tenant_id = s.tenant_id and o.code = s.topic_code
                   where s.tenant_id = p.tenant_id and s.code = p.skill_code and o.subject_code = 'ENG')
        then 'drafted with the English foundation, not yet checked by the English educator'
      else 'drafted by a grade rule: a skill after every skill of its topic on the nearest grade below'
    end
where p.source is null;

alter table skill_prerequisite alter column reason set not null;
alter table skill_prerequisite alter column source set not null;
alter table skill_prerequisite drop constraint if exists skill_prerequisite_reason_check;
alter table skill_prerequisite add constraint skill_prerequisite_reason_check check (btrim(reason) <> '');
alter table skill_prerequisite drop constraint if exists skill_prerequisite_source_check;
alter table skill_prerequisite add constraint skill_prerequisite_source_check check (btrim(source) <> '');
alter table skill_prerequisite drop constraint if exists skill_prerequisite_tenant_id_strength_fkey;
alter table skill_prerequisite add constraint skill_prerequisite_tenant_id_strength_fkey
  foreign key (tenant_id, strength) references link_strength (tenant_id, code) on update cascade;
alter table skill_prerequisite drop constraint if exists skill_prerequisite_tenant_id_status_fkey;
alter table skill_prerequisite add constraint skill_prerequisite_tenant_id_status_fkey
  foreign key (tenant_id, status) references link_status (tenant_id, code) on update cascade;

-- A link in a confirming state names the person and the time; one in any other state names neither. Shared by both tables.
create or replace function internal.skill_link_confirmation() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  counts boolean;
begin
  select confirmed into counts from link_status where tenant_id = new.tenant_id and code = new.status;
  if coalesce(counts, false) then
    if new.confirmed_by is null then
      raise exception 'a confirmed link names the member of staff who confirmed it' using errcode = 'check_violation';
    end if;
    new.confirmed_at := coalesce(new.confirmed_at, now());
  elsif new.confirmed_by is not null or new.confirmed_at is not null then
    raise exception 'a link nobody confirmed names no one who did' using errcode = 'check_violation';
  end if;
  return new;
end $$;

drop trigger if exists skill_link_confirmation on skill_link;
create trigger skill_link_confirmation before insert or update on skill_link
  for each row execute function internal.skill_link_confirmation();
drop trigger if exists skill_prerequisite_confirmation on skill_prerequisite;
create trigger skill_prerequisite_confirmation before insert or update on skill_prerequisite
  for each row execute function internal.skill_link_confirmation();

-- No skill comes before itself, however long the way round: the pattern of internal.skill_prerequisite_no_circle, on the
-- broad skills. It counts proposed links too, so a ring is refused when it is proposed, not found when it is confirmed.
create or replace function internal.skill_link_no_circle() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (
    with recursive before(code) as (
      select new.before_code
      union
      select l.before_code from skill_link l join before b on l.tenant_id = new.tenant_id and l.skill_code = b.code
    ) select 1 from before where code = new.skill_code
  ) then
    raise exception 'skill % would come before itself through %', new.skill_code, new.before_code
      using errcode = 'check_violation';
  end if;
  return null;
end $$;

drop trigger if exists skill_link_no_circle on skill_link;
create constraint trigger skill_link_no_circle after insert or update of tenant_id, skill_code, before_code on skill_link
  for each row execute function internal.skill_link_no_circle();

-- What a reader sees: confirmed links only.
create or replace view skill_link_confirmed with (security_invoker = true) as
  select l.id, l.tenant_id, l.skill_code, l.before_code, l.strength, l.reason, l.source, l.confirmed_by, l.confirmed_at
  from skill_link l join link_status s on s.tenant_id = l.tenant_id and s.code = l.status
  where s.confirmed;

create or replace view skill_prerequisite_confirmed with (security_invoker = true) as
  select p.id, p.tenant_id, p.skill_code, p.before_code, p.strength, p.reason, p.source, p.confirmed_by, p.confirmed_at
  from skill_prerequisite p join link_status s on s.tenant_id = p.tenant_id and s.code = p.status
  where s.confirmed;

-- Every row of each table, whatever its status: for the checks that count them and look for a ring (engine links check,
-- the M1-15 scenario). No feature reads these; a test names the files that may.
create or replace view skill_prerequisite_audit with (security_invoker = true) as
  select id, tenant_id, skill_code, before_code, strength, reason, source, status, confirmed_by, confirmed_at, created_at
  from skill_prerequisite;

create or replace view skill_link_audit with (security_invoker = true) as
  select id, tenant_id, skill_code, before_code, strength, reason, source, status, confirmed_by, confirmed_at, created_at
  from skill_link;

-- Loading a person's pair, and confirming a link. Each is one fixed function, so the engine's commands hold no SQL of
-- their own about these tables. A pair already there is left as it is (never unconfirmed, never reworded).
create or replace function public.propose_skill_link(
  p_tenant uuid, p_before text, p_after text, p_reason text, p_source text, p_strength text default 'hard'
) returns text language plpgsql as $$
declare
  made integer;
begin
  insert into skill_link (tenant_id, skill_code, before_code, strength, reason, source)
  values (p_tenant, p_after, p_before, p_strength, p_reason, p_source)
  on conflict (tenant_id, skill_code, before_code) do nothing;
  get diagnostics made = row_count;
  return case when made = 1 then 'added' else 'there' end;
end $$;

-- 'confirmed', 'already' (someone confirmed it first: their word stands), 'no link', 'not staff' or 'no confirming state'. A member of staff of
-- the link's own school who is still active; the link is looked for among both tables (an id is unique across them).
create or replace function public.confirm_skill_link(p_id uuid, p_staff uuid) returns text
language plpgsql as $$
declare
  school uuid;
  word text;
  found boolean;
begin
  select tenant_id into school from staff where id = p_staff and active;
  if school is null then
    return 'not staff';
  end if;
  select code into word from link_status where tenant_id = school and confirmed order by ord limit 1;
  if word is null then
    return 'no confirming state';
  end if;
  if exists (select 1 from skill_link where id = p_id and tenant_id = school) then
    update skill_link l set status = word, confirmed_by = p_staff, confirmed_at = now()
    where l.id = p_id and not exists (select 1 from link_status s where s.tenant_id = l.tenant_id and s.code = l.status and s.confirmed);
    get diagnostics found = row_count;
  elsif exists (select 1 from skill_prerequisite where id = p_id and tenant_id = school) then
    update skill_prerequisite l set status = word, confirmed_by = p_staff, confirmed_at = now()
    where l.id = p_id and not exists (select 1 from link_status s where s.tenant_id = l.tenant_id and s.code = l.status and s.confirmed);
    get diagnostics found = row_count;
  else
    return 'no link';
  end if;
  return case when found then 'confirmed' else 'already' end;
end $$;

do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert, update on skill_link, link_strength, link_status to app_engine;
    grant select on skill_link_confirmed, skill_prerequisite_confirmed, skill_prerequisite_audit, skill_link_audit to app_engine;
    revoke delete on skill_link, link_strength, link_status from app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on skill_link, link_strength, link_status to app_web;
    grant select on skill_link_confirmed, skill_prerequisite_confirmed to app_web;
    revoke delete on skill_link, link_strength, link_status from app_web;
  end if;
end $$;

select internal.apply_conventions();
