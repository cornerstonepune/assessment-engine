-- Every named mistake says which skill a wrong answer showing it counts against (ADR 0023, step 8b).
--
-- Most mistakes break the operation they happen in — a forgotten carry is an addition slip, a zero that
-- lends without reducing its neighbour is a subtraction one — so the default is `skill_from =
-- 'operation'`: the question's own operation decides. A mistake that belongs to something else says so
-- on its row: "reads = as 'the answer comes next'" is about equality whatever the numbers, "rounds one
-- number only" is about rounding. `skill_code` is then the registry skill.
--
-- `item.mistake_skills` keeps, beside each question's predicted wrong answers, the skill each mistake on
-- that question charges — the same mistake can charge different skills on different questions ("chose
-- the wrong operation" is a word-problem slip in a story and an arithmetic one in a bare sum). It is a
-- derived label (ADR 0030), recomputed by `engine bank relabel`.

alter table public.misconception
  add column skill_from text not null default 'operation' check (skill_from in ('operation', 'row')),
  add column skill_code text,
  add constraint misconception_skill_named check (skill_from = 'operation' or skill_code is not null),
  add constraint misconception_skill_fkey foreign key (tenant_id, skill_code)
    references public.skill (tenant_id, code);

alter table public.item
  add column mistake_skills jsonb not null default '{}'::jsonb;

-- The vocabulary rows the seed does not hold came from the mistake-finding prompt (`spec._store`);
-- the ones whose skill is not their operation are named here once. `engine load` keeps the seeded ones.
update public.misconception m set skill_from = 'row', skill_code = x.skill
from (values
  ('M_ADD_ALL', 'NUM.OPS.05'), ('M_ADD_INSTEAD', 'NUM.OPS.05'), ('M_EQUALS_MEANS_ANSWER', 'NUM.OPS.05'),
  ('M_READS_EQUALS_MAKE', 'NUM.OPS.05'), ('M_COUNTS_ONE_BY_ONE', 'NUM.OPS.05'),
  ('M_BRIDGES_LANDS_WRONG', 'NUM.OPS.05'), ('M_TREATS_NUMBER_WALL', 'NUM.OPS.05'),
  ('M_APPLIES_COMPENSATION_ONE', 'NUM.OPS.05'), ('M_APPLIES_FRIENDLY_NUMBER', 'NUM.OPS.05'),
  ('M_COMPENSATION_ADJUSTMENT', 'NUM.OPS.05'), ('M_COMPENSATION_SIGN', 'NUM.OPS.05'),
  ('M_CONFUSES_COMPENSATION', 'NUM.OPS.05'), ('M_FRIENDLY_NUMBER_APPLIED', 'NUM.OPS.05'),
  ('M_IDENTIFIES_FRIENDLY_NUMBER', 'NUM.OPS.05'), ('M_TREATS_FRIENDLY_NUMBER', 'NUM.OPS.05'),
  ('M_SUM_ONLY', 'NUM.OPS.02'), ('M_SUBTRACTS_COSTS_WRONG', 'NUM.OPS.02'),
  ('M_ONE_STEP_ONLY', 'NUM.PRB.02'), ('M_STOPS_AFTER_SUBTRACTING', 'NUM.PRB.02'),
  ('M_IGNORES_QUESTION_ANSWERS', 'NUM.PRB.02'), ('M_KEYWORD_OVERGENERALISED', 'NUM.PRB.02'),
  ('M_READS_LEFT_REMAINS', 'NUM.PRB.02'),
  ('M_ROUNDS_AWAY_ZERO', 'NUM.PV.03'), ('M_ROUNDS_NEAREST_FIVE', 'NUM.PV.03'),
  ('M_ROUNDS_ONE_NUMBER', 'NUM.PV.03'), ('M_TREATS_ESTIMATE_FINAL', 'NUM.PV.03'),
  ('M_COMPARE_ESTIMATE_EXACT', 'NUM.PV.03'),
  ('M_COMPARE_REVERSED', 'NUM.PV.02'),
  ('M_DIGITS_INDEPENDENT', 'NUM.PV.01'), ('M_REGROUP_CHANGES_TOTAL', 'NUM.PV.01'),
  ('M_EXCHANGE_UNEXPLAINED', 'NUM.PV.01'), ('M_TREATS_EXCHANGE_COMPENSATION', 'NUM.PV.01'),
  ('M_EXPLAINS_MAGNITUDE_WITHOUT', 'NUM.PRB.03'), ('M_EXPLAINS_MISTAKE_DIFFERENT', 'NUM.PRB.03'),
  ('M_GIVES_RIGHT_COLUMN', 'NUM.PRB.03'), ('M_IDENTIFIES_WRONG_COLUMN', 'NUM.PRB.03'),
  ('M_REVERSES_CLAIM_TRUTH', 'NUM.PRB.03'), ('M_SPOT_MISTAKE_EXISTS', 'NUM.PRB.03'),
  ('M_MISSING_DIGIT_LOCAL', 'NUM.PRB.03')
) as x(code, skill)
join public.skill s on s.code = x.skill
where m.code = x.code and s.tenant_id = m.tenant_id;
