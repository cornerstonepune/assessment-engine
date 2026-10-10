-- "Three times as many" read as three more is its own mistake, M_TIMES_AS_MORE (goals/md2d1-multiplication-models.yaml):
-- a story that says times as many names adding its two numbers that way, not as the wrong operation chosen. MUL.2D1D's
-- Advance holds such stories (B08), so its list names the mistake its questions now show. A database built now gets the
-- same from the seed; this is the change for one loaded before. The mistake list is not a level's words, so no approval
-- is withdrawn (internal.skill_set_version_on_change); the mistake's own row comes with the seed (`engine load`).
update skill_set set misconception_codes = array_append(misconception_codes, 'M_TIMES_AS_MORE')
 where code = 'MUL.2D1D' and not ('M_TIMES_AS_MORE' = any(misconception_codes));
