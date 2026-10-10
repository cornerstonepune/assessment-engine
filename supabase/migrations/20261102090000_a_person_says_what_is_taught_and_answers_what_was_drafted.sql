-- What waits on a person, and who it is for (goals/ny1-needs-you.yaml).
--
-- A topic is switched on or off by a person on the site, in their own name. The rows (`supabase/seed/topics.json`)
-- decide a topic only until a person has: `engine load` never switches back what an educator switched. Who decided
-- last, and when; both empty while the rows decide.
alter table topic add column taught_by text, add column taught_at timestamptz;
alter table topic add constraint topic_taught_by_a_person check ((taught_by is null) = (taught_at is null));
grant update (taught, taught_by, taught_at) on topic to app_web;

-- A question the engine drafted for a person to answer: its words, what the engine drafted and why, where the draft
-- lives, and whose it is — a role on the staff list (`app.staff`). Answered on the site, it is agreed as drafted or
-- corrected in the person's own words, by whom and when. A reload of the rows rewords a question no one has answered
-- and never touches one that has been: an answer stands on the words it was given to.
create table ask (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,
  ord          int not null default 0,          -- the order the rows draft them in
  for_role     text not null,
  question     text not null,
  drafted      text not null,
  why          text,
  source       text not null,
  link         text,
  answer       text check (answer in ('agreed', 'corrected')),
  correction   text,
  answered_by  text,
  answered_at  timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code),
  -- answered whole or not at all; a correction is words, and only a correction has them
  check ((answer is null) = (answered_by is null) and (answer is null) = (answered_at is null)),
  check ((answer = 'corrected') = (coalesce(correction, '') <> ''))
);
grant update (answer, correction, answered_by, answered_at) on ask to app_web;

select internal.apply_conventions();
