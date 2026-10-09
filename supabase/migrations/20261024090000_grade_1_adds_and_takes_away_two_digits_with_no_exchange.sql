-- Grade 1 as its educator taught it to September (Nimish, 2026-10-06; goals/g1-taught-till-september.yaml): 2-digit
-- + and − a 1-digit or a 2-digit number, with no exchange — 46 + 12, 25 − 13, 28 − 8 — is Grade 1 work. The Easy
-- level of each of these four skills is exactly that (no carry, no exchange), so it moves to Grade 1; their other
-- levels stay Grade 2. A database built now gets the same from the seed (`level_band` in skill_sets.json): this is
-- the one change for a database whose skills were loaded before. A level a person moved elsewhere stays moved, and
-- the move changes no level's words, so no approval is withdrawn (`internal.skill_set_version_on_change`).
update skill_set set level_band = level_band || '{"Easy": "G1"}'::jsonb
 where code in ('ADD.2D1D', 'ADD.2D2D', 'SUB.2D1D', 'SUB.2D2D');
