import type { Session } from "./auth";
import type { Kind } from "./decides";

// What a member of staff may use: the one place that says (goals/ux9c-one-role.yaml). Nimish, 2026-10-22: "Achal sir is
// the educator coordinator right now. Just keep all the features available for both educators and coordinators for
// now. As we become bigger, we'll have that bifurcation, so don't differentiate that." So every page, table, button and
// decision is every member of staff's, and an educator reaches every class as the coordinator does. Pages still open on
// the person's own grade first (`ownClasses`); that is where a page starts, not what it hides.
//
// To split the roles again, answer by `me.role` here: each caller already asks for the one thing it offers.

/** A thing a person may use: a decision (`Kind`), every class rather than their own, the engineering map, the bank's stock
 *  columns, or a question the engine drafted for another role. */
export type Feature = Kind | "every_class" | "the_map" | "stock" | "any_ask";

export function mayUse(me: Pick<Session, "role">, what: Feature): boolean {
  void me;
  void what;
  return true;
}
