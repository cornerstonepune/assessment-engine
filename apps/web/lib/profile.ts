import type { ChildSkill } from "./queries-children";
import { rag, type Rag } from "./rag";

// A child's profile by topic (goals/ui4b1-child-by-topic.yaml): each taught topic of theirs with its skills counted by
// where the graph's states put them, and those no checked answer has reached. Counted here from `childSkills`, never
// decided here: the states are the engine's.
export type TopicStanding = { code: string; name: string; notYet: number } & Record<Rag, number>;

export function byTopic(skills: ChildSkill[]): TopicStanding[] {
  const topics = new Map<string, TopicStanding>();
  for (const s of skills) {
    const t = topics.get(s.topic_code) ?? { code: s.topic_code, name: s.topic, red: 0, amber: 0, green: 0, grey: 0, notYet: 0 };
    if (s.n_events > 0) t[rag(s.state)] += 1;
    else t.notYet += 1;
    topics.set(s.topic_code, t);
  }
  return [...topics.values()];
}

/** Where a skill comes on its topic's list: the ones that need help first, then practising, secure, too few answers. */
export const NEED: Record<Rag, number> = { red: 0, amber: 1, green: 2, grey: 3 };
