import { redirect } from "next/navigation";
import { requireStaff, type Session } from "./auth";
import { sql } from "./db";
import { isMine, scopeOf } from "./scope";

// Who decides what (goals/f1c-who-decides-what.yaml, ADR 0073 decision 3): every decision taken on the site is checked on
// the server before it writes. The roles are the school's row, `people.decides`; the coordinator may take any decision;
// and what a decision touches must be in one of the signer's classes. Hiding a button is not the check — a form can be
// changed by hand.

export type Kind =
  | "answers"
  | "papers"
  | "home_papers"
  | "class_papers"
  | "skills"
  | "skill_drafts"
  | "topics"
  | "reports"
  | "questions"
  | "week"
  | "asks";

/** Each decision as a person says it, for the page a refusal lands on. */
export const KIND_WORDS: Record<Kind, string> = {
  answers: "Checking a child's answers",
  papers: "Signing off a paper",
  home_papers: "Approving a home assessment",
  class_papers: "Approving class papers",
  skills: "Approving a skill",
  skill_drafts: "Changing a skill",
  topics: "Saying a topic is taught",
  reports: "A parent report",
  questions: "Correcting a question in the bank",
  week: "Declaring the week",
  asks: "Answering a question the engine drafted",
};

/** The roles the school's row names for a kind, or null where the row names it not at all: a kind not named yet is
 *  refused to no one, as it was before the row named any (a deploy carries the row with the engine's settings, a little
 *  after the website). */
export async function decidersOf(kind: Kind): Promise<string[] | null> {
  const [row] = await sql<{ roles: string[] | null }[]>`
    select value -> ${kind} as roles from config where key = 'people.decides'`;
  return row?.roles ?? null;
}

/** Whether a person may take a kind of decision on these classes; a class of null (nothing found) is no one's. */
export async function mayDecide(me: Session, kind: Kind, classes: (string | null)[] = []): Promise<boolean> {
  if (me.role === "coordinator") return true;
  const roles = await decidersOf(kind);
  if (roles && !roles.includes(me.role)) return false;
  const scope = scopeOf(me);
  return classes.every((c) => isMine(scope, c));
}

/** For a server action, first: the signed-in person, when their role may take this kind of decision; otherwise the page
 *  that says whose decision it is, and nothing is written. */
export async function deciding(kind: Kind): Promise<Session> {
  const me = await requireStaff();
  if (me.role === "coordinator") return me;
  const roles = await decidersOf(kind);
  if (roles && !roles.includes(me.role)) redirect(`/refused?kind=${kind}`);
  return me;
}

/** For a server action, once it knows what it touches: every class must be one of the signer's, or nothing is written. */
export function mustBeMine(me: Session, kind: Kind, classes: (string | null)[]): void {
  if (me.role === "coordinator") return;
  const scope = scopeOf(me);
  if (classes.some((c) => !isMine(scope, c))) redirect(`/refused?kind=${kind}&class=1`);
}
