import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, GRADE_GROUPS, skillSets } from "@/lib/queries";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// The skills the engine teaches, each as what a child can do — the words a teacher reads, never a
// code or a topic label (Nimish, 2026-09-21: "the outcome needs to be articulated as a skill").
// Grouped by grade; every number opens what it counts.
export default async function SkillMapPage({ searchParams }: Props) {
  const q = await searchParams;
  const sets = await deadline(skillSets());
  const waiting = sets.filter((s) => s.status !== "ratified");

  return (
    <>
      <PageHeader
        stage="Stage 1 · Input"
        title="Skill Map"
        sub={`The ${sets.length} skills the engine teaches in addition, subtraction, multiplication and reasoning, each written as what a child can do. Open one to see it at every level with a real question, the mistakes it watches for, and its worksheets.`}
      />
      <Body>
        {q.approved ? <Notice tone="neem">Approved {q.approved} as written, in your name.</Notice> : null}
        {waiting.length ? (
          <Notice tone="terracotta">
            {waiting.length === sets.length ? "All" : waiting.length} {waiting.length === 1 ? "skill is" : "skills are"} waiting
            for approval: the engine has written {waiting.length === 1 ? "it" : "them"} as what a child can do.{" "}
            <Link href="/skill-sets/approve">Read and approve →</Link>
          </Notice>
        ) : null}
        <div className="grid gap-[18px]">
          {GRADE_GROUPS.map(([band, words]) => {
            const group = sets.filter((s) => s.band === band);
            if (!group.length) return null;
            return (
              <Panel key={band} title={words} aside={`${group.length} ${group.length === 1 ? "skill" : "skills"}`}>
                <div className="overflow-x-auto">
                  <table className="grid" aria-label={`${words} skills`}>
                    <thead>
                      <tr>
                        <th>What the child can do</th>
                        {DIFFICULTIES.map((d) => (
                          <th key={d} className="text-right">
                            {d}
                          </th>
                        ))}
                        <th>Approved</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.map((s) => (
                        <tr key={s.code}>
                          <td className="min-w-[300px] max-w-[520px]">
                            <Link href={`/skill-sets/${s.code}`} className="text-basalt">
                              {s.learning_objective}
                            </Link>
                            <div className="note mt-1">
                              Skill {sets.indexOf(s) + 1} · {s.name}
                            </div>
                          </td>
                          {DIFFICULTIES.map((d) => (
                            <td key={d} className="num whitespace-nowrap align-top">
                              <Link
                                href={`/library?set=${s.code}&difficulty=${d}#questions`}
                                aria-label={`${s.name}, ${d}: ${s.counts[d] ?? 0} questions`}
                              >
                                {s.counts[d] ?? 0} questions
                              </Link>
                              <div className="note">
                                {s.worksheets[d] ? (
                                  <Link href={`/skill-sets/${s.code}?level=${d}#worksheets`}>{s.worksheets[d]} worksheets</Link>
                                ) : (
                                  "no worksheets yet"
                                )}
                              </div>
                            </td>
                          ))}
                          <td className="align-top">
                            {s.status === "ratified" ? (
                              <Pill tone="neem">{s.ratified_by?.split(" (")[0]}</Pill>
                            ) : (
                              <Pill tone="bamboo">waiting</Pill>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            );
          })}
        </div>
      </Body>
    </>
  );
}
