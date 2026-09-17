import Link from "next/link";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { DIFFICULTIES, numSkills, skillSets } from "@/lib/queries";

export default async function SkillMapPage() {
  const [sets, skills] = await Promise.all([skillSets(), numSkills()]);
  const banked = sets.reduce((n, s) => n + Object.values(s.counts).reduce((a, b) => a + (b ?? 0), 0), 0);

  return (
    <>
      <PageHeader
        stage="Stage 1 · Input"
        title="Skill Map"
        sub="The single source of truth for what a child can be tested on: every skill, its rung, and the skill sets that generate questions for it."
      />
      <Body>
        <Panel title="Skill sets and their banks" aside={`${sets.length} sets · ${banked} verified items`}>
          <p className="note mb-4">
            A skill set is what Neha and Achal author and Aseem ratifies: the rule for each difficulty, in words and as a
            check. The counts are verified items waiting to be printed, per difficulty.
          </p>
          <div className="overflow-x-auto">
            <table className="grid">
              <thead>
                <tr>
                  <th>Set</th>
                  <th>Rung</th>
                  <th>Name</th>
                  {DIFFICULTIES.map((d) => (
                    <th key={d} className="text-right">{d}</th>
                  ))}
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sets.map((s) => (
                  <tr key={s.code}>
                    <td className="fact">
                      <Link href={`/skill-sets/${s.code}`}>{s.code}</Link>
                    </td>
                    <td className="fact">
                      {s.rung_code} <span className="text-basalt/55">· {s.band}</span>
                    </td>
                    <td>{s.name}</td>
                    {DIFFICULTIES.map((d) => (
                      <td key={d} className="num">{s.counts[d] ?? 0}</td>
                    ))}
                    <td>
                      {s.status === "ratified" ? (
                        <Pill tone="neem">Ratified · {s.ratified_by}</Pill>
                      ) : (
                        <Pill tone="bamboo">Draft</Pill>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="h-[18px]" />

        <Panel title="Registry skills · Number" aside={`${skills.length} skills`}>
          <div className="overflow-x-auto">
            <table className="grid">
              <thead>
                <tr>
                  <th>Skill ID</th>
                  <th>Name</th>
                  <th>Rungs</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((k) => (
                  <tr key={k.code}>
                    <td className="fact">{k.code}</td>
                    <td>
                      {k.name}
                      {k.description ? <div className="note mt-1">{k.description}</div> : null}
                    </td>
                    <td className="fact">{k.rungs.length ? k.rungs.join(" · ") : <span className="text-basalt/40">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <p className="note mt-[14px]">
          Every worksheet item, every marked answer and every child&apos;s skill state trace back to a row on this page.
        </p>
      </Body>
    </>
  );
}
