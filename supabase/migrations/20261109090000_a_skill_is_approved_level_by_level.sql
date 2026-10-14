-- A skill's questions are approved level by level (goals/f1d-questions-approved-per-level.yaml, ADR 0073 D2). Nimish,
-- 2026-10-14: "When I approve a skill, it gets approved throughout all the grades. If I just want to approve something
-- for a grade level today, I'm not able to do that." A level's questions are right or not for every grade alike, so a
-- level is approved once, by the coordinator; which levels a grade uses is the grade's own plan.
--
-- `level_approved` is {level: {by, at}}. A skill is approved (`status` 'ratified', as every reader already asks) exactly
-- when every level it has is, and `ratified_by` is whoever approved its last level. Only a change to what makes a
-- level's questions withdraws that level: its rule — everything of the level but its words — or the kinds of question
-- the skill uses, which are every level's. Its name, what a child can do and a level's words withdraw nothing: the
-- questions did not change. Every change a person can read is still filed as a version. A status set whole — approved
-- or withdrawn — approves or withdraws every level with it.
--
-- Written to run twice: the test of a skill approved before runs it again over one.

alter table skill_set add column if not exists level_approved jsonb not null default '{}'::jsonb;

create or replace function internal.skill_set_version_on_change() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if row(new.rung_code, new.name, new.learning_objective, new.philosophy, new.formats,
         new.difficulty, new.eval_type)
     is distinct from
     row(old.rung_code, old.name, old.learning_objective, old.philosophy, old.formats,
         old.difficulty, old.eval_type) then
    insert into skill_set_version (tenant_id, code, version, rung_code, name, learning_objective,
      philosophy, formats, misconception_codes, difficulty, eval_type, status, ratified_by, valid_from)
    values (old.tenant_id, old.code, old.version, old.rung_code, old.name, old.learning_objective,
      old.philosophy, old.formats, old.misconception_codes, old.difficulty, old.eval_type,
      old.status, old.ratified_by, old.updated_at);
    new.version := old.version + 1;
  end if;
  -- the skill approved or withdrawn whole, by its status (`engine ratify`, a person approving every level at once): every
  -- level with it, so the status and the levels never disagree, whoever writes the row
  if new.status is distinct from old.status and new.level_approved is not distinct from old.level_approved then
    new.level_approved := case when new.status = 'ratified'
      then (select jsonb_object_agg(k, jsonb_build_object('by', coalesce(new.ratified_by, 'someone'), 'at', now()))
            from jsonb_object_keys(new.difficulty) k)
      else '{}'::jsonb end;
  end if;
  -- a level keeps its approval while what makes its questions is the one that was approved
  new.level_approved := coalesce((
    select jsonb_object_agg(e.key, e.value) from jsonb_each(new.level_approved) e
    where new.difficulty ? e.key
      and (old.difficulty -> e.key) - 'words' is not distinct from (new.difficulty -> e.key) - 'words'
      and new.formats is not distinct from old.formats
      and new.eval_type is not distinct from old.eval_type), '{}'::jsonb);
  if (select bool_and(new.level_approved ? k) from jsonb_object_keys(new.difficulty) k) then
    new.status := 'ratified';
    new.ratified_by := coalesce(
      (select e.value ->> 'by' from jsonb_each(new.level_approved) e
       order by e.value ->> 'at' desc limit 1), new.ratified_by);
  else
    new.status := 'draft';
    new.ratified_by := null;
  end if;
  return new;
end $$;

-- a skill approved whole before keeps its approval at every level it has, in the name of who approved it
update skill_set s
set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', s.ratified_by, 'at', s.updated_at))
                      from jsonb_object_keys(s.difficulty) k)
where s.status = 'ratified' and s.level_approved = '{}'::jsonb;
