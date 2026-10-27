import { redirect } from "next/navigation";
import { requireStaff, type Session } from "./auth";
import { sql } from "./db";
import { mayUse } from "./access";
import { sees, type Thing } from "./reach";

// Who decides what (goals/f1c-who-decides-what.yaml, ADR 0073 decision 3): every decision taken on the site is checked on
// the server before it writes. The roles are the school's row, `people.decides`; the coordinator may take any decision;
// and what a decision touches must be the signer's to see (`staff_sees`, lib/reach.ts). Hiding a button is not the check — a form can be
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

/** Which kinds of decision a person's role may take, the row read once: the one rule a page offers by
 *  (goals/ux1-who-sees-what.yaml) and the server refuses by. */
export async function decidable(me: Pick<Session, "role">): Promise<(kind: Kind) => boolean> {
  // every member of staff may take every decision for now (`mayUse`, goals/ux9c-one-role.yaml); `people.decides` says
  // whose each is, for the day the roles split again
  return (kind) => mayUse(me, kind);
}

/** Whether a person may take a kind of decision on these classes; a class of null (nothing found) is no one's. */
export async function mayDecide(me: Session, kind: Kind, classes: (string | null)[] = []): Promise<boolean> {
  if (!(await decidable(me))(kind)) return false;
  return sees(me, classes.map((section) => ({ section })));
}

/** For a server action, first: the signed-in person, when their role may take this kind of decision; otherwise the page
 *  that says whose decision it is, and nothing is written. */
export async function deciding(kind: Kind): Promise<Session> {
  const me = await requireStaff();
  if (!(await decidable(me))(kind)) redirect(`/refused?kind=${kind}`);
  return me;
}

/** For a server action, once it knows what it touches: every class must be one the signer sees, or nothing is written. */
export async function mustBeMine(me: Session, kind: Kind, classes: (string | null)[]): Promise<void> {
  if (!(await sees(me, classes.map((section) => ({ section }))))) redirect(`/refused?kind=${kind}&class=1`);
}

/** For a server action on a child's paper or answers: every paper, scan and answer it names must be one the signer sees
 *  (goals/own_who_sees_answers.yaml), or nothing is written and they read that the paper belongs to another class. */
export async function mustSee(me: Session, kind: Kind, things: Thing[]): Promise<void> {
  if (!(await sees(me, things))) redirect(`/refused?kind=${kind}&paper=1`);
}
