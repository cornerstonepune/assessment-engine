-- A taxonomy case belongs to one of the school's documents (goals/md1-taxonomy-rows.yaml): the addition and
-- subtraction taxonomy's 270 cases, or the multiplication and division taxonomy's 247. Each case's match names it as
-- well, so a question is a case of its own operations' document only (a × odd-or-even question is never R06); this
-- column is what `engine bank taxonomy` counts by, and what keeps the two documents' sections apart (both have a §11).
--
-- Every row made before this column is the addition and subtraction document's, and so is every row of a copy taken
-- before it: the default says so, and stays, because a copy is restored into the schema as the migrations now build it
-- (the rehearsal of update-live does exactly that). The loader writes the column for every row it loads from the seed,
-- and the seed names it on every row (tests/test_md_cases.py), so the default fills only rows older than the column.
alter table public.taxonomy_case add column if not exists taxonomy text not null default 'ADD_SUB';
