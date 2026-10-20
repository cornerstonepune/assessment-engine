-- Every grade a row holds is a key into `grade`, and grades sort by its order (goals/b0b-grades-from-the-table.yaml,
-- ADR 0085).
--
-- B0a made `grade`; nothing read it. A grade was text in ten columns and a JSON object (`skill_set.level_band`) that
-- the database never checked, and the pages read a grade's number out of its code ("G10" read as 1) and sorted grades as
-- text ("G10" before "G2"). Reasoning's rungs held "G2+", a grade no table could hold: it meant first met in Grade 2,
-- which is what every level's grade means, so it is Grade 2 (Nimish's decision, B3 on the design).
--
-- Written to run twice.

-- Reasoning's "G2+" is Grade 2, wherever a grade is held.
update rung set band = rtrim(band, '+') where band like '%+';
update sheet_template set band = rtrim(band, '+') where band like '%+';
update blueprint set band = rtrim(band, '+') where band like '%+';
update level_rule set band = rtrim(band, '+') where band like '%+';
update skill_set s set level_band = (
  select jsonb_object_agg(e.key, rtrim(e.value, '+')) from jsonb_each_text(s.level_band) e
) where exists (select 1 from jsonb_each_text(s.level_band) e where e.value like '%+');

-- A grade's place among the school's grades: sort by this, never by the code as text.
create or replace function public.grade_ord(tenant uuid, code text) returns int
language sql stable set search_path = public as $$
  select g.ord from grade g where g.tenant_id = $1 and g.code = $2
$$;
grant execute on function public.grade_ord(uuid, text) to app_web;

-- A class's grade, the lower on a tie by the grades' order: as text, a class of one Grade 9 and one Grade 10 child was
-- Grade 10.
create or replace function public.class_band(tenant uuid, section text) returns text
language sql stable set search_path = public as $$
  select c.band from child c
  join grade g on g.tenant_id = c.tenant_id and g.code = c.band
  where c.tenant_id = $1 and c.section = $2 and c.active
  group by c.band, g.ord
  order by count(*) desc, g.ord
  limit 1
$$;

-- Each column that holds a grade: a key on (school, code) into `grade`.
do $$
declare t text;
begin
  foreach t in array array['rung', 'child', 'sheet_template', 'blueprint', 'level_rule', 'milestone',
                           'learning_objective', 'activity', 'report_item', 'trait'] loop
    execute format('alter table %I drop constraint if exists %I', t, t || '_tenant_id_band_fkey');
    execute format('alter table %I add constraint %I foreign key (tenant_id, band) references grade (tenant_id, code)',
                   t, t || '_tenant_id_band_fkey');
  end loop;
end $$;

-- A level's grade is a value inside `skill_set.level_band`, which no key can reach until a level is a row of its own
-- (B1, `skill_level.grade`). Until then the database checks it on every write as a key would: each level a row of
-- `difficulty`, each grade a row of `grade`, refused with a key's own error; and a grade a level names is not deleted
-- or renamed from under it.
create or replace function internal.level_band_is_keyed() returns trigger
language plpgsql set search_path = public as $$
declare bad text;
begin
  select e.key || ' → ' || e.value into bad
  from jsonb_each_text(new.level_band) e
  where not exists (select 1 from difficulty d where d.tenant_id = new.tenant_id and d.code = e.key)
     or not exists (select 1 from grade g where g.tenant_id = new.tenant_id and g.code = e.value)
  limit 1;
  if bad is not null then
    raise foreign_key_violation using message = format('skill_set %s: level_band %s is no level and grade', new.code, bad);
  end if;
  return new;
end $$;

drop trigger if exists level_band_is_keyed on skill_set;
create trigger level_band_is_keyed before insert or update of level_band on skill_set
  for each row execute function internal.level_band_is_keyed();

create or replace function internal.grade_held_by_a_level() returns trigger
language plpgsql set search_path = public as $$
begin
  if exists (select 1 from skill_set s, jsonb_each_text(s.level_band) e
             where s.tenant_id = old.tenant_id and e.value = old.code) then
    raise foreign_key_violation using message = format('grade %s is the grade of a level (skill_set.level_band)', old.code);
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;

drop trigger if exists grade_held_by_a_level on grade;
create trigger grade_held_by_a_level before delete on grade
  for each row execute function internal.grade_held_by_a_level();
drop trigger if exists grade_renamed_under_a_level on grade;
create trigger grade_renamed_under_a_level before update of code on grade
  for each row when (old.code is distinct from new.code) execute function internal.grade_held_by_a_level();

select internal.apply_conventions();
