-- One answer counts once, and one roll order (goals/p0-one-answer-counts-once.yaml).
--
-- A signed-off answer is evidence for every skill its question tests: a right answer writes one row per skill, all on
-- the question's rung (`answer_evidence`), and on 2026-09-30 10,437 of 21,176 active questions tested two or more.
-- The graph counts per skill, so a row per skill is right there. But the report card, the parent report and a
-- child's answer count added rows on a rung and called them answers: a right answer counted two or three times, a
-- wrong one once (code review, 2026-09-30). `answer_placed` is one row per answer, its latest batch, for every count
-- of answers to read.

create or replace view answer_placed with (security_invoker = true) as
select coalesce(e.item_result_id, e.id) as answer,
       e.item_result_id, e.tenant_id, e.child_id, e.placed_rung, e.correct, e.confirmed_by, e.observed_at,
       array_agg(distinct e.skill_code order by e.skill_code) as skill_codes,
       coalesce(array_agg(distinct m.code order by m.code) filter (where m.code is not null), '{}') as misconception_codes
from evidence_placed e
left join lateral unnest(e.misconception_codes) as m(code) on true
group by coalesce(e.item_result_id, e.id), e.item_result_id, e.tenant_id, e.child_id, e.placed_rung, e.correct,
         e.confirmed_by, e.observed_at;

-- The order a class is listed in: by the number in the roll ("2" before "10", "12A" after "12"), then by the roll
-- itself; a roll with no number last. It was written out twelve times, three of them in the website as '\D' inside a
-- JS template, which reaches Postgres as 'D', so a roll with a letter in it broke the page's `::int` (2026-09-30).
create or replace function public.roll_order(roll text)
returns integer
language sql immutable parallel safe as $$
  select coalesce(substring(roll from '\d{1,9}')::integer, 2147483647)
$$;
