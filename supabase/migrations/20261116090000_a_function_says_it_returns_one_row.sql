-- A function that returns one row says so (packages/engine/tests/test_db_plans.py). Postgres guesses 1,000 rows from a
-- function that returns a table. `pii.read_child` returns one row, a child's name, and every page that lists children
-- reads it once per child, so the Children page's query was guessed at 24,000 rows for 24 children, cost 653,786:
-- Postgres compiled it to machine code (JIT) before running it, 2,057 ms of compiling for 25 ms of work on a laptop,
-- past the page's 8 s on CI's runner ("This page could not load", main's browser job on 3d07f66, 2026-10-15).
-- `next_difficulty` returns one row on every path too. Planned as one row each, the same queries cost a few hundred
-- and are run, not compiled.
--
-- Written to run twice.

alter function pii.read_child(uuid, text) rows 1;
alter function public.next_difficulty(uuid, text) rows 1;
