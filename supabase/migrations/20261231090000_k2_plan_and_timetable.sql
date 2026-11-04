-- The K2 plan and timetable, first slice (goals/m1-06-plan-today.yaml; task M1-06; decisions D-018, D-028, D-067;
-- design in docs/notes/m1-06-k2-plan-timetable.md).
-- The system holds the school's dated days, the fortnight plan, the two-week frame of periods for a class, and the
-- sessions a class has on a day, so the timetable is generated from the plans and a person changes only what is wrong.
--
--   * `fortnight`: the school's fortnights of a year with their start and end dates and kind (teaching, buffer week,
--     vacation, settling, celebration), as the Graph tab of the planning sheet gives them. Dates are stored as a
--     person confirms them; nothing here checks a fortnight is 14 days (the sheet's Fortnight 10 and 11 disagree).
--   * `school_day`: one row per campus and date, with a kind: teaching, holiday, or changed timing. "Stuck for six
--     weeks" counts teaching days only.
--   * `period`: a row of the day for a grade, with its times; `fixed` rows (settling, circle, fruit, lunch, reflection,
--     dispersal, the bus) are the same every day, the others are subject periods.
--   * `timetable_slot`: the frame, one class in one period of week A or B on one weekday: its kind (fixed, subject,
--     specialist, empty), its subject and the school's own wording. A change ends a slot (`valid_to`) and opens another.
--   * `plan_entry`: one line of a class's fortnight plan under a heading of the Monthly Planner, in the order the
--     planner has it; `activity_id` names the Activity-list row it is when a person or M1-05 has mapped it. Text is
--     copied, never written by the system.
--   * `session`: one class, on one school day, in one period, for one subject, led by named staff. Its state is
--     delivery only (planned, done, not done, moved); approval is in the `approval` ledger, never here. An unplanned
--     session is `planned = false` and shows to the coordinator as unplanned, not as a mistake (data-architecture Q4).
--     `activity_observation.session_id` stays free; pointing it here is the next slice, after the observed rows are read.
--
-- Not here: `week_plan` and `timetable_version` (they come with the approval step), a person's rights over these rows
-- (`internal.apply_conventions()` still gives both app roles `using (true)`, ADR 0024), and any child's name (none of
-- these tables holds one).
--
-- ADDITIVE ONLY: no existing table is read or written differently, nothing is dropped, deleted or rewritten. Written to
-- run twice.

create table if not exists fortnight (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references tenant(id) on delete cascade,
  academic_year_id uuid not null references academic_year(id),
  number           int check (number is null or number > 0),
  kind             text not null check (kind in ('settling', 'teaching', 'buffer', 'vacation', 'celebration')),
  starts_on        date not null,
  ends_on          date not null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  check (ends_on >= starts_on),
  check (kind <> 'teaching' or number is not null),
  unique (tenant_id, academic_year_id, starts_on)
);
create unique index if not exists fortnight_number_once on fortnight (academic_year_id, number) where number is not null;

create table if not exists school_day (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  campus_id  uuid not null references campus(id),
  on_date    date not null,
  kind       text not null check (kind in ('teaching', 'holiday', 'changed_timing')),
  note       text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, campus_id, on_date)
);

create table if not exists period (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  grade_code text not null,
  ord        int not null,
  starts_at  time not null,
  ends_at    time,
  label      text not null check (btrim(label) <> ''),
  fixed      boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (tenant_id, grade_code) references grade (tenant_id, code),
  check (ends_at is null or ends_at > starts_at),
  unique (tenant_id, grade_code, starts_at)
);

create table if not exists timetable_slot (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  period_id       uuid not null references period(id),
  week_code       text not null check (week_code in ('A', 'B')),
  weekday         smallint not null check (weekday between 1 and 5),
  kind            text not null check (kind in ('fixed', 'subject', 'specialist', 'empty')),
  subject_code    text,
  text            text not null default '',
  valid_from      date not null,
  valid_to        date,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (valid_to is null or valid_to >= valid_from),
  check (kind = 'empty' or btrim(text) <> ''),
  unique (school_class_id, period_id, week_code, weekday, valid_from)
);
create index if not exists timetable_slot_class_idx on timetable_slot (school_class_id) where valid_to is null;

create table if not exists plan_entry (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  fortnight_id    uuid not null references fortnight(id),
  plan_key        text not null check (btrim(plan_key) <> ''),
  ord             int not null check (ord > 0),
  text            text not null check (btrim(text) <> ''),
  activity_id     uuid references activity(id),
  source          text not null check (btrim(source) <> ''),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (school_class_id, fortnight_id, plan_key, ord)
);
create index if not exists plan_entry_fortnight_idx on plan_entry (fortnight_id);

create table if not exists session (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  school_day_id   uuid not null references school_day(id),
  period_id       uuid not null references period(id),
  subject_code    text,
  led_by_staff_id uuid references staff(id),
  state           text not null default 'planned' check (state in ('planned', 'done', 'not_done', 'moved')),
  planned         boolean not null default true,
  plan_entry_id   uuid references plan_entry(id),
  text            text not null default '',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (school_class_id, school_day_id, period_id)
);
create index if not exists session_day_idx on session (school_day_id);

select internal.apply_conventions();
