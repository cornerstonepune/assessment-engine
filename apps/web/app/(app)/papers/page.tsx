import Link from "@/components/link";
import { Body, PageHeader, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { checkQueue } from "@/lib/queries-read";
import { KIND_WORDS, paperList, STAGES, type PaperFilter, type PaperListRow, type Stage } from "@/lib/queries-papers";
import { deadline } from "@/lib/deadline";
import { ReadScan } from "../capture/read-scan";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const UUID = /^[0-9a-f-]{36}$/;
// A stage's material: what waits on a person reads warm, what is done reads settled (pills never red or green).
const STAGE_TONE: Record<Stage, "neem" | "bamboo" | "terracotta" | "monsoon"> = {
  made: "monsoon",
  printed: "monsoon",
  scanned: "terracotta",
  checked: "bamboo",
  "signed off": "neem",
};

// Where a paper's work is: its answers once it is read, the page itself before.
const opens = (p: PaperListRow) =>
  p.stage === "made" || p.stage === "printed" ? `/worksheets/${encodeURIComponent(p.qr)}` : `/capture/${p.id}`;

function query(f: PaperFilter, change: Partial<PaperFilter>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...f, ...change })) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `/papers?${s}` : "/papers";
}

function Select({ name, label, value, all, options }: {
  name: string; label: string; value?: string; all: string; options: [string, string][];
}) {
  return (
    <label className="field min-w-[11rem]">
      <span className="label">{label}</span>
      <select className="select" name={name} defaultValue={value ?? ""}>
        <option value="">{all}</option>
        {options.map(([v, words]) => <option key={v} value={v}>{words}</option>)}
      </select>
    </label>
  );
}

// Papers (goals/u9-papers.yaml): Marking and Make papers as one. Every paper in one table, filtered by class, child,
// kind, week and stage; a click anywhere on a row opens the paper where its work is. Reading a scan, the queue of
// answers to check, and making a paper start here.
export default async function PapersPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const f: PaperFilter = {
    class: q.class || undefined,
    child: q.child && UUID.test(q.child) ? q.child : undefined,
    kind: q.kind && q.kind in KIND_WORDS ? q.kind : undefined,
    week: q.week || undefined,
    stage: q.stage && (STAGES as readonly string[]).includes(q.stage) ? q.stage : undefined,
  };
  const [{ rows, more, stages, options }, queue] = await deadline(Promise.all([paperList(f, me.email), checkQueue()]));
  const toCheck = queue.filter((e) => !e.spot).length;
  const all = STAGES.reduce((n, s) => n + stages[s], 0);

  return (
    <>
      <PageHeader
        stage="Papers"
        title="Papers"
        sub="Every paper, from made to signed off. Filter them; click one to print it, or to check its answers once it is read."
      />
      <Body>
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          <Link href="/make" className="btn">
            Make a paper
          </Link>
          <Link href="/capture/check" className="btn secondary">
            {toCheck} answers to check →
          </Link>
          <Link href="/capture" className="text-[13px] md:ml-auto">
            Scans, and how the reader is doing
          </Link>
        </div>

        <nav aria-label="Papers by stage" className="mb-3 flex flex-wrap gap-2">
          <Link href={query(f, { stage: undefined })} className={`chip ${!f.stage ? "on" : ""}`}
            aria-current={!f.stage ? "page" : undefined}>
            every stage <span className="fact ml-1 opacity-70">{all}</span>
          </Link>
          {STAGES.map((s) => (
            <Link key={s} href={query(f, { stage: s })} className={`chip ${f.stage === s ? "on" : ""}`}
              aria-current={f.stage === s ? "page" : undefined}>
              {s} <span className="fact ml-1 opacity-70">{stages[s]}</span>
            </Link>
          ))}
        </nav>

        <form action="/papers" className="panel mb-[18px] flex flex-wrap items-end gap-3 p-4">
          {f.stage ? <input type="hidden" name="stage" value={f.stage} /> : null}
          <Select name="class" label="Class" value={f.class} all="Every class" options={options.classes.map((c) => [c, c])} />
          <Select name="child" label="Child" value={f.child} all="Every child" options={options.children.map((c) => [c.id, c.label])} />
          <Select name="kind" label="Kind" value={f.kind} all="Any kind" options={Object.entries(KIND_WORDS)} />
          <Select name="week" label="Week" value={f.week} all="Every week" options={options.weeks.map((w) => [w, w])} />
          <button type="submit" className="btn">Show</button>
          {f.class || f.child || f.kind || f.week || f.stage ? (
            <Link href="/papers" className="text-[13px]">Clear</Link>
          ) : null}
        </form>

        <section className="panel" aria-label="Papers">
          <div className="overflow-x-auto">
            <table className="grid" aria-label="Every paper">
              <thead>
                <tr>
                  <th>Paper</th>
                  <th>Kind</th>
                  <th>Class</th>
                  <th>Child</th>
                  <th>Week</th>
                  <th>Stage</th>
                  <th className="text-right">Waiting</th>
                  <th className="text-right">Score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} data-paper={p.id} className="relative cursor-pointer hover:bg-basalt/3">
                    <td>
                      {/* the one link of the row, stretched over all of it: a click anywhere opens the paper */}
                      <Link href={opens(p)} className="font-medium text-basalt no-underline after:absolute after:inset-0 after:content-['']">
                        {p.title}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap">{KIND_WORDS[p.kind] ?? p.kind}</td>
                    <td className="whitespace-nowrap">{p.section ?? <span className="text-basalt/45">—</span>}</td>
                    <td className="whitespace-nowrap">{p.child ?? <span className="text-basalt/45">spare copy</span>}</td>
                    <td className="fact whitespace-nowrap">{p.week ?? <span className="text-basalt/45">—</span>}</td>
                    <td>
                      <Pill tone={STAGE_TONE[p.stage]}>{p.stage}</Pill>
                    </td>
                    <td className="num">{p.waiting ? p.waiting : <span className="text-basalt/45">—</span>}</td>
                    <td className="num whitespace-nowrap">
                      {(p.stage === "checked" || p.stage === "signed off") && p.scored ? (
                        `${p.right} of ${p.scored}`
                      ) : (
                        <span className="text-basalt/45">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length === 0 ? <p className="note p-4">No paper matches these filters.</p> : null}
          {more ? <p className="note p-4">The newest 300 are shown; narrow the filters to see the rest.</p> : null}
        </section>

        <div className="mt-[18px]">
          <ReadScan from="/papers" read={q.read} why={q.why} pages={q.pages} />
        </div>
      </Body>
    </>
  );
}
