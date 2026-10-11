# ADR 0069 — The staff list is the database's, and a command Nimish runs puts a person on it

**Status:** accepted (2026-10-11, step UI4a of BUILD-ORDER "UI1 to UI4").
Goal: goals/ui4a-staff-and-search.yaml

## What happened

Nimish, 2026-10-11: "Right now, this is majorly used by Achal and Neha ma'am. They are the educators … Maybe we can
simply add a user ID/password for them: simple user ID/password, nothing complex. I can provide the email IDs to you
for now." Sign-in by email and password already existed (`apps/web/lib/auth.ts`, `engine set-password`). What did not:
a way onto the list. `app.staff` was seeded once from `supabase/seed/config.json`, in the public repository, and
`engine set-password` refused anyone not already on it ("who is on the list is not a thing a command decides").

## Decision

- `engine staff add <email> --name <name> [--role educator]`, run by Nimish on his own machine, puts a person on the
  list with a password typed there twice and never echoed. A role is one the school's decisions name
  (`people.decides`) or one someone on the list already holds; an email already on the list is refused.
- The seed's list is empty. The list is the database's alone; `seed_once` already kept the loader from overwriting it.
- `engine set-password` stays, beside `staff add` in `engine/core/cli_staff.py`, for a person already on the list.

## Rejected

- **Nimish sends the emails to Claude, who writes them into the seed.** The repository is public; the seed would
  publish the educators' emails, and the emails would pass through a chat.
- **Claude adds them to live directly.** The live database does not answer from Claude's sandbox (STATE.md "The done
  report asks live, not the copy"), and writing to live unattended was refused earlier in the session in any case.
- **A sign-up page.** One more door to guard for two people; nothing to gain over a command Nimish runs once each.
