-- The written methods' mistakes on the lists of the skills whose questions name them (goals/md2d2-multiplication-
-- methods.yaml, ADR 0055). MUL.2D1D, MUL.3D1D and MUL.2D2D print each calculation in every written method their levels
-- list; a step or a total can be a part with its tens taken as ones (M_PARTITION_TENS_AS_ONES), a grid added without its
-- ones-by-ones cell (M_GRID_CELL_DROPPED), the steps added without a carry (M_NOCARRY, addition's: assumption A11), a
-- step's own slips (x 1 taken as adding one, a zero too few, a carry dropped). The seed carries the lists for a new
-- database; a skill set is loaded insert-only, so one loaded before gets them here.
update public.skill_set s
set misconception_codes = array(select distinct c collate "C" from unnest(s.misconception_codes || x.codes) as c order by 1)
from (values
  ('MUL.2D1D', array['M_GRID_CELL_DROPPED', 'M_NOCARRY', 'M_ONE_ADDED', 'M_PARTITION_TENS_AS_ONES']),
  ('MUL.3D1D', array['M_NOCARRY', 'M_ONE_ADDED', 'M_PARTITION_TENS_AS_ONES', 'M_TENS_ZERO_DROPPED']),
  ('MUL.2D2D', array['M_GRID_CELL_DROPPED', 'M_MUL_NO_CARRY', 'M_NOCARRY', 'M_ONE_ADDED', 'M_PARTITION_TENS_AS_ONES', 'M_TENS_ZERO_DROPPED'])
) as x(code, codes)
where s.code = x.code;
