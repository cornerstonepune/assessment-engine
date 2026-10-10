-- The written divisions' mistakes on the lists of the skills whose questions name them (goals/md3d-division-methods.yaml,
-- ADR 0063). DIV.2D1D and DIV.3D1D print each calculation in every written method their levels list; a step names its own
-- small operation's slips: a part's or an exchange's division (a smaller number divided by the bigger, a number divided by
-- itself read as nothing, a first digit skipped, a zero too many), a long division's or chunking's product (one row out,
-- x 1 as adding one, a carry dropped, a zero too few, 0 taken as 1) and what it leaves (smaller from larger, an exchange
-- not taken from, a fact off by one or ten, a zero dropped). The seed carries the lists for a new database; a skill set is
-- loaded insert-only, so one loaded before gets them here.
update public.skill_set s
set misconception_codes = array(select distinct c collate "C" from unnest(s.misconception_codes || x.codes) as c order by 1)
from (values
  ('DIV.2D1D', array['M_DIV_BIGGER_BY_SMALLER', 'M_DIV_LEAD_DROPPED', 'M_DIV_SELF_AS_ZERO', 'M_DIV_TENS_ZERO_EXTRA', 'M_ZERO_DROPPED']),
  ('DIV.3D1D', array['M_DIV_BIGGER_BY_SMALLER', 'M_FACT_PM1', 'M_FACT_PM10', 'M_MUL_NO_CARRY', 'M_MUL_ROW_OUT', 'M_NO_DECREMENT',
                     'M_ONE_ADDED', 'M_SMALL_FROM_LARGE', 'M_TENS_ZERO_DROPPED', 'M_ZERO_AS_ONE', 'M_ZERO_DROPPED'])
) as x(code, codes)
where s.code = x.code;
