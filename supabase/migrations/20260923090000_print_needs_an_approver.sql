-- A paper reaches a child only after a person said so, and the database is what enforces it.
-- W2/N7: `print_status = 'printed'` was a label anything could set. Now a *printed* sheet must name
-- who approved it and when, so "the teacher approved before printing" is a guarantee rather than a
-- convention — the app's one-tap action and the engine both have to record a person.
--
-- Only 'printed' is gated. A legacy paper (N3) is entered after a child has already done it, on
-- paper we never printed, and lands as 'returned' with nobody to name: gating that would refuse
-- history to protect a future print.
alter table sheet_instance
  add column if not exists approved_by text,
  add column if not exists approved_at timestamptz;

update sheet_instance
   set approved_by = coalesce(approved_by, 'before this rule (2026-09-23)'),
       approved_at = coalesce(approved_at, printed_at, now())
 where print_status = 'printed';

alter table sheet_instance drop constraint if exists sheet_instance_printed_needs_approver;
alter table sheet_instance add constraint sheet_instance_printed_needs_approver
  check (print_status <> 'printed' or approved_by is not null);
