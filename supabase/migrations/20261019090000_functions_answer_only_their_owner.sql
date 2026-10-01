-- Our functions answer only their owner (goals/p0-the-database-answers-only-its-own.yaml).
--
-- Postgres lets everyone execute a new function unless told otherwise, and Supabase exposes every function in
-- `public` through its REST API. Seven of ours run as their owner (SECURITY DEFINER): `confirm_results`,
-- `correct_signed_off`, `resolve_result`, `answer_evidence`, `rebuild_child_skill_state`, `next_difficulty` and
-- `pii.read_child`. On a copy built from these migrations the `anon` role could run every one, so the project's
-- publishable key and a paper's id were enough to sign off or change a child's marks (code review, 2026-09-30).
-- The website and the engine connect as the owner and need no grant; nothing calls our functions over the API.

do $$
declare
  f record;
  r text;
begin
  for f in
    select p.oid::regprocedure as sig
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'pii', 'internal')
      and p.proowner = (select oid from pg_roles where rolname = current_user)
      and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')
  loop
    execute format('revoke execute on function %s from public', f.sig);
    for r in select rolname from pg_roles where rolname in ('anon', 'authenticated') loop
      execute format('revoke execute on function %s from %I', f.sig, r);
    end loop;
  end loop;
end $$;

-- And every function made from now on: its owner runs it, and anyone else only by a grant a migration writes.
alter default privileges revoke execute on functions from public;

do $$
declare
  r text;
begin
  for r in select rolname from pg_roles where rolname in ('anon', 'authenticated') loop
    execute format('alter default privileges in schema public revoke execute on functions from %I', r);
  end loop;
end $$;
