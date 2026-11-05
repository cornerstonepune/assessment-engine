-- A skill offered to a person to add (goals/m1-12c-skill-offers.yaml, task M1-12c). Additive: one wider list of kinds.
-- A proposal for a skill the proposer was not shown in any nearest example is not passed on its own: it is a `skill_offer`,
-- one proposal for one skill, waiting for a person to add it or not. Written to run twice.

alter table curriculum_proposal drop constraint if exists curriculum_proposal_kind_check;
alter table curriculum_proposal add constraint curriculum_proposal_kind_check
  check (kind in ('skill', 'objective', 'levels', 'lo_skill', 'page_part', 'material', 'skill_offer'));
