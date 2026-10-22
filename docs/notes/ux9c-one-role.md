# ux9c-one-role: every feature is every member of staff's

Nimish, 2026-10-22: "Achal sir is the educator coordinator right now. Just keep all the features available for both
educators and coordinators for now. As we become bigger, we'll have that bifurcation, so don't differentiate that."
Goal: `goals/ux9c-one-role.yaml`.

## Verified

- One place decides what a person may use: `apps/web/lib/access.ts` (`mayUse`), true for every member of staff. Every
  role check of the website asks it: a decision (`decides.ts`), every class (`scope.ts`), a question drafted for another
  role (`asks`, Today), the engineering map (the menu), the bank's stock columns.
- An educator of one class, after "See every class", and the coordinator open the same 20 pages, every section folded
  open; every button, link, field and column the coordinator is offered, the educator is too, and no page refuses them:
  `cd apps/web && npx playwright test tests/u49-one-role.spec.ts` → 2 passed (they fail on main: no such button).
- Kept as a default, not hiding: a person's pages open on their own classes and grade (`scopeOf`, `ownClasses`);
  "See every class" in the menu (`seeClasses`, a cookie) shows every class in one tap, and any class's page, child,
  paper or decision opens for every member of staff (`reachOf`).

## Handoff

- **Live:** nothing until merged and deployed. No migration; `people.decides` stays as the record of whose each decision
  is, read by nothing that refuses.
- **Changed on purpose:** the tests of UX1, F1b, F1c, F1d, F1f, UI1 and UX6 that said an educator is refused, offered
  no approval or shown no stock now say the reverse; their goals name Nimish's sentence of 2026-10-22.
- **Local only, not this branch's:** u15 "Today lists everything…", u26 "the coordinator sees every class" and u46 "one
  word for one thing" fail on a local copy many runs old (Today lists five packs then "and N more"; a name's colour);
  u46 fails the same on main's code there. CI's fresh copy decides.
- **To split the roles again:** answer by `me.role` in `mayUse`.
