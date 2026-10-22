-- The school's skills are the table `skill` (goals/b4b-the-skill-is-called-skill.yaml, decision B4-1, deploy 2 of 2).
--
-- Nimish, 2026-10-20: "we need proper tables". B4 (20261201090000) renamed the registry's table `registry_skill` and
-- left `rung` and the registry's old `skill` answering as views for one deploy; that deploy is past, so both go, and the
-- school's `skill_set` takes the name `skill`. Only names change: its columns, rows, keys and triggers are the same
-- (a column that names it, `skill_set_code`, `skill_set_version`, keeps its name: the decision names the table).
-- The functions that read it by name are written again with the new name. For the one deploy in which B4's code may
-- still run, `skill_set` answers as a view that reads and writes the table; the next schema slice drops it.
--
-- Written to run twice.

drop view if exists rung;

do $$
declare f record; c record;
begin
  if (select relkind from pg_class where oid = to_regclass('public.skill')) = 'v' then
    drop view skill;
  end if;
  if (select relkind from pg_class where oid = to_regclass('public.skill_set')) = 'r' then
    alter table skill_set rename to skill;
  end if;
  -- the keys' names follow the table's (the registry's gave up `skill_pkey` and the rest in B4)
  for c in select conname from pg_constraint where conrelid = 'public.skill'::regclass and conname like 'skill\_set\_%' loop
    execute format('alter table skill rename constraint %I to %I', c.conname, 'skill_' || substr(c.conname, 11));
  end loop;
  -- every function that reads the table by its old name, written again with the new one
  for f in
    select p.oid from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'internal') and p.prokind = 'f' and p.prosrc ~ '\mskill_set\M'
  loop
    execute regexp_replace(pg_get_functiondef(f.oid), '\mskill_set\M', 'skill', 'g');
  end loop;
end $$;

create or replace view skill_set with (security_invoker = true) as select * from skill;
revoke all on skill_set from public;
grant select, insert, update, delete on skill_set to app_engine;
grant select, update on skill_set to app_web;

select internal.apply_conventions();
