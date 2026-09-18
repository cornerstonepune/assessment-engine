import Link from "next/link";
import { Body, NotYet, PageHeader, Panel, Pill } from "@/components/shell";
import { DIFFICULTIES, RULE_WORDS, spareSheets, tableCounts, weekPlan, weeks } from "@/lib/queries";
import { approvePack, overrideChild } from "./actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function WorksheetsPage({ searchParams }: Props) {
  const q = await searchParams;
  const all = await weeks();

  if (all.length === 0) {
    const c = await tableCounts();
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
  const [plan, spares] = await Promise.all([
    weekPlan(current.section, current.week, current.kind),
    spareSheets(current.section, current.week),
  ]);
  const here = `/worksheets?section=${current.section}&week=${current.week}&kind=${current.kind}`;
  const printed = plan.filter((r) => r.print_status === "printed").length;
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
          <div className="mb-4 flex flex-wrap gap-2">
            {all.map((w) => (
              <Link
                key={`${w.section}-${w.week}-${w.kind}`}
                href={`/worksheets?section=${w.section}&week=${w.week}&kind=${w.kind}`}
                className={`chip ${w === current ? "on" : ""}`}
              >
                {w.section} · {w.week} · {w.kind}
              </Link>
            ))}
          </div>
        ) : null}

        <Panel
          title={`${current.section} · ${current.week} · ${current.kind}`}
          aside={Object.entries(counts).map(([d, n]) => `${n} at ${d}`).join(" · ")}
        >
          <p className="note mb-4">
            {plan[0]?.skill_set_name
              ? `Everyone is working on ${plan[0].skill_set_name.toLowerCase()}. What changes per child is how hard their paper is.`
              : "What changes per child is how hard their paper is."}
          </p>
          <div className="overflow-x-auto">
            <table className="grid">
              <thead>
                <tr>
                  <th>Roll</th>
                  <th>Level</th>
                  <th>Why this level</th>
                  <th>Paper</th>
                  <th className="text-right">Questions</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {plan.map((r) => (
                  <tr key={r.prescription_id}>
                    <td className="fact">{r.roll_no}</td>
                    <td>
                      <Pill tone={r.rule_fired === "override" ? "bamboo" : "monsoon"}>{r.difficulty}</Pill>
                    </td>
                    <td className="max-w-[340px] text-[12.5px]">
                      {RULE_WORDS[r.rule_fired] ?? r.rule_fired}
                      {r.override_reason ? (
                        <span className="note block">
                          {r.override_by}: {r.override_reason}
                        </span>
                      ) : null}
                    </td>
                    <td className="fact">{r.qr_code ?? <span className="text-basalt/40">not made yet</span>}</td>
                    <td className="num">{r.questions ?? 0}</td>
                    <td>
                      {r.print_status === "printed" ? (
                        <Pill tone="neem">printed</Pill>
                      ) : r.qr_code ? (
                        <Pill tone="monsoon">ready</Pill>
                      ) : (
                        <Pill tone="bamboo">waiting</Pill>
                      )}
                    </td>
                    <td>
                      <details>
                        <summary className="cursor-pointer whitespace-nowrap text-[12.5px] text-terracotta">
                          Change level
                        </summary>
                        <form action={overrideChild} className="mt-2 grid w-[230px] gap-2">
                          <input type="hidden" name="prescription_id" value={r.prescription_id} />
                          <input type="hidden" name="back" value={here} />
                          <label className="field">
                            <span className="label">New level</span>
                            <select className="select" name="difficulty" defaultValue={r.difficulty}>
                              {DIFFICULTIES.map((d) => (
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
                ))}
              </tbody>
            </table>
          </div>
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
                    <span key={s.qr_code} className="chip">
                      <span className="fact">{s.qr_code}</span> · {s.difficulty}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <p className="note">No spares were made for this week.</p>
            )}
          </Panel>

          <Panel title="The pack">
            <p className="note mb-3">
              {printed === plan.length && plan.length > 0
                ? "This pack is approved and marked printed."
                : "One tap approves the whole class. Change any child above first."}
            </p>
            <form action={approvePack}>
              <input type="hidden" name="section" value={current.section} />
              <input type="hidden" name="week" value={current.week} />
              <input type="hidden" name="kind" value={current.kind} />
              <input type="hidden" name="back" value={here} />
              <button className="btn" type="submit" disabled={plan.length === 0}>
                Approve and print
              </button>
            </form>
          </Panel>
        </div>
      </Body>
    </>
  );
}

function Header() {
  return (
    <PageHeader
      stage="Stage 2 · Print"
      title="Worksheets"
      sub="This week's paper for each child, the level it is set at, and why. Change any child, then approve the pack."
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
