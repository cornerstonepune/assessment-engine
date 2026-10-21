-- The website reads a skill's levels from their rows (goals/b1-levels-are-rows.yaml): its pages select
-- `skill_levels`, the one object the rows build, as the engine does. Our functions answer only those a migration
-- names (20261019090000), and 20261123090000 named only the engine, so the site's every page that reads a skill's
-- levels was refused ("permission denied for function skill_levels").

grant execute on function public.skill_levels(uuid, text) to app_web, app_engine;
