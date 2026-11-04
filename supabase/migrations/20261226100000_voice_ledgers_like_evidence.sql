-- The two K2 voice-note ledgers (20261226090000) held like evidence_event (task M1-01). Their append-only trigger also
-- refused TRUNCATE, which no other ledger's does: the rehearsal's copy of live empties every table before it loads
-- live's rows (`engine live copy`), and refused on `pii.note_claim`, so every rehearsal after that migration reached
-- live failed. A ledger refuses update and delete by its trigger, as evidence_event does (20260917090000), and is kept
-- from being emptied by grant: `internal.apply_conventions()` revokes update, delete and truncate on every table
-- guarded by `internal.forbid_change` from both services. No row, column or grant is changed here; the tables are
-- empty on live (nothing writes them yet).
--
-- Written to run twice.

drop trigger if exists activity_observation_append_only on activity_observation;
create trigger activity_observation_append_only before update or delete on activity_observation
  for each statement execute function internal.forbid_change();

drop trigger if exists note_claim_append_only on pii.note_claim;
create trigger note_claim_append_only before update or delete on pii.note_claim
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
