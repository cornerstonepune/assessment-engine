-- Each service reaches the database as a role of its own (goals/p1-the-roles-hold.yaml).
--
-- Until now the website and the engine connected as the owner. Either could read every child's name without the
-- access log, and only a trigger stood between them and a ledger row (code review, 2026-09-30). Two login roles,
-- each able to do what its code does and no more; packages/engine/tests/test_roles.py reads their privileges back.
-- No password is set here: Nimish gives each role one and points its service's DATABASE_URL at it. Until then both
-- services keep the owner's connection, and nothing they do changes.

do $$
begin
  if not exists (select from pg_roles where rolname = 'app_web') then create role app_web login; end if;
  if not exists (select from pg_roles where rolname = 'app_engine') then create role app_engine login; end if;
end $$;

grant usage on schema public to app_web, app_engine;
grant usage on schema pii to app_web, app_engine;

-- Every migration ends by calling this. It now also lets the two roles see every row (what each may do is its
-- grants), and keeps every ledger — a table `internal.forbid_change` guards — to reading and adding for them, so a
-- ledger made later is one the moment its trigger is.
create or replace function internal.apply_conventions() returns void
language plpgsql as $$
declare t record;
begin
  for t in
    select n.nspname as s, c.relname as r
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relkind = 'r' and n.nspname in ('public', 'pii')
  loop
    execute format('alter table %I.%I enable row level security', t.s, t.r);
    execute format('alter table %I.%I force row level security', t.s, t.r);
    execute format('drop policy if exists service_role_all on %I.%I', t.s, t.r);
    execute format(
      'create policy service_role_all on %I.%I for all to service_role using (true) with check (true)',
      t.s, t.r);
    if exists (select from pg_roles where rolname = 'app_engine') then
      execute format('drop policy if exists app_all on %I.%I', t.s, t.r);
      execute format(
        'create policy app_all on %I.%I for all to app_web, app_engine using (true) with check (true)',
        t.s, t.r);
    end if;
    execute format('drop trigger if exists touch_updated_at on %I.%I', t.s, t.r);
    execute format(
      'create trigger touch_updated_at before update on %I.%I '
      'for each row execute function internal.touch_updated_at()',
      t.s, t.r);
  end loop;
  if exists (select from pg_roles where rolname = 'app_engine') then
    for t in
      select distinct tgrelid::regclass as ledger from pg_trigger where tgfoid = 'internal.forbid_change'::regproc
    loop
      execute format('revoke update, delete, truncate on %s from app_web, app_engine', t.ledger);
    end loop;
  end if;
end $$;

-- The engine is the system's writer: every table, and every function of ours. Names are not a table to it.
grant select, insert, update, delete on all tables in schema public to app_engine;
grant usage, select on all sequences in schema public to app_engine;
grant execute on all functions in schema public to app_engine;
alter default privileges in schema public grant select, insert, update, delete on tables to app_engine;
alter default privileges in schema public grant usage, select on sequences to app_engine;
alter default privileges in schema public grant execute on functions to app_engine;

-- The website reads, and writes only what a person changes on it: a reading or a judgement, an override of a
-- prescription, a skill set approved or edited, the approved table of what a mistake charges.
grant select on all tables in schema public to app_web;
alter default privileges in schema public grant select on tables to app_web;
grant insert on read_correction to app_web;
grant update on item_result, prescription, skill_set, config to app_web;
grant execute on function public.confirm_results(uuid, text, uuid) to app_web;
grant execute on function public.resolve_result(uuid, text, text[], text) to app_web;
grant execute on function public.roll_order(text) to app_web;

-- A skill set's history is the system's record of a change, written whoever made it. The website edits a skill set
-- and has no business writing history rows of its own, so the trigger that keeps them writes them as their owner.
alter function internal.skill_set_version_on_change() security definer set search_path = public;

-- A child's name, only through the accessors, which write who asked to `access_log`.
revoke all on all tables in schema pii from app_web, app_engine;
grant execute on function pii.read_child(uuid, text) to app_web, app_engine;

-- The children a first name names, in one class or (with no class) the whole school, each one logged as read. The
-- importer and the gold set find a child by the name a paper or a report carries; they read `pii.child` themselves
-- until now.
create or replace function pii.find_child(p_section text, p_first_name text, p_actor text)
returns setof uuid
language plpgsql
security definer
set search_path = pii, public
as $$
begin
  return query
  with found as (
    select c.id, c.tenant_id
    from public.child c
    join pii.child p on p.child_id = c.id
    where lower(p.first_name) = lower(p_first_name) and (p_section is null or c.section = p_section)
  ), logged as (
    insert into public.access_log (tenant_id, actor, child_id, action)
    select f.tenant_id, p_actor, f.id, 'find_child' from found f
  )
  select f.id from found f;
end $$;

revoke execute on function pii.find_child(text, text, text) from public;
grant execute on function pii.find_child(text, text, text) to app_engine;

select internal.apply_conventions();
