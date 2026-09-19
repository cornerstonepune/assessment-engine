-- How a question is evaluated is a property of the question, declared in rows.
--
-- Four kinds of assessable thing, and they differ in the only two ways that matter to this
-- engine: how the question is produced, and how a wrong answer is recognised.
--
--   computable      a formula with slots. Code enumerates the questions, computes the answer,
--                   and computes what each named mistake would produce. All of maths so far.
--   closed_set      the answer space is a table of content that already exists (capitals,
--                   dates, vocabulary, a labelled diagram). Marked by exact match; the wrong
--                   options are the confusable neighbours from that same table.
--   rule_governed   a checker decides (grammar, spelling, a balanced equation, significant
--                   figures). The rule violations ARE the misconception list.
--   open_response   no enumerable answer set. Marked against a rubric by a person or a model,
--                   and its mistakes are DISCOVERED by clustering what children actually wrote,
--                   never predicted in advance.
--
-- The engine may only auto-mark the first three. An open_response question routes to a person
-- with its rubric, which is what `subject.mark_mode = 'rubric'` already says at subject level —
-- this says it per question, because one paper mixes them (find-the-mistake asks for a tick, a
-- number AND a sentence).
--
-- Only `computable` has an evaluator today. The other three are named here so the engine can
-- refuse them loudly instead of silently marking a question it does not understand; each gains
-- its evaluator when a subject needs it.

create type eval_type as enum ('computable', 'closed_set', 'rule_governed', 'open_response');

alter table skill_set add column eval_type eval_type not null default 'computable';
alter table item      add column eval_type eval_type not null default 'computable';

comment on column skill_set.eval_type is
  'How questions in this set are evaluated. A row, so a coordinator can say it without a deploy.';
comment on column item.eval_type is
  'Stamped from the skill set when the item is generated, so marking never has to re-derive it.';

create index item_eval_type_idx on item (tenant_id, eval_type) where status = 'active';

select internal.apply_conventions();
