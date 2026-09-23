-- Nimish, 2026-09-23: "I'm surprised we haven't even started teaching multiplication" — skills the school does not
-- teach yet showed on every screen. A topic is taught or not (supabase/seed/topics.json); only a taught topic's
-- skills appear on the site or on a child's paper. The others keep their questions, out of sight, until switched on.
alter table topic add column taught boolean not null default false;

-- "It is still showing 10 skills for me to approve": an approval was withdrawn whenever the engine's upkeep rewrote
-- a skill's list of mistakes its questions can show — a derived list no person approves. Only what a person writes
-- and approves (the name, the outcome, the levels, the kinds of question) now withdraws an approval.
create or replace function internal.skill_set_version_on_change() returns trigger
language plpgsql as $$
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
    -- A changed rule is a new draft. The old ratification approved the old rule, not this one.
    new.status := 'draft';
    new.ratified_by := null;
  end if;
  return new;
end $$;
