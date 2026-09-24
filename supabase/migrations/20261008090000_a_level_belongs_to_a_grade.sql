-- A skill's levels can belong to different grades: 2-digit + 1-digit at Easy and Medium is Grade 1's, at Hard and
-- Advance Grade 2's (Nimish, 2026-09-24). Each level belongs to one grade. {level: band}; a level not named here
-- belongs to the skill's own grade (its rung's band). Its own column, outside `skill_set_version_on_change`: which
-- grade teaches a level is not the level's words, and moving it does not withdraw the skill's approval.
alter table skill_set add column if not exists level_band jsonb not null default '{}'::jsonb;
alter table skill_set drop constraint if exists skill_set_level_band_shape;
alter table skill_set add constraint skill_set_level_band_shape check (jsonb_typeof(level_band) = 'object');
