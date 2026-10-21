import Link from "@/components/link";
import { LIBRARY_CODE, sheetWords } from "../../worksheets/[qr]/library-sheet";
import { Body, NotYet, PageHeader, Panel, Pill } from "@/components/shell";
import { levels } from "@/lib/levels";
import { RULE_WORDS, tableCounts } from "@/lib/queries";
import { spareSheets, unplanned, weekPlan, weeks, type WeekRow } from "@/lib/queries-approve";
import { approvePack, overrideChild } from "./actions";
import { deadline } from "@/lib/deadline";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { weekWords } from "@/lib/week";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Class papers to approve (goals/ui3-curriculum.yaml, goals/ux5-papers-grouped.yaml): a class's week, each child by name
// with the level they are set and why and the paper they were handed, a level changed with its reason; every child of the
// class with no paper, and why; the pack approved and printed in one tap that says what it approves. It is Assessments'
// work; it sat under the worksheet library until 2026-10-11, where Today's "Class papers to approve" opened the
// Curriculum tab.
export default async function ApprovePage({ searchParams }: Props) {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const q = await searchParams;
  const all = await deadline(weeks(scope));

  if (all.length === 0) {
    const c = await deadline(tableCounts());
    return (
      <>
        <Header />
        <Body>
          <NotYet
            what={[
              "One row per child: the level they are set, and the reason it was chosen.",
              "The pack in handout order: a named paper for each child, spares, one teacher key.",
              "Change one child's level, or approve the whole pack with one tap.",
            ]}
            when="Nothing has been planned for a week yet. A coordinator runs the week from the engine, then it appears here."
            facts={[
              ["children on roll", c.child],
              ["papers made", c.sheet_instance],
              ["weeks planned", 0],
            ]}
          />
        </Body>
      </>
    );
  }

  const current = all.find((w) => w.section === q.section && w.week === q.week && w.kind === q.kind) ?? all[0];
  // the two latest weeks planned (`weeks` is newest first), and how many chips they name
  const latest = new Set([...new Set(all.map((w) => w.week))].slice(0, 2));
  const recent = all.filter((w) => latest.has(w.week)).length;
  const chip = (w: (typeof all)[number]) => (
    <Link
      key={`${w.section}-${w.week}-${w.kind}`}
      href={`/papers/approve?section=${w.section}&week=${w.week}&kind=${w.kind}`}
      className={`chip ${w === current ? "on" : ""}`}
    >
      {w.section} · {weekWords(w.week)} · {w.kind}
    </Link>
  );
  const [rows, spares, missing] = await deadline(Promise.all([
    weekPlan(current.section, current.week, current.kind, me.email),
    spareSheets(current.section, current.week, current.kind),
    unplanned(current.section, current.week, current.kind, me.email),
  ]));
  const here = `/papers/approve?section=${current.section}&week=${current.week}&kind=${current.kind}`;
  // the children handed a paper; those with none are named under them, with why
  const plan = rows.filter((r) => r.qr_code);
  const none = [
    ...rows.filter((r) => !r.qr_code).map((r) => ({ id: r.child_id, roll: r.roll_no, name: r.first_name, why: noPaper(r) })),
    ...missing.map((c) => ({
      id: c.child_id,
      roll: c.roll_no,
      name: c.first_name,
      why: c.later ? "joined the class after this week was planned" : "not on this week's plan",
    })),
  ];
  // what one tap approves: the pack's papers still waiting for a person, its spares among them
  const waiting = plan.filter((r) => r.print_status === "new").length;
  const sparesWaiting = spares.filter((s) => s.print_status === "new").length;
  const toApprove = waiting + sparesWaiting;
  const counts = plan.reduce<Record<string, number>>(
    (a, r) => ({ ...a, [r.difficulty]: (a[r.difficulty] ?? 0) + 1 }),
    {},
  );

  return (
    <>
      <Header />
      <Body>
        {q.approved ? <Notice tone="neem">Approved. The pack is marked printed.</Notice> : null}
        {q.changed ? <Notice tone="neem">Changed. That child keeps this level until you change it again.</Notice> : null}
        {q.error === "override" ? (
          <Notice tone="terracotta">A change needs a level and a reason. Nothing was changed.</Notice>
        ) : null}

        {all.length > 1 ? (
          // the latest two weeks' classes by name, the weeks before them folded (goals/ui6b-no-long-lists.yaml): one chip
          // for each class, week and kind ever planned grew by about sixteen a week
          <nav aria-label="Classes and weeks" className="mb-4 flex flex-wrap gap-2">
            {all.filter((w) => latest.has(w.week)).map(chip)}
            {all.length > recent ? (
              <details className="basis-full" open={!latest.has(current.week)}>
                <summary className="cursor-pointer text-[13px]">Earlier weeks ({all.length - recent})</summary>
                <div className="mt-2 flex flex-wrap gap-2">{all.filter((w) => !latest.has(w.week)).map(chip)}</div>
              </details>
            ) : null}
          </nav>
        ) : null}

        <Panel
          title={`${current.section} · ${weekWords(current.week)} · ${current.kind}`}
          aside={Object.entries(counts).map(([d, n]) => `${n} at ${d}`).join(" · ")}
        >
          <p className="note mb-4">
            {rows[0]?.skill_set_name
              ? `Everyone is working on ${rows[0].skill_set_name.toLowerCase()}. What changes per child is how hard their paper is.`
              : "What changes per child is how hard their paper is."}
          </p>
          <div className="overflow-x-auto">
            <table className="grid" aria-label="Each child's paper this week">
              <thead>
                <tr>
                  <th>Roll</th>
                  <th>Child</th>
                  <th>Level</th>
                  <th>Paper</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {plan.map((r) => (
                  <ChildPaper key={r.prescription_id} r={r} back={here} />
                ))}
              </tbody>
            </table>
          </div>
          {none.length ? (
            <section aria-label="No paper this week" className="mt-4 border-t border-basalt/10 pt-3">
              <h3 className="label mb-2">No paper this week</h3>
              <ul className="grid gap-1 text-[13.5px]">
                {none.map((c) => (
                  <li key={c.id}>
                    <span className="fact mr-2 text-basalt/55">{c.roll}</span>
                    <span className="font-medium">{c.name}</span>
                    <span className="text-basalt/70"> — {c.why}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </Panel>

        <div className="mt-[18px] grid gap-[18px] md:grid-cols-[1fr_300px]">
          <Panel title="Spare copies" aside={`${spares.length} unnamed`}>
            {spares.length ? (
              <>
                <p className="note mb-3">
                  Extra papers with no name on them, for a spoilt page or a child who arrives late.
                </p>
                <div className="flex flex-wrap gap-2">
                  {spares.map((s) => (
                    <Link key={s.qr_code} href={`/worksheets/${s.qr_code}`} className="chip">
                      {s.difficulty} · <span className="fact">printed code {s.qr_code}</span>
                    </Link>
                  ))}
                </div>
              </>
            ) : (
              <p className="note">No spares were made for this week.</p>
            )}
          </Panel>

          <Panel title="The pack">
            <p className="note mb-3">
              {toApprove === 0 && plan.length > 0
                ? "This pack is approved and marked printed."
                : "One tap approves the whole class. Change any child above first."}
            </p>
            <form action={approvePack}>
              <input type="hidden" name="section" value={current.section} />
              <input type="hidden" name="week" value={current.week} />
              <input type="hidden" name="kind" value={current.kind} />
              <input type="hidden" name="back" value={here} />
              <button className="btn" type="submit" disabled={toApprove === 0}>
                {toApprove === 0 ? "Nothing left to approve" : approveWords(waiting, sparesWaiting)}
              </button>
            </form>
          </Panel>
        </div>
      </Body>
    </>
  );
}

/** What one tap approves, the children's papers and the spares apart: Today counts the children's (goals/ux2). */
const approveWords = (papers: number, spares: number) =>
  `Approve ${[papers && `${papers} paper${papers === 1 ? "" : "s"}`, spares && `${spares} spare${spares === 1 ? "" : "s"}`].filter(Boolean).join(" and ")}`;

/** Why a child on the plan has no paper: the reason the week's assembly found, or that it has not run yet. */
const noPaper = (r: WeekRow) => r.no_paper ?? "the class's papers are not made yet";

/** One child's line: who, the level they are set and why, the paper they were handed, and a change of level. */
async function ChildPaper({ r, back }: { r: WeekRow; back: string }) {
  const { order } = await levels();
  return (
    <tr data-child={r.child_id}>
      <td className="fact">{r.roll_no}</td>
      <td className="font-medium">{r.first_name}</td>
      <td className="max-w-[340px] text-[12.5px]">
        <Pill tone={r.rule_fired === "override" ? "bamboo" : "monsoon"}>{r.difficulty}</Pill>
        <span className="mt-1 block text-basalt/70">
          {RULE_WORDS[r.rule_fired] ?? r.rule_fired}
          {r.override_reason ? ` ${r.override_by}: ${r.override_reason}` : ""}
        </span>
      </td>
      <td className="fact whitespace-nowrap">
        {/* the paper by what it is, its printed code only to match a page in hand (goals/ux8b-papers-named.yaml) */}
        <Link href={`/worksheets/${r.qr_code}`}>See the paper</Link>
        {/* which library worksheet it is, by its number at that level; an old paper's name is its own */}
        {r.worksheet ? (
          <>
            {" · "}
            {LIBRARY_CODE.test(r.worksheet) ? <Link href={`/worksheets/${r.worksheet}`}>{sheetWords(r.worksheet)}</Link> : r.worksheet}
          </>
        ) : null}
        <span className="block text-[11.5px] text-basalt/55">
          {r.print_status === "printed" ? "approved and printed" : "to approve"} · printed code {r.qr_code}
        </span>
      </td>
      <td>
        <details>
          <summary className="cursor-pointer whitespace-nowrap text-[12.5px] text-terracotta">Change level</summary>
          <form action={overrideChild} className="mt-2 grid w-[230px] gap-2">
            <input type="hidden" name="prescription_id" value={r.prescription_id} />
            <input type="hidden" name="back" value={back} />
            <label className="field">
              <span className="label">New level</span>
              <select className="select" name="difficulty" defaultValue={r.difficulty}>
                {order.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="label">Why</span>
              <input className="input" name="reason" maxLength={300} required />
            </label>
            <button className="btn" type="submit">
              Change this child
            </button>
          </form>
        </details>
      </td>
    </tr>
  );
}

function Header() {
  return (
    <PageHeader
      stage="Assessments · approve and print"
      title="Class papers to approve"
      sub="A class's week: each child's paper, the level it is set at and why. Change any child, then approve the pack to print it."
    />
  );
}

function Notice({ tone, children }: { tone: "neem" | "terracotta"; children: React.ReactNode }) {
  return (
    <div
      className={`mb-[18px] border p-3 text-[13.5px] ${
        tone === "neem" ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"
      }`}
      role="status"
    >
      {children}
    </div>
  );
}
