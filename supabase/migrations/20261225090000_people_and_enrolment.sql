-- People and enrolment, first slice (goals/m0-05-people-enrolment.yaml; task M0-05; decisions D-039, D-046, D-047, D-055).
-- The system knows who a member of staff is, which class they teach, and which children are in that class.
--
--   * `campus`, `academic_year`, `school_class`: where and when a class is. A class is a campus, a year and the class's
--     own name, which is the string `child.section` already carries ("K2", "G2"), so the new table and the old column
--     say the same thing; its grade is a row of `grade`.
--   * `enrolment`: the only link between a child and a class. A move closes one row (`to_date`) and opens another, so a
--     child's history of classes is kept. At most one open row per child, and one open row per roll number in a class.
--     `enrol_child()` is the one place that does the closing and opening.
--   * `staff`, `pii.staff`: a person is an id; their name, email and phone are in `pii` and nowhere else (rule 6). The
--     website's sign-in list (`config` key app.staff) is untouched and stays the master of passwords.
--   * `role`, `staff_role_grant`: roles are rows; holding one is a dated grant. A role that belongs to one class at a time
--     (`class_teacher`) warns when a second person is given it and allows it only with a reason, which is kept on the
--     grant (D-039). The check is a trigger, so no path around `enrol`/`import` can skip it.
--   * `pii.child.birthday`: the class list carries one; it is a child's personal data, so it is beside the name.
--   * `pii.read_staff()`: a staff member's name, email and phone, only through this, which writes who asked to `access_log`.
--
-- Not here: who may see which class (per-person access rules need a proven route first, P-05), and `move_child` writing
-- an enrolment (it still changes `child.section` only; a class-change by that route does not yet close an enrolment).
-- btree_gist is not needed: "one open row" is a partial unique index, and closing is done by `enrol_child()`.
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
  unique (tenant_id, campus_id, academic_year_id, section)
);
create index if not exists school_class_section_idx on school_class (tenant_id, section);

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
  per_class     boolean not null default false,  -- held for one class (class_id on the grant), not for the school
  one_per_class boolean not null default false,  -- one holder at a time in a class (D-039): a second warns
  ord           integer not null default 0,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  primary key (tenant_id, code),
  check (not one_per_class or per_class)
);
create table if not exists staff_role_grant (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  staff_id        uuid not null references staff(id),
  role_code       text not null,
  class_id        uuid references school_class(id),
  from_date       date not null,
  to_date         date,
  granted_by      text not null check (btrim(granted_by) <> ''),
  override_reason text check (override_reason is null or btrim(override_reason) <> ''),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  foreign key (tenant_id, role_code) references role (tenant_id, code),
  check (to_date is null or to_date >= from_date)
);
create index if not exists staff_role_grant_staff_idx on staff_role_grant (staff_id);
create index if not exists staff_role_grant_class_idx on staff_role_grant (class_id) where class_id is not null;

-- The checks on a grant. The messages are plain words the engine shows as they are; the first word says which check.
--   needs_class / not_for_a_class: a class role names its class, a school role does not.
--   already_holds: the same person already holds the same role (for the same class) on that date. Never overridable.
--   one_per_class: another person holds a role that has one holder at a time. A warning (D-039): the grant goes through
--   only when `override_reason` says why, and the reason stays on the grant.
create or replace function internal.check_role_grant() returns trigger
language plpgsql set search_path = public as $$
declare
  r role%rowtype;
  other uuid;
begin
  select * into r from role where tenant_id = new.tenant_id and code = new.role_code;
  if r.per_class and new.class_id is null then
    raise exception 'needs_class: % is held for one class; name the class', r.label;
  end if;
  if not r.per_class and new.class_id is not null then
    raise exception 'not_for_a_class: % is held for the whole school, not for a class', r.label;
  end if;
  if exists (
    select 1 from staff_role_grant g
    where g.tenant_id = new.tenant_id and g.staff_id = new.staff_id and g.role_code = new.role_code
      and g.class_id is not distinct from new.class_id
      and (g.to_date is null or g.to_date > new.from_date)
  ) then
    raise exception 'already_holds: this person already holds % there from an earlier date', r.label;
  end if;
  if r.one_per_class and new.override_reason is null then
    select g.staff_id into other from staff_role_grant g
    where g.tenant_id = new.tenant_id and g.role_code = new.role_code and g.class_id = new.class_id
      and (g.to_date is null or g.to_date > new.from_date)
    limit 1;
    if other is not null then
      raise exception 'one_per_class: the class already has a % (staff %); give a reason to add another', r.label, other;
    end if;
  end if;
  return new;
end $$;

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

-- The engine writes; the website reads what is not a person's contact details, and writes none of it yet.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    revoke all on pii.staff from app_engine;
    grant select, insert, update, delete on campus, academic_year, school_class, enrolment, staff, role,
      staff_role_grant to app_engine;
    grant execute on function public.enrol_child(uuid, uuid, text, date, text) to app_engine;
    grant execute on function pii.read_staff(uuid, text) to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    revoke all on pii.staff from app_web;
    grant select on campus, academic_year, school_class, enrolment, staff, role, staff_role_grant to app_web;
    grant execute on function pii.read_staff(uuid, text) to app_web;
  end if;
end $$;

-- The rows every school starts with: the roles the school's decisions already name (config `people.decides`) and the class
-- educator, and the one campus (D-046 says one school), named for the school as the tenant is. Given to every school there
-- now and to any added later, as the vocabulary tables are, so a database built from these files alone has them too.
create or replace function internal.people_vocabulary(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into role (tenant_id, code, label, per_class, one_per_class, ord)
  select p_tenant, v.code, v.label, v.per_class, v.one_per_class, v.ord
  from (values
    ('coordinator',   'Coordinator',    false, false, 0),
    ('educator',      'Educator',       false, false, 1),
    ('specialist',    'Specialist',     false, false, 2),
    ('class_teacher', 'Class educator', true,  true,  3)
  ) v (code, label, per_class, one_per_class, ord)
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
