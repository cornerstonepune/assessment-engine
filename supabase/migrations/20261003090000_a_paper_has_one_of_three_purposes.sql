-- U4 (goals/u4-papers.yaml): a paper has one of three purposes — class practice, class assessment, or the
-- child's own next paper sent home (`focus`). Nimish, 2026-09-23: "home assignments are not a separate
-- purpose" — a home paper is the child's next paper, so `home` leaves the prescription's kinds, and a
-- printed copy's kind is held to the three.
alter table prescription drop constraint if exists prescription_kind_check;
alter table prescription add constraint prescription_kind_check check (kind in ('practice', 'assessment'));

alter table sheet_instance add constraint sheet_instance_kind_check
  check (kind is null or kind in ('practice', 'assessment', 'focus'));

-- A paper generated before step 7 found its week only through its template, so it was missing from any list read
-- by class, week and purpose. Each now records its own: a child's paper takes its child's class and its
-- prescription's purpose; a spare takes the class only when one class of its grade had papers that week.
update sheet_instance si
   set week = st.week,
       section = c.section,
       kind = coalesce((select p.kind from prescription p where p.sheet_instance_id = si.id limit 1), 'practice')
  from sheet_template st, child c
 where st.id = si.sheet_template_id and c.id = si.child_id
   and st.source = 'generated' and st.week is not null and si.week is null;

update sheet_instance si
   set week = st.week, section = one.section, kind = 'practice'
  from sheet_template st,
       lateral (select min(c.section) as section, count(distinct c.section) as n
                  from sheet_template t join child c on c.id = t.child_id
                 where t.source = 'generated' and t.week = st.week and t.band = st.band) one
 where st.id = si.sheet_template_id and si.child_id is null
   and st.source = 'generated' and st.week is not null and si.week is null and one.n = 1;
