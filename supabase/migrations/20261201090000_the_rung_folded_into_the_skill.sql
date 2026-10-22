-- The rung folded into the skill, and the registry's table named for what it holds (goals/b4-the-rung-folded-in.yaml,
-- ADR 0084, decisions B4-1 to B4-3 in docs/drafts/b2-b4-decisions.md).
--
-- Nimish, 2026-10-20: "we need proper tables". Every skill had exactly one rung, and the rung held four facts about the
-- skill: its grade, its place on the ladder, its description and the registry skills it covers. They are now the
-- skill's own columns, and the rung's code stays the skill's permanent second code (`skill_set.rung_code`, unique per
-- school), so every question, answer and piece of evidence already recorded points at a skill without being rewritten.
-- Evidence is not touched (B4-2, rule 4): its `rung_code` keeps its name and every row its value.
--
-- The registry's `skill` becomes `registry_skill` now, and the school's `skill_set` becomes `skill` in the next deploy
-- (B4-1: registry first). For the one deploy in between, while the code before this one may still be running, a view
-- answers to each old name (`rung`, `skill`), read only through the same row security; the next deploy drops both.
--
-- Written to run twice.

-- 1. The rung's facts on the skill.
alter table skill_set add column if not exists grade text;
alter table skill_set add column if not exists ladder_order integer;
alter table skill_set add column if not exists descriptor text;
alter table skill_set add column if not exists registry_codes text[] not null default '{}';

do $$
begin
  if to_regclass('public.rung') is not null and (select relkind from pg_class where oid = 'public.rung'::regclass) = 'r' then
    -- Nothing is lost: a rung's milestone was never written by any code; if live holds one, stop and say so.
    if exists (select 1 from rung where milestone_id is not null) then
      raise exception 'B4: % rungs carry a milestone, which the skill has no column for',
        (select count(*) from rung where milestone_id is not null);
    end if;
    -- A rung no skill holds is the old ladder's (bank rehome removes one once nothing names it). One a question still
    -- names cannot be folded into any skill: stop and say which, rather than lose the question's link.
    if exists (select 1 from item i where not exists
                 (select 1 from skill_set s where s.tenant_id = i.tenant_id and s.rung_code = i.rung_code)) then
      raise exception 'B4: questions name rungs no skill holds: %',
        (select string_agg(distinct i.rung_code, ', ') from item i where not exists
           (select 1 from skill_set s where s.tenant_id = i.tenant_id and s.rung_code = i.rung_code));
    end if;
    -- The copy only: the skill's curriculum is not edited by anyone here, so neither its version nor its updated_at
    -- moves (a level approved without a time takes the skill's updated_at, internal.skill_level_sync).
    alter table skill_set disable trigger user;
    update skill_set s
       set grade = r.band, ladder_order = r.ladder_order, descriptor = r.descriptor, registry_codes = r.skill_codes
      from rung r
     where r.tenant_id = s.tenant_id and r.code = s.rung_code
       and row(s.grade, s.ladder_order, s.descriptor, s.registry_codes)
           is distinct from row(r.band, r.ladder_order, r.descriptor, r.skill_codes);
    alter table skill_set enable trigger user;
  end if;
end $$;

alter table skill_set alter column grade set not null;
alter table skill_set alter column descriptor set not null;
alter table skill_set drop constraint if exists skill_set_tenant_id_grade_fkey;
alter table skill_set add constraint skill_set_tenant_id_grade_fkey
  foreign key (tenant_id, grade) references grade (tenant_id, code);

-- 2. A question's rung is a skill's second code, a key the database checks, as it was the rung's.
alter table item drop constraint if exists item_tenant_id_rung_code_fkey;
alter table skill_set drop constraint if exists skill_set_tenant_id_rung_code_fkey;
alter table skill_set drop constraint if exists skill_set_rung_code_key;
alter table skill_set add constraint skill_set_rung_code_key unique (tenant_id, rung_code);
drop index if exists skill_set_one_per_rung;
alter table item add constraint item_tenant_id_rung_code_fkey
  foreign key (tenant_id, rung_code) references skill_set (tenant_id, rung_code) on update cascade;

-- 3. A level's grade, when the skill's says nothing else, is the skill's own.
create or replace function internal.skill_level_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from skill_level l
  where l.tenant_id = p_tenant and l.skill_code = p_code
    and not exists (select 1 from skill_set s where s.tenant_id = p_tenant and s.code = p_code and s.difficulty ? l.difficulty);
  insert into skill_level as l (tenant_id, skill_code, difficulty, grade, looks_like, rule, confirmed_by, confirmed_at)
  select s.tenant_id, s.code, e.key, coalesce(s.level_band ->> e.key, s.grade), e.value ->> 'words', e.value - 'words',
         s.level_approved -> e.key ->> 'by',
         case when s.level_approved ? e.key
              then coalesce((s.level_approved -> e.key ->> 'at')::timestamptz, s.updated_at) end
  from skill_set s
  cross join jsonb_each(s.difficulty) e
  where s.tenant_id = p_tenant and s.code = p_code
  on conflict (tenant_id, skill_code, difficulty) do update
    set grade = excluded.grade, looks_like = excluded.looks_like, rule = excluded.rule,
        confirmed_by = excluded.confirmed_by, confirmed_at = excluded.confirmed_at
    where row(l.grade, l.looks_like, l.rule, l.confirmed_by, l.confirmed_at)
          is distinct from row(excluded.grade, excluded.looks_like, excluded.rule, excluded.confirmed_by, excluded.confirmed_at);
end $$;

drop trigger if exists skill_level_on_update on skill_set;
create trigger skill_level_on_update after update on skill_set
  for each row when (row(old.code, old.rung_code, old.difficulty, old.level_band, old.level_approved, old.grade)
                     is distinct from row(new.code, new.rung_code, new.difficulty, new.level_band, new.level_approved, new.grade))
  execute function internal.skill_level_from_skill_set();

-- 4. A skill's registry links kept equal to its own list, as they were to its rung's.
create or replace function internal.skill_registry_link_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from skill_registry_link k
  where k.tenant_id = p_tenant and k.skill_code = p_code
    and not exists (select 1 from skill_set s
                    where s.tenant_id = p_tenant and s.code = p_code and k.registry_skill = any(s.registry_codes));
  insert into skill_registry_link (tenant_id, skill_code, registry_skill)
  select s.tenant_id, s.code, c
  from skill_set s cross join unnest(s.registry_codes) c
  where s.tenant_id = p_tenant and s.code = p_code
  on conflict (tenant_id, skill_code, registry_skill) do nothing;
end $$;

drop trigger if exists skill_links_on_update on skill_set;
create trigger skill_links_on_update after update on skill_set
  for each row when (row(old.code, old.rung_code, old.misconception_codes, old.registry_codes)
                     is distinct from row(new.code, new.rung_code, new.misconception_codes, new.registry_codes))
  execute function internal.skill_links_from_skill_set();

-- 5. The rung table goes; its name answers for one deploy.
do $$
begin
  if to_regclass('public.rung') is not null and (select relkind from pg_class where oid = 'public.rung'::regclass) = 'r' then
    drop table rung;
  end if;
end $$;
drop function if exists internal.skill_level_from_rung();
drop function if exists internal.skill_registry_link_from_rung();

create or replace view rung with (security_invoker = true) as
  select id, tenant_id, rung_code as code, grade as band, ladder_order, descriptor, registry_codes as skill_codes,
         null::uuid as milestone_id, created_at, updated_at
  from skill_set;

-- 6. The registry's skills are `registry_skill`; `skill` answers for one deploy.
do $$
begin
  if to_regclass('public.registry_skill') is null then
    alter table skill rename to registry_skill;
  end if;
  -- its keys' names too, so the school's skills can take `skill_pkey` and the rest in the next deploy
  if exists (select 1 from pg_constraint where conrelid = 'registry_skill'::regclass and conname = 'skill_pkey') then
    alter table registry_skill rename constraint skill_pkey to registry_skill_pkey;
    alter table registry_skill rename constraint skill_tenant_id_code_key to registry_skill_tenant_id_code_key;
    alter table registry_skill rename constraint skill_tenant_id_fkey to registry_skill_tenant_id_fkey;
  end if;
end $$;

create or replace view skill with (security_invoker = true) as select * from registry_skill;

revoke all on rung, skill from public;
grant select on rung, skill to app_web, app_engine;

select internal.apply_conventions();
