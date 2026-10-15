-- A class has one grade (goals/ux2-one-count-one-thing.yaml). The engine took a class's grade as the one most of its
-- active children are in, the lower on a tie (`roster.class_band`); the website took it three ways — that, the lowest
-- of them, and a paper's own — so a Grade 2 class given a Grade 1 worksheet had its papers said "Grade 1". The rule is
-- the database's now, and the engine and every page ask it. None for a class with no active child.
--
-- Written to run twice.

create or replace function public.class_band(tenant uuid, section text) returns text
language sql stable set search_path = public as $$
  select c.band from child c
  where c.tenant_id = $1 and c.section = $2 and c.active
  group by c.band
  order by count(*) desc, c.band
  limit 1
$$;

grant execute on function public.class_band(uuid, text) to app_web;

select internal.apply_conventions();
