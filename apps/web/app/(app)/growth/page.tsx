import Link from "@/components/link";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { childTable, type ChildRow } from "@/lib/queries-children";
import { gradeWords } from "@/lib/queries";
import { deadline } from "@/lib/deadline";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const fmtDay = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).replace(/ /g, "-");

// What needs doing first: a report out of date, then a draft, then none, then approved.
const reportRank = (r: ChildRow["report"]) => (!r ? 2 : r.out_of_date ? 0 : r.approved ? 3 : 1);
const helpRank = (h: ChildRow["help"]) => (!h ? 2 : h.rag === "red" ? 0 : 1);

// Each column, in order: its heading, and how it sorts (none: the roll order, as the class list has it).
const COLUMNS: { key: string; label: string; num?: boolean; by?: (a: ChildRow, b: ChildRow) => number }[] = [
  { key: "roll", label: "Roll" },
  { key: "name", label: "Name", by: (a, b) => a.first_name.localeCompare(b.first_name) },
  { key: "grade", label: "Grade" },
  { key: "class", label: "Class", by: (a, b) => a.section.localeCompare(b.section) },
  {
    key: "help",
    label: "Needs help on",
    by: (a, b) => helpRank(a.help) - helpRank(b.help) || (a.help?.name ?? "").localeCompare(b.help?.name ?? ""),
  },
  { key: "secure", label: "Secure", num: true, by: (a, b) => b.secure - a.secure },
  { key: "practising", label: "Practising", num: true, by: (a, b) => b.practising - a.practising },
  { key: "last", label: "Last paper read", by: (a, b) => (b.last_read ?? "").localeCompare(a.last_read ?? "") },
  { key: "report", label: "Parent report", by: (a, b) => reportRank(a.report) - reportRank(b.report) },
];

function Report({ r }: { r: ChildRow["report"] }) {
  if (!r) return <span className="text-basalt/45">—</span>;
  const [tone, words] = r.out_of_date
    ? (["terracotta", "out of date"] as const)
    : r.approved
      ? (["neem", "approved"] as const)
      : (["bamboo", "draft"] as const);
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <Pill tone={tone}>{words}</Pill>
      <span className="text-[11.5px] text-basalt/55">{fmtDay(r.written)}</span>
    </span>
  );
}

// Children (goals/u8-children-table.yaml): each grade a table of its children, one row each with their standing and
// next step; a click anywhere on a row opens the child, any heading sorts. A class still opens as its children against
// every skill (goals/u2-children.yaml).
export default async function ChildrenPage({ searchParams }: Props) {
  const me = await requireStaff();
  const { sort = "roll" } = await searchParams;
  const rows = await deadline(childTable(me.email));
  const by = COLUMNS.find((c) => c.key === sort)?.by;
  const grades = [...new Set(rows.map((r) => r.band))];

  return (
    <>
      <PageHeader
        stage="Children"
        title="Children"
        sub="Every child, grade by grade: the skill they most need help on, what is secure, and where their parent report stands. Click a child to open them; click a heading to sort."
      />
      <Body>
        {grades.length === 0 ? <p className="note">No child is on the roll yet.</p> : null}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-[18px]">
          {grades.map((band) => {
            const children = rows.filter((r) => r.band === band);
            const shown = by ? [...children].sort(by) : children;
            const classes = [...new Set(children.map((r) => r.section))];
            return (
              <Panel
                key={band}
                label={gradeWords(band)}
                title={gradeWords(band)}
                aside={`${children.length} ${children.length === 1 ? "child" : "children"}`}
              >
                <p className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px]">
                  {classes.map((s) => {
                    const n = children.filter((r) => r.section === s).length;
                    return (
                      <Link key={s} href={`/growth/class/${encodeURIComponent(s)}`}>
                        {s} · {n} {n === 1 ? "child" : "children"} against every skill →
                      </Link>
                    );
                  })}
                </p>
                <div className="overflow-x-auto">
                  <table className="grid" aria-label={`${gradeWords(band)}: every child`}>
                    <thead>
                      <tr>
                        {COLUMNS.map((c) => (
                          <th
                            key={c.key}
                            className={c.num ? "text-right" : undefined}
                            aria-sort={c.key === sort ? (c.by ? "descending" : "ascending") : undefined}
                          >
                            {c.key === "grade" ? (
                              c.label
                            ) : (
                              <Link
                                href={c.key === "roll" ? "/growth" : `/growth?sort=${c.key}`}
                                className={`no-underline ${c.key === sort ? "text-basalt" : "text-inherit"}`}
                              >
                                {c.label}
                                {c.key === sort ? " ▾" : ""}
                              </Link>
                            )}
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
                          <td>{gradeWords(r.band)}</td>
                          <td>{r.section}</td>
                          <td>
                            {r.help ? (
                              <span className="inline-flex items-center gap-2">
                                <span
                                  aria-hidden="true"
                                  className={`h-[9px] w-[9px] shrink-0 rounded-full ${r.help.rag === "red" ? "bg-terracotta" : "bg-bamboo"}`}
                                />
                                {r.help.name}
                              </span>
                            ) : (
                              <span className="text-basalt/45">—</span>
                            )}
                          </td>
                          <td className="num">{r.secure}</td>
                          <td className="num">{r.practising}</td>
                          <td className="fact whitespace-nowrap">
                            {r.last_read ? fmtDay(r.last_read) : <span className="text-basalt/45">—</span>}
                          </td>
                          <td>
                            <Report r={r.report} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            );
          })}
          <p className="note">
            From checked papers only. &ldquo;Needs help on&rdquo; is the skill with a repeating mistake or under half
            right (red dot), else the one still being practised (amber); secure counts the skills got. A parent report is
            out of date once answers were signed off after it was written.
          </p>
        </div>
      </Body>
    </>
  );
}
