-- A skill set the school has replaced is retired, not deleted (goals/s13-levels-by-taxonomy.yaml).
--
-- The calculation skills were steps of a ladder that put addition and subtraction in one skill and changed
-- the kind of question from level to level. They are replaced by one skill per operation and digit shape,
-- read from the taxonomy (ADR 0034). A retired set keeps its row, so every paper printed from it, every
-- question it once held and every answer recorded against it still names it; nothing builds from it again.
-- Who retired it and when are kept on the row, as ratification is.

alter table skill_set drop constraint skill_set_status_check;
alter table skill_set add constraint skill_set_status_check check (status in ('draft', 'ratified', 'retired'));
alter table skill_set add column retired_by text;
alter table skill_set add column retired_at timestamptz;
alter table skill_set add constraint skill_set_retired_says_who
  check ((status = 'retired') = (retired_by is not null and retired_at is not null));
