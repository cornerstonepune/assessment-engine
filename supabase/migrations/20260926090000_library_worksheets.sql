-- Every question in the bank sits on a numbered worksheet (ADR 0026). A library worksheet is a
-- sheet_template with source 'library': one skill at one level, twelve questions, a code such as
-- R5-H07, and no child and no week — a child's paper will point at it through its own
-- sheet_instance. A worksheet is never edited once made; when a question on it leaves the bank it
-- is retired (retired_at) and a new one, with a new code, replaces it. Codes are never reused.
alter table sheet_template add column code text;
alter table sheet_template add column retired_at timestamptz;

alter table sheet_template drop constraint sheet_template_source_check;
alter table sheet_template add constraint sheet_template_source_check
  check (source in ('generated', 'legacy', 'library'));

alter table sheet_template alter column week drop not null;
alter table sheet_template add constraint sheet_template_week_unless_library
  check (week is not null or source = 'library');
alter table sheet_template add constraint sheet_template_library_has_a_code
  check ((source = 'library') = (code is not null));

create unique index sheet_template_code_key on sheet_template (tenant_id, code) where code is not null;
