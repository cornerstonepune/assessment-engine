import Link from "@/components/link";
import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { childTable } from "@/lib/queries-children";
import { grades as schoolGrades } from "@/lib/queries";
import { deadline } from "@/lib/deadline";
import { ColourKeyLine } from "@/components/colour-key";
import { colourRules } from "@/lib/colours";
import { childStates } from "@/lib/states";
import { reportRank, reportWaits } from "@/lib/queries-reports";
import type { ChildRow } from "@/lib/queries-children";
import { ChildrenTable, ClassesTable, childState, needsFirst, type ClassLine } from "./tables";

// how each column sorts, as the query gives the roll order and a sort is stable: "help" is the one that puts who needs the
// educator first, and what a click on any other heading gives
const helpRank = (h: ChildRow["help"]) => (!h ? 2 : h.rag === "red" ? 0 : 1);
const SORTS: Record<string, { dir: "ascending" | "descending" | "other"; by: (a: ChildRow, b: ChildRow) => number }> = {
  roll: { dir: "ascending", by: () => 0 },
  name: { dir: "ascending", by: (a, b) => a.first_name.localeCompare(b.first_name) },
  help: { dir: "other", by: (a, b) => needsFirst(a, b) || helpRank(a.help) - helpRank(b.help) },
  needs: { dir: "descending", by: (a, b) => b.needs_help - a.needs_help },
  amber: { dir: "descending", by: (a, b) => b.amber - a.amber },
  green: { dir: "descending", by: (a, b) => b.green - a.green },
  waiting: { dir: "descending", by: (a, b) => b.waiting - a.waiting },
  report: { dir: "other", by: (a, b) => reportRank(a.report) - reportRank(b.report) },
};

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const STATUS = [
  ["help", "Needs help"],
  ["waiting", "Answers or a report waiting"],
  ["fine", "Doing well"],
] as const;

// Class results (goals/ux3-children-grouped.yaml, ux10-declutter.yaml, uxn9-class-results.yaml): the classes side by side,
// and under them the children of the class chosen (an educator who teaches one class opens on it) or, across the
// classes, the children who need the educator first. A class still opens against every skill (goals/u2-children.yaml).
// Finding a child is the bar at the top's (goals/s1-subject-class-and-today.yaml).
export default async function ChildrenPage({ searchParams }: Props) {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const q = await searchParams;
  const [rows, rules, school, states] = await deadline(Promise.all([childTable(me.email, null, scope), colourRules(), schoolGrades(), childStates()]));
  const sortKey = q.sort && q.sort in SORTS ? q.sort : "help";
  const own = scope.classes !== null;
  const classes = [...new Set(rows.map((r) => r.section))].sort();
  const bands = school.list.map((x) => x.code).filter((b) => rows.some((r) => r.band === b));
  const grade = q.grade && bands.includes(q.grade) ? q.grade : undefined;
  const status = STATUS.some(([v]) => v === q.status) ? q.status : undefined;
  // the class asked for, else the one an educator teaches alone
  const section = (q.class && classes.includes(q.class) ? q.class : undefined) ?? (classes.length === 1 ? classes[0] : undefined);
  const keep = { grade, class: q.class && classes.includes(q.class) ? q.class : undefined, status };
  const inStatus = (c: (typeof rows)[number]) => !status || (status === "help" ? c.needs_help > 0 : status === "waiting" ? c.needs_help === 0 && (c.waiting > 0 || reportWaits(c.report)) : childState(c).state === "fine");
  const inGrade = rows.filter((r) => !grade || r.band === grade);
  const lines: ClassLine[] = [...new Set(inGrade.map((r) => r.section))].sort().map((s) => {
    const kids = inGrade.filter((r) => r.section === s);
    return { section: s, grade: school.name(kids[0].band), kids };
  });
  const shownClasses = lines.filter((c) => (!keep.class || c.section === keep.class) && (!status || c.kids.some(inStatus)));
  const kids = inGrade.filter((r) => (!section || r.section === section) && inStatus(r));
  // one class: its children in roll order, help first; across classes only those who need the educator
  const children = (section ? kids : kids.filter((c) => c.needs_help > 0 || c.waiting > 0 || reportWaits(c.report) || !!status)).sort(SORTS[sortKey].by);
  const waiting = rows.reduce((n, r) => n + r.waiting, 0);
  const page = Math.max(1, Math.floor(Number(q.page)) || 1);
  const pageHref = (n: number, k = "page") => `/growth?${new URLSearchParams({ ...(Object.fromEntries(Object.entries(keep).filter(([, v]) => v)) as Record<string, string>), [k]: String(n) })}`;

  return (
    <PageShell
      stage="Class results"
      title="Class results"
      purpose={own ? "Your classes. The children who need you come first." : "Every class, grade by grade. The children who need you come first."}
      action={
        waiting ? (
          <Link href="/capture/check" className="btn">
            Check {waiting} {waiting === 1 ? "answer" : "answers"} →
          </Link>
        ) : (
          <Link href="/papers/make?kind=assessment&way=same" className="btn">
            Make an assessment
          </Link>
        )
      }
      next={{ href: "/today", label: "Today" }}
    >
      {rows.length === 0 ? (
        <p className="note">No child is on the roll yet.</p>
      ) : (
        <div id="children" className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          <FilterBar
            action="/growth"
            filters={[
              { name: "grade", label: "Grade", value: grade, all: "Every grade", options: bands.map((b) => [b, school.name(b)] as const) },
              { name: "class", label: "Class", value: keep.class, all: "Every class", options: classes.map((c) => [c, c] as const) },
              { name: "status", label: "Status", value: status, all: "Any status", options: STATUS },
            ]}
          />
          <section aria-label={section ? `Children of ${section}` : "Children who need you"}>
            <h2 className="label mb-2">{section ? `Children of ${section}` : "Children who need you"} · {children.length}</h2>
            {children.length ? (
              <ChildrenTable rows={children} label={section ? `${section}: its children` : "Children who need you"} withClass={!section} page={page} pageHref={(n) => pageHref(n)} sort={{ key: sortKey, dir: SORTS[sortKey].dir, href: (key) => `/growth?${new URLSearchParams({ ...(Object.fromEntries(Object.entries(keep).filter(([, v]) => v)) as Record<string, string>), ...(key === "help" ? {} : { sort: key }) })}` }} />
            ) : (
              <p className="note">{section || status ? "Nobody matches these filters." : "Nobody needs you right now."}</p>
            )}
          </section>
          <section aria-label="Classes">
            <h2 className="label mb-2">Classes · {shownClasses.length}</h2>
            <ClassesTable rows={shownClasses} page={Math.max(1, Math.floor(Number(q.cpage)) || 1)} pageHref={(n) => pageHref(n, "cpage")} />
          </section>
          {/* the reading of the table and the key to its colours: put away until asked for */}
          <details className="text-[12px] text-basalt/65">
            <summary className="cursor-pointer text-basalt/55 underline underline-offset-2">Details</summary>
            <div className="mt-3 grid gap-3">
              <p className="note">
                From checked papers only, across every topic switched on. &ldquo;Needs help on&rdquo; is a skill the child is at
                &ldquo;{states.colours.red.count_words}&rdquo; on where they have one, else one they are at &ldquo;
                {states.colours.amber.count_words}&rdquo; on, with the mistake they repeat there. &ldquo;Waiting on you&rdquo; is their
                answers the reader could not settle. A parent report shows here only when it waits to be approved or is out of date.
                A column with nothing in it is left out.
              </p>
              <ColourKeyLine rules={rules} states={states} />
            </div>
          </details>
        </div>
      )}
    </PageShell>
  );
}
