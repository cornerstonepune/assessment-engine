-- A child's next paper chosen from the child's own graph (goal s11-focus-paper): twelve bank questions
-- from the areas the child lags in, made for that one child. It is a sheet_template like any other —
-- its questions, its week, the child it was made for — with source 'focus', and the child's
-- sheet_instance carries its QR, so it prints, comes back and is read and marked like any other paper.
alter table sheet_template drop constraint sheet_template_source_check;
alter table sheet_template add constraint sheet_template_source_check
  check (source in ('generated', 'legacy', 'library', 'focus'));
alter table sheet_template add constraint sheet_template_focus_is_for_a_child
  check (source <> 'focus' or child_id is not null);
