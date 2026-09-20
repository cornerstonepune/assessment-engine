import Link from "next/link";
import { notFound } from "next/navigation";
import { Bar, Body, MarkPill, Notice, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { misconceptionNames, numSkills } from "@/lib/queries";
import { paperAnswers, paperHeader, type CaptureAnswer } from "@/lib/queries-read";
import { confirmPaper, correctRead, judgeRead } from "../actions";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

// What the engine did with this answer, said as a sentence rather than a state name. A teacher
// should never have to learn the word `illegible` to use this screen.
function reading(a: CaptureAnswer): string {
  if (a.human_read !== null) return `You said the child wrote ${a.human_read || "nothing"}.`;
  const sure = a.confidence ? ` It is ${Math.round(Number(a.confidence))}% sure.` : "";
  if (a.answer_state === "written") return `The reader read ${a.read}.${sure}`;
  if (a.answer_state === "blank") return "The reader found nothing written here.";
  if (a.answer_state === "not_found") return "The reader could not find this question on the photograph.";
  return "There is writing here that the reader could not make out.";
}

// The three signals stay three (rule 5), and an answer nobody has settled is not one of them.
const settled = (a: CaptureAnswer) => ["correct", "wrong", "blank"].includes(a.status);

export default async function CaptureDetail({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const q = await searchParams;
  const [paper, answers, names, skills] = await Promise.all([
    paperHeader(id, me.email),
    paperAnswers(id),
    misconceptionNames(),
    numSkills(),
  ]);
  if (!paper) notFound();

  const skillName = Object.fromEntries(skills.map((s) => [s.code, s.name]));
  const waiting = answers.filter((a) => a.state === "candidate" && !settled(a));
  const ready = answers.filter((a) => a.state === "candidate" && settled(a));
  const confirmed = answers.filter((a) => a.state === "confirmed");
  const corrected = answers.filter((a) => a.human_read !== null);
  const pages = [...new Set(answers.map((a) => a.page))].sort((x, y) => x - y);

  // One lane per skill this paper touches: what it says about the child, before anyone drills in.
  const lanes = [...new Set(answers.map((a) => a.skill_code))].map((code) => {
    const rows = answers.filter((a) => a.skill_code === code);
    const marked = rows.filter(settled);
    return {
      code,
      name: skillName[code] ?? code,
      rows,
      right: marked.filter((a) => a.status === "correct").length,
      marked: marked.length,
      open: rows.length - marked.length,
      mistakes: [...new Set(marked.flatMap((a) => a.misconception_codes))],
    };
  });

  return (
    <>
      <PageHeader
        stage={`Stage 3 · Read · ${paper.section}`}
        title={`${paper.first_name} · ${paper.title ?? paper.paper}`}
        sub={`Sat ${fmtDate(paper.date)}. ${answers.length} answers on ${paper.pages} page${paper.pages === 1 ? "" : "s"}. The engine read what it could and flagged the rest; nothing here reaches ${paper.first_name}'s ladder until you sign it off.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href="/capture" className="chip">← All papers</Link>
          <Link href={`/growth/${paper.child_id}`} className="chip">{paper.first_name}&rsquo;s ladder</Link>
        </p>

        {q.confirmed ? <Notice tone="neem">Signed off {q.confirmed} answers in your name. {paper.first_name}&rsquo;s ladder is rebuilt from them.</Notice> : null}
        {q.corrected ? <Notice tone="neem">Saved: the child wrote {q.corrected}. The engine has marked it again, and your reading is now part of what the reader is measured against.</Notice> : null}
        {q.error === "engine" ? <Notice tone="terracotta">The engine is not answering, so nothing was changed. The page images and corrections both need it running.</Notice> : null}

        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-4">
          <Tile tone="neem" n={confirmed.length} words="signed off" />
          <Tile tone="monsoon" n={ready.length} words="read and marked, waiting for your signature" />
          <Tile tone="terracotta" n={waiting.length} words="the reader could not settle" />
          <Tile tone="bamboo" n={corrected.length} words="you have corrected" />
        </div>

        <div className="grid gap-[18px] xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid min-w-0 content-start gap-[18px]">
            <Panel title="What this paper says, by skill" aside="from the answers settled so far">
              <ol className="grid gap-4">
                {lanes.map((l) => (
                  <li key={l.code} className="border-t border-basalt/12 pt-4 first:border-t-0 first:pt-0">
                    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <h3 className="text-[15px]">{l.name}</h3>
                      <span className="text-[12.5px] text-basalt/62">
                        {l.marked ? `${l.right} of ${l.marked} right` : "nothing settled yet"}
                        {l.open ? ` · ${l.open} still with you` : ""}
                      </span>
                      {l.marked ? (
                        <span className="md:ml-auto">
                          <Bar tone={l.right / l.marked >= 0.8 ? "neem" : l.right / l.marked < 0.5 ? "terracotta" : "bamboo"} share={l.right / l.marked} width={90} />
                        </span>
                      ) : null}
                    </div>
                    <ol className="mt-2 flex flex-wrap gap-[6px]">
                      {l.rows.map((a) => (
                        <li key={a.id}>
                          <a href={`#a-${a.id}`} title={`Question ${a.slot}: ${a.question}`} className="no-underline">
                            <Glyph status={settled(a) ? a.status : "waiting"} label={a.slot} />
                          </a>
                        </li>
                      ))}
                    </ol>
                    {l.mistakes.length ? (
                      <p className="mt-2 text-[12.5px] text-terracotta">
                        Mistake matched: {l.mistakes.map((c) => names[c] ?? c).join("; ")}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
              <p className="note mt-4">
                One box per answer, in the order they sit on the page. A tick is right, a cross is wrong, an open ring is
                blank, and a bang is an answer still waiting for you. Click one to go to it.
              </p>
            </Panel>

            {pages.map((n) => (
              <Panel key={n} title={`Page ${n}, answer by answer`} aside={`${answers.filter((a) => a.page === n).length} answers`}>
                <ul className="grid gap-4">
                  {answers.filter((a) => a.page === n).map((a) => (
                    <AnswerCard key={a.id} a={a} paperId={id} names={names} />
                  ))}
                </ul>
              </Panel>
            ))}
          </div>

          <div className="grid content-start gap-[18px] self-start xl:sticky xl:top-6">
            <Panel title="Sign this paper off">
              {confirmed.length === answers.length ? (
                <p className="note">Every answer on this paper is signed off.</p>
              ) : (
                <form action={confirmPaper} className="grid gap-3">
                  <input type="hidden" name="paper_id" value={id} />
                  <input type="hidden" name="child_id" value={paper.child_id} />
                  <button className="btn" type="submit" disabled={ready.length === 0}>
                    Sign off {ready.length} answer{ready.length === 1 ? "" : "s"} as {me.name}
                  </button>
                  {waiting.length ? (
                    <p className="note">
                      {waiting.length} answer{waiting.length === 1 ? " is" : "s are"} still waiting on you. Until you say
                      what is written there, {waiting.length === 1 ? "it stays" : "they stay"} off the ladder — the engine
                      never guesses a child&rsquo;s answer to fill a gap.
                    </p>
                  ) : null}
                  <p className="note">
                    Signing off records each answer as evidence in your name and rebuilds the ladder. Evidence is never
                    edited afterwards; a correction is a new row.
                  </p>
                </form>
              )}
            </Panel>

            <Panel title="The whole page">
              {pages.map((n) => {
                const first = answers.find((a) => a.page === n);
                return first ? (
                  <figure key={n} className="mb-3 last:mb-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`/api/scan/${first.capture_id}/${n}`} alt={`Page ${n} of the paper`} className="w-full border border-basalt/14" />
                    <figcaption className="note mt-1">Page {n}, as it was photographed.</figcaption>
                  </figure>
                ) : null;
              })}
              <p className="note mt-2">
                The scan stays on the school&rsquo;s disk. It is shown here, never stored in the database and never sent
                anywhere with a name on it.
              </p>
            </Panel>
          </div>
        </div>
      </Body>
    </>
  );
}

// One answer: the patch of the photograph it was read from, what the engine made of it, and the
// one thing a person is asked — what the child actually wrote.
function AnswerCard({ a, paperId, names }: { a: CaptureAnswer; paperId: string; names: Record<string, string> }) {
  const box = a.box?.length === 4 ? `?box=${a.box.join(",")}` : "";
  const value = a.human_read ?? a.read ?? "";
  const judged = a.status === "needs_teacher";
  return (
    <li id={`a-${a.id}`} className="grid scroll-mt-6 gap-3 border border-basalt/12 p-4 md:grid-cols-[300px_minmax(0,1fr)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/scan/${a.capture_id}/${a.page}${box}`}
        alt={`What the child wrote for question ${a.slot}`}
        className="max-h-[170px] w-full border border-basalt/14 bg-chalk object-contain"
      />
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <span className="label">Question {a.slot}</span>
          <MarkPill status={a.status} working={a.working_shown === "none" ? "" : a.working_shown} />
          {a.state === "confirmed" ? <Pill tone="neem">signed off</Pill> : null}
          {a.human_read !== null ? <span className="text-[12px] text-basalt/55">corrected by {a.corrected_by}</span> : null}
        </div>
        <div className="mt-1 text-[14px] leading-snug">{a.question}</div>
        <p className="mt-2 text-[13.5px]">{reading(a)}</p>
        {a.misconception_codes.length ? (
          <p className="mt-1 text-[12.5px] text-terracotta">
            The mistake this matches: {a.misconception_codes.map((c) => names[c] ?? c).join("; ")}
            <span className="fact ml-2 text-[11px] text-basalt/45">{a.misconception_codes.join(" ")}</span>
          </p>
        ) : null}
        {a.state === "confirmed" ? null : (
          <>
            <form action={correctRead} className="mt-3 flex flex-wrap items-end gap-2">
              <input type="hidden" name="result_id" value={a.id} />
              <input type="hidden" name="paper_id" value={paperId} />
              <label className="field">
                <span className="label">What the child wrote</span>
                <input className="input w-[150px]" name="human_read" defaultValue={value} placeholder="leave empty for blank" />
              </label>
              <button className="btn secondary" type="submit">Save</button>
            </form>
            {judged ? (
              <form action={judgeRead} className="mt-2 flex flex-wrap items-center gap-2">
                <input type="hidden" name="result_id" value={a.id} />
                <input type="hidden" name="paper_id" value={paperId} />
                <span className="note">The engine cannot mark this one — only you can say:</span>
                <button className="btn secondary" name="status" value="correct" type="submit">Right</button>
                <button className="btn secondary" name="status" value="wrong" type="submit">Wrong</button>
                <button className="btn secondary" name="status" value="blank" type="submit">Blank</button>
              </form>
            ) : null}
          </>
        )}
      </div>
    </li>
  );
}

// A tick, a cross, an open ring, a bang. Never colour alone: each carries its own shape and its
// question number underneath.
function Glyph({ status, label }: { status: string; label: string }) {
  const tone =
    status === "correct" ? "bg-neem" : status === "wrong" ? "bg-terracotta" : status === "blank" ? "bg-transparent" : "bg-basalt";
  const ring = status === "blank" ? "border-2 border-dashed border-basalt/40" : "";
  return (
    <span className="block w-[34px] text-center">
      <span className={`flex h-[26px] w-[26px] items-center justify-center text-chalk ${tone} ${ring}`}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden="true">
          {status === "correct" ? <path d="M5 12.5l4.5 4.5L19 7" /> : null}
          {status === "wrong" ? <path d="M6 6l12 12M18 6L6 18" /> : null}
          {status === "waiting" ? <path d="M12 7v7M12 17.4v.2" /> : null}
        </svg>
      </span>
      <span className="fact mt-[2px] block text-[10px] text-basalt/55">{label}</span>
    </span>
  );
}
