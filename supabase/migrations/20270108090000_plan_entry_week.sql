-- M1-06d: a planner line knows which week of its fortnight it plans.
--
-- A fortnight the Monthly Planner lists under two month headings (Fortnight 10: November's and December's) has a row
-- in each. The loader (engine/w2_print/k2_timetable_load.py, `_parts`) gives week A the first row and week B the
-- second, and numbers the second row's lines on from the first's under each heading. Until now the week was not kept,
-- so a period showed both rows' lines: General Awareness said "Insects" and "lifecycle of a butterfly" twice.
--
-- `week_code` is 'A' or 'B' on a line of such a fortnight, null on a fortnight listed once (its lines plan every day).
-- Additive and nullable: no row is removed, and a reader that ignores the column sees what it saw before.

alter table plan_entry add column if not exists week_code text check (week_code in ('A', 'B'));

comment on column plan_entry.week_code is
  'The week of its fortnight this line plans, when the fortnight is listed under two month headings: A from the first '
  'row, B from the second. Null when the fortnight has one row, whose lines plan both weeks.';

-- The rows already loaded. The loader wrote each half's month into `source` ("… (November block)"). Under a heading
-- with lines in both rows, the second row's lines are numbered on from the first's, so the row holding that heading's
-- first line is week A's.
with tagged as (
  select id, school_class_id as c, fortnight_id as f, plan_key as k, ord,
         substring(source from '\((\w+) block\)$') as block
  from plan_entry
  where week_code is null
), split as (
  select c, f from tagged where block is not null group by c, f having count(distinct block) = 2
), first_row as (
  select distinct on (t.c, t.f) t.c, t.f, t.block
  from tagged t join split using (c, f)
  where exists (select 1 from tagged u where u.c = t.c and u.f = t.f and u.k = t.k and u.block <> t.block)
  order by t.c, t.f, t.ord
)
update plan_entry pe
set week_code = case when t.block = fr.block then 'A' else 'B' end
from tagged t join first_row fr using (c, f)
where pe.id = t.id and t.block is not null;

-- A fortnight under two headings whose rows share no heading cannot be told apart from what was stored: stop, so the
-- rehearsal on a copy of live says so before live is touched.
do $$
begin
  if exists (
    select 1 from plan_entry
    where week_code is null and substring(source from '\((\w+) block\)$') is not null
  ) then
    raise exception 'a planner line of a fortnight under two month headings has no week: load it again';
  end if;
end $$;
