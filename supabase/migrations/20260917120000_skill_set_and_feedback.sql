-- W1: the skill-set spec as rows, and the staff flag that retires an item.
-- A skill set is what Neha and Achal author and Aseem ratifies (workflow N1): one row per set,
-- the difficulty bands as JSON — words for the prompt, a `check` object for the verifier.

create table skill_set (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  code                 text not null,                       -- ADD.2D.REG, SUB.2D.EXCH …
  rung_code            text not null,
  name                 text not null,
  learning_objective   text not null,
  philosophy           text[] not null default '{}',        -- set-specific lines; school-wide ones live in config
  formats              text[] not null default '{}',
  misconception_codes  text[] not null default '{}',
  difficulty           jsonb not null,                      -- {"Easy": {"words": …, "check": {…}}, …}
  status               text not null default 'draft' check (status in ('draft', 'ratified')),
  ratified_by          text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (tenant_id, code),
  foreign key (tenant_id, rung_code) references rung (tenant_id, code)
);
create index skill_set_rung_idx on skill_set (tenant_id, rung_code);

-- A generated item belongs to the skill set and difficulty it was generated for; that is how
-- W2 draws "SUB.2D.EXCH at Hard" for a child. Legacy items leave both null.
alter table item
  add column skill_set_code text,
  add column difficulty     text check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance'));
create index item_skill_set_idx on item (tenant_id, skill_set_code, difficulty) where status = 'active';

-- Any staff member, any item, after the fact. A 'retire' verdict pulls the item by trigger so
-- every writer — engine, app, SQL — gets the same effect.
create table item_feedback (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  item_id     uuid not null references item(id) on delete cascade,
  actor       text not null,
  verdict     text not null check (verdict in ('retire', 'keep')),
  note        text not null default '',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index item_feedback_item_idx on item_feedback (item_id);

create or replace function internal.retire_flagged_item() returns trigger
language plpgsql as $$
begin
  if new.verdict = 'retire' then
    update item set status = 'retired' where id = new.item_id;
  end if;
  return new;
end $$;

create trigger retire_flagged_item after insert on item_feedback
  for each row execute function internal.retire_flagged_item();

select internal.apply_conventions();
