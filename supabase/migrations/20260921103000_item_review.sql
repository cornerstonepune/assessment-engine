-- The reviewers' verdicts, as rows a person can act on (BUILD-ORDER W1 gate 4, amended).
--
-- Two narrow advisory passes — `pedagogy_review` (does this test the claimed skill, rung and
-- signal?) and `language_review` (can a child of this grade read it?). A verdict is advice: it
-- never changes an item's status by itself. `ref` is the item_key for an item, or
-- "template:<skill_set>:<band>" for the band's own rule, which is judged once per ADR 0010 —
-- the whole point is that language is paid for per pattern, not per question.

create table item_review (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  reviewer        text not null check (reviewer in ('pedagogy_review', 'language_review')),
  skill_set_code  text not null,
  difficulty      text not null check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance')),
  ref             text not null,                       -- item_key, or template:<code>:<band>
  verdict         text not null check (verdict in ('pass', 'revise', 'reject')),
  reasons         text[] not null default '{}',
  note            text not null default '',
  prompt_id       uuid references prompt(id),
  model           text,
  flow_run_id     uuid references flow_run(id),
  acted_on_by     text,                                -- the person who agreed or overruled
  acted_at        timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (tenant_id, reviewer, ref)
);
create index item_review_open_idx on item_review (tenant_id, verdict)
  where acted_on_by is null and verdict <> 'pass';

select internal.apply_conventions();
