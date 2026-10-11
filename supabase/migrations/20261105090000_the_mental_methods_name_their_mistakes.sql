-- The mental methods' own mistakes on the lists of the skills whose questions name them (goals/md4a-mental-methods.yaml,
-- ADR 0064). × 5 as × 10 then halved and a number near a round one (MUL.2D1D's Advance) name the step stopped short,
-- the answer put right the wrong way and one taken away or added for a whole group; ÷ 5 as ÷ 10 then doubled
-- (DIV.3D1D's Advance) the step stopped short. MD.MENTAL is new and is loaded with its list; a skill set is loaded
-- insert-only, so the two loaded before get theirs here.
update public.skill_set s
set misconception_codes = array(select distinct c collate "C" from unnest(s.misconception_codes || x.codes) as c order by 1)
from (values
  ('MUL.2D1D', array['M_COMPENSATION_SIGN', 'M_MENTAL_ONE_NOT_GROUP', 'M_MENTAL_STOPS_SHORT']),
  ('DIV.3D1D', array['M_MENTAL_STOPS_SHORT'])
) as x(code, codes)
where s.code = x.code;
