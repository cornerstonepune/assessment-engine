import type { ChildSkill } from "./queries-children";
import type { Rag } from "./rag";
import type { States } from "./states";

// A child's profile by topic (goals/ui4b1-child-by-topic.yaml): each taught topic of theirs with its skills counted by
// where the graph's states put them, and those no checked answer has reached. Counted here from `childSkills`, never
// decided here: the states are the engine's.
export type TopicStanding = { code: string; name: string; notYet: number } & Record<Rag, number>;

export function byTopic(skills: ChildSkill[], states: States): TopicStanding[] {
  const topics = new Map<string, TopicStanding>();
  for (const s of skills) {
    const t = topics.get(s.topic_code) ?? { code: s.topic_code, name: s.topic, red: 0, amber: 0, green: 0, grey: 0, notYet: 0 };
    if (s.n_events > 0) t[states.of(s.state).colour] += 1;
    else t.notYet += 1;
    topics.set(s.topic_code, t);
  }
  return [...topics.values()];
}

/** Where a skill comes on its topic's list: the ones that need help first, then practising, secure, too few answers. */
export const NEED: Record<Rag, number> = { red: 0, amber: 1, green: 2, grey: 3 };

/** A topic's worst standing: the most severe state of the skills a checked answer reached (as a skill set takes its worst
 *  skill), or `none` with no checked answer in it. */
export function topicStanding(skills: ChildSkill[], states: States): Rag | "none" {
  const assessed = skills.filter((s) => s.n_events > 0).map((s) => states.of(s.state));
  if (!assessed.length) return "none";
  return assessed.reduce((a, b) => (b.severity < a.severity ? b : a)).colour;
}

/** A topic's one line of strength or weakness, in plain words, worked out from the graph's states (never a model): the
 *  skill that needs the most help, with the mistake that repeats on it where there is one; else the skill most often
 *  right; else that there are too few answers to say. `mistake` names the repeating mistake of a skill's line. */
export function topicNote(skills: ChildSkill[], states: States, mistake: (s: ChildSkill) => string | null): string | null {
  const assessed = skills.filter((s) => s.n_events > 0);
  if (!assessed.length) return null;
  const share = (s: ChildSkill) => s.n_correct / s.n_events;
  const weak = assessed
    .filter((s) => states.of(s.state).needs_work)
    .sort((a, b) => states.of(a.state).severity - states.of(b.state).severity || share(a) - share(b));
  if (weak.length) {
    const [s] = weak;
    const m = mistake(s);
    return `Weakest: ${s.name}, ${m ? `keeps making “${m}”` : `${s.n_correct} of ${s.n_events} right`}`;
  }
  const strong = assessed.filter((s) => states.of(s.state).enough).sort((a, b) => share(b) - share(a) || b.n_events - a.n_events);
  if (strong.length) return `Strongest: ${strong[0].name}, ${strong[0].n_correct} of ${strong[0].n_events} right`;
  return "Too few answers yet to say";
}
