-- Division is an operation wherever one is named (goals/md0b-division-is-an-operation.yaml). A mistake row names the
-- operation it is a mistake of, and the check refused ÷, so no division mistake could be written down: the rows
-- M3 adds ("a remainder bigger than the divisor", "a zero left out of the quotient") had nowhere to live.
alter table misconception drop constraint if exists misconception_op_check;
alter table misconception add constraint misconception_op_check
  check (op in ('+', '-', '×', '÷', 'any'));
