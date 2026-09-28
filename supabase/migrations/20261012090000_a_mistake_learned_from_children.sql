-- A wrong answer no named mistake explains becomes a mistake the system knows (goals/s22-learned-mistakes.yaml).
-- Code finds the column rule that reproduces such answers on several questions and proposes it; a person names and
-- adopts it (or rejects it); an adopted rule joins the vocabulary and is predicted like the named mistakes.
alter table bank_proposal drop constraint bank_proposal_kind_check;
alter table bank_proposal add constraint bank_proposal_kind_check check (kind in ('mislevelled', 'new_mistake'));
alter table bank_decision drop constraint bank_decision_verdict_check;
alter table bank_decision add constraint bank_decision_verdict_check
  check (verdict in ('remove', 'keep', 'adopt', 'reject'));

create table learned_mistake (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,                  -- L_ + the rule's own hash: the same rule is the same code
  op           text not null check (op in ('+', '-')),
  rule         jsonb not null,                 -- `assess/learned_rules.py`: write, carry, to, last, align, turn
  proposal_id  uuid not null unique references bank_proposal(id),
  by           text not null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

create trigger learned_mistake_append_only before update or delete on learned_mistake
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
