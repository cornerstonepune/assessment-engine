import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, GRADE_GROUPS } from "@/lib/queries";
import { type CurriculumSkill, curriculum } from "@/lib/queries-curriculum";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Curriculum — one tree a teacher reads top to bottom (goals/u5-curriculum.yaml): grade → subject → skill, as what
// a child can do → its levels, each in a sentence → the worksheets under each level. Every number opens what it counts.
export default async function CurriculumPage({ searchParams }: Props) {
  const q = await searchParams;
  const { subject, skills } = await deadline(curriculum());
  const waiting = skills.filter((s) => s.status !== "ratified");

  return (
    <>
      <PageHeader
        stage="Curriculum"
        title="Curriculum"
        sub="Each grade's skills, each written as what a child can do. Open a skill for its levels, and a level for its worksheets."
      />
      <Body>
        {q.approved ? <Notice tone="neem">Approved {q.approved} as written, in your name.</Notice> : null}
        {waiting.length ? (
          <Notice tone="terracotta">
            {waiting.length} {waiting.length === 1 ? "skill waits" : "skills wait"} for approval.{" "}
            <Link href="/skill-sets/approve">Read and approve →</Link>
          </Notice>
        ) : null}
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href="/worksheets/taxonomy" className="chip">
            Read the same worksheets by the taxonomy
          </Link>
        </p>
        <div className="grid gap-[18px]">
          {GRADE_GROUPS.map(([band, words]) => {
            const group = skills.filter((s) => s.band === band);
            if (!group.length) return null;
            return (
              <Panel key={band} title={words} label={words} aside={`${group.length} ${group.length === 1 ? "skill" : "skills"}`}>
                <div className="mb-2 font-heading text-[14px] text-basalt/70">{subject}</div>
                <div className="grid gap-2">
                  {group.map((s) => (
                    <SkillNode key={s.code} s={s} />
                  ))}
                </div>
              </Panel>
            );
          })}
        </div>
      </Body>
    </>
  );
}

function SkillNode({ s }: { s: CurriculumSkill }) {
  const levels = DIFFICULTIES.filter((d) => s.difficulty[d]);
  return (
    <details role="group" aria-label={s.learning_objective} className="rounded-md border border-basalt/15 px-3 py-2">
      <summary className="cursor-pointer text-[14px]">
        <span className="text-basalt">{s.learning_objective}</span>
        <span className="ml-2 inline-flex flex-wrap items-center gap-2 align-middle text-[12px] text-basalt/62">
          {s.name}
          {s.status === "ratified" ? (
            <Pill tone="neem">approved</Pill>
          ) : (
            <Pill tone="bamboo">waiting for approval</Pill>
          )}
          <Link href={`/skill-sets/${s.code}`}>Read, edit and approve</Link>
        </span>
      </summary>
      <ul className="mt-3 grid gap-3" aria-label={`Levels of ${s.name}`}>
        {levels.map((d) => {
          const codes = s.sheets[d] ?? [];
          return (
            <li key={d} className="text-[13.5px]">
              <div className="flex flex-wrap items-baseline gap-2">
                <Pill tone="monsoon">{d}</Pill>
                <Link href={`/library?set=${s.code}&difficulty=${d}#questions`}>{`${s.counts[d] ?? 0} questions`}</Link>
                <span className="text-[12px] text-basalt/62">{`${codes.length} worksheets`}</span>
              </div>
              <div className="mt-1 text-basalt/80">{s.difficulty[d].words}</div>
              {codes.length ? (
                <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-[12.5px]">
                  {codes.map((c) => (
                    <Link key={c} href={`/worksheets/${c}`} className="font-mono">
                      {c}
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="note mt-1">no worksheets yet</div>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
