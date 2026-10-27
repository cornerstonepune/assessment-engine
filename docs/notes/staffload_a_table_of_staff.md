# staffload_a_table_of_staff — a table of staff put on the list in one command

Nimish, 27 Oct 2026: "I will give you a table of teachers and subjects and grades and you then do the needful."
A setup tool for the site's sign-in: no gate of `BUILD-ORDER.md` moves. No migration, no website page.

## Verified

`bin/engine done staffload_a_table_of_staff`, on a database built by `bin/testdb fresh`, 27 Oct 2026: 8 of Nimish's
sentences PROVED, 2 criteria PASSED (15 staff tests; `bin/check` 34 passed). It ends on NOT DONE for one reason: the
live database does not answer from a branch's container (`ConnectionTimeout`).

## Handoff

**Live**: nothing yet. Nimish runs, from any directory, with the table kept outside the repository:
`~/cornerstone/assessment-engine/bin/engine staff load ~/Downloads/staff.csv` (dry run), then the same with `--apply`.
Columns: name, email, role, subjects, classes. Not run against live: nothing here could reach it.

**Open question (not built)**: a new person's one-time password is not marked as temporary; the site has no "must
change on first sign-in". A `must_change` flag set by this tool and honoured at sign-in is about six files and no
migration (the flag lives in the `app.staff` JSON): the `Staff` type, `lib/auth.ts` (carry it into the session),
the app layout (send a flagged person to `/account/password`), `lib/password.ts` (clear it when they set a password),
this tool (set it for new people), and a browser test.
