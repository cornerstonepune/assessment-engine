-- How far the reader is trusted on each kind of question (ADR 0032, goals/ny2-the-queue-shrinks.yaml): one rule, here,
-- that the engine marks by (`profiles.kind_trust`) and the website shows (`queries-read.readerReport`). Until now each
-- decided it for itself: the engine in Python, the website in its own SQL over a window its code wrote again, ordered
-- by when the paper was read alone — which every answer of a paper shares, so where the window's last check fell inside
-- a paper its count was arbitrary.
--
-- A kind's checks are the answers a person settled that the reader stood behind (`answer_checked.stood`), newest first:
-- by when the paper was read, then the question, then the answer, so the window is the same every time it is read. Its
-- standing is the newest `marking.agreement_window` of them: how many there are, how many matched the person, trusted
-- once there are that many and `marking.agreement_gate` of them matched.

-- The right checks still needed, one after another, before the window holds enough of them: none once trusted.
-- `recent` is the kind's checks, newest first, true where the reader matched the person. After k more right checks the
-- window is those k and the newest (size - k) of the rest; the answer is the fewest k that makes it trusted. At most
-- `size`: a window of right checks alone is always trusted.
create or replace function public.checks_to_trust(recent boolean[], size int, bar float) returns int
language sql immutable as $$
  select min(k)::int from generate_series(0, size) k
   where k + least(coalesce(cardinality(recent), 0), size - k) >= size
     and (k + (select count(*) from unnest(recent[1:size - k]) r where r))::float >= bar * size
$$;

create or replace view kind_trust with (security_invoker = true) as
with gate as (
  select coalesce((select value::float from threshold where key = 'marking.agreement_gate'), 0.95) as bar,
         coalesce((select value::int from threshold where key = 'marking.agreement_window'), 50) as size
), checks as (
  select a.tenant_id, a.fmt, a.reader_right,
         row_number() over (partition by a.tenant_id, a.fmt
                            order by a.read_at desc, a.item_key desc, a.item_result_id desc) as rn
    from answer_checked a
   where a.stood
)
select c.tenant_id, c.fmt,
       count(*) filter (where c.rn <= g.size)::int as n,
       count(*) filter (where c.rn <= g.size and c.reader_right)::int as "right",
       count(*) filter (where c.rn <= g.size) >= g.size
         and count(*) filter (where c.rn <= g.size and c.reader_right) >= g.bar * g.size as trusted,
       public.checks_to_trust(array_agg(c.reader_right order by c.rn) filter (where c.rn <= g.size), g.size, g.bar)
         as checks_to_trust
  from checks c cross join gate g
 group by c.tenant_id, c.fmt, g.size, g.bar;
comment on view kind_trust is
  'Each kind of question''s standing against marking.agreement_gate over its newest marking.agreement_window checks '
  'the reader stood behind (ADR 0032): n, right, trusted, and the right checks still needed. The one rule the engine '
  'marks by and the website shows.';

grant execute on function public.checks_to_trust(boolean[], int, float) to app_web, app_engine;
grant select on kind_trust to app_web, app_engine;
