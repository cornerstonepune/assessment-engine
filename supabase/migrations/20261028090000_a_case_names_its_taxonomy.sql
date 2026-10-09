-- A taxonomy case belongs to one of the school's documents (goals/md1-taxonomy-rows.yaml): the addition and
-- subtraction taxonomy's 270 cases, or the multiplication and division taxonomy's 247. Each case's match names it as
-- well, so a question is a case of its own operations' document only (a × odd-or-even question is never R06); this
-- column is what `engine bank taxonomy` counts by, and what keeps the two documents' sections apart (both have a §11).
-- Every row here before this migration is the addition and subtraction document's.
alter table public.taxonomy_case add column if not exists taxonomy text not null default 'ADD_SUB';
alter table public.taxonomy_case alter column taxonomy drop default;
