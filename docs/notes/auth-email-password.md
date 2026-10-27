# auth-email-password — a password its owner sets

Nimish, 26 Oct 2026: "Forget the Google sign-in. We will have to have a proper email password login with an option to
forget password and all. No 2FA needed for now, keep it simple." PR #265 (Google sign-in) is closed and stays closed.
No gate of `BUILD-ORDER.md` moves: this is the sign-in gate of the site W1–W3 already have, not a step of the workflow.

## Verified

Each claim with the command that proves it and its last output, from this branch on 2026-10-26. `bin/engine done
auth-email-password` runs all of them: 15 of Nimish's sentences PROVED, 4 criteria PASSED.

- The link, the limits, the health line and the rows behind them:
  `cd packages/engine && .venv/bin/python -m pytest -q tests/test_password_rules.py` — 5 passed
- The website writes only what a person changes on it, the two new tables included:
  `cd packages/engine && .venv/bin/python -m pytest -q tests/test_roles.py` — 5 passed
- Forgotten, set, signed in, used once, refused, changed — in a browser, with a sender of the run's own:
  `cd apps/web && npx playwright test tests/gate-password.spec.ts tests/gate.spec.ts` — 22 passed
- The staff list, the menu and the UX rules still hold:
  `cd apps/web && npx playwright test tests/u51-ux-rules.spec.ts tests/u53-the-menu.spec.ts tests/screens.spec.ts` — 38 passed;
  `… tests/u18-staff-and-search.spec.ts tests/u53-staff-and-school.spec.ts tests/u25-each-educator-has-classes.spec.ts tests/u27-who-decides-what.spec.ts` — 10 passed
- The code sits where the map says; every promise has its command; lint: `bin/check` — 32 passed

`engine done` ends on NOT DONE for one reason only: the live database does not answer from a branch's container
(`ConnectionTimeout`), so live's migrations are unchecked until this is merged and `migrate live` has run.

## What a member of staff sees

1. `/login` says "Staff only" and carries "Forgot your password?". The line sending people to Nimish is gone.
2. `/login/forgot` takes an email and always answers "If that email is a staff email, we have sent a link" — the same
   words, and the same wait, for an email nobody holds. The email itself is sent after the answer has gone (`after`),
   which is what keeps the two the same length.
3. The emailed link lands on `/login/link`, which moves the token out of the address into a cookie of that browser's
   and sends the person to `/login/new-password` with nothing in the address. The link is spent when the password is
   actually set, never on opening — a mail scanner that follows links must not burn it.
4. A new password must be at least `password.min_length` characters, not the person's own email, and not one of
   `supabase/seed/common_passwords.json`.
5. Setting a password ends every other session that person has open, anywhere.
6. A signed-in person changes their own password from "Change password" in the account line (their current password is
   asked for, and guessing it is counted and refused exactly as the sign-in page counts a wrong password).
7. A coordinator adds a member of staff on `/staff`: name, email, role — no password field. The person is emailed a
   first-time link good for `password_link.first_days` days. Nobody types or sees anyone else's password.

## Handoff

**Live**: nothing yet — this is a branch.

**Needed before the email can leave Vercel** (names only, values are Nimish's): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM`. Until they are set the forgotten-password form answers exactly as it always does, and
`engine live watch` says `mail is not configured, so N set-password links of the last 1440 minutes were never sent`,
so nobody is left waiting for an email in silence. No provider is named anywhere in the repository.

**Before merge**: the rehearsal (`rehearse-update-live.yml`) must run on this branch — two new tables
(`20261215090000_a_password_is_set_by_its_owner.sql`).

**Two weaknesses in the old code, fixed at the cause here** (both in `apps/web/lib/auth.ts`):
- A stored hash carried no cost, so the cost could never be raised without locking everyone out. A hash is now
  `scrypt$n$salt$hash`, the cost is the `password.scrypt_n` row (65536, four times node's default), and every hash
  written before this still verifies.
- The sign-in form answered an unknown email at once while a staff email was still being hashed, which told anyone
  with a clock who works here. A miss is now checked against a decoy hash of the same cost.

**Next**: `engine staff add` on the command line still asks whoever runs it to type the new person's password. It stays
as the way in when mail is not configured (and for Nimish's own account); the Staff page is the normal route. Worth
retiring once mail is live.

**Blocked**: nothing.
