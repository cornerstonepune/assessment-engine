-- A subject's validation rules go when the subject does (slice C4, goals/c4-validation-rules-per-subject-and-kind.yaml).
--
-- 20261207090000 makes a subject's rule the moment the subject is made (trigger validation_rule_on_new_subject), but
-- its link to the subject had no `on delete`, so no subject could be removed any more: tests/s43-across-classes.spec.ts,
-- which adds a subject and takes it away, failed once C4 met main (#305). A rule is the subject's setting, never a
-- record of what happened, so it goes with its subject. Written to run twice.

alter table validation_rule drop constraint if exists validation_rule_tenant_id_subject_code_fkey;
alter table validation_rule add constraint validation_rule_tenant_id_subject_code_fkey
  foreign key (tenant_id, subject_code) references subject (tenant_id, code) on update cascade on delete cascade;
