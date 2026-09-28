-- The bank learns from children's answers and proposes; a person decides (step 7, goals/s21-real-difficulty.yaml).
-- Both append-only: a proposal is what the evidence said when it was made, a decision is who decided what and why.
-- One decision per proposal. A proposal still open is one with no decision.
create table bank_proposal (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  kind        text not null check (kind in ('mislevelled')),  -- a question far easier or harder than its level
  subject     text not null,                -- what it is about: the question's item_key
  direction   text not null,                -- 'easier' or 'harder' than its level
  evidence    jsonb not null,               -- {n, correct, p_correct, difficulty, skill_set_code} when proposed
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index bank_proposal_subject_idx on bank_proposal (tenant_id, kind, subject);

create table bank_decision (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  proposal_id  uuid not null unique references bank_proposal(id),
  verdict      text not null check (verdict in ('remove', 'keep')),
  by           text not null,
  note         text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create trigger bank_proposal_append_only before update or delete on bank_proposal
  for each statement execute function internal.forbid_change();
create trigger bank_decision_append_only before update or delete on bank_decision
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
