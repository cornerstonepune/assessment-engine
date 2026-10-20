-- A child's states and the subject are read from rows (goals/b0d-states-and-subject-from-tables.yaml, ADR 0085).
--
-- Nimish, 2026-10-20: "we need proper tables". B0a made `child_state` (code, order, words, colour, whether a next paper
-- works on it), and nothing read it: every rule about a state was a list in code — which wait on too few answers, how
-- the children table takes a skill set's worst skill, which are ready to move up, which may be nearly secure, how
-- Friday's card groups them, the reason a paper prints. Each is now a column, set to exactly what the list said, so no
-- paper, page or map changes. Each colour's words are rows too (`state_colour`), and a state's colour a key into them.
-- A subject gains the word its pages say it by (`label`: "Maths" for "Mathematics — Number").
--
-- The rows are supabase/seed/vocabulary.json's, made here for every school, there now or added later (as B0a's are);
-- a load keeps them (engine/core/vocabulary.py), and tests/test_states_and_subject.py compares both with the code's
-- old answers. Written to run twice.

create table if not exists state_colour (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,                       -- red, amber, green, grey: the website's four
  ord          int not null,                        -- what needs help first
  words        text not null,                       -- the colour's own words, in a key or a legend: "got it"
  count_words  text not null,                       -- a count of skills that colour: "3 secure"
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

-- Each has a default, the plain answer for a state nobody has described: B0a's internal.school_vocabulary still writes
-- a new school's states with its five columns, and Postgres checks NOT NULL before ON CONFLICT, so without one it
-- could not add a school. internal.school_states below then writes each seeded state's own values.
alter table child_state add column if not exists enough boolean not null default true;  -- false: too few answers yet
alter table child_state add column if not exists severity int not null default 0;  -- the children table counts a
                                              -- skill set as its most severe skill's state; unset is the most severe,
                                              -- so a state nobody described is shown, never hidden
alter table child_state add column if not exists move_up boolean not null default false;  -- ready to move up a level
alter table child_state add column if not exists nearly boolean not null default false;   -- a set in it may be nearly
                                                                                          -- secure
alter table child_state add column if not exists card_group text;   -- its group on Friday's class card; none: its own
alter table child_state add column if not exists why text;          -- the reason a paper prints; {threshold.key} is
                                                                    -- that row's share, in words

-- A school's colours, and its states whole: the seed's values, for every school there now or added later.
create or replace function internal.school_states(p_tenant uuid) returns void
language plpgsql as $$
begin
  insert into state_colour (tenant_id, code, ord, words, count_words)
  select p_tenant, v.code, v.ord, v.words, v.count_words
  from (values
    ('red', 0, 'needs help', 'needs help'),
    ('amber', 1, 'practising', 'practising'),
    ('green', 2, 'got it', 'secure'),
    ('grey', 3, 'not enough yet', 'too few answers')
  ) v (code, ord, words, count_words)
  on conflict (tenant_id, code) do nothing;

  insert into child_state (tenant_id, code, ord, words, colour, needs_work, enough, severity, move_up, nearly,
                           card_group, why)
  select p_tenant, v.code, v.ord, v.words, v.colour, v.needs_work, v.enough, v.severity, v.move_up, v.nearly,
         v.card_group, v.why
  from (values
    ('patterned_error', 0, 'repeating mistake', 'red', true, true, 1, false, false, 'reteach',
     'the same mistake more than once'),
    ('emerging', 1, 'under half right', 'red', true, true, 2, false, false, 'emerging',
     'fewer than {next_sheet.demote_below} right'),
    ('practising', 2, 'practising', 'amber', true, true, 3, false, true, 'practising',
     'not yet {next_sheet.promote_at} right'),
    ('secure', 3, 'secure', 'green', false, true, 5, false, false, 'secure',
     '{next_sheet.promote_at} right — a step up'),
    ('stretch_ready', 4, 'ready to move up', 'green', false, true, 5, true, false, 'move_up', 'ready to move up'),
    ('not_enough_yet', 5, 'not enough yet', 'grey', false, false, 4, false, false, 'not_enough_yet', null)
  ) v (code, ord, words, colour, needs_work, enough, severity, move_up, nearly, card_group, why)
  -- the seed's values, as a load writes them (engine/core/vocabulary.py): over B0a's defaults on a new school
  on conflict (tenant_id, code) do update set
    enough = excluded.enough, severity = excluded.severity, move_up = excluded.move_up, nearly = excluded.nearly,
    card_group = excluded.card_group, why = excluded.why;
end $$;

create or replace function internal.school_states_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.school_states(new.id);
  return new;
end $$;

-- Named to fire before B0a's school_vocabulary (Postgres fires a table's triggers in name order): a state's colour is
-- a key, so a new school's colours are written before any of its states.
drop trigger if exists school_states on tenant;
create trigger school_states after insert on tenant
  for each row execute function internal.school_states_on_new_school();

select internal.school_states(id) from tenant;

-- One state says "too few answers": the one a skill no answer has reached reads as.
create unique index if not exists child_state_one_too_few on child_state (tenant_id) where not enough;

-- A state's colour is one of the school's colours.
alter table child_state drop constraint if exists child_state_tenant_id_colour_fkey;
alter table child_state add constraint child_state_tenant_id_colour_fkey
  foreign key (tenant_id, colour) references state_colour (tenant_id, code);

-- What a subject's pages call it; none: its name. Maths' is what its pages have said until now.
alter table subject add column if not exists label text;
update subject set label = 'Maths' where code = 'NUM' and label is null;

select internal.apply_conventions();
