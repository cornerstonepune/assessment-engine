import { randomUUID } from "node:crypto";
import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { workScope } from "@/lib/reach";
import { deadline } from "@/lib/deadline";
import { forChildren, KINDS, lineTopics, planBatch, readBatch, topicLines, UUID, WAYS } from "@/lib/maker";
import { levels } from "@/lib/levels";
import { grades, skillSets } from "@/lib/queries";
import { classRoll } from "@/lib/queries-children";
import { homeByClass, homeLength } from "@/lib/queries-make";
import { isoWeek } from "@/lib/week";
import { MakerLines } from "../../make/lines";
import { Made, ThePapers } from "./parts";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

const LINES = 3; // a paper of up to three skills
const QR = /^CS[0-9A-F]{6}$/;
const all = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);

function Choice({ name, value, words, line, checked }: { name: string; value: string; words: string; line: string; checked: boolean }) {
  return (
    <label className="flex cursor-pointer gap-2 border border-basalt/14 p-2 has-[:checked]:border-basalt">
      <input type="radio" name={name} value={value} defaultChecked={checked} className="mt-[3px]" />
      <span>
        <span className="block text-[14px] font-medium">{words}</span>
        <span className="note block">{line}</span>
      </span>
    </label>
  );
}

// The maker (goals/m3-the-maker.yaml). Nimish, 2026-09-30: class practice, class assessments and home assessments,
// each for "multiple children", in one "interface in itself". An educator picks the class, what the paper is, how
// they are made and which children; sees every child's paper; and makes them all in their name.
export default async function Maker({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const get = (k: string) => all(q[k]);
  const week = isoWeek();
  const [classes, homeN, g, { usual }] = await deadline(Promise.all([homeByClass(week, await workScope(me)), homeLength(), grades(), levels()]));
  const cls = classes.find((c) => c.section === get("class")[0]);
  // every skill, each saying whether this class was taught it: an educator may choose any (ADR 0081); the engine's
  // own choice, a child's next step, keeps to what the class was taught (goals/f1f-taught-per-class.yaml)
  const every = cls ? await deadline(skillSets({ untaught: true, section: cls.section })) : [];
  const sets = every.filter((x) => x.taught);
  // a starting point's kind and way hold until the class is chosen; "for one child" ticks no one until they are chosen
  const one = get("one")[0] === "1";
  const topic = get("topic")[0] ?? "";
  const fromTopic = cls && topic && !get("s").some(Boolean) && !get("a").length ? topicLines(g, sets, topic, cls.band, homeN, LINES, usual) : [];
  const roll = cls ? await deadline(classRoll(cls.section, me.email)) : [];
  // every child is ticked until the form for this class has been sent
  const sent = get("picked").length > 0 && get("of")[0] === cls?.section;
  const read = cls ? readBatch((k) => (k === "a" && fromTopic.length ? fromTopic : get(k)), week) : null;
  const batch = read && forChildren(read, roll.filter((c) => (sent ? read.children.includes(c.id) : !one)).map((c) => c.id));
  const ticked = new Set(batch ? batch.children : one ? [] : roll.map((c) => c.id));
  const kind = batch?.kind ?? get("kind")[0] ?? "practice";
  const way = batch?.way ?? get("way")[0] ?? "each";
  const ready = batch && batch.children.length > 0 && (batch.way === "own" || batch.areas.length > 0) ? batch : null;
  const planned = ready ? await planBatch(ready) : null;
  // a form the engine did not answer on comes back with its own `once`, so sending it again makes its papers once
  const once = UUID.test(get("once")[0] ?? "") ? get("once")[0] : randomUUID();
  const made = (get("made")[0] ?? "").split(".").filter((x) => QR.test(x));
  const lines = Array.from({ length: LINES }, (_, i) => batch?.areas[i]);

  return (
    <>
      <PageHeader
        stage="Assessments · make"
        title="Make papers"
        sub="Class practice, class assessments and home assessments, for any children of a class: one paper for all, the same skill with different questions for each, or each child's own next step. You see every paper before anything prints."
      />
      <Body>
        {made.length ? (
          <div className="mb-[18px]">
            <Made qrs={made} section={get("class")[0] ?? ""} kind={get("kind")[0] ?? ""} week={week} already={!!get("already").length} />
          </div>
        ) : null}
        {get("why")[0] ? <Notice tone="terracotta">{get("why")[0]}</Notice> : null}
        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)]">
          <Panel title="Choose">
            <form id="choose" method="get" action="/papers/make" aria-label="Choose the papers" className="group grid gap-4">
              <label className="field">
                <span className="label">Class</span>
                <select className="select" name="class" defaultValue={cls?.section ?? ""}>
                  <option value="">Choose a class</option>
                  {classes.map((c) => (
                    <option key={c.section} value={c.section}>
                      {c.section} · {g.name(c.band)} · {c.children} children
                    </option>
                  ))}
                </select>
              </label>
              {cls ? null : (
                <>
                  <input type="hidden" name="kind" value={kind} />
                  <input type="hidden" name="way" value={way} />
                  {one ? <input type="hidden" name="one" value="1" /> : null}
                </>
              )}
              {cls ? (
                <>
                  <input type="hidden" name="picked" value="1" />
                  <input type="hidden" name="of" value={cls.section} />
                  <fieldset className="grid gap-2">
                    <legend className="label mb-2">What it is</legend>
                    {KINDS.map(([v, words, line]) => (
                      <Choice key={v} name="kind" value={v} words={words} line={line} checked={v === kind} />
                    ))}
                  </fieldset>
                  <fieldset className="grid gap-2">
                    <legend className="label mb-2">How</legend>
                    {WAYS.map(([v, words, line]) => (
                      <Choice key={v} name="way" value={v} words={words} line={line} checked={v === way} />
                    ))}
                  </fieldset>
                  <fieldset className="grid gap-1">
                    <legend className="label mb-2">Children</legend>
                    <div className="grid gap-1 sm:grid-cols-2">
                      {roll.map((c) => (
                        <label key={c.id} className="flex items-center gap-2 text-[14px]">
                          <input type="checkbox" name="c" value={c.id} defaultChecked={ticked.has(c.id)} />
                          <span className="fact w-6 text-basalt/55">{c.roll_no}</span> {c.first_name}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  {/* the skill and level are the educator's for one paper for all and for the same skill for each */}
                  <fieldset className="grid gap-2 group-has-[input[value=own]:checked]:hidden">
                    <legend className="label mb-2">Each line: a topic, its skill, a level, how many questions</legend>
                    <MakerLines
                      key={`${cls.section}|${lines.map((a) => (a ? `${a.skill_set}~${a.level}~${a.n}` : "")).join("|")}`}
                      topics={lineTopics(g, every, cls.band, homeN, LINES, usual)}
                      usual={usual}
                      start={lines.map((a, i) => (a ? `${a.skill_set}~${a.level}~${a.n}` : i === 0 ? `~~${homeN ?? ""}` : ""))}
                      topic={topic}
                      fill
                    />
                  </fieldset>
                  <p className="note hidden group-has-[input[value=own]:checked]:block">
                    The engine picks each child&rsquo;s skill and level from their checked answers. See the papers, then change any child.
                  </p>
                </>
              ) : null}
              <button className="btn self-start" type="submit">
                {cls ? "See the papers" : "Show the class"}
              </button>
            </form>
          </Panel>

          {/* a grid item is as wide as its widest content unless told otherwise: the table scrolls, the page does not */}
          <section aria-label="The papers" className="min-w-0">
            {planned && "refused" in planned ? (
              <Notice tone="terracotta">{planned.refused}</Notice>
            ) : planned && ready && cls ? (
              <ThePapers plan={planned.plan} batch={ready} roll={roll} sets={sets} band={cls.band} once={once} />
            ) : (
              <Panel title="The papers">
                <p className="note">
                  {!cls
                    ? "Choose a class to begin."
                    : batch && !batch.children.length
                      ? "Tick at least one child."
                      : "Choose what the paper is, how, and the children, then see every child's paper before anything is made."}
                </p>
                <p className="note mt-3">
                  The engine&rsquo;s own home assessment for each child, class by class, is also one click away in{" "}
                  <Link href="/make">Home assessments</Link>.
                </p>
              </Panel>
            )}
          </section>
        </div>
      </Body>
    </>
  );
}
