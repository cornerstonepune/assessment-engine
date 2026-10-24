import type { State } from "@/components/status-chip";

// A topic's flow in one class (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026: "When they start with a new
// topic they go through the skills; they generate some assessments; then they give a first baseline assessment; then as a
// child progresses they give home assessments; maybe some children get more home assessments; maybe they go back to a
// previous topic and give them practice." Derived from the papers on record, never typed in:
//   skills ready    every skill of the topic approved
//   baseline        the class's first class assessment (`kind = assessment`) on the topic
//   home            home assessments (`kind = focus`) on the topic: how many, for how many children, how many more than once
//   practice        practice papers (`kind = practice`) made after the class was taught the topic
// What the papers cannot say: which child went back to which earlier topic (a paper has a topic, not a reason), and a
// baseline given on paper outside the system.

export type Sheet = { kind: string | null; child: string | null; at: string };
export type FlowIn = { skills: { total: number; approved: number }; sheets: readonly Sheet[]; taughtAt: string | null };
export type Flow = {
  skills: { total: number; approved: number; ready: boolean };
  baseline: { done: boolean; at: string | null };
  home: { papers: number; children: number; repeat: number };
  practice: { papers: number };
};

export function topicFlow(f: FlowIn): Flow {
  const kind = (k: string) => f.sheets.filter((s) => s.kind === k);
  const baseline = kind("assessment").map((s) => s.at).sort()[0] ?? null;
  const home = kind("focus");
  const perChild = new Map<string, number>();
  for (const s of home) if (s.child) perChild.set(s.child, (perChild.get(s.child) ?? 0) + 1);
  const taught = f.taughtAt;
  return {
    skills: { ...f.skills, ready: f.skills.total > 0 && f.skills.approved === f.skills.total },
    baseline: { done: baseline !== null, at: baseline },
    home: { papers: home.length, children: perChild.size, repeat: [...perChild.values()].filter((n) => n > 1).length },
    practice: { papers: taught ? kind("practice").filter((s) => s.at > taught).length : 0 },
  };
}

/** The class result of a topic, said as a colour the school already uses: the colour most children hold on the topic's
 *  skills, the worse one when two tie. None when no child has enough answers to say. */
export function classResult(c: { red: number; amber: number; green: number }): State {
  const n = c.red + c.amber + c.green;
  if (!n) return "noResult";
  if (c.red >= c.amber && c.red >= c.green) return "needsHelp";
  if (c.amber >= c.green) return "gettingThere";
  return "fine";
}

/** A topic's status in a class view: taught; being taught this week (a class declared one of its skills for the week);
 *  the next not-yet-taught topic of its subject in the curriculum's order; or not taught yet. */
export type TopicStatus = "taught" | "teachingNow" | "nextUp" | "notTaught";
export function topicStatuses(
  topics: readonly { code: string; subject: string; taught: boolean }[],
  declared: ReadonlySet<string>,
): Map<string, TopicStatus> {
  const out = new Map<string, TopicStatus>();
  const nextOf = new Set<string>();
  const seen = new Set<string>();
  for (const t of topics) {
    if (!t.taught && !declared.has(t.code) && !seen.has(t.subject)) {
      seen.add(t.subject);
      nextOf.add(t.code);
    }
  }
  for (const t of topics) out.set(t.code, declared.has(t.code) ? "teachingNow" : t.taught ? "taught" : nextOf.has(t.code) ? "nextUp" : "notTaught");
  return out;
}
