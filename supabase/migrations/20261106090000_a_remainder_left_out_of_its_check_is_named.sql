-- A remainder left out of its check is named (goals/md4b2-equality.yaml, ADR 0066). A division checked by multiplying
-- back whose claim carries a remainder — 85 ÷ 4 = 21 r 1? 21 × 4 + 1 = □ (MD.EQUALITY's Advance), and DIV.2D1D's
-- Advance, whose wrong claims carry one (96 ÷ 4 = 21 r 2? 21 × 4 + 2 = □) — names the product written alone (84).
-- MD.EQUALITY is new and is loaded with its list; a skill set is loaded insert-only, so DIV.2D1D gets its here.
update public.skill_set s
set misconception_codes = array(select distinct c collate "C" from unnest(s.misconception_codes || x.codes) as c order by 1)
from (values
  ('DIV.2D1D', array['M_DIV_REMAINDER_LEFT_OUT'])
) as x(code, codes)
where s.code = x.code;
