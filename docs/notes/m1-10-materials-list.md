# M1-10 — the K2 educator's materials list (engine side)

**Gate:** W2, step N4 (files added to the step, no thirteenth step; the orchestrator agreed, 4 Nov). Goal: `goals/m1-10-materials-list.yaml`.
Screens are 4b's; this branch is the migration, the engine and its routes. Everything is behind `educator.timetable_enabled` (default off).

## Verified
_(filled at the end of the session with each command's last output)_

## Handoff
- **Box timer** (the 48-hour timer's neighbour; counts only, sends nothing; the educator sees reminders in her inbox):
    30 2 * * * docker exec deploy-engine-1 engine reminders --due >> /var/log/materials-reminders.log 2>&1
- Depends on M1-11's `20270101090000_k2_page_parts.sql` (`material_item`, `activity_material`); not on main yet when this was written.
