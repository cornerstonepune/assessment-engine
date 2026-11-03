-- K2 voice notes, the tables (goals/m1-01-voice-intake.yaml, task M1-01 step 3). Additive only: new tables, their
-- vocabulary rows and two config rows; nothing existing is altered, dropped or rewritten.
--
-- After an activity a K2 educator records one short note, saying children as their roll numbers (enrolment.roll_no).
-- The engine reads it into draft lines by code (engine/w3_read/voice_note.py); she confirms; only then are rows
-- written here, one per child, by code. Nothing here is evidence yet: evidence_event rows follow in step 5.
--   * pii.educator_note       one row per voice note: where its audio is kept (a key into private storage, never the
--                             audio), its transcript, when it reached us (the server's clock) and where it stands
--                             (received, drafted, confirmed, left unconfirmed). The audio is a child's classroom, so
--                             it is on the private side; the website has no grant on it.
--   * pii.note_claim          each draft line of a confirmed note: what code read, the words it came from, and what
--                             she did with it (accepted, changed, removed). Her changes are the reader's accuracy
--                             record. Written once, at confirm; never edited.
--   * activity_observation    one row per child per activity she confirmed: the outcome (above, below, as expected,
--                             not willing, absent), how the child came to be named (individually, or as "the rest
--                             did as expected"), by voice or the form, the level she expected, the two clocks, who
--                             observed and who confirmed (staff ids). Never edited or deleted: a correction is a new
--                             row naming the row it replaces and why. A child not mentioned gets no row (not seen).
-- The words are rows (rule 1): outcomes, entry modes, routes, note statuses, claim decisions. How long a note may wait
-- for her (48 hours) and how long audio is kept (not yet decided: O-14) are config rows, never code.
--
-- Written to run twice.

-- The words, each a row for every school.
create table if not exists observation_outcome (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  code       text not null,
  ord        int not null,
  words      text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists observation_entry_mode (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  code       text not null,
  ord        int not null,
  words      text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists observation_route (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  code       text not null,
  ord        int not null,
  words      text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists note_status (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  code       text not null,
  ord        int not null,
  words      text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists claim_decision (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  code       text not null,
  ord        int not null,
  words      text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, code)
);

create or replace function internal.voice_vocabulary(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into observation_outcome (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values ('above', 0, 'above'), ('as_expected', 1, 'as expected'), ('below', 2, 'below'),
               ('not_willing', 3, 'not willing'), ('absent', 4, 'absent')) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
  insert into observation_entry_mode (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values ('individual', 0, 'named'), ('group_as_expected', 1, 'the rest did as expected')) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
  insert into observation_route (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values ('voice', 0, 'voice note'), ('form', 1, 'form')) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
  insert into note_status (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values ('received', 0, 'reading your note'), ('drafted', 1, 'to confirm'), ('confirmed', 2, 'confirmed'),
               ('left_unconfirmed', 3, 'unconfirmed')) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
  insert into claim_decision (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values ('accepted', 0, 'kept as read'), ('changed', 1, 'changed'), ('removed', 2, 'removed')) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
  -- How long a note waits for her, and how long its audio is kept. Audio retention is Nimish's open question (O-14):
  -- null keeps it, and nothing deletes audio until a number is set and a deletion is built.
  insert into config (tenant_id, key, value, description)
  values (p_tenant, 'voice.confirm_within_hours', '48'::jsonb,
          'A K2 voice note not confirmed within this many hours leaves the educator''s queue, is kept as unconfirmed, and never becomes evidence (observation model, section 4).'),
         (p_tenant, 'voice.audio_retention_days', 'null'::jsonb,
          'How many days a voice note''s audio is kept. Not decided (O-14): null keeps it. Nothing deletes audio until this is a number and a deletion is built.')
  on conflict (tenant_id, key) do nothing;
end $$;

create or replace function internal.voice_vocabulary_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.voice_vocabulary(new.id);
  return new;
end $$;

drop trigger if exists voice_vocabulary on tenant;
create trigger voice_vocabulary after insert on tenant
  for each row execute function internal.voice_vocabulary_on_new_school();

select internal.voice_vocabulary(id) from tenant;

-- One voice note. Its audio is in private storage under `audio_key`; this row never holds the audio.
create table if not exists pii.educator_note (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenant(id) on delete cascade,
  staff_id    uuid not null references public.staff(id),
  class_id    uuid not null references public.school_class(id),
  audio_key   text not null check (btrim(audio_key) <> ''),
  transcript  text,
  received_at timestamptz not null default now(),  -- the server's clock, set on insert, never the phone's
  status      text not null default 'received',
  status_at   timestamptz not null default now(),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, audio_key),
  foreign key (tenant_id, status) references public.note_status (tenant_id, code)
);
create index if not exists educator_note_queue_idx on pii.educator_note (tenant_id, staff_id, status);

create or replace function internal.note_received_now() returns trigger
language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    new.received_at := now();
  else
    new.received_at := old.received_at;  -- when it reached us never moves
    new.staff_id := old.staff_id;
    new.audio_key := old.audio_key;
  end if;
  if tg_op = 'UPDATE' then
    -- a confirmed note is what its claims were read from: its words and class never change after, and a confirmed or
    -- left-unconfirmed note stays so; no note moves back to an earlier status
    if old.status in ('confirmed', 'left_unconfirmed') and (new.status is distinct from old.status
        or new.transcript is distinct from old.transcript or new.class_id is distinct from old.class_id) then
      raise exception 'a % note is kept as it was', old.status using errcode = 'check_violation';
    end if;
    if (select ord from public.note_status where tenant_id = new.tenant_id and code = new.status)
       < (select ord from public.note_status where tenant_id = old.tenant_id and code = old.status) then
      raise exception 'a note does not go back from % to %', old.status, new.status using errcode = 'check_violation';
    end if;
  end if;
  if tg_op = 'INSERT' or new.status is distinct from old.status then
    new.status_at := now();
  end if;
  return new;
end $$;

drop trigger if exists educator_note_clock on pii.educator_note;
create trigger educator_note_clock before insert or update on pii.educator_note
  for each row execute function internal.note_received_now();

-- One child, one activity, one confirmation. Never edited: a correction is a new row naming the one it replaces.
create table if not exists activity_observation (
  id                 uuid primary key default gen_random_uuid(),
  tenant_id          uuid not null references tenant(id) on delete cascade,
  confirmation_id    uuid not null,  -- one confirm of one note (or one save of the form) is one id
  note_id            uuid references pii.educator_note(id),
  session_id         uuid,           -- the session table comes with M1's timetable; kept free to link then
  activity_code      text not null,
  curriculum_version int,            -- the version in force at confirm: the database fills it when the engine gives none
  child_id           uuid not null references child(id),
  class_id           uuid not null references school_class(id),
  outcome            text not null,
  entry_mode         text not null,
  route              text not null,
  expected_level     int not null check (expected_level between 0 and 3),  -- activity.level_0 … level_3
  observed_at        timestamptz not null,                   -- when it was taught, as she said; never the future
  stored_at          timestamptz not null default now(),     -- the database's clock, never the phone's
  observed_by        uuid not null references staff(id),
  confirmed_by       uuid not null references staff(id),
  supersedes         uuid,           -- the row this one corrects: the same school, child and activity, corrected once
  reason             text check (btrim(reason) <> ''),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (confirmation_id, child_id),
  unique (id, tenant_id, child_id, activity_code),
  foreign key (supersedes, tenant_id, child_id, activity_code)
    references activity_observation (id, tenant_id, child_id, activity_code),
  check (supersedes <> id),
  check ((supersedes is null) = (reason is null)),
  check ((route = 'voice') = (note_id is not null)),
  check (entry_mode <> 'group_as_expected' or outcome = 'as_expected'),
  check (observed_at <= stored_at),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code),
  foreign key (tenant_id, curriculum_version) references curriculum_version (tenant_id, number),
  foreign key (tenant_id, outcome) references observation_outcome (tenant_id, code),
  foreign key (tenant_id, entry_mode) references observation_entry_mode (tenant_id, code),
  foreign key (tenant_id, route) references observation_route (tenant_id, code)
);
create unique index if not exists activity_observation_corrected_once on activity_observation (supersedes)
  where supersedes is not null;
create index if not exists activity_observation_child_idx on activity_observation (tenant_id, child_id, activity_code);
create index if not exists activity_observation_note_idx on activity_observation (note_id) where note_id is not null;

create or replace function internal.observation_stored_now() returns trigger
language plpgsql as $$
begin
  new.stored_at := now();
  return new;
end $$;

drop trigger if exists activity_observation_clock on activity_observation;
create trigger activity_observation_clock before insert on activity_observation
  for each row execute function internal.observation_stored_now();
drop trigger if exists activity_observation_curriculum on activity_observation;
create trigger activity_observation_curriculum before insert on activity_observation
  for each row execute function internal.result_names_its_curriculum();
drop trigger if exists activity_observation_append_only on activity_observation;
create trigger activity_observation_append_only before update or delete or truncate on activity_observation
  for each statement execute function internal.forbid_change();

-- Each draft line of a confirmed note and what she did with it. Written once, at confirm.
create table if not exists pii.note_claim (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.tenant(id) on delete cascade,
  note_id     uuid not null references pii.educator_note(id),
  section     text not null check (btrim(section) <> ''),  -- a heading of the template (supabase/seed/voice_template.json)
  read_as     text not null,  -- what code read: its numbers, or its words
  words       text not null,  -- the transcript's words it was read from
  span_start  int not null check (span_start >= 0),
  span_end    int not null,
  decision    text not null,
  kept_as     text,           -- what she kept, when she changed it
  decided_by  uuid not null references public.staff(id),
  decided_at  timestamptz not null default now(),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (span_end >= span_start),
  check ((decision = 'changed') = (kept_as is not null)),
  foreign key (tenant_id, decision) references public.claim_decision (tenant_id, code)
);
create index if not exists note_claim_note_idx on pii.note_claim (note_id);

create or replace function internal.claim_decided_now() returns trigger
language plpgsql as $$
begin
  new.decided_at := now();  -- when she decided is the database's clock, never the phone's
  return new;
end $$;

drop trigger if exists note_claim_clock on pii.note_claim;
create trigger note_claim_clock before insert on pii.note_claim
  for each row execute function internal.claim_decided_now();
drop trigger if exists note_claim_append_only on pii.note_claim;
create trigger note_claim_append_only before update or delete or truncate on pii.note_claim
  for each statement execute function internal.forbid_change();

-- The engine writes; the website reads the observations and the words, and never a note. No DELETE anywhere: a note
-- is kept (O-14), an observation is corrected by a new row. The default privileges of 20261021090000 give the engine
-- DELETE on every new public table; it is taken back.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert, update on observation_outcome, observation_entry_mode, observation_route, note_status,
      claim_decision to app_engine;
    grant select, insert on activity_observation to app_engine;
    revoke update, delete, truncate on activity_observation from app_engine;
    revoke delete on observation_outcome, observation_entry_mode, observation_route, note_status, claim_decision
      from app_engine;
    grant select, insert, update on pii.educator_note to app_engine;
    grant select, insert on pii.note_claim to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    revoke all on pii.educator_note, pii.note_claim from app_web;
    grant select on observation_outcome, observation_entry_mode, observation_route, note_status, claim_decision,
      activity_observation to app_web;
  end if;
end $$;

select internal.apply_conventions();
