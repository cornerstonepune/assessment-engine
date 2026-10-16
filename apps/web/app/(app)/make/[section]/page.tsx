import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { NotYours } from "@/components/not-yours";
import { isMine, scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { staffList } from "@/lib/queries";
import { seeHref } from "@/lib/next-paper";
import { classHome, type ClassChild } from "@/lib/queries-make";
import { classPacksWaiting } from "@/lib/queries-today";
import { isoWeek } from "@/lib/week";
import { approveHome } from "../actions";

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | undefined>> };

// One class's home papers for the week (goals/ux5b-make-and-marking.yaml): each child still waiting is one line — the
// one skill the engine proposes, why, and one next step: approve it, or choose one where the engine has nothing to go on.
// The paper is seen from what it works on; the children already approved fold under one line.
export default async function ClassHomePapers({ params, searchParams }: Props) {
  const me = await requireStaff();
  const [{ section: raw }, q] = await Promise.all([params, searchParams]);
  const section = decodeURIComponent(raw);
  const scope = scopeOf(me);
  if (!isMine(scope, section)) return <NotYours what={section} />;
  const week = isoWeek();
  const [children, staff, packs] = await deadline(Promise.all([classHome(section, me.email, week), staffList(), classPacksWaiting(scope)]));
  const name = Object.fromEntries(staff.map((s) => [s.email, s.name]));
  const waiting = children.filter((c) => !c.proposal.approved);
  const approved = children.flatMap((c) => (c.proposal.approved ? [{ ...c, done: c.proposal.approved }] : []));
  const proposed = waiting.filter((c) => c.proposal.areas.length);
  // how many questions a paper holds is said once when every paper holds the same
  const lengths = new Set(proposed.map((c) => c.proposal.areas[0].questions.length));
  const each = lengths.size === 1 ? [...lengths][0] : null;
  const custom = (c: ClassChild) => `/make/custom?child=${c.id}`;

  return (
    <>
      <PageHeader
        stage="Assessments · make"
        title={`${section} · home assessments`}
        sub={`Week ${week}. Each child's home assessment works on one skill from their own map. Approve them, or choose a different one for any child.`}
      />
      <Body>
        {q.approved ? <Notice tone="neem">Approved {q.approved}, in your name. They print as each child&rsquo;s home assessment.</Notice> : null}
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          {scope.classes?.length === 1 ? null : (
            <Link href="/make" className="chip">
              ← Every class
            </Link>
          )}
          <Link href={`/make/${encodeURIComponent(section)}/week`} className="chip">
            This week&rsquo;s declaration
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
        {packs
          .filter((p) => p.section === section)
          .map((p) => (
            <p key={`${p.week}|${p.kind}`} className="mb-3 text-[13.5px]">
              Class papers waiting for you:{" "}
              <Link href={`/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`}>
                {p.week} · {p.kind === "assessment" ? "class assessment" : "class practice"} — {p.n} papers
              </Link>
            </p>
          ))}
        <Panel title="Each child's home assessment" aside={`${proposed.length} waiting for you${each ? ` · ${each} questions each` : ""}`}>
          {waiting.length ? (
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Each child's home assessment">
                <thead>
                  <tr>
                    <th>Roll</th>
                    <th>Child</th>
                    <th>Works on</th>
                    {/* on a phone the why folds away: what a child works on and the next step stay on screen */}
                    <th className="max-sm:hidden">Why</th>
                    <th>Next step</th>
                  </tr>
                </thead>
                <tbody>
                  {waiting.map((c) => {
                    const a = c.proposal.areas[0];
                    return (
                      <tr key={c.id}>
                        <td className="fact">{c.roll_no}</td>
                        <td>
                          <Link href={`/growth/${c.id}`}>{c.first_name}</Link>
                        </td>
                        <td className="sm:min-w-[9rem]">
                          {a ? (
                            <a href={seeHref(c.id, week)} target="_blank" rel="noreferrer">
                              {a.name} · {a.level}
                              {each ? null : ` · ${a.questions.length} questions`}
                            </a>
                          ) : (
                            <span className="text-basalt/62">Not enough checked work yet</span>
                          )}
                        </td>
                        <td className="text-[12.5px] max-sm:hidden sm:min-w-[24rem]">{a?.why}</td>
                        <td className="sm:whitespace-nowrap">
                          {a ? (
                            <>
                              <form action={approveHome}>
                                <input type="hidden" name="week" value={week} />
                                <input type="hidden" name="section" value={section} />
                                <input type="hidden" name="child_id" value={c.id} />
                                <button className="cursor-pointer font-semibold text-terracotta underline-offset-2 hover:underline" type="submit">
                                  Approve
                                </button>
                              </form>
                              <Link href={custom(c)} className="mt-1 block text-[12.5px]">
                                or choose another
                              </Link>
                            </>
                          ) : (
                            <Link href={custom(c)}>Choose one</Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="note">Every child&rsquo;s home assessment this week is approved.</p>
          )}
          {approved.length ? (
            <details data-approved="" open={!waiting.length} className="mt-4">
              <summary className="cursor-pointer text-[13.5px]">{approved.length} approved this week</summary>
              <table className="grid mt-2" aria-label="Approved this week">
                <tbody>
                  {approved.map((c) => (
                    <tr key={c.id}>
                      <td className="fact">{c.roll_no}</td>
                      <td>
                        <Link href={`/growth/${c.id}`}>{c.first_name}</Link>
                      </td>
                      <td>
                        <Pill tone="neem">Approved by {name[c.done.approved_by] ?? c.done.approved_by}</Pill>
                      </td>
                      <td>
                        <Link href={`/worksheets/${c.done.qr}`} className="fact">
                          {c.done.qr}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          ) : null}
        </Panel>
      </Body>
    </>
  );
}
