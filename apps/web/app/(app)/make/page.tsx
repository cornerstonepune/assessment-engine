import { redirect } from "next/navigation";
import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { deadline } from "@/lib/deadline";
import { grades } from "@/lib/queries";
import { homeByClass } from "@/lib/queries-make";
import { classPacksWaiting } from "@/lib/queries-today";
import { isoWeek, weekWords } from "@/lib/week";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { classState, ClassesTable, PacksTable, type ClassLine } from "./classes-table";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const STAGES: Record<string, string> = { toApprove: "To approve", done: "Approved", waiting: "Not enough work yet" };

// Home assessments (goals/m1-make-papers.yaml, goals/uxn5-print-and-give.yaml): each class's home papers for the week,
// proposed by the engine from each child's own map, and the class papers waiting for a person. A class opens where they
// are approved, and where a paper is chosen for any one child. An educator who teaches one class opens on it
// (goals/ux5b-make-and-marking.yaml).
export default async function MakePapers({ searchParams }: Props) {
  const scope = scopeOf(await requireStaff());
  const q = await searchParams;
  if (scope.classes?.length === 1) redirect(`/make/${encodeURIComponent(scope.classes[0])}`);
  const [classes, allPacks, g] = await deadline(Promise.all([homeByClass(undefined, scope), classPacksWaiting(scope), grades()]));
  const lines: ClassLine[] = classes.map((c) => ({
    section: c.section,
    grade: g.name(c.band),
    children: c.children,
    proposed: c.proposed,
    approved: c.approved,
    tooFew: c.children - c.proposed - c.approved,
  }));
  const f = {
    class: q.class && lines.some((c) => c.section === q.class) ? q.class : undefined,
    grade: q.grade && lines.some((c) => c.grade === q.grade) ? q.grade : undefined,
    status: q.status && q.status in STAGES ? q.status : undefined,
  };
  const shown = lines.filter((c) => (!f.class || c.section === f.class) && (!f.grade || c.grade === f.grade) && (!f.status || classState(c) === f.status));
  const packs = allPacks.filter((p) => (!f.class || p.section === f.class) && (!f.grade || g.name(p.band) === f.grade));
  const first = allPacks[0];
  const page = Math.max(1, Math.floor(Number(q.page)) || 1);
  const pageHref = (n: number) => `/make?${new URLSearchParams({ ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), page: String(n) })}`;
  return (
    <PageShell
      stage="Assessments · home assessments"
      title="Home assessments"
      purpose="Each child's home assessment for the week, from their own map, and the class papers waiting for you. Nothing prints until you approve it."
      action={
        first ? (
          <Link href={`/papers/approve?section=${encodeURIComponent(first.section)}&week=${encodeURIComponent(first.week)}&kind=${first.kind}`} className="btn">
            Approve class papers
          </Link>
        ) : (
          <Link href="/papers/make?kind=assessment&way=same" className="btn">
            Make an assessment
          </Link>
        )
      }
      next={{ href: "/capture", label: "Upload papers" }}
    >
      <FilterBar
        action="/make"
        filters={[
          { name: "class", label: "Class", value: f.class, all: "Every class", options: lines.map((c) => [c.section, c.section] as const) },
          { name: "grade", label: "Grade", value: f.grade, all: "Every grade", options: [...new Set(lines.map((c) => c.grade))].map((x) => [x, x] as const) },
          { name: "status", label: "Status", value: f.status, all: "Any status", options: Object.entries(STAGES) },
        ]}
      />
      <section aria-label="Home assessments this week" className="mb-6">
        <h2 className="label mb-2">Home assessments · {weekWords(isoWeek())}</h2>
        <p className="note mb-3">
          One skill per child, never a mix: the weakest they are working on, at a level where their mistake can show; a child with
          nothing red or amber is stretched one level up on their strongest skill. Open a class to approve, or to choose a different
          paper for any child.
        </p>
        <ClassesTable rows={shown} page={page} pageHref={pageHref} />
        {shown.length === 0 ? <p className="note mt-2">Nothing matches these filters.</p> : null}
      </section>
      <section aria-label="Class papers">
        <h2 className="label mb-2">Class papers · {packs.length} waiting for you</h2>
        {packs.length ? <PacksTable rows={packs} page={Math.max(1, Math.floor(Number(q.ppage)) || 1)} pageHref={(n) => `/make?${new URLSearchParams({ ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), ppage: String(n) })}`} /> : <p className="note">Nothing waiting.</p>}
        <p className="mt-3 text-[13px]">
          <Link href="/worksheets">Every class&rsquo;s papers, week by week →</Link>
        </p>
      </section>
    </PageShell>
  );
}
