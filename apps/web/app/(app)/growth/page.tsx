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
import { childStates } from "@/lib/states";
import { reportRank, reportWaits, reportWords } from "@/lib/queries-reports";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const helpRank = (h: ChildRow["help"]) => (!h ? 2 : h.rag === "red" ? 0 : 1);
// the query gives the roll order, and a sort is stable: "Roll" keeps it, and every other column falls back to it
const byRoll = () => 0;

// Each column, in order: its heading, how it sorts and which way, as a screen reader says it ("other" where the order is
// what needs doing first, rather than smallest or largest), whether a phone folds it away (`wide`): there the child
// and what they need help on are what matters, and a click opens the child for the rest; and when a child has anything
// to put in it (`has`): a column of noughts and dashes is not shown (goals/ux10-declutter.yaml).
type Dir = "ascending" | "descending" | "other";
type Column = {
  key: string;
  label: string;
  num?: boolean;
  wide?: boolean;
  dir: Dir;
  by: (a: ChildRow, b: ChildRow) => number;
  has: (c: ChildRow) => boolean;
};
const COLUMNS: Column[] = [
  { key: "roll", label: "Roll", dir: "ascending", by: byRoll, has: () => true },
  { key: "name", label: "Child", dir: "ascending", by: (a, b) => a.first_name.localeCompare(b.first_name), has: () => true },
  { key: "help", label: "Needs help on", dir: "other", by: (a, b) => helpRank(a.help) - helpRank(b.help), has: (c) => !!c.help },
  { key: "needs", label: "Needs help", num: true, wide: true, dir: "descending", by: (a, b) => b.needs_help - a.needs_help, has: (c) => c.needs_help > 0 },
  { key: "amber", label: "Practising", num: true, wide: true, dir: "descending", by: (a, b) => b.amber - a.amber, has: (c) => c.amber > 0 },
  { key: "green", label: "Secure", num: true, wide: true, dir: "descending", by: (a, b) => b.green - a.green, has: (c) => c.green > 0 },
  { key: "waiting", label: "Waiting on you", num: true, wide: true, dir: "descending", by: (a, b) => b.waiting - a.waiting, has: (c) => c.waiting > 0 },
  { key: "report", label: "Parent report", wide: true, dir: "other", by: (a, b) => reportRank(a.report) - reportRank(b.report), has: (c) => reportWaits(c.report) },
];
const FOLD = "max-sm:hidden";

// A parent report only when it waits on someone — to approve, or out of date (`reportWaits`); an approved report, or none
// written yet, is no one's work here.
function Report({ r }: { r: ChildRow["report"] }) {
  if (!reportWaits(r)) return null;
  const { tone, short } = reportWords(r);
  return <Pill tone={tone}>{short}</Pill>;
}

// a number only where someone must act on it: a nought is left blank
function Count({ n }: { n: number }) {
  return n ? <span>{n}</span> : null;
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
  const columns = COLUMNS.filter((c) => kids.some(c.has));
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
      <div className="overflow-x-auto pb-1">
        <table className="grid" aria-label={`${section}: its children`} data-children>
          <thead>
            <tr>
              {columns.map((c) => (
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
                {columns.map((c) => {
                  if (c.key === "roll") return <td key={c.key} className="fact">{r.roll_no}</td>;
                  if (c.key === "name") {
                    return (
                      <td key={c.key}>
                        {/* the one link of the row, stretched over all of it: a click anywhere opens the child */}
                        <Link href={`/growth/${r.id}`} className="font-medium after:absolute after:inset-0 after:content-['']">
                          {r.first_name}
                        </Link>
                      </td>
                    );
                  }
                  if (c.key === "help") {
                    return (
                      <td key={c.key}>
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
                        ) : null}
                      </td>
                    );
                  }
                  if (c.key === "report") {
                    return (
                      <td key={c.key} className={FOLD}>
                        <Report r={r.report} />
                      </td>
                    );
                  }
                  const n = { needs: r.needs_help, amber: r.amber, green: r.green, waiting: r.waiting }[c.key] ?? 0;
                  return (
                    <td key={c.key} className={`num ${FOLD}`}>
                      <Count n={n} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="pb-3 text-[12px] text-basalt/55">
        <Link href={`/growth/class/${encodeURIComponent(section)}`} className="text-basalt/55">
          {section} against every skill →
        </Link>
      </p>
    </details>
  );
}

// The children who need the educator, as a short list that leads the page: help first (red before waiting answers), then
// whoever has answers waiting. A child with nothing for the educator to do is not on it (goals/ux10-declutter.yaml).
const LEAD = 8;
function NeedYou({ rows }: { rows: ChildRow[] }) {
  const need = rows
    .filter((c) => c.needs_help > 0 || c.waiting > 0)
    .sort((a, b) => Number(b.needs_help > 0) - Number(a.needs_help > 0) || b.waiting - a.waiting || a.first_name.localeCompare(b.first_name));
  return (
    <section aria-label="Children who need you" className="panel">
      <div className="panel-head">
        <h2 className="text-[16px]">Children who need you</h2>
      </div>
      {need.length ? (
        <ul className="panel-body grid gap-2 text-[13.5px]">
          {need.slice(0, LEAD).map((c) => (
            <li key={c.id} className="flex flex-wrap items-baseline gap-x-2">
              <Link href={`/growth/${c.id}`} className="font-medium">
                {c.first_name}
              </Link>
              <span className="text-basalt/60">{c.section}</span>
              <span className="text-basalt/80">
                {[c.needs_help > 0 && c.help ? `needs help on ${c.help.name}` : "", c.waiting ? `${many(c.waiting, "answer")} waiting` : ""]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
          ))}
          {need.length > LEAD ? <li className="text-basalt/60">and {need.length - LEAD} more, in their classes below</li> : null}
        </ul>
      ) : (
        <p className="note panel-body">Nobody needs you right now.</p>
      )}
    </section>
  );
}

// Children (goals/ux3-children-grouped.yaml, ux10-declutter.yaml): the children who need the educator first, then one
// group per class, under its grade. An educator's own classes open; the coordinator's every class closed, each saying in
// one line what waits in it. A class's table shows only the columns with something in them; a class still opens against
// every skill (goals/u2-children.yaml). Finding a child is the bar at the top's (goals/s1-subject-class-and-today.yaml).
export default async function ChildrenPage({ searchParams }: Props) {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const q = await searchParams;
  const sort = COLUMNS.find((c) => c.key === q.sort) ?? COLUMNS.find((c) => c.key === "help")!;
  const [rows, rules, school, states] = await deadline(Promise.all([childTable(me.email, null, scope), colourRules(), schoolGrades(), childStates()]));
  // a class sorted stays open: the coordinator's classes open one by one, and a sort is a new page
  const opened = q.open ?? null;
  const href = (to: { sort?: string; open?: string }) => {
    const p = new URLSearchParams();
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
        stage="Class results"
        title="Class results"
        sub={own ? "Your classes. The children who need you come first." : "Every class, grade by grade. The children who need you come first."}
      />
      <Body>
        {grades.length === 0 ? (
          <p className="note">No child is on the roll yet.</p>
        ) : (
          <div id="children" className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
            <NeedYou rows={rows} />
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
            {/* the reading of the table and the key to its colours: put away until asked for */}
            <details className="text-[12px] text-basalt/65">
              <summary className="cursor-pointer text-basalt/55 underline underline-offset-2">Details</summary>
              <div className="mt-3 grid gap-3">
                <p className="note">
                  From checked papers only, across every topic switched on. &ldquo;Needs help on&rdquo; is a skill the child is at
                  &ldquo;{states.colours.red.count_words}&rdquo; on where they have one, else one they are at &ldquo;
                  {states.colours.amber.count_words}&rdquo; on, with the mistake they repeat there; its dot is that colour.
                  &ldquo;Waiting on you&rdquo; is their answers the reader could not settle. A parent report shows here only when it waits
                  to be approved or is out of date. A column with nothing in it for a class is left out.
                </p>
                <ColourKeyLine rules={rules} states={states} />
              </div>
            </details>
          </div>
        )}
      </Body>
    </>
  );
}
