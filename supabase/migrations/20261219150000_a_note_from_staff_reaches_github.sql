-- A note a member of staff writes from any page, "Something is broken / I would like something new / A question", kept
-- here first and then made into one GitHub issue (goals/feed_report_from_the_tool.yaml). Kept first, so a note is never
-- lost: GitHub down or not connected leaves it `saved` or `failed`, and a later try sends it.
--
-- No name and no email: who wrote it is their role and classes, as the issue says it, and `reporter`, an HMAC of their
-- email under the site's secret, which lets the form count a person's notes per hour and show them their own and
-- names nobody to anyone who reads the row. The page is its path with every id taken out.
--
-- Append-only for the words: the website adds a note and may set only how its sending went (`status`, `issue_number`,
-- `tried_at`); nothing changes what was written, and no note is removed (the trigger, for every role).
create table staff_note (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  kind          text not null check (kind in ('bug', 'feature', 'question')),
  doing         text not null,                    -- "What were you doing?"
  happened      text not null,                    -- "What did you expect, and what happened?"
  how_often     text check (how_often in ('once', 'sometimes', 'every time')),
  route         text not null,                    -- the page's path, ids taken out, never a query string
  role          text not null,
  classes       text not null default '',         -- the classes the person teaches, as the staff list names them
  browser       text not null default '',         -- the browser and system, short ("Chrome 130 on Windows")
  reporter      text not null,                    -- HMAC of the email, never the email
  status        text not null default 'saved' check (status in ('saved', 'sent', 'failed')),
  issue_number  int,
  tried_at      timestamptz,                      -- the last try to send it; a try in hand holds it for a minute
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index staff_note_reporter_idx on staff_note (reporter, created_at desc);
create index staff_note_unsent_idx on staff_note (created_at) where status <> 'sent';

create or replace function internal.staff_note_words_stay() returns trigger
language plpgsql as $$
begin
  if tg_op = 'DELETE' then
    raise exception 'a note from staff is kept: it is never removed';
  end if;
  if (new.tenant_id, new.kind, new.doing, new.happened, new.how_often, new.route, new.role, new.classes, new.browser,
      new.reporter, new.created_at)
     is distinct from
     (old.tenant_id, old.kind, old.doing, old.happened, old.how_often, old.route, old.role, old.classes, old.browser,
      old.reporter, old.created_at) then
    raise exception 'a note from staff keeps its words: only how its sending went may change';
  end if;
  return new;
end $$;

create trigger staff_note_words_stay before update or delete on staff_note
  for each row execute function internal.staff_note_words_stay();

grant insert on staff_note to app_web;
grant update (status, issue_number, tried_at) on staff_note to app_web;

select internal.apply_conventions();
