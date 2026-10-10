-- A skill's mistakes are the ones its own questions can show (goals/as1-every-listed-case-draws.yaml). The audit drew
-- a level made of cases from its raw rows, numbers of any size, so it counted mistakes no level of the skill makes:
-- two 1-digit numbers have no column sums to write side by side and no exchange to forget, and two numbers of one
-- length cannot be lined up from the left. Drawn as the bank draws them, these four claims are mistakes no question of
-- these skills can show. A database built now gets the same from the seed; this is the change for one loaded before.
-- The mistake list is not a level's words, so no approval is withdrawn (internal.skill_set_version_on_change).
update skill_set set misconception_codes = array_remove(misconception_codes, 'M_CONCAT')
 where code = 'ADD.1D1D';
update skill_set set misconception_codes = array_remove(misconception_codes, 'M_ALIGN_LEFT')
 where code in ('ADD.3D3D', 'SUB.2D2D');
update skill_set
   set misconception_codes = array_remove(array_remove(misconception_codes, 'M_NO_DECREMENT'), 'M_SMALL_FROM_LARGE')
 where code = 'SUB.1D1D';
