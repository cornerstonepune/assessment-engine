-- The list form of a K2 page's steps and thinking (goals/m1-12b-apply-and-edit.yaml, task M1-12b).
-- Nimish, 2026-11-05: the site shows bullets with the keywords highlighted, never a wall of text, so a drafted page's
-- steps are a list and its thinking is an idea and a list of slips (a keyword and how to spot it).
--
-- Additive only, written to run twice. The text columns stay exactly what they were: they are what the school wrote or
-- what the lists read as, one bullet to a line, so nothing that reads them changes. The lists are the structured form of
-- the SAME words, kept so a screen need not pick a sentence apart; a reader trusts a list only while it reads out as the
-- text beside it (a text changed any other way leaves a stale list that is simply not used).
--   activity.steps_list     ["Show ten beads on the floor.", ...]
--   activity.thinking_doc   {"idea": "...", "slips": [{"keyword": "counts twice", "spot": "..."}]}

alter table activity
  add column if not exists steps_list    jsonb check (steps_list is null or jsonb_typeof(steps_list) = 'array'),
  add column if not exists thinking_doc  jsonb check (thinking_doc is null or jsonb_typeof(thinking_doc) = 'object');
