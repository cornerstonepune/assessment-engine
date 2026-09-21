-- A person's correction to a question is a new question that points at the one it replaces. The
-- old row is retired, never rewritten (Ring A: append or approve); who corrected it and why is the
-- `item_feedback` row on the old question. This link is how the question page reads that history
-- in either direction.
alter table item add column corrected_from uuid references item (id);

create index item_corrected_from_idx on item (corrected_from);
