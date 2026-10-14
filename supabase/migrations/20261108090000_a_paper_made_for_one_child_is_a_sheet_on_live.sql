-- Live refused every paper made for one child on 2026-10-14 (goals/l3-a-class-paper-prints-on-live.yaml): its
-- `sheet_template_source_check` held the rule as 20260926090000 wrote it — generated, legacy, library — though it
-- records 20260929090000, which adds 'focus', as applied. How live came to differ is not known from here; this says
-- the rule again as the migrations hold it, so live holds it too, and on a database that already does it changes
-- nothing. The child a 'focus' paper is made for is said again with it.
alter table sheet_template drop constraint if exists sheet_template_source_check;
alter table sheet_template add constraint sheet_template_source_check
  check (source in ('generated', 'legacy', 'library', 'focus'));
alter table sheet_template drop constraint if exists sheet_template_focus_is_for_a_child;
alter table sheet_template add constraint sheet_template_focus_is_for_a_child
  check (source <> 'focus' or child_id is not null);
