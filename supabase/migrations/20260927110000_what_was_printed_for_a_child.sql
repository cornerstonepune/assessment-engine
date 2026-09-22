-- A child's paper is a library worksheet (step 7): one sheet_template shared by every child given it,
-- and never edited once made. What was printed for one child — the page geometry a reader needs when
-- that QR comes back — belongs to that child's sheet_instance, not to the worksheet.
alter table sheet_instance add column key jsonb;
