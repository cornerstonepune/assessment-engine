# staffrm_remove_a_person — `engine staff remove`

Nimish, 27 Oct 2026: a placeholder staff entry (the text `your-email`, coordinator, password set, every class) was on the
live list and nothing could remove it ("the account should not exist"). A setup tool for the site's sign-in: no gate of
`BUILD-ORDER.md` moves. No migration, no website change.

## Verified

`bin/engine done staffrm_remove_a_person`, on a database built by `bin/testdb fresh`, 27 Oct 2026: 8 sentences PROVED,
2 criteria PASSED (23 staff tests; `bin/check` 34 passed). It ends on NOT DONE for one reason: the live database does not
answer from a branch's container (`ConnectionTimeout`). The lock test was checked to bite: with `for update` removed from
the command it fails ("apply did not wait for the lock on the staff list").

What a removed person's past shows (read from `apps/web`, not run in a browser): every sign-off row stores their email or
name as plain text, with no key to the staff list, so nothing breaks and nothing is blank. Pages that turn an old row's
email into a name (`growth/[id]` panels, `make/[section]`, `papers/review/[qr]`, the parent letter) fall back to the stored
email. Names the site wrote itself (skill-set approvals, kind changes) stay as the name. One column holds a staff id
(`capture.uploaded_by`): it is only compared, never looked up, so a scan they uploaded is seen afterwards by the
coordinators and by the classes it belongs to, not by them.

A signed-in person: the cookie only says who (`lib/session-cookie.ts`, checked by `proxy.ts` for its signature); every page,
route and action then calls `requireStaff`, whose `currentStaff` reads the staff list afresh on every request and returns
null for an email no longer on it, which redirects to /login. Confirmed by reading `lib/auth.ts`, and pinned by a source
check in the test file (a browser run needs the whole site built; not run).

## Handoff

**Live**: nothing yet. Nimish runs, from any directory: `~/cornerstone/assessment-engine/bin/engine staff remove your-email`
(dry run, changes nothing), then the same with `--apply`. His two coordinator rows are his to choose between; the command
refuses to remove the last coordinator who can sign in.

**Open, not built**: a remove button on the Staff page (out of scope here).
