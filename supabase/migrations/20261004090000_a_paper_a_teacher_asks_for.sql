-- Make papers: a teacher may ask for a paper for one child — any skills, any levels, how many questions each —
-- made by the same engine as the home paper and printed in their name. Its printed copy's purpose is `custom`.
alter table sheet_instance drop constraint if exists sheet_instance_kind_check;
alter table sheet_instance add constraint sheet_instance_kind_check
  check (kind is null or kind in ('practice', 'assessment', 'focus', 'custom'));
