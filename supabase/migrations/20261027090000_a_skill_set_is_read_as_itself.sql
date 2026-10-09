-- A skill set is read as itself (goals/md0c-a-skill-set-is-read-as-itself.yaml).
--
-- Every report, the graph's own functions and the website read a skill set through its rung (`skill_set.rung_code`),
-- and nothing kept a second skill set off a rung: two on one rung would each be read as whichever came last. The
-- seed has always put one on each; this says so where it cannot be broken (ADR 0048). A new skill set gets a rung of
-- its own, as every row in `supabase/seed/rungs.json` does.
drop index if exists skill_set_rung_idx;
create unique index if not exists skill_set_one_per_rung on skill_set (tenant_id, rung_code);

-- The one sign an operation is written as, from however a question's spec writes it: its first character, folded as
-- the engine folds it (`assess/operations.sign`, held to this by a test). A two-step story's "+-" is its first step's.
create or replace function public.operation_sign(p_op text)
returns text
language sql immutable as $$
  select case left(p_op, 1)
    when '+' then '+' when '-' then '-' when '−' then '-' when '–' then '-'
    when '×' then '×' when 'x' then '×' when 'X' then '×' when '*' then '×'
    when '÷' then '÷' when '/' then '÷' when ':' then '÷'
  end
$$;

-- A mistake's name, by one rule the engine's `core/mistake_names.name_of` also follows (held to it by a test): the
-- name for the question's own operation (`p_op`, its spec's), else for the operation of the skill the mistake was
-- charged to (`skills.by_operation`, read backwards); failing that operation's own row, its name for any operation;
-- else the one name all its rows share; else its code. `M_WRONG_OP` is three mistakes in three operations, and the
-- website took whichever row came first: a subtraction's wrong answer read "added instead of multiplying".
create or replace function public.mistake_name(p_code text, p_skill text, p_op text default null)
returns text
language sql stable as $$
  with op as (
    select coalesce(
      operation_sign(p_op),
      (select e.key from config c, jsonb_each_text(c.value) e
        where c.key = 'skills.by_operation' and e.value = p_skill limit 1)) as key
  ), named as (
    select op, name from misconception where code = p_code
  )
  select coalesce(
    (select name from named where op = (select key from op) limit 1),
    (select name from named where op = 'any' limit 1),
    (select min(name) from named having count(distinct name) = 1),
    p_code)
$$;

grant execute on function public.operation_sign(text) to app_web, app_engine;
grant execute on function public.mistake_name(text, text, text) to app_web, app_engine;
