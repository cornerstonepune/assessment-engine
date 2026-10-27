/**
 * The numbers of Results by topic, read back (goals/res_results_by_topic.yaml): each query function's answer against the
 * rows themselves, on the class tests/results-rows.ts makes from real papers signed off as a person signs them off. The
 * states are the graph's (`confirm_results` rebuilds them); this holds the counting, never the graph's rules.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { childLevels, childTopicPapers, classTopics, skillChildren, topicPapers, topicSkills } from "../lib/queries-results";
import { A, OTHER, SKILL, TOPIC, aResultsClass } from "./results-rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const COORDINATOR = { role: "coordinator", classes: [], subjects: [], id: undefined, email: "e2e@cornerstone.test" };
let kids: Record<string, string> = {};

test.beforeAll(async () => {
  test.setTimeout(120_000);
  ({ kids } = await aResultsClass(sql));
});
test.afterAll(async () => sql.end());

/** A child's colour on the topic, from the rows alone: the colour of the most severe state among their skills of it. */
async function colourOn(child: string, topic: string): Promise<string | null> {
  const rows = await sql<{ colour: string; severity: number }[]>`
    select cs.colour, cs.severity from child_skill_state s
    join skill ss on ss.rung_code = s.rung_code and s.skill_code = any(ss.registry_codes)
    join child_state cs on cs.code = s.state and cs.tenant_id = s.tenant_id
    where s.child_id = ${child} and ss.topic_code = ${topic} and s.n_events > 0`;
  return rows.sort((a, b) => a.severity - b.severity)[0]?.colour ?? null;
}

test("a topic counts each child once, by the state of their weakest skill in it, and the child with no answer as not assessed", async () => {
  const topics = await classTopics(A, COORDINATOR);
  const t = topics.find((x) => x.code === TOPIC)!;
  expect(t, "the class's addition and subtraction").toBeTruthy();
  expect(t.children).toBe(3);
  const want = { red: 0, amber: 0, green: 0, grey: 0, none: 0 } as Record<string, number>;
  for (const c of Object.values(kids)) want[(await colourOn(c, TOPIC)) ?? "none"] += 1;
  expect(t.spread).toEqual(want);
  expect(want.none).toBe(1); // Chetan
  expect(t.last).not.toBeNull();
  // the skill's own line counts the same children the same way, and says the level they last answered at
  const [s] = (await topicSkills(A, TOPIC)).filter((x) => x.code === SKILL);
  expect(s.spread).toEqual(want);
  expect(s.levels).toEqual([{ level: "Medium", n: 2 }]);
});

test("a child on a skill: the three signals apart, the level of their newest question, and their answers waiting", async () => {
  const { rows, of } = await skillChildren(A, SKILL, COORDINATOR, 1, 10);
  expect(of).toBe(3);
  const by = Object.fromEntries(rows.map((r) => [r.first_name, r]));
  expect(by.Asha).toMatchObject({ right: 2, wrong: 1, wrong_working: 1, blank: 1, level: "Medium", waiting: 0 });
  expect(by.Bina).toMatchObject({ right: 10, wrong: 1, wrong_working: 0, blank: 0, level: "Medium", waiting: 1 });
  expect(by.Chetan).toMatchObject({ right: 0, wrong: 0, wrong_working: 0, blank: 0, level: null, state: null });
  // who needs the educator comes first; the child with nothing checked comes last
  expect(rows.at(-1)!.first_name).toBe("Chetan");
  // a page of one is one child, and still says how many there are
  expect((await skillChildren(A, SKILL, COORDINATOR, 2, 1)).rows).toHaveLength(1);
});

test("a topic's papers by kind: one class assessment for two children; two home assessments for one", async () => {
  const kinds = Object.fromEntries((await topicPapers(A, TOPIC, COORDINATOR)).map((k) => [k.kind, k]));
  expect(kinds.assessment).toMatchObject({ papers: 2, sets: 1, children: 2, most: 1 });
  expect(kinds.focus).toMatchObject({ papers: 2, children: 1, most: 2 });
  // an educator of another class sees none of them: the one rule (`staff_sees`)
  const [{ id }] = await sql<{ id: string }[]>`select staff_id(${OTHER.email}) as id`;
  expect(await topicPapers(A, TOPIC, { role: "educator", classes: OTHER.classes, subjects: [], id })).toEqual([]);
});

test("a child's papers in a topic carry the signals and the pages of the scan; their level is their newest question's", async () => {
  const papers = (await childTopicPapers(kids.Asha, COORDINATOR)).filter((p) => p.topic_code === TOPIC);
  expect(papers).toHaveLength(1);
  expect(papers[0]).toMatchObject({ qr_code: "CSU71A01", kind: "assessment", right: 2, wrong: 1, wrong_working: 1, blank: 1, pages: [1] });
  expect((await childLevels(kids.Asha)).find((l) => l.code === SKILL)?.level).toBe("Medium");
  expect(await childTopicPapers(kids.Chetan, COORDINATOR)).toEqual([]);
});
