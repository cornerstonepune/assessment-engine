-- `item_placement` is on live and made by no migration (rule 9); nothing in the engine, the website or n8n reads
-- or writes it. Its foreign key to skill_set stopped `engine bank rehome` removing the old ladder's skill sets on
-- 2026-09-24 (ForeignKeyViolation on ADD.1D.BRIDGE10). Its rows are kept exactly as they are, for whoever made it
-- to say what they are; only its hold on skill_set and rung is released. Where the table does not exist, nothing.
do $$
declare c record;
begin
  if to_regclass('public.item_placement') is null then
    return;
  end if;
  for c in
    select conname from pg_constraint
    where conrelid = 'public.item_placement'::regclass and contype = 'f'
      and confrelid in ('public.skill_set'::regclass, 'public.rung'::regclass)
  loop
    execute format('alter table public.item_placement drop constraint %I', c.conname);
  end loop;
end $$;
