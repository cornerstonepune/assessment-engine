-- Aseem's five Grade 3 reports, transcribed once: the target output of the whole pipeline, written
-- by hand (W3's gold, ADR 0028). One row per finding — a concept he called strong or faulty for one
-- child; the question on the child's own papers that shows it, where there is one; the answer he
-- quotes; the named mistake where his words name a method the vocabulary holds; and his own words,
-- with the child's name taken out. Keyed by child_id, never a name (rule 6). A person confirms the
-- transcription before `engine gold check` trusts it, and changing a row withdraws that confirmation.
create table gold_finding (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  child_id            uuid not null references child(id) on delete cascade,
  verdict             text not null check (verdict in ('strong', 'faulty')),
  skill_code          text not null,
  item_key            text,
  expect_mark         text check (expect_mark in ('correct', 'wrong')),
  child_answer        text,
  misconception_code  text,
  words               text not null,
  source              text not null,
  confirmed_by        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint gold_finding_one_per_example
    unique nulls not distinct (tenant_id, child_id, verdict, skill_code, item_key)
);
create index gold_finding_child_idx on gold_finding (tenant_id, child_id);

select internal.apply_conventions();
