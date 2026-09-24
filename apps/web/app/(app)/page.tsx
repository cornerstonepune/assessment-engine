import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { DIFFICULTIES, GRADE_GROUPS, gradeOf, type Difficulty } from "@/lib/queries";
import { type CurriculumSkill, curriculum } from "@/lib/queries-curriculum";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const fmt = (n: number) => n.toLocaleString("en-IN");

// Curriculum — the shared tree (goals/t1-topics.yaml, u5-curriculum.yaml): grade → subject → topic → skill, as what a
// child can do → its levels, each with its rule, its questions and its worksheets. Every number opens what it counts,
// and a skill waiting for approval says so where it stands.
export default async function CurriculumPage({ searchParams }: Props) {
  const q = await searchParams;
  const { subject, skills } = await deadline(curriculum());
  const waiting = skills.filter((s) => s.status !== "ratified");

  return (
    <>
      <PageHeader
        stage="Curriculum"
        title="Curriculum"
        sub="Every grade's skills, by subject and topic, each written as what a child can do. Open a skill for its levels, their questions and their worksheets."
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
          <Link href="/library" className="chip">
            Every question in the bank
          </Link>
        </p>
        <div className="grid gap-[18px]">
          {GRADE_GROUPS.map(([band, words]) => {
            // A skill stands under every grade one of its levels belongs to, with those levels only.
            const inGrade = (s: CurriculumSkill) => DIFFICULTIES.filter((d) => s.difficulty[d] && gradeOf(s, d) === band);
            const group = skills.filter((s) => inGrade(s).length);
            if (!group.length) return null;
            const topics = [...new Map(group.map((s) => [s.topic_code ?? "", s])).values()].sort(
              (a, b) => (a.topic_ord ?? 99) - (b.topic_ord ?? 99),
            );
            const count = (xs: Partial<Record<string, number>>, s: CurriculumSkill) => inGrade(s).reduce((n, d) => n + (xs[d] ?? 0), 0);
            const counts = `${group.length} ${group.length === 1 ? "skill" : "skills"} · ${fmt(group.reduce((n, s) => n + count(s.counts, s), 0))} questions · ${fmt(group.reduce((n, s) => n + count(s.worksheets, s), 0))} worksheets`;
            return (
              <Panel key={band} title={words} label={words} aside={counts}>
                <div className="mb-2 font-heading text-[14px] text-basalt/70">{subject}</div>
                <div className="grid gap-3">
                  {topics.map((t) => (
                    <Topic key={t.topic_code ?? ""} name={t.topic_name ?? "Other"} band={band} skills={group.filter((s) => s.topic_code === t.topic_code)} />
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

function Topic({ name, band, skills }: { name: string; band: string; skills: CurriculumSkill[] }) {
  const waiting = skills.filter((s) => s.status !== "ratified").length;
  return (
    <details open data-topic={name} className="rounded-md border border-basalt/10 bg-chalk/40 px-3 py-2">
      <summary className="cursor-pointer text-[14.5px]">
        <span className="font-heading">{name}</span>
        <span className="ml-2 text-[12px] text-basalt/62">
          {skills.length} {skills.length === 1 ? "skill" : "skills"}
        </span>
        {waiting ? (
          <span className="ml-2">
            <Pill tone="bamboo">{waiting} waiting for approval</Pill>
          </span>
        ) : null}
      </summary>
      <div className="mt-2 grid gap-2">
        {skills.map((s) => (
          <SkillNode key={s.code} s={s} band={band} />
        ))}
      </div>
    </details>
  );
}

function SkillNode({ s, band }: { s: CurriculumSkill; band: string }) {
  const levels: Difficulty[] = DIFFICULTIES.filter((d) => s.difficulty[d] && gradeOf(s, d) === band);
  const elsewhere = DIFFICULTIES.filter((d) => s.difficulty[d] && gradeOf(s, d) !== band);
  return (
    <details role="group" aria-label={s.learning_objective} className="rounded-md border border-basalt/15 bg-white px-3 py-2">
      <summary className="cursor-pointer text-[14px]">
        <span className="text-basalt">{s.learning_objective}</span>
        <span className="ml-2 inline-flex flex-wrap items-center gap-2 align-middle text-[12px] text-basalt/62">
          {s.name}
          {s.status === "ratified" ? <Pill tone="neem">approved</Pill> : <Pill tone="bamboo">waiting for approval</Pill>}
          <Link href={`/skill-sets/${s.code}`}>Read, edit and approve</Link>
          {elsewhere.length ? (
            <span className="text-basalt/55">
              · {elsewhere.map((d) => `${d} in ${GRADE_GROUPS.find(([b]) => b === gradeOf(s, d))?.[1] ?? gradeOf(s, d)}`).join(", ")}
            </span>
          ) : null}
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
                <Link href={`/skill-sets/${s.code}?level=${d}#worksheets`} className="text-[12px]">{`${codes.length} worksheets`}</Link>
              </div>
              <div className="mt-1 text-basalt/80">{s.difficulty[d].words}</div>
              <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-[12.5px]">
                {codes.map((c) => (
                  <Link key={c} href={`/worksheets/${c}`} className="font-mono">
                    {c}
                  </Link>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
