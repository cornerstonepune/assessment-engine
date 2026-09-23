import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { staffList } from "@/lib/queries";
import { classHome } from "@/lib/queries-make";
import { isoWeek } from "@/lib/week";
import { approveHome } from "../actions";

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | undefined>> };

// One class's home papers for the week: for each child, the one skill the engine proposes and why, or the paper
// already approved; approve one child or every proposal at once, or choose a different paper for a child.
export default async function ClassHomePapers({ params, searchParams }: Props) {
  const me = await requireStaff();
  const [{ section: raw }, q] = await Promise.all([params, searchParams]);
  const section = decodeURIComponent(raw);
  const week = isoWeek();
  const [children, staff] = await deadline(Promise.all([classHome(section, me.email, week), staffList()]));
  const name = Object.fromEntries(staff.map((s) => [s.email, s.name]));
  const proposed = children.filter((c) => !c.proposal.approved && c.proposal.areas.length);

  return (
    <>
      <PageHeader
        stage="Make papers"
        title={`${section} · home papers`}
        sub={`Week ${week}. Each child's home paper works on one skill from their own map. Approve them, or choose a different paper for any child.`}
      />
      <Body>
        {q.approved ? <Notice tone="neem">Approved {q.approved}, in your name. They print as each child&rsquo;s own paper.</Notice> : null}
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          <Link href="/make" className="chip">
            ← Every class
          </Link>
          {proposed.length ? (
            <form action={approveHome}>
              <input type="hidden" name="week" value={week} />
              <input type="hidden" name="section" value={section} />
              {proposed.map((c) => (
                <input key={c.id} type="hidden" name="child_id" value={c.id} />
              ))}
              <button className="btn" type="submit">
                Approve all {proposed.length}
              </button>
            </form>
          ) : null}
        </div>
        <Panel title="Each child's home paper" aside={`${proposed.length} waiting for you`}>
          <div className="overflow-x-auto">
            <table className="grid" aria-label="Each child's home paper">
              <thead>
                <tr>
                  <th>Roll</th>
                  <th>Child</th>
                  <th>Works on</th>
                  <th>Why</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {children.map((c) => {
                  const a = c.proposal.areas[0];
                  const done = c.proposal.approved;
                  return (
                    <tr key={c.id}>
                      <td className="fact">{c.roll_no}</td>
                      <td>
                        <Link href={`/growth/${c.id}`}>{c.first_name}</Link>
                      </td>
                      <td className="whitespace-nowrap">
                        {done ? (
                          <>
                            <Pill tone="neem">Approved by {name[done.approved_by] ?? done.approved_by}</Pill>{" "}
                            <Link href={`/worksheets/${done.qr}`} className="fact">
                              {done.qr}
                            </Link>
                          </>
                        ) : a ? (
                          `${a.name} · ${a.level} · ${a.questions.length} questions`
                        ) : (
                          <span className="text-basalt/62">Not enough checked work yet</span>
                        )}
                      </td>
                      <td className="max-w-[320px] text-[12.5px]">{!done && a ? a.why : null}</td>
                      <td className="whitespace-nowrap">
                        {!done && a ? (
                          <form action={approveHome} className="mr-3 inline">
                            <input type="hidden" name="week" value={week} />
                            <input type="hidden" name="section" value={section} />
                            <input type="hidden" name="child_id" value={c.id} />
                            <button className="cursor-pointer text-terracotta underline-offset-2 hover:underline" type="submit">
                              Approve
                            </button>
                          </form>
                        ) : null}
                        <Link href={`/make/custom?child=${c.id}`}>Choose a paper</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      </Body>
    </>
  );
}
