-- A kind of question is a row (ADR 0075, goals/sf1-a-kind-of-question-is-a-row.yaml). Until now every kind was a Python
-- function (`bands.NATIVE_GENERATORS`), so a new kind waited for a developer. Nimish, 2026-10-15: approval for "all
-- unique formats of questions", and an engine that "simply checks whether a certain question belongs to a certain
-- format".
--
-- `kind` is the row as the engine reads it (`assess/cards.py`):
--   - its words, with each number named in braces;
--   - the answer and each mistake, as formulas of those numbers;
--   - the examples it was made from.
-- The numbers' ranges are the level's, in `skill_set.difficulty`. Rows come from supabase/seed/question_formats.json,
-- the first draft only (`engine load` inserts, never overwrites), as skill sets do.
create table if not exists question_format (
  tenant_id       uuid not null references tenant(id) on delete cascade,
  code            text not null,
  skill_set_code  text not null,
  name            text not null,
  kind            jsonb not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  primary key (tenant_id, code),
  foreign key (tenant_id, skill_set_code) references skill_set (tenant_id, code) on delete cascade
);

select internal.apply_conventions();
