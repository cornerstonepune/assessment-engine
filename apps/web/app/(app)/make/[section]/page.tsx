import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { NotYours } from "@/components/not-yours";
import { isMine, reachOf, scopeOf } from "@/lib/scope";
import { deadline } from "@/lib/deadline";
import { staffList } from "@/lib/queries";
import { readDraw, seeHref } from "@/lib/next-paper";
import { CHANGED, Questions } from "@/components/questions";
import { classHome, type ClassChild } from "@/lib/queries-make";
import { classPacksWaiting } from "@/lib/queries-today";
import { isoWeek, weekWords } from "@/lib/week";
import { approveHome } from "../actions";

type Props = { params: Promise<{ section: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> };

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

// One class's home papers for the week (goals/ux5b-make-and-marking.yaml): each child still waiting is one line — the
// one skill the engine proposes, why, and one next step: approve it, or choose one where the engine has nothing to go on.
// Each paper's questions are on the line before anything prints, and "Different questions" draws others for that child
// alone, making nothing (goals/preview-before-print.yaml); approving prints the questions shown. The address carries
// each child's draw as `draw=<child>~<n>`. The children already approved fold under one line.
export default async function ClassHomePapers({ params, searchParams }: Props) {
  const me = await requireStaff();
  const [{ section: raw }, q] = await Promise.all([params, searchParams]);
  const section = decodeURIComponent(raw);
  const scope = scopeOf(me);
  if (!isMine(reachOf(me), section)) return <NotYours what={section} />;
  const week = isoWeek();
  const draws: Record<string, number> = {};
  for (const d of [q.draw ?? []].flat()) {
    const [child, n] = d.split("~");
    if (child && readDraw(n)) draws[child] = readDraw(n);
  }
  // "Different questions" for one child: every other child keeps the questions on screen
  const differentFor = (id: string) => {
    const next = new URLSearchParams();
    for (const [c, n] of Object.entries({ ...draws, [id]: (draws[id] ?? 0) + 1 })) next.append("draw", `${c}~${n}`);
    return `/make/${encodeURIComponent(section)}?${next}`;
  };
  const [children, staff, packs] = await deadline(Promise.all([classHome(section, me.email, week, draws), staffList(), classPacksWaiting(scope)]));
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
        sub={`This week, ${weekWords(week)}. Each child's home assessment works on one skill from their own map; its questions are on its line before anything prints. Approve them, ask for different questions, or choose a different one for any child.`}
      />
      <Body>
        {one(q.approved) ? <Notice tone="neem">Approved {one(q.approved)}, in your name. They print as each child&rsquo;s home assessment.</Notice> : null}
        {one(q.changed) ? (
          <Notice tone="terracotta">
            {one(q.changed)} not printed. {CHANGED}
          </Notice>
        ) : null}
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          {scope.classes?.length === 1 ? null : (
            <Link href="/make" className="chip">
              ← Every class
            </Link>
          )}
          <Link href={`/make/${encodeURIComponent(section)}/week`} className="chip">
            What the class did this week
          </Link>
          {proposed.length ? (
            <form action={approveHome}>
              <input type="hidden" name="week" value={week} />
              <input type="hidden" name="section" value={section} />
              {proposed.map((c) => (
                <span key={c.id} hidden>
                  <input type="hidden" name="child_id" value={c.id} />
                  <input type="hidden" name="draw" value={draws[c.id] ?? 0} />
                  <input type="hidden" name="seen" value={c.proposal.seen} />
                </span>
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
                {weekWords(p.week)} · {p.kind === "assessment" ? "class assessment" : "class practice"} — {p.n} papers
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
                    {/* on a phone the why moves under what the child works on: it is what an educator approves on
                        (goals/ux8d-phone-and-one-action.yaml) */}
                    <th className="max-sm:hidden">Why</th>
                    <th>Next step</th>
                  </tr>
                </thead>
                <tbody>
                  {waiting.map((c) => {
                    const a = c.proposal.areas[0];
                    return (
                      <tr key={c.id} data-child={c.id}>
                        <td className="fact">{c.roll_no}</td>
                        <td>
                          <Link href={`/growth/${c.id}`}>{c.first_name}</Link>
                        </td>
                        <td className="sm:min-w-[9rem]">
                          {a ? (
                            <>
                              <a href={seeHref(c.id, week, [], draws[c.id] ?? 0)} target="_blank" rel="noreferrer">
                                {a.name} · {a.level}
                                {each ? null : ` · ${a.questions.length} questions`}
                              </a>
                              {a.why ? <span className="mt-1 line-clamp-2 block text-[12px] text-basalt/70 sm:hidden">{a.why}</span> : null}
                              <details className="mt-1">
                                <summary className="cursor-pointer text-[13px]">Its questions</summary>
                                <Questions name={a.name} level={a.level} questions={a.questions} />
                              </details>
                            </>
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
                                <input type="hidden" name="draw" value={draws[c.id] ?? 0} />
                                <input type="hidden" name="seen" value={c.proposal.seen} />
                                <button className="cursor-pointer font-semibold text-terracotta underline-offset-2 hover:underline" type="submit">
                                  Approve
                                </button>
                              </form>
                              <Link href={differentFor(c.id)} className="mt-1 block text-[12.5px]">
                                Different questions
                              </Link>
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
                        {c.done.replaced.length ? <span className="note"> · replaces {c.done.replaced.join(", ")}</span> : null}
                      </td>
                      <td>
                        {/* made again as often as an educator likes: the newest is the week's (goals/home-assessment-remake.yaml) */}
                        <Link href={`/growth/${c.id}`}>Make a new one</Link>
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
