-- Versioned rules, provenance on every item (BUILD-ORDER W1 gate 4 amendment, 2026-09-19;
-- external architecture proposal §15 "immutable versioning").
--
-- Editing a skill-set rule in the app used to rewrite the row every existing item had been
-- generated from, so "why did the engine give this child this question on that date" stopped
-- being answerable the moment a band was corrected. Now an edit that changes the *rule* files the
-- previous rule in skill_set_version and bumps `version`; ratifying (a status change only) does
-- not, because approving a rule is not writing a new one. Every item records the version,
-- generator, prompt and model that produced it.

alter table skill_set add column version integer not null default 1;

create table skill_set_version (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  code                 text not null,
  version              integer not null,
  rung_code            text not null,
  name                 text not null,
  learning_objective   text not null,
  philosophy           text[] not null,
  formats              text[] not null,
  misconception_codes  text[] not null,
  difficulty           jsonb not null,
  eval_type            eval_type not null,
  status               text not null,
  ratified_by          text,
  valid_from           timestamptz not null,               -- when this rule became current
  valid_to             timestamptz not null default now(), -- when it was replaced
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (tenant_id, code, version)
);

create or replace function internal.skill_set_version_on_change() returns trigger
language plpgsql as $$
begin
  if row(new.rung_code, new.name, new.learning_objective, new.philosophy, new.formats,
         new.misconception_codes, new.difficulty, new.eval_type)
     is distinct from
     row(old.rung_code, old.name, old.learning_objective, old.philosophy, old.formats,
         old.misconception_codes, old.difficulty, old.eval_type) then
    insert into skill_set_version (tenant_id, code, version, rung_code, name, learning_objective,
      philosophy, formats, misconception_codes, difficulty, eval_type, status, ratified_by, valid_from)
    values (old.tenant_id, old.code, old.version, old.rung_code, old.name, old.learning_objective,
      old.philosophy, old.formats, old.misconception_codes, old.difficulty, old.eval_type,
      old.status, old.ratified_by, old.updated_at);
    new.version := old.version + 1;
    -- A changed rule is a new draft. The old ratification approved the old rule, not this one.
    new.status := 'draft';
    new.ratified_by := null;
  end if;
  return new;
end $$;

-- Named to sort before touch_updated_at (both BEFORE UPDATE; Postgres runs them alphabetically),
-- so valid_from above reads the old row's own updated_at before the touch trigger moves it.
create trigger skill_set_version_on_change before update on skill_set
  for each row execute function internal.skill_set_version_on_change();

alter table item
  add column skill_set_version  integer,
  add column generator          text,       -- sampled:+ | native:balance_scale | model:item_generate
  add column prompt_id          uuid references prompt(id),
  add column model              text;

-- Everything already in the bank predates provenance. Version 1 is true (no rule has been edited
-- since it was loaded); the generator is recorded as unknown rather than reconstructed from a
-- plausible story — a guess written into a provenance column is worse than a blank.
update item set skill_set_version = 1, generator = 'pre-provenance'
  where skill_set_code is not null and generator is null;

select internal.apply_conventions();
