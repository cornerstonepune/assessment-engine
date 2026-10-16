-- Why a child has no paper this week (goals/ux5-papers-grouped.yaml). `assemble.for_week` never hands a child a short
-- paper or a repeat: it names them with the reason — the library holds no worksheet at their level, they have sat every
-- one, or every one left shares a question with another child's paper — and returned that reason to whoever ran it,
-- where nothing kept it. The class's papers to approve showed such a child nowhere. The reason is kept on their plan
-- for the week; handing them a paper clears it.
alter table prescription add column no_paper text;

comment on column prescription.no_paper is
  'Why the week''s assembly could not give this child a paper, in words; null once they have one (w2_print/assemble.py).';
