-- The taxonomy cases a question is (goal s12-worksheets-by-taxonomy), kept on the question so the worksheet
-- library can be read case by case. A derived label like `skill_codes` and `tags` (ADR 0030): measured by
-- code from the question's own tags against `taxonomy_case.match`, written when the question is made,
-- recomputed by `engine bank relabel`, and held true by `engine audit`. Never typed by a person.
alter table public.item add column case_codes text[] not null default '{}';
create index item_case_codes_idx on public.item using gin (case_codes) where status = 'active';
