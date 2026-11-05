-- The timetable's rules as rows a person edits on a screen (goals/m1-14a-timetable-rules.yaml; task M1-14 part a; decisions
-- D-072, D-074, D-075). The generator (part b) is driven from these rows and the rows the six timetable tables already hold.
--
--   * period            (existing) a person edits its times and its name; nothing new here.
--   * timetable_slot    (existing) a `fixed` slot is a fixed-slot rule: the school pinned this period, this day, this week.
--   * timetable_block   a day, a weekday, or one period of either, on which nothing may be placed for a class, and why.
--   * timetable_limit   the fewest and the most periods of a subject for a class in a week or in a fortnight.
--   * timetable_rule_edit  every change to any of the four, with who made it and when and the row before and after.
--                       Append-only: what was changed is never rewritten (the same pattern as materials_line_edit).
-- No name is stored: `who` is the staff row; the name stays in pii.

create table if not exists timetable_block (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  on_date         date,
  weekday         smallint check (weekday between 1 and 5),
  week_code       text check (week_code in ('A', 'B')),
  period_id       uuid references period(id),
  reason          text not null check (btrim(reason) <> ''),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check ((on_date is null) <> (weekday is null)),
  check (on_date is null or extract(isodow from on_date) between 1 and 5),
  check (week_code is null or weekday is not null)
);
-- one rule once: the same day (or weekday and week) and period cannot be blocked twice for a class
create unique index if not exists timetable_block_once on timetable_block (
  school_class_id,
  coalesce(on_date, '0001-01-01'::date),
  coalesce(weekday, 0),
  coalesce(week_code, ''),
  coalesce(period_id, '00000000-0000-0000-0000-000000000000'::uuid)
);

create table if not exists timetable_limit (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  subject_code    text not null check (btrim(subject_code) <> ''),
  span            text not null check (span in ('week', 'fortnight')),
  fewest          int check (fewest is null or fewest >= 0),
  most            int check (most is null or most >= 0),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (fewest is not null or most is not null),
  check (fewest is null or most is null or fewest <= most),
  unique (school_class_id, subject_code, span)
);

create table if not exists timetable_rule_edit (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  rule            text not null check (rule in ('period', 'block', 'limit', 'fixed')),
  action          text not null check (action in ('set', 'remove')),
  who             uuid not null references staff(id),
  at              timestamptz not null default clock_timestamp(),
  before          jsonb,
  after           jsonb,
  check (before is not null or after is not null)
);
create index if not exists timetable_rule_edit_class_idx on timetable_rule_edit (school_class_id, at desc);
drop trigger if exists timetable_rule_edit_append_only on timetable_rule_edit;
create trigger timetable_rule_edit_append_only before update or delete on timetable_rule_edit
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
