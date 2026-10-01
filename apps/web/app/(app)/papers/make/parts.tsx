import Link from "@/components/link";
import { Panel, Pill } from "@/components/shell";
import type { SkillSet } from "@/lib/queries";
import { KINDS, type Batch, type MakerPlan, type PlannedPaper } from "@/lib/maker";
import { SkillLevelSelect } from "../../make/skill-level";
import { makePapers } from "./actions";
import { MakeButton } from "./make-button";

type Child = { id: string; roll_no: string; first_name: string };

function Questions({ areas }: { areas: PlannedPaper["areas"] }) {
  return (
    <>
      {areas.map((a) => (
        <ol key={`${a.skill_set}~${a.level}`} aria-label={`${a.name} · ${a.level}`} className="grid list-decimal gap-1 pl-5 text-[13px]">
          {a.questions.map((x) => (
            <li key={x.item_key}>{x.text}</li>
          ))}
        </ol>
      ))}
    </>
  );
}

const paperWords = (p: PlannedPaper) => p.areas.map((a) => `${a.name} · ${a.level}`).join(" + ");

// Every picked child's paper before anything is made (goals/m3-the-maker.yaml): what it holds, why, and each child
// whose paper cannot be made with the engine's words. On each child's own next step, any child can be changed; the
// papers are made in the educator's name only when every one can be.
export function ThePapers({ plan, batch, roll, sets, band, once }: {
  plan: MakerPlan; batch: Batch; roll: Child[]; sets: SkillSet[]; band: string; once: string;
}) {
  const papers = new Map(plan.papers.map((p) => [p.child_id, p]));
  const refused = new Map(plan.refused.map((r) => [r.child_id, r]));
  const own = batch.way === "own";
  const shared = batch.way === "same" ? plan.papers[0] : undefined;
  const ready = plan.papers.length > 0 && plan.refused.length === 0;
  const n = plan.papers.length;
  return (
    <Panel title="The papers" aside={`${n} ${n === 1 ? "paper" : "papers"}`}>
      {shared ? (
        <div className="mb-4">
          <p className="note mb-2">
            Every paper holds these {shared.n} questions, {paperWords(shared)}; each child&rsquo;s copy has its own code.
          </p>
          <Questions areas={shared.areas} />
        </div>
      ) : null}
      <div className="overflow-x-auto">
        <table className="grid" aria-label="Each child's paper">
          <thead>
            <tr>
              <th>Roll</th>
              <th>Child</th>
              <th>Their paper</th>
              {own ? <th>Change</th> : null}
            </tr>
          </thead>
          <tbody>
            {roll
              .filter((c) => papers.has(c.id) || refused.has(c.id))
              .map((c) => {
                const p = papers.get(c.id);
                const r = refused.get(c.id);
                const change = batch.changed[c.id]?.[0];
                return (
                  <tr key={c.id} data-child={c.id}>
                    <td className="fact">{c.roll_no}</td>
                    <td className="whitespace-nowrap">{c.first_name}</td>
                    <td>
                      {p ? (
                        <>
                          <div className="font-medium">
                            {paperWords(p)} <span className="text-basalt/55">· {p.n} questions</span>
                          </div>
                          {own ? (
                            <div className="note">{p.chosen === "graph" ? p.areas.map((a) => a.why).join(" ") : "Chosen by you."}</div>
                          ) : null}
                          {shared ? null : (
                            <details className="mt-1">
                              <summary className="cursor-pointer text-[13px]">Its questions</summary>
                              <Questions areas={p.areas} />
                            </details>
                          )}
                        </>
                      ) : (
                        <>
                          <Pill tone="terracotta">cannot be made</Pill>
                          <div className="mt-1 text-[13px]">{r?.why}</div>
                        </>
                      )}
                    </td>
                    {own ? (
                      <td className="min-w-[14rem]">
                        <SkillLevelSelect
                          name="x"
                          label={`Change ${c.first_name}'s paper`}
                          value={change ? `${c.id}~${change.skill_set}~${change.level}` : ""}
                          sets={sets}
                          band={band}
                          prefix={`${c.id}~`}
                          empty="their own next step"
                          form="choose"
                        />
                      </td>
                    ) : null}
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
      {own ? (
        <button form="choose" className="btn secondary mt-3" type="submit">
          See the papers with these changes
        </button>
      ) : null}
      <form action={makePapers} className="mt-4 border-t border-basalt/10 pt-4">
        <input type="hidden" name="class" value={batch.section} />
        <input type="hidden" name="kind" value={batch.kind} />
        <input type="hidden" name="way" value={batch.way} />
        <input type="hidden" name="week" value={batch.week} />
        <input type="hidden" name="once" value={once} />
        {batch.children.map((c) => (
          <input key={c} type="hidden" name="c" value={c} />
        ))}
        {batch.areas.map((a) => (
          <input key={`${a.skill_set}~${a.level}`} type="hidden" name="a" value={`${a.skill_set}~${a.level}~${a.n}`} />
        ))}
        {Object.entries(batch.changed).map(([c, [a]]) => (
          <input key={c} type="hidden" name="x" value={`${c}~${a.skill_set}~${a.level}`} />
        ))}
        <MakeButton n={n} kind={(KINDS.find(([k]) => k === batch.kind)?.[1] ?? batch.kind).toLowerCase()} ready={ready} />
      </form>
    </Panel>
  );
}

// The papers just made: print them as one, or find them in Papers.
export function Made({ qrs, section, kind, week, already }: {
  qrs: string[]; section: string; kind: string; week: string; already: boolean;
}) {
  const n = qrs.length;
  return (
    <Panel title={already ? "Already made" : "Made"} label="Made">
      <p className="mb-3 text-[14px]">
        {already
          ? `These ${n} papers were made before; nothing was printed twice.`
          : `${n} ${n === 1 ? "paper" : "papers"} made and approved in your name.`}
      </p>
      <div className="flex flex-wrap gap-3">
        <a className="btn" href={`/api/papers/print?${qrs.map((q) => `qr=${q}`).join("&")}`} target="_blank" rel="noreferrer">
          Print them all
        </a>
        <Link href={`/papers?class=${encodeURIComponent(section)}&week=${week}&kind=${kind}`} className="btn secondary">
          See them in Papers
        </Link>
      </div>
    </Panel>
  );
}
