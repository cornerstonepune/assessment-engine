import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { papersToApprove, type PaperRow } from "@/lib/queries-read";
import { deadline } from "@/lib/deadline";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

type Student = {
  id: string;
  first_name: string;
  section: string;
  roll_no: string;
  papers: PaperRow[];
  toSign: number; // papers read with an answer not yet signed off
  answers: number; // answers not yet signed off, across those papers
};

// Nimish, 2026-09-22: a student's name, then their papers, then every question of one paper — checked
// student by student, so each child's ladder is whole once their papers are signed off, and a class can
// be handed to one person. Students in roll order within a class, as Child Growth lists them.
function byStudent(papers: PaperRow[]): Student[] {
  const out = new Map<string, Student>();
  for (const p of papers) {
    const s = out.get(p.child_id) ?? { id: p.child_id, first_name: p.first_name, section: p.section, roll_no: p.roll_no, papers: [], toSign: 0, answers: 0 };
    s.papers.push(p);
    if (p.n_results > 0 && p.n_candidate > 0) {
      s.toSign += 1;
      s.answers += p.n_candidate;
    }
    out.set(p.child_id, s);
  }
  const roll = (s: Student) => Number(s.roll_no.replace(/\D/g, "")) || 9999;
  return [...out.values()].sort((a, b) => a.section.localeCompare(b.section) || roll(a) - roll(b) || a.first_name.localeCompare(b.first_name));
}

export default async function CapturePage({ searchParams }: Props) {
  const me = await requireStaff();
  const { child } = await searchParams;
  const students = byStudent(await deadline(papersToApprove(me.email)));
  if (child) return <StudentPapers students={students} id={child} />;

  const sections = [...new Set(students.map((s) => s.section))];
  const done = students.filter((s) => s.toSign === 0);
  const papersToSign = students.reduce((n, s) => n + s.toSign, 0);
  const answers = students.reduce((n, s) => n + s.answers, 0);
  const flagged = students.reduce((n, s) => n + s.papers.reduce((m, p) => m + p.n_flagged, 0), 0);
  const broken = students.flatMap((s) => s.papers.filter((p) => p.n_results === 0));

  return (
    <>
      <PageHeader
        stage="Stage 3 · Read"
        title="Capture & Mark"
        sub="Student by student: open a student, open a paper, check every answer against the child's writing and sign it off. A student's ladder is built once their papers are signed off."
      />
      <Body>
        {flagged > 0 ? (
          <div className="mb-[18px] flex flex-wrap items-center gap-3">
            <Link href="/capture/check" className="btn">
              Check the {flagged} answers the reader was unsure of →
            </Link>
            <span className="note">One at a time across every student, with the child&rsquo;s own writing and the reader&rsquo;s best guess.</span>
          </div>
        ) : null}
        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-4">
          <Tile tone="neem" n={done.length} words={`of ${students.length} students fully signed off`} />
          <Tile tone="terracotta" n={students.length - done.length} words="students with papers to check" />
          <Tile tone="bamboo" n={papersToSign} words="papers to sign off" />
          <Tile tone="monsoon" n={answers} words="answers not yet signed off" />
        </div>

        <div className="grid min-w-0 gap-[18px]">
          {sections.map((section) => {
            const rows = students.filter((s) => s.section === section);
            return (
              <Panel key={section} title={section} aside={`${rows.filter((s) => s.toSign === 0).length} of ${rows.length} students done`}>
                <div className="min-w-0 overflow-x-auto">
                  <table className="grid">
                    <thead>
                      <tr>
                        <th>Roll</th>
                        <th>Student</th>
                        <th className="text-right">Papers</th>
                        <th className="text-right">Papers to sign off</th>
                        <th className="text-right">Answers to check</th>
                        <th>State</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((s) => (
                        <tr key={s.id}>
                          <td className="fact">{s.roll_no}</td>
                          <td>
                            <Link href={`/capture?child=${s.id}`}>{s.first_name}</Link>
                          </td>
                          <td className="num">{s.papers.filter((p) => p.n_results > 0).length}</td>
                          <td className="num">{s.toSign || "—"}</td>
                          <td className="num">{s.answers || "—"}</td>
                          <td className="whitespace-nowrap">
                            {s.toSign === 0 ? <Pill tone="neem">all signed off</Pill> : <Pill tone="bamboo">to check</Pill>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            );
          })}

          {broken.length > 0 ? (
            <Panel title="Read, but nothing came back" aside={`${broken.length}`}>
              <p className="note mb-3">
                These papers were opened and produced no answers at all. A paper entered with the wrong questions, or a
                read that failed part way — either way nothing here counts for anything yet.
              </p>
              <PaperTable rows={broken} withChild />
            </Panel>
          ) : null}
        </div>
      </Body>
    </>
  );
}

// One student's papers, oldest first — the order the paper page steps through with "Next paper".
function StudentPapers({ students, id }: { students: Student[]; id: string }) {
  const at = students.findIndex((s) => s.id === id);
  if (at < 0) notFound();
  const s = students[at];
  const papers = s.papers.filter((p) => p.n_results > 0).sort((a, b) => (a.date ?? "9999").localeCompare(b.date ?? "9999"));
  const next = students.slice(at + 1).find((n) => n.toSign > 0);

  return (
    <>
      <PageHeader
        stage={`Stage 3 · Read · ${s.section}`}
        title={s.first_name}
        sub={`Roll ${s.roll_no}. ${papers.length} paper${papers.length === 1 ? "" : "s"} read, ${s.toSign} still to sign off. Open a paper, check every answer against ${s.first_name}'s writing, then sign it off.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href="/capture" className="chip">← All students</Link>
          <Link href={`/growth/${s.id}`} className="chip">{s.first_name}&rsquo;s ladder</Link>
          {next ? (
            <Link href={`/capture?child=${next.id}`} className="chip ml-auto">
              Next student to check: {next.first_name} →
            </Link>
          ) : null}
        </p>
        <Panel title="Papers" aside={s.toSign === 0 ? "all signed off" : `${s.toSign} to sign off`}>
          <PaperTable rows={papers} />
        </Panel>
      </Body>
    </>
  );
}

function PaperTable({ rows, withChild = false }: { rows: PaperRow[]; withChild?: boolean }) {
  return (
    <div className="min-w-0 overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            {withChild ? <th>Child</th> : null}
            <th>Paper</th>
            <th>Sat</th>
            <th className="text-right">Answers</th>
            <th className="text-right">Not signed yet</th>
            <th className="text-right">Score</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              {withChild ? (
                <td>
                  {p.first_name}
                  <div className="text-[12px] text-basalt/55">{p.section}</div>
                </td>
              ) : null}
              <td className="max-w-[280px] text-[13px]">
                <Link href={`/capture/${p.id}`}>{p.title ?? p.paper}</Link>
              </td>
              <td className="fact whitespace-nowrap">{fmtDate(p.date)}</td>
              <td className="num">{p.n_results}</td>
              <td className="num">{p.n_candidate || "—"}</td>
              <td className="num whitespace-nowrap">
                {/* A score once nothing on the sheet waits for a person: right, of every answer that counts. */}
                {p.n_results > 0 && p.n_flagged === 0 ? `${p.n_right} / ${p.n_scored} right` : "—"}
              </td>
              <td className="whitespace-nowrap">
                {p.n_results === 0 ? (
                  <Pill tone="terracotta">nothing read</Pill>
                ) : p.n_candidate === 0 ? (
                  <Pill tone="neem">signed off</Pill>
                ) : p.n_flagged > 0 ? (
                  <Pill tone="bamboo">{p.n_flagged} need your eyes</Pill>
                ) : (
                  <Pill tone="monsoon">read, not confirmed</Pill>
                )}
                {p.n_corrected > 0 ? (
                  <span className="ml-2 text-[12px] text-basalt/55">{p.n_corrected} corrected</span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
