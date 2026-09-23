-- The old ladder leaves (ADR 0034). A replaced skill set is not kept "retired": `engine bank rehome` moves every
-- question it held to its taxonomy-shaped skill and deletes it, with its rule history and the rungs nothing
-- names any more, in one transaction. So a skill set is draft or ratified again, and nothing in the engine or on
-- a screen has to remember to leave retired rows out.
--
-- `coverage_target` held, per old rung, the tag values its questions had to show. The taxonomy's cases now say
-- what each level holds (ADR 0031, 0034), `engine bank taxonomy` counts them, and nothing read this table but
-- the loader that filled it.

alter table skill_set drop constraint skill_set_retired_says_who;
update skill_set set status = 'draft', ratified_by = null where status = 'retired';
alter table skill_set drop column retired_by;
alter table skill_set drop column retired_at;
alter table skill_set drop constraint skill_set_status_check;
alter table skill_set add constraint skill_set_status_check check (status in ('draft', 'ratified'));

drop table coverage_target;
