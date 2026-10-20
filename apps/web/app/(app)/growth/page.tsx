import Link from "@/components/link";
import { Body, PageHeader, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { childTable, type ChildRow } from "@/lib/queries-children";
import { grades as schoolGrades } from "@/lib/queries";
import { many } from "@/lib/needs-you";
import { deadline } from "@/lib/deadline";
import { ColourKeyLine } from "@/components/colour-key";
import { colourRules } from "@/lib/colours";
import { ChildFinder } from "./finder";
import { reportRank, reportWaits, reportWords } from "@/lib/queries-reports";
import { topics } from "@/lib/queries-people";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const helpRank = (h: ChildRow["help"]) => (!h ? 2 : h.rag === "red" ? 0 : 1);
// the query gives the roll order, and a sort is stable: "Roll" keeps it, and every other column falls back to it
const byRoll = () => 0;

// Each column, in order: its heading, how it sorts and which way, as a screen reader says it ("other" where the order is
// what needs doing first, rather than smallest or largest), and whether a phone folds it away (`wide`): there the child
// and what they need help on are what matters, and a click opens the child for the rest.
type Dir = "ascending" | "descending" | "other";
type Column = { key: string; label: string; num?: boolean; wide?: boolean; dir: Dir; by: (a: ChildRow, b: ChildRow) => number };
const COLUMNS: Column[] = [
  { key: "roll", label: "Roll", dir: "ascending", by: byRoll },
  { key: "name", label: "Child", dir: "ascending", by: (a, b) => a.first_name.localeCompare(b.first_name) },
  { key: "help", label: "Needs help on", dir: "other", by: (a, b) => helpRank(a.help) - helpRank(b.help) },
  { key: "needs", label: "Needs help", num: true, wide: true, dir: "descending", by: (a, b) => b.needs_help - a.needs_help },
  { key: "practising", label: "Practising", num: true, wide: true, dir: "descending", by: (a, b) => b.practising - a.practising },
  { key: "secure", label: "Secure", num: true, wide: true, dir: "descending", by: (a, b) => b.secure - a.secure },
  { key: "waiting", label: "Waiting on you", num: true, wide: true, dir: "descending", by: (a, b) => b.waiting - a.waiting },
  { key: "report", label: "Parent report", wide: true, dir: "other", by: (a, b) => reportRank(a.report) - reportRank(b.report) },
];
const FOLD = "max-sm:hidden";

// A parent report only when it waits on someone — to approve, or out of date (`reportWaits`); an approved report, or none
// written yet, is no one's work here.
function Report({ r }: { r: ChildRow["report"] }) {
  if (!reportWaits(r)) return null;
  const { tone, short } = reportWords(r);
  return <Pill tone={tone}>{short}</Pill>;
}

function Count({ n }: { n: number }) {
  return <span className={n ? undefined : "text-basalt/40"}>{n}</span>;
}

/** One class: its line says what waits in it; open, its children, those who need help first. */
function ClassGroup({ section, kids, open, sort, href }: {
  section: string;
  kids: ChildRow[];
  open: boolean;
  sort: Column;
  href: (sort: string) => string;
}) {
  const shown = [...kids].sort(sort.by);
  const needHelp = kids.filter((c) => c.needs_help > 0).length;
  const waiting = kids.reduce((n, c) => n + c.waiting, 0);
  const reports = kids.filter((c) => reportWaits(c.report)).length;
  // only what waits is said: a quiet class is one line, not a row of noughts
  const waits = [
    needHelp ? `${needHelp} ${needHelp === 1 ? "needs" : "need"} help` : "",
    waiting ? `${many(waiting, "answer")} waiting` : "",
    reports ? `${many(reports, "parent report")} waiting` : "",
  ].filter(Boolean);
  if (!waits.length) waits.push("nothing waiting");
  return (
    <details
      data-class={section}
      open={open}
      data-open={open ? "" : undefined}
      className="group border-t border-basalt/10 px-[18px] first:border-t-0"
    >
      <summary className="flex cursor-pointer list-none items-baseline gap-x-2 py-3 text-[13.5px] [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className="inline-block w-3 text-basalt/50 transition-transform group-open:rotate-90">
          ▸
        </span>
        <span className="font-semibold text-basalt">{section}</span>
        <span className="text-basalt/70">· {[many(kids.length, "child", "children"), ...waits].join(" · ")}</span>
      </summary>
      <p className="mb-2 text-[12.5px]">
        <Link href={`/growth/class/${encodeURIComponent(section)}`}>{section} against every skill →</Link>
      </p>
      <div className="overflow-x-auto pb-3">
        <table className="grid" aria-label={`${section}: its children`} data-children>
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={`${c.num ? "num" : ""} ${c.wide ? FOLD : ""}`}
                  aria-sort={c.key === sort.key ? c.dir : undefined}
                >
                  <Link href={href(c.key)} className={`no-underline ${c.key === sort.key ? "text-basalt" : "text-inherit"}`}>
                    {c.label}
                    {c.key === sort.key ? " ▾" : ""}
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr
                key={r.id}
                data-child={r.id}
                data-section={r.section}
                data-name={r.first_name.toLowerCase()}
                data-roll={r.roll_no}
                className="relative cursor-pointer hover:bg-basalt/3"
              >
                <td className="fact">{r.roll_no}</td>
                <td>
                  {/* the one link of the row, stretched over all of it: a click anywhere opens the child */}
                  <Link
                    href={`/growth/${r.id}`}
                    className="font-medium text-basalt no-underline after:absolute after:inset-0 after:content-['']"
                  >
                    {r.first_name}
                  </Link>
                </td>
                <td>
                  {r.help ? (
                    <span className="inline-flex items-start gap-2">
                      <span
                        aria-hidden="true"
                        className={`mt-[5px] h-[9px] w-[9px] shrink-0 rounded-full ${r.help.rag === "red" ? "bg-terracotta" : "bg-bamboo"}`}
                      />
                      <span>
                        {r.help.name}
                        {r.help.mistake ? <span className="block text-[12px] text-basalt/65">{r.help.mistake}</span> : null}
                      </span>
                    </span>
                  ) : (
                    <span className="text-basalt/45">—</span>
                  )}
                </td>
                <td className={`num ${FOLD}`}>
                  <Count n={r.needs_help} />
                </td>
                <td className={`num ${FOLD}`}>
                  <Count n={r.practising} />
                </td>
                <td className={`num ${FOLD}`}>
                  <Count n={r.secure} />
                </td>
                <td className={`num ${FOLD}`}>
                  <Count n={r.waiting} />
                </td>
                <td className={FOLD}>
                  <Report r={r.report} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

// Children (goals/ux3-children-grouped.yaml): one group per class, under its grade. An educator's own classes open; the
// coordinator's every class closed, each saying in one line what waits in it. Their standing is every taught topic's, or
// one topic's, chosen at the top (goals/ui4b2-class-by-topic.yaml). A class still opens against every skill
// (goals/u2-children.yaml).
export default async function ChildrenPage({ searchParams }: Props) {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const q = await searchParams;
  const sort = COLUMNS.find((c) => c.key === q.sort) ?? COLUMNS.find((c) => c.key === "help")!;
  const taught = (await deadline(topics(scope))).filter((t) => t.shown);
  // only a topic that is taught narrows the table; any other word is every topic
  const topic = taught.find((t) => t.code === q.topic) ?? null;
  const [rows, rules, school] = await deadline(Promise.all([childTable(me.email, topic?.code ?? null, scope), colourRules(), schoolGrades()]));
  // a class sorted stays open: the coordinator's classes open one by one, and a sort is a new page
  const opened = q.open ?? null;
  const href = (to: { sort?: string; topic?: string | null; open?: string }) => {
    const p = new URLSearchParams();
    const t = to.topic === undefined ? topic?.code : to.topic;
    if (t) p.set("topic", t);
    const s = to.sort ?? sort.key;
    if (s !== "help") p.set("sort", s);
    if (to.open && !own) p.set("open", to.open);
    return p.size ? `/growth?${p}` : "/growth";
  };
  // an educator's own classes are their work, open; every class, as the coordinator sees them, is a list to choose from
  const own = scope.classes !== null;
  // in the grades' own order (`grade`), never as text: Grade 10 after Grade 9
  const grades = school.list.map((x) => x.code).filter((b) => rows.some((r) => r.band === b));

  return (
    <>
      <PageHeader
        stage="Children"
        title="Children"
        sub={
          own
            ? "Your classes, the children who need help first: what each needs help on, what waits on you, and their parent report. Click a child to open them."
            : "Every class, grade by grade. Each line says what waits in that class; open it to see its children, the ones who need help first."
        }
      />
      <Body>
        <nav aria-label="Topic" className="mb-3 flex flex-wrap gap-2">
          <Link href={href({ topic: null })} className={`chip ${!topic ? "on" : ""}`} aria-current={!topic ? "page" : undefined}>
            All topics
          </Link>
          {taught.map((t) => (
            <Link
              key={t.code}
              href={href({ topic: t.code })}
              className={`chip ${topic?.code === t.code ? "on" : ""}`}
              aria-current={topic?.code === t.code ? "page" : undefined}
            >
              {t.name}
            </Link>
          ))}
        </nav>
        {grades.length === 0 ? <p className="note">No child is on the roll yet.</p> : <ChildFinder within="children" />}
        <div id="children" className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          {grades.map((band) => {
            const children = rows.filter((r) => r.band === band);
            const classes = [...new Set(children.map((r) => r.section))];
            return (
              <section key={band} aria-label={school.name(band)} className="panel">
                <div className="panel-head">
                  <h2 className="text-[16px]">{school.name(band)}</h2>
                  <div className="fact text-[11px] text-basalt/55">
                    {many(classes.length, "class", "classes")} · {many(children.length, "child", "children")}
                  </div>
                </div>
                {classes.map((s) => (
                  <ClassGroup
                    key={s}
                    section={s}
                    kids={children.filter((r) => r.section === s)}
                    open={own || s === opened}
                    sort={sort}
                    href={(key) => href({ sort: key, open: s })}
                  />
                ))}
              </section>
            );
          })}
          <p className="note">
            From checked papers only{topic ? `, in ${topic.name} alone` : ", across every topic switched on"}. &ldquo;Needs help on&rdquo; is
            the child&rsquo;s red skill (a dot in red) where they have one, else their amber one, with the mistake they repeat there.
            &ldquo;Waiting on you&rdquo; is their answers the reader could not settle. A parent report shows here only when it waits to be
            approved or is out of date.
          </p>
          <ColourKeyLine rules={rules} />
        </div>
      </Body>
    </>
  );
}
