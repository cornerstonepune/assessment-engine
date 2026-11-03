-- People and enrolment, first slice (goals/m0-05-people-enrolment.yaml; task M0-05; decisions D-026, D-039, D-046, D-047, D-055).
-- The system knows who a member of staff is, which class they teach, and which children are in that class.
--
--   * `campus`, `academic_year`, `school_class`: where and when a class is: one campus, one school year, one grade, one
--     section (K2-A in 2026-27 and in 2027-28 are two rows). The grade is a row of `grade`.
--   * `enrolment`: the only link between a child and a class. A move closes one row (`to_date`) and opens another, so a
--     child's history of classes is kept. At most one open row per child, and one open row per roll number in a class.
--     `enrol_child()` is the one place that does the closing and opening. `child.section`/`roll_no` are untouched: the
--     existing pages still read them (moving them into enrolment is a later slice).
--   * `staff`, `pii.staff`: a person is an id and a campus; their name, email and phone are in `pii` and nowhere else
--     (rule 6). The website's sign-in list (`config` key app.staff) is untouched and stays the master of passwords.
--   * `role`: a kind of job (D-026) as a row: its words, its scope (campus, class, class and subject, or child) and which
--     roles may give it. A new role is an insert. `staff_role_grant`: one person holding one role for one scope from a date
--     to a date; it is never deleted, it ends (`valid_to`).
--   * The checks on a grant are one trigger: the scope fits the role; the same person does not hold the same thing twice;
--     a class has one class teacher at a time; and D-039, from Grade 1 a core-subject teacher is not a class teacher
--     (config row `people.class_teacher_rule`). The last two warn: the grant stands only with an `override_reason`, which
--     stays on the grant.
--   * `pii.child.birthday`: the class list carries one; it is a child's personal data, so it is beside the name.
--   * `pii.read_staff()`: a staff member's name, email and phone, only through this, which writes who asked to `access_log`.
--   * `public.staff_of_email()`: the staff id of a signed-in email (never a name), logged the same way; for M1-01. Engine only.
--
-- Not here: who may see which class (per-person access rules need a proven way to carry the signed-in staff id on one
-- database login first, ADR 0024; `internal.apply_conventions()` still gives both app roles `using (true)`), enforcing
-- `may_grant` (the grant's `granted_by` is still the typed name, not a staff id), `internal.grants_now()`, and
-- `move_child` writing an enrolment.
-- btree_gist is not needed: "one open row" is a partial unique index, and one class teacher at a time is the trigger.
--
-- ADDITIVE ONLY: no existing table is read or written differently, nothing is dropped, deleted or rewritten. Written to
-- run twice.

alter table pii.child add column if not exists birthday date;

create table if not exists campus (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  name       text not null check (btrim(name) <> ''),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, name)
);

create table if not exists academic_year (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  label      text not null check (label ~ '^[0-9]{4}-[0-9]{2}$'),
  starts_on  date not null,
  ends_on    date not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ends_on > starts_on),
  unique (tenant_id, label)
);

create table if not exists school_class (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references tenant(id) on delete cascade,
  campus_id        uuid not null references campus(id),
  academic_year_id uuid not null references academic_year(id),
  grade_code       text not null,
  section          text not null check (btrim(section) <> ''),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  foreign key (tenant_id, grade_code) references grade (tenant_id, code),
  unique (tenant_id, campus_id, academic_year_id, grade_code, section)
);

create table if not exists enrolment (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  child_id    uuid not null references child(id),
  class_id    uuid not null references school_class(id),
  roll_no     text not null check (roll_no ~ '^[A-Za-z0-9-]{1,8}$'),
  from_date   date not null,
  to_date     date,
  recorded_by text not null check (btrim(recorded_by) <> ''),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (to_date is null or to_date >= from_date)
);
create unique index if not exists enrolment_one_open_per_child on enrolment (child_id) where to_date is null;
create unique index if not exists enrolment_one_open_roll_per_class on enrolment (class_id, roll_no) where to_date is null;
create index if not exists enrolment_class_idx on enrolment (class_id) where to_date is null;

create table if not exists staff (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  campus_id  uuid not null references campus(id),
  active     boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pii.staff (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references public.tenant(id) on delete cascade,
  staff_id   uuid not null references public.staff(id) on delete cascade,
  name       text not null check (btrim(name) <> ''),
  email      text not null check (email = lower(btrim(email)) and email like '%_@_%._%'),
  phone      text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, staff_id)
);
create unique index if not exists pii_staff_email_idx on pii.staff (tenant_id, email);

create table if not exists role (
  tenant_id     uuid not null references tenant(id) on delete cascade,
  code          text not null,
  label         text not null,
  scope         text not null check (scope in ('campus', 'class', 'class_subject', 'child')),
  may_grant     text[] not null default '{}',  -- the roles that may give this one (kept; not yet enforced)
  one_per_class boolean not null default false,  -- one holder at a time in a class (D-039): a second warns
  ord           integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  primary key (tenant_id, code),
  check (not one_per_class or scope = 'class')
);

create table if not exists staff_role_grant (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  staff_id        uuid not null references staff(id),
  role_code       text not null,
  school_class_id uuid references school_class(id),
  subject_code    text,
  child_id        uuid references child(id),
  valid_from      date not null,
  valid_to        date,
  granted_by      text not null check (btrim(granted_by) <> ''),
  override_reason text check (override_reason is null or btrim(override_reason) <> ''),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  foreign key (tenant_id, role_code) references role (tenant_id, code),
  foreign key (tenant_id, subject_code) references subject (tenant_id, code),
  check (valid_to is null or valid_to >= valid_from)
);
create index if not exists staff_role_grant_staff_idx on staff_role_grant (staff_id);
create index if not exists staff_role_grant_class_idx on staff_role_grant (school_class_id) where school_class_id is not null;

-- D-039 as a row, not code: from this grade up, a teacher of a core subject is not a class teacher. "Core" is the
-- mastery subjects; science and Hindi join the list when they are subjects of the school (only these two are today).
insert into config (tenant_id, key, value, description)
select id, 'people.class_teacher_rule',
  '{"from_grade": "G1", "core_subjects": ["NUM", "ENG"]}'::jsonb,
  'D-039: from this grade up, someone who teaches a core subject is not a class teacher, and the other way round, unless the grant gives a reason (people.staff_role_grant). Core subjects are subject codes; science and Hindi are added when they are subjects of the school. Before this grade (pre-primary) one educator is the class''s class teacher.'
from tenant
on conflict (tenant_id, key) do nothing;

-- A grant is never deleted: it ends (valid_to).
create or replace function internal.forbid_delete() returns trigger
language plpgsql as $$
begin
  raise exception '% is never deleted: end it with valid_to', tg_table_name;
end $$;

drop trigger if exists staff_role_grant_never_deleted on staff_role_grant;
create trigger staff_role_grant_never_deleted before delete on staff_role_grant
  for each statement execute function internal.forbid_delete();

-- The checks on a grant. The messages are plain words the engine shows as they are; the first word says which check.
--   needs_class / needs_subject / needs_child / wrong_scope: the grant names what the role's scope needs, and nothing else.
--   already_holds: the same person already holds the same thing on that date. Never overridable.
--   one_per_class: another person is the class's class teacher. core_teacher: D-039. Both warn: they stand only with
--   `override_reason`, which stays on the grant.
create or replace function internal.check_role_grant() returns trigger
language plpgsql set search_path = public as $$
declare
  r role%rowtype;
  rule jsonb;
  from_ord integer;
  grade_ord integer;
  other uuid;
begin
  select * into r from role where tenant_id = new.tenant_id and code = new.role_code;
  if r.scope in ('class', 'class_subject') and new.school_class_id is null then
    raise exception 'needs_class: % is held for one class; name the class', r.label;
  end if;
  if r.scope = 'class_subject' and new.subject_code is null then
    raise exception 'needs_subject: % is held for a subject in a class; name the subject', r.label;
  end if;
  if r.scope = 'child' and new.child_id is null then
    raise exception 'needs_child: % is held for one child; name the child', r.label;
  end if;
  if (r.scope in ('campus', 'child') and new.school_class_id is not null)
     or (r.scope in ('campus', 'class', 'child') and new.subject_code is not null)
     or (r.scope <> 'child' and new.child_id is not null) then
    raise exception 'wrong_scope: % is held for %, and nothing else', r.label, replace(r.scope, '_', ' and ');
  end if;
  if exists (
    select 1 from staff_role_grant g
    where g.tenant_id = new.tenant_id and g.staff_id = new.staff_id and g.role_code = new.role_code
      and g.school_class_id is not distinct from new.school_class_id
      and g.subject_code is not distinct from new.subject_code
      and g.child_id is not distinct from new.child_id
      and (g.valid_to is null or g.valid_to > new.valid_from)
  ) then
    raise exception 'already_holds: this person already holds % there from an earlier date', r.label;
  end if;
  if new.override_reason is not null then
    return new;
  end if;
  if r.one_per_class then
    select g.staff_id into other from staff_role_grant g
    where g.tenant_id = new.tenant_id and g.role_code = new.role_code and g.school_class_id = new.school_class_id
      and (g.valid_to is null or g.valid_to > new.valid_from)
    limit 1;
    if other is not null then
      raise exception 'one_per_class: the class already has a %; give a reason to add another', r.label;
    end if;
  end if;
  -- D-039, both ways round: a class teacher given a core subject, and a core-subject teacher made a class teacher
  select value into rule from config where tenant_id = new.tenant_id and key = 'people.class_teacher_rule';
  if rule is not null and new.role_code in ('class_teacher', 'subject_educator') then
    select ord into from_ord from grade where tenant_id = new.tenant_id and code = rule ->> 'from_grade';
    -- fail closed: a rule whose grade is not a grade cannot say who it applies to, so it refuses until a reason is given
    if from_ord is null then
      raise exception 'core_teacher: the rule starts from %, which is not a grade of the school; give a reason to allow it', rule ->> 'from_grade';
    end if;
    if new.role_code = 'class_teacher' then
      select g.ord into grade_ord from school_class c join grade g on g.tenant_id = c.tenant_id and g.code = c.grade_code
        where c.id = new.school_class_id;
      if grade_ord is null then
        raise exception 'core_teacher: the class''s grade could not be read, so the rule cannot be checked; give a reason to allow it';
      end if;
      if grade_ord >= from_ord and exists (
        select 1 from staff_role_grant g where g.tenant_id = new.tenant_id and g.staff_id = new.staff_id
          and g.role_code = 'subject_educator' and g.subject_code in (select jsonb_array_elements_text(rule -> 'core_subjects'))
          and (g.valid_to is null or g.valid_to > new.valid_from)
      ) then
        raise exception 'core_teacher: from % up, a teacher of a core subject is not a class teacher; give a reason to allow it', rule ->> 'from_grade';
      end if;
    elsif new.subject_code in (select jsonb_array_elements_text(rule -> 'core_subjects')) and exists (
      select 1 from staff_role_grant g join school_class c on c.id = g.school_class_id
        join grade gr on gr.tenant_id = c.tenant_id and gr.code = c.grade_code
      where g.tenant_id = new.tenant_id and g.staff_id = new.staff_id and g.role_code = 'class_teacher'
        and gr.ord >= from_ord and (g.valid_to is null or g.valid_to > new.valid_from)
    ) then
      raise exception 'core_teacher: from % up, a class teacher does not teach a core subject; give a reason to allow it', rule ->> 'from_grade';
    end if;
  end if;
  return new;
end $$;

-- A grant is never edited: it ends. Only `valid_to` may change, only from open to a date, or to an earlier date; every
-- other column, and reopening an ended grant, would skip the checks above, so they are refused whoever asks.
create or replace function internal.refuse_grant_edit() returns trigger
language plpgsql as $$
begin
  if (new.tenant_id, new.staff_id, new.role_code, new.school_class_id, new.subject_code, new.child_id, new.valid_from,
      new.granted_by, new.override_reason, new.created_at)
     is distinct from
     (old.tenant_id, old.staff_id, old.role_code, old.school_class_id, old.subject_code, old.child_id, old.valid_from,
      old.granted_by, old.override_reason, old.created_at) then
    raise exception 'grant_is_not_edited: a grant ends with valid_to; give the person a new grant instead';
  end if;
  if new.valid_to is null and old.valid_to is not null
     or new.valid_to > old.valid_to then
    raise exception 'grant_is_not_edited: an ended grant is not reopened or lengthened; give the person a new grant instead';
  end if;
  return new;
end $$;

drop trigger if exists staff_role_grant_not_edited on staff_role_grant;
create trigger staff_role_grant_not_edited before update on staff_role_grant
  for each row execute function internal.refuse_grant_edit();

drop trigger if exists staff_role_grant_check on staff_role_grant;
create trigger staff_role_grant_check before insert on staff_role_grant
  for each row execute function internal.check_role_grant();

-- A child into a class from a date, with the roll number. The one place a move is done: it closes the child's open row
-- (to_date = the new row's from_date) and opens the new one, in the caller's transaction. The child's own row is
-- untouched, so no answer, result or piece of evidence moves. Returns {"changed": false} when the child is already in
-- that class with that roll number, so a second run is a no-op.
create or replace function public.enrol_child(
  p_child uuid, p_class uuid, p_roll text, p_from date, p_by text
) returns jsonb
language plpgsql set search_path = public as $$
declare
  t uuid;
  open_row enrolment%rowtype;
begin
  select tenant_id into t from school_class where id = p_class;
  if t is null then raise exception 'no_such_class'; end if;
  select * into open_row from enrolment where child_id = p_child and to_date is null for update;
  if found then
    if open_row.class_id = p_class and open_row.roll_no = p_roll then
      return jsonb_build_object('changed', false);
    end if;
    if p_from < open_row.from_date then
      raise exception 'date_before_current: the child is in their present class from %, not earlier', open_row.from_date;
    end if;
    update enrolment set to_date = p_from, updated_at = now() where id = open_row.id;
  end if;
  insert into enrolment (tenant_id, child_id, class_id, roll_no, from_date, recorded_by)
  values (t, p_child, p_class, p_roll, p_from, p_by);
  return jsonb_build_object('changed', true, 'moved_from', open_row.class_id);
end $$;

-- A staff member's name, email and phone, only through here: who asked is written to `access_log`.
create or replace function pii.read_staff(p_staff_id uuid, p_actor text)
returns table (name text, email text, phone text)
language plpgsql security definer set search_path = pii, public as $$
begin
  insert into public.access_log (tenant_id, actor, action)
  select s.tenant_id, p_actor, 'read_pii_staff' from pii.staff s where s.staff_id = p_staff_id;
  return query select s.name, s.email, s.phone from pii.staff s where s.staff_id = p_staff_id;
end $$;

revoke execute on function pii.read_staff(uuid, text) from public;

-- The id of the member of staff a signed-in email belongs to, and nothing else: never a name. The email is matched in
-- lower case against `pii.staff`; null for an email nobody has (or, in a school with two of them, for either). Each
-- lookup is written to `access_log`, as a read of `pii.staff` is. It lives in `public` because neither app role has
-- USAGE on schema `internal`; only the engine may call it (nothing on the website does yet).
create or replace function public.staff_of_email(p_email text) returns uuid
language plpgsql security definer set search_path = pii, public as $$
declare
  ids uuid[];
  school uuid;
begin
  select array_agg(s.staff_id order by s.id), (array_agg(s.tenant_id order by s.id))[1] into ids, school
  from pii.staff s where s.email = lower(btrim(p_email));
  if ids is null then return null; end if;
  insert into public.access_log (tenant_id, actor, action) values (school, 'staff_of_email', 'lookup_staff_by_email');
  if array_length(ids, 1) <> 1 then return null; end if;
  return ids[1];
end $$;

revoke execute on function public.staff_of_email(text) from public;

-- The engine writes; the website reads what is not a person's contact details, and writes none of it yet. Nothing on
-- the website reads a staff member's contact details, so only the engine may call `pii.read_staff`.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    revoke all on pii.staff from app_engine;
    -- no DELETE anywhere: history is kept. A class's children leave it by an enrolment ending, a person by `active`.
    grant select, insert, update on campus, academic_year, school_class, enrolment, staff, role to app_engine;
    grant select, insert, update on staff_role_grant to app_engine;
    -- the default privileges of 20261021090000 give the engine DELETE on every new table; history is kept, so it is taken back
    revoke delete on campus, academic_year, school_class, enrolment, staff, role, staff_role_grant from app_engine;
    grant execute on function public.enrol_child(uuid, uuid, text, date, text) to app_engine;
    grant execute on function pii.read_staff(uuid, text) to app_engine;
    grant execute on function public.staff_of_email(text) to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    revoke all on pii.staff from app_web;
    grant select on campus, academic_year, school_class, enrolment, staff, role, staff_role_grant to app_web;
  end if;
end $$;

-- The rows every school starts with: the twelve roles of D-026 and the sign-in list's `educator`, and the one campus (D-046 says one school), named for the school as the tenant is. Given to every school there
-- now and to any added later, as the vocabulary tables are, so a database built from these files alone has them too.
create or replace function internal.people_vocabulary(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into role (tenant_id, code, label, scope, may_grant, one_per_class, ord)
  select p_tenant, v.code, v.label, v.scope, array['head', 'coordinator'], v.one_per_class, v.ord
  from (values
    ('subject_educator',  'Subject educator',                 'class_subject', false, 0),
    ('class_teacher',     'Class teacher',                    'class',         true,  1),
    ('mentor',            'Mentor',                           'child',         false, 2),
    ('assistant',         'Assistant',                        'class',         false, 3),
    ('coordinator',       'Coordinator',                      'campus',        false, 4),
    ('deputy_coordinator','Deputy coordinator',               'campus',        false, 5),
    ('curriculum_team',   'Curriculum team',                  'campus',        false, 6),
    ('head',              'Head',                             'campus',        false, 7),
    ('ops',               'Ops',                              'campus',        false, 8),
    ('cover_educator',    'Cover educator',                   'class',         false, 9),
    ('special_educator',  'Special educator or counsellor',   'child',         false, 10),
    ('specialist',        'Specialist (PE, music, art)',      'class',         false, 11),
    -- the one role on the sign-in list (config app.staff) that D-026 does not name
    ('educator',          'Educator (as on the sign-in list)','campus',        false, 12)
  ) v (code, label, scope, one_per_class, ord)
  on conflict (tenant_id, code) do nothing;
  insert into campus (tenant_id, name) select p_tenant, t.name from tenant t where t.id = p_tenant
  on conflict (tenant_id, name) do nothing;
end $$;

create or replace function internal.people_vocabulary_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.people_vocabulary(new.id);
  return new;
end $$;

drop trigger if exists people_vocabulary on tenant;
create trigger people_vocabulary after insert on tenant
  for each row execute function internal.people_vocabulary_on_new_school();

select internal.people_vocabulary(id) from tenant;

select internal.apply_conventions();
