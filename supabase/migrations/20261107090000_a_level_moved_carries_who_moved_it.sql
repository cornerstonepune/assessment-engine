-- A level moved to another grade carries who moved it and when (goals/c1-whole-curriculum.yaml). Achal reviews the
-- multiplication and division progression on the Curriculum and moves levels between grades there (Nimish,
-- 2026-10-11: "Achal will make the changes later on the curriculum page or move certain stuff by grades"); every
-- decision on the site is in the name of whoever took it. Outside `skill_set_version_on_change`'s columns, as
-- `level_band` is: which grade teaches a level is not its words, and a move does not withdraw the skill's approval.
alter table skill_set add column if not exists level_band_by text;
alter table skill_set add column if not exists level_band_at timestamptz;
alter table skill_set drop constraint if exists skill_set_level_band_moved_by_someone;
alter table skill_set add constraint skill_set_level_band_moved_by_someone
  check ((level_band_by is null) = (level_band_at is null));
