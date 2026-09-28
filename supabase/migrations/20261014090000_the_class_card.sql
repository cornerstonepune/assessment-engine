-- W4, Friday's class card (goals/w4a-class-card.yaml). `class_card` (Ring B, 2026-09-17) held three of the graph's
-- groups; it now keeps them all as `groups` — {move_up, secure, practising, emerging, not_enough_yet: [child_id],
-- reteach: {misconception: [child_id]}} — still a pure function of the graph, rebuilt, never edited.
-- The educator's confirmation of a week's card is Ring A: append-only, by name, with what they saw.
alter table class_card add column groups jsonb not null default '{}'::jsonb;

create table class_card_confirmation (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  section     text not null,
  week        text not null,
  by          text not null,
  card        jsonb not null,                -- the card as the educator confirmed it
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index class_card_confirmation_week_idx on class_card_confirmation (tenant_id, section, week, created_at desc);

create trigger class_card_confirmation_append_only before update or delete on class_card_confirmation
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
