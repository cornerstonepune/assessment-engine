-- The website's role does not compile a query to machine code (packages/engine/tests/test_db_plans.py).
--
-- Postgres compiles a query first (JIT) when it guesses the query costly. That pays for a long report and never for a
-- page, whose queries take milliseconds. Its guesses are wrong wherever a query reads rows out of a function: such a
-- function is guessed at 100 or 1,000 rows unless it says otherwise. Migration 20261116090000 made our own functions
-- say so; Postgres's own cannot. A skill's page counts its mistakes through `jsonb_array_elements` and
-- `jsonb_object_keys`: guessed at 8,730,000 rows for 3,530, it compiled for 366 ms to work for 40 ms on a laptop, and
-- for 4 s on CI's runner, where the page's heading missed its 5 s (PR #213's browser job on 3135c85, 2026-10-15).
--
-- So the website's sessions never compile. The engine's batch work keeps Postgres's own choice. A role's setting
-- applies to each session it opens from now on, through the pooler too.
--
-- Written to run twice.

alter role app_web set jit = off;
