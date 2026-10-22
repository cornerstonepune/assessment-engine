-- A person approves a way of asking on the website (E0, goals/e0-english-in-the-system.yaml), and the approval is a row
-- added to `question_type_approval`. The migration that made the table said "the engine and the website may add one, not
-- change or remove it" and took the website's update, delete and truncate away, but the website holds only select on a
-- table it was not named in (20261021090000), so its insert was refused: "permission denied for table
-- question_type_approval". Insert only; an approval is never edited.
do $$
begin
  if exists (select from pg_roles where rolname = 'app_web') then
    grant insert on question_type_approval to app_web;
  end if;
end $$;
