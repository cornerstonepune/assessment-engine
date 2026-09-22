-- The school team's Addition & Subtraction Assessment Skill Taxonomy, one row per case (step 8e).
--
-- The document treats a question as its own case whenever a child can make a different kind of mistake
-- on it, and advises (§12) storing the dimensions as tags and selecting questions by combinations of
-- them, so that no case is "accidentally omitted". A row is exactly that: `match` is the combination of
-- tags (`assess/taxonomy.py` reads it), `example` the document's own example as a question the tag code
-- can measure, and `min_items` how many questions the bank must hold for the case to count as covered —
-- one worksheet's worth. `engine bank taxonomy` counts the bank against every row.
create table taxonomy_case (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  code           text not null,
  section        text not null,
  section_name   text not null,
  label          text not null,
  example_text   text not null default '',
  example        jsonb not null,
  match          jsonb not null,
  min_items      integer not null default 12 check (min_items > 0),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (tenant_id, code)
);

select internal.apply_conventions();
