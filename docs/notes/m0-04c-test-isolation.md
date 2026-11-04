# m0-04c-test-isolation: a test leaves the database as it found it

Task M0-04c (workflow: W3, gate N10; tests only: no engine, schema or seed change). Asked by the orchestrator after
M0-04b: find which test commits an item with no skill set and leaves it, fix it at the cause, make a test that leaves a
committed row fail loudly, and make the sheet codes tests create unique.

## Verified

- **The leaver.** On the 12-shard run of 2026-11-03 (local, four databases, three shards each in turn), shard 11 failed 7
  tests of `test_question_types` (`TypeError: '<' not supported between 'NoneType' and 'str'`, and `['rows']` not a type)
  and shard 3 one of `test_goal` ("1 generated items carry no version or generator"). Cause: `test_who_sees` commits a read
  paper (`rows.a_read_paper`: an item with template `rows` and no skill set, a child, copy, scan) so a second connection can
  see it, and cleaned up only the flow run. CI never met it because each CI shard has a database of its own.
- **Measured, every table's row count before and after each test module, over the whole suite** (report-only run, 3,217
  tests): left rows were `test_who_sees` (the item chain), `test_cli` (293 flow runs), `test_staff` (2 children),
  `test_graph` (a child, its evidence and state), `test_people_signer` (88 children, 39 access log rows), `test_people` (200
  children, 74 access log rows), `api/test_maker_routes` (a flow run), and by order `test_week` (2 children) and
  `test_staff_load` (2 children).
- **The check.** `tests/conftest.py::a_module_leaves_no_committed_row` (autouse, per module) counts every table of `public` and
  `pii` before and after a module and fails the module's last test, naming the tables and the rows added. Seen failing before
  the fixes, e.g. `test_cli left committed rows (table: rows added): {'public.flow_run': 293}`; `ISOLATION_REPORT=<file>`
  writes them instead, to measure.
- **The cleanup.** `rows.forget_paper` removes a paper a test had to commit, with the triggers off for that transaction
  (`session_replication_role = replica`; reading writes append-only rows such as `page_choice`, which a plain delete
  refuses) and deleting by the columns that name the paper (`capture_id`, `item_id`, `sheet_instance_id`, `child_id`), so
  a table added later is reached too. `forgets_what_it_commits` (module fixture) removes every row created since the
  module began, for the modules whose commands or own connections commit: `test_cli`, `test_staff`, `test_staff_load`,
  `test_graph`, `test_people`, `test_people_signer`, `test_week`, `api/test_maker_routes`. A table that does not stamp
  `created_at` is not reached; the check then says so.
- **Sheet codes.** `"CS" + uuid4().hex[:6]` (24 bits, a unique column shared by every test) stood in `test_child_move`,
  `test_learn`, `test_learned_mistakes`, and the tag in `rows.a_read_paper`; now the whole id.
  `test_test_ids.py::test_no_test_makes_a_sheet_code_from_a_cut_short_random_id` failed on exactly those three lines first.
- **Whole suite, 12 shards of CI's own cut (`bin/ci-shard pick`), four fresh databases, the check failing:** shards 1, 2, 4–11
  passed; shard 3 passed on re-run after `test_staff_load` was found by the check (273 passed); shard 12 passed on re-run
  after `test_week` was found (268 passed) except two tests of `test_spine_provenance`, which download a PDF from
  `ncert.nic.in` and fail here on the sandbox's certificate (`CERTIFICATE_VERIFY_FAILED`), not on the code; they pass in CI.

## Not changed, named

- Short random ids on columns that are not unique across the database (sections, names, roll numbers in a section of the
  test's own) stay: a collision there cannot fail a run.
- A test that leaves a row in a table with no `created_at` is caught by the check but not undone by the fixture.

## Handoff

- **Live:** nothing; tests only.
- **Next:** CI; the orchestrator merges.
