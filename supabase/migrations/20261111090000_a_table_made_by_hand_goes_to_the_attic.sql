-- `item_placement` was made on live by hand, by no migration (rule 9), and nothing in the engine, the website or n8n
-- reads or writes it; 20261007090000 let go of its hold on skill_set and rung, and kept its rows for whoever made it
-- to say what they are. No one has. The watcher's first look at live's rules (2026-10-15, L3b) named its five as
-- rules no migration makes. Nimish, the same day: "move item_placement to attic too".
--
-- It moves, rows and all, out of the school's tables (`public`, which the engine, the website and the watcher read)
-- into `attic`, which nothing reads and no role but the owner may open: nothing is lost, and it can be moved back or
-- dropped once its maker says what it was. Where it does not exist — every database built from the migrations —
-- nothing happens.
create schema if not exists attic;
revoke all on schema attic from public;

do $$
begin
  if to_regclass('public.item_placement') is not null and to_regclass('attic.item_placement') is null then
    alter table public.item_placement set schema attic;
  end if;
end $$;
