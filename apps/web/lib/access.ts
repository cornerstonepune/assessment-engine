import type { Session } from "./auth";
import type { Kind } from "./decides";

// What a member of staff may use: the one place that says (goals/ux9c-one-role.yaml). Nimish, 2026-10-22: "Achal sir is
// the educator coordinator right now. Just keep all the features available for both educators and coordinators for
// now. As we become bigger, we'll have that bifurcation, so don't differentiate that." So every page, table, button and
// decision is every member of staff's. Which classes and papers a person reaches is not a feature: since 27 Oct 2026 it
// is the one rule `staff_sees` (lib/reach.ts, goals/own_who_sees_answers.yaml).
//
// To split the roles again, answer by `me.role` here: each caller already asks for the one thing it offers.
//
// One thing is the coordinator's alone (Nimish, 27 Oct 2026, goals/mov_move_a_child.yaml): changing a child's grade or
// moving them to another class. It changes where a child is read and counted, so it is not every member of staff's.

/** A thing a person may use: a decision (`Kind`), the engineering map, the bank's stock columns, a question the engine
 *  drafted for another role, or the Setup group of the menu. Which children, papers and answers a person sees is not
 *  here: that is `staff_sees` (lib/reach.ts, goals/own_who_sees_answers.yaml). */
export type Feature = Kind | "the_map" | "stock" | "any_ask" | "setup" | "move_child";

export function mayUse(me: Pick<Session, "role">, what: Feature): boolean {
  if (what === "move_child") return me.role === "coordinator";
  return true;
}
