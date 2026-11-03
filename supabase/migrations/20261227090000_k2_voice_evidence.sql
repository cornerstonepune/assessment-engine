-- K2 voice notes become evidence (goals/m1-01-voice-intake.yaml, task M1-01 step 4). Additive only: one nullable
-- column on evidence_event (no default, so no row is rewritten and no trigger fires) and config rows.
--
-- A confirmed observation is evidence on each skill its activity names (activity_skill), one evidence_event row per
-- skill, all sharing the observation's id, so counts are of observations, not rows (observation model, section 2).
-- Its mark sits on the `seen` scale: the outcome moves the level she expected (above +1, as expected 0, below -1, kept
-- within 0 to 3), and the level gives the mark (3 yes, 2 sometimes, 0 and 1 not yet). Both are config rows, unverified
-- for every activity. Not willing and absent are observations only, never evidence. How lightly "the rest did as
-- expected" counts is the nightly rebuild's rule, read through the observation's entry mode; it is not on the row.
-- A correction of an observation is a new observation with its own evidence; evidence of a superseded observation
-- is no longer current, which a reader finds through `observation_id`.
--
-- Written to run twice.

alter table evidence_event add column if not exists observation_id uuid;
alter table evidence_event drop constraint if exists evidence_event_observation_id_fkey;
alter table evidence_event add constraint evidence_event_observation_id_fkey
  foreign key (observation_id) references activity_observation (id);
create index if not exists evidence_event_observation_idx on evidence_event (observation_id)
  where observation_id is not null;

create or replace function internal.voice_evidence_settings(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into config (tenant_id, key, value, description)
  values
    (p_tenant, 'voice.outcome_moves_level', '{"above": 1, "as_expected": 0, "below": -1}'::jsonb,
     'How each outcome of a K2 voice note moves the level the educator expected, before the level gives its mark. Unverified for every activity (orchestrator, 3 Nov).'),
    (p_tenant, 'voice.level_mark', '{"0": "not_yet", "1": "not_yet", "2": "sometimes", "3": "yes"}'::jsonb,
     'The mark on the seen scale for each activity level a child reached (observation model; child-and-learning section 3). Unverified for every activity.'),
    (p_tenant, 'voice.screens_enabled', 'false'::jsonb,
     'Whether the K2 educator sees Record and Confirm. Off until she is trained; Nimish turns it on. A page or route asked for while it is off refuses.')
  on conflict (tenant_id, key) do nothing;
end $$;

create or replace function internal.voice_evidence_settings_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.voice_evidence_settings(new.id);
  return new;
end $$;

drop trigger if exists voice_evidence_settings on tenant;
create trigger voice_evidence_settings after insert on tenant
  for each row execute function internal.voice_evidence_settings_on_new_school();

select internal.voice_evidence_settings(id) from tenant;

select internal.apply_conventions();
