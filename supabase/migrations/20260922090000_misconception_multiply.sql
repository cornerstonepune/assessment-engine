-- Multiplication mistakes need an op of their own. The check constraint predates the × rung
-- (MUL.1D, added as the "any topic by rows" proof), so its vocabulary had nowhere to live and the
-- bank produced multiplication questions no marker could diagnose — found by `engine goal`.
alter table misconception drop constraint if exists misconception_op_check;
alter table misconception add constraint misconception_op_check
  check (op in ('+', '-', '×', 'any'));
