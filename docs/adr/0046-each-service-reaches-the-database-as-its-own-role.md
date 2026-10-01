# ADR 0046 — Each service reaches the database as its own role

**Status:** accepted (Nimish, 2026-10-01: "go ahead with phase 1", after the code review of 2026-09-30 asked for
least-privilege roles for the website and the engine)
Goal: goals/p1-the-roles-hold.yaml

## What happened

The website and the engine both connected as the database's owner.

- Either could read every child's name straight from `pii.child`, without writing who asked to `access_log`. The
  engine did so in two places: the importer's `roster.find` and the gold set.
- Only a trigger (`internal.forbid_change`) stood between either service and a ledger row such as `evidence_event`.
  A trigger is a rule a later migration can drop; a grant is checked on every statement.

## Decision

1. **Two login roles, `app_web` and `app_engine`**, are made by a migration with no password. Nimish gives each one
   its password and points its service's `DATABASE_URL` at it. Until then both keep the owner's connection.
2. **The engine is the system's writer.** It may read and write every table in `public` and run every function of
   ours. It has no update, delete or truncate on a ledger, and nothing on `pii.child`.
3. **The website reads every table in `public`.** It writes the five a person changes on it, and calls the four
   functions its pages call.
4. **A name is read only through the accessors that log who asked:** `pii.read_child`, and `pii.find_child` for a
   child found by name.
5. **`internal.apply_conventions`, which every migration ends with, keeps these true for a table made later:**
   - a row-security policy for both roles;
   - a ledger's update, delete and truncate revoked the moment its trigger exists.
6. **A trigger that writes a consequence elsewhere runs as its owner.** A skill set's history is the system's record,
   whoever edits the skill set (`skill_set_version_on_change`).
7. **Proved both ways.**
   - `tests/test_roles.py` reads each role's privileges from the database and fails on any wider grant.
   - CI runs every browser test with the website and the engine connected as these roles, so a grant too narrow fails
     too.

## Rejected

- **`SET ROLE` inside the owner's connection.** It is no boundary: the session can `RESET ROLE`. Through Supabase's
  transaction pooler it would also have to be set again in every transaction, or land on another client's connection.
- **Making the roles members of `service_role`.** Supabase grants `service_role` everything in `public`, so the roles
  would have inherited all of it.
- **One role for both services.** The website writes five tables and the engine writes them all. One role would give
  the website the engine's reach.
- **Granting the website insert on `skill_set_version` so its edits keep their history.** The website would then be
  able to write history rows of its own.
