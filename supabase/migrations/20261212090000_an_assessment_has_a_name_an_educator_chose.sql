-- An educator names an assessment (goals/asm_assessments_page.yaml). Nimish, 2026-10-24: "we should ideally have the
-- ability to name the assessment. We should not use these file names."
--
--   assessment_name  one row each time an educator names (or renames) an assessment. Never edited (rule 4): the newest
--                    row for a key is the name; an assessment with none is named from its sheet's own code (topic,
--                    level, kind, class, day), built by the page. `key` is the assessment's own key on the site:
--                    kind~class~week~skill set. Names no child (rule 6).
--
-- Written to run twice.

create table if not exists assessment_name (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  key         text not null check (btrim(key) <> ''),
  name        text not null check (btrim(name) <> '' and char_length(name) <= 120),
  named_by    text not null check (btrim(named_by) <> ''),
  created_at  timestamptz not null default clock_timestamp(),
  updated_at  timestamptz not null default now()
);
create index if not exists assessment_name_key_idx on assessment_name (tenant_id, key, created_at desc);

drop trigger if exists assessment_name_kept on assessment_name;
create trigger assessment_name_kept before update or delete on assessment_name
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();

-- The website writes a name (the educator's own word, from the page), and only adds: the table is append-only.
do $$
begin
  if exists (select from pg_roles where rolname = 'app_web') then
    grant insert on assessment_name to app_web;
  end if;
end $$;
