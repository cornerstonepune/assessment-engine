-- A generated paper found its week through its own sheet_template; a library worksheet has no week
-- (it is handed out in many), so a spare copy of one could not be listed with the week it was
-- printed for. A printed copy now records the week, the class and the kind of pack it belongs to.
alter table sheet_instance add column week text;
alter table sheet_instance add column section text;
alter table sheet_instance add column kind text;
