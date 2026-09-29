import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Bar, Body, MarkPill, Notice, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { misconceptionNames, numSkills } from "@/lib/queries";
import { held, paperAnswers, paperHeader, sameChildPapers, type CaptureAnswer } from "@/lib/queries-read";
import { confirmPaper, correctRead, judgeRead, nameMistake } from "../actions";
import { deadline } from "@/lib/deadline";
import { EngineDown, engineGet } from "@/lib/engine";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

// What the engine did with this answer, said as a sentence rather than a state name. A teacher
// should never have to learn the word `illegible` to use this screen.
function reading(a: CaptureAnswer): string {
  if (a.human_read !== null) return `You said the child wrote ${a.human_read || "nothing"}.`;
  const reason = a.why ?? "";
  // ADR 0032: a right answer waits until the reader has earned trust on this kind of question; a
  // reading the child's own notebook doubts says why; the second reader's guess says who made it.
  if (reason.includes("until the reader is trusted"))
    return `The reader read ${a.read} and marks it right. This kind of question is not yet trusted (${reason.match(/\(([^)]*)\)$/)?.[1] ?? "not enough checks yet"}), so a person confirms it.`;
  if (reason.startsWith("this child's")) return `The reader read ${a.guess}, but ${reason}.`;
  if (a.guess && a.guess_by)
    return `The reader could not settle this (${reason}). The second reader, shown ${a.guess_by.match(/with (\d+)/)?.[1] ?? "some"} of the child's own answers, reads it as ${a.guess}.`;
  if (held(a))
    return a.answer_state === "blank"
      ? "The reader found nothing written here. Every blank is checked by a person before it counts."
      : `The reader read ${a.read}, a wrong answer. Every wrong answer is checked by a person before it counts.`;
  // No percentage. The engine only stands behind a reading it is sure enough of; printing "82% sure"
  // beside it turned every settled answer into a question for the teacher.
  if (a.answer_state === "written") return `The reader read ${a.read}.`;
  if (a.answer_state === "blank") return "The reader found nothing written here.";
  if (a.answer_state === "not_found") return "The reader could not find this question on the photograph.";
  // The reader knows WHICH of five things went wrong, and saying so turns "your problem now" into
  // a question the teacher can answer at a glance: an answer under the floor she confirms or
  // corrects, a region holding four numbers for two answers she has to split herself.
  const why = a.why ? ` (${a.why})` : "";
  return `There is writing here that the reader could not make out.${why}`;
}

// A wrong answer no named mistake explains, with Jev's shortlist and every named mistake of its operation
// (`GET /capture/{id}/mistakes`, ADR 0036). The engine down is not the page down: nothing is offered then.
type Unnamed = { answer: string; shortlist: [string, number][]; options: string[]; why: string };
async function unnamedOn(captureId: string): Promise<Record<string, Unnamed>> {
  try {
    const res = await engineGet(`/capture/${captureId}/mistakes`);
    return res.ok ? ((await res.json()) as Record<string, Unnamed>) : {};
  } catch (e) {
    if (e instanceof EngineDown) return {};
    throw e;
  }
}

// The three signals stay three (rule 5), and an answer nobody has settled is not one of them.
const settled = (a: CaptureAnswer) => ["correct", "wrong", "blank"].includes(a.status);

export default async function CaptureDetail({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const q = await searchParams;
  const [paper, answers, names, skills, siblings, unnamed] = await deadline(Promise.all([
    paperHeader(id, me.email),
    paperAnswers(id),
    misconceptionNames(),
    numSkills(),
    sameChildPapers(id),
    unnamedOn(id),
  ]));
  if (!paper) notFound();
  const at = siblings.findIndex((s) => s.id === id);
  const [prev, next] = [siblings[at - 1], siblings[at + 1]];

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
        stage={`Marking · ${paper.section}`}
        title={`${paper.first_name} · ${paper.title ?? paper.paper}`}
        sub={`Sat ${fmtDate(paper.date)}. ${answers.length} answers on ${paper.pages} page${paper.pages === 1 ? "" : "s"}. The engine read what it could and flagged the rest; nothing here reaches ${paper.first_name}'s ladder until you sign it off.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href={`/capture?child=${paper.child_id}`} className="chip">← {paper.first_name}&rsquo;s papers</Link>
          <Link href={`/growth/${paper.child_id}`} className="chip">{paper.first_name}&rsquo;s page</Link>
          {siblings.length > 1 ? (
            <span className="ml-auto flex flex-wrap items-center gap-2">
              {prev ? <Link href={`/capture/${prev.id}`} className="chip">← Previous paper</Link> : null}
              <span className="text-[13px] text-basalt/62">
                {paper.first_name}&rsquo;s paper {at + 1} of {siblings.length}
              </span>
              {next ? <Link href={`/capture/${next.id}`} className="chip">Next paper →</Link> : null}
            </span>
          ) : null}
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

            {/* What needs a person comes first, and only that. The answers the engine marked itself
                sit folded underneath, one click away: shown side by side with the doubtful ones, each
                with "it is 82% sure", every settled answer read as a question put to the teacher, and
                Nimish found himself checking dozens of answers nobody had asked him about. */}
            {pages.map((n) => {
              const here = answers.filter((a) => a.page === n);
              const yours = here.filter((a) => !settled(a) && a.state === "candidate");
              const theirs = here.filter((a) => !yours.includes(a));
              return (
                <Panel
                  key={n}
                  title={`Page ${n}`}
                  aside={yours.length ? `${yours.length} need${yours.length === 1 ? "s" : ""} you` : "nothing needs you"}
                >
                  {yours.length ? (
                    <ul className="grid gap-4">
                      {yours.map((a) => (
                        <AnswerCard key={a.id} a={a} paperId={id} names={names} unnamed={unnamed[a.id]} />
                      ))}
                    </ul>
                  ) : null}
                  {theirs.length ? (
                    <details className={yours.length ? "mt-4" : ""}>
                      <summary className="cursor-pointer text-[13.5px] text-basalt/70">
                        {theirs.length} answer{theirs.length === 1 ? "" : "s"} the engine marked itself — open to check
                      </summary>
                      <ul className="mt-3 grid gap-4">
                        {theirs.map((a) => (
                          <AnswerCard key={a.id} a={a} paperId={id} names={names} unnamed={unnamed[a.id]} />
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </Panel>
              );
            })}
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
                    <img src={`/api/scan/${first.capture_id}/${first.file_page}`} alt={`Page ${n} of the paper`} className="w-full border border-basalt/14" />
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
function AnswerCard({
  a,
  paperId,
  names,
  unnamed,
}: {
  a: CaptureAnswer;
  paperId: string;
  names: Record<string, string>;
  unnamed?: Unnamed;
}) {
  const box = a.box?.length === 4 ? `?box=${a.box.join(",")}` : "";
  const value = a.human_read ?? (a.read || a.guess) ?? ""; // a guess is offered back, filled in: one press if it is right
  // A held reading (ADR 0029) is confirmed in "What the child wrote", which keeps the engine's mark and
  // named mistake; a Right/Wrong press would record a judgement and drop both.
  const judged = a.status === "needs_teacher" && !held(a);
  return (
    <li id={`a-${a.id}`} className="grid scroll-mt-6 gap-3 border border-basalt/12 p-4 md:grid-cols-[300px_minmax(0,1fr)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/scan/${a.capture_id}/${a.file_page}${box}`}
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
        {unnamed && a.state !== "confirmed" ? <MistakePicker a={a} paperId={paperId} names={names} u={unnamed} /> : null}
        {a.state === "confirmed" ? (
          // A paper signed off by mistake is put right here: the answer is marked again and its evidence replaced by
          // a new batch in your name; the old one is kept (migration 20261015090000).
          <details className="mt-3">
            <summary className="cursor-pointer text-[12.5px] text-basalt/60">Signed off wrongly? Correct what the child wrote</summary>
            <form action={correctRead} className="mt-2 flex flex-wrap items-end gap-2">
              <input type="hidden" name="result_id" value={a.id} />
              <input type="hidden" name="paper_id" value={paperId} />
              <label className="field">
                <span className="label">What the child wrote</span>
                <input className="input w-[150px]" name="human_read" defaultValue={value} placeholder="leave empty for blank" />
              </label>
              <button className="btn secondary" type="submit">Save the correction</button>
            </form>
          </details>
        ) : (
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


// Wrong, and in a way no named mistake reproduces (goals/j2-name-the-mistake.yaml): Jev's three likeliest are one press
// each, any other named mistake is in the list, and "none of these" is an answer too. Jev only proposes.
function MistakePicker({ a, paperId, names, u }: { a: CaptureAnswer; paperId: string; names: Record<string, string>; u: Unnamed }) {
  const listed = new Set(u.shortlist.map(([c]) => c));
  const label = (c: string) => (c === "NONE" ? "None of these" : (names[c] ?? c));
  return (
    <div className="mt-3 border-l-2 border-terracotta/40 pl-3" aria-label={`Name the mistake for question ${a.slot}`}>
      <p className="text-[12.5px]">
        No named mistake makes {u.answer}. {u.shortlist.length ? "The likeliest, from Jev — you decide:" : u.why || "Which is it?"}
      </p>
      <form action={nameMistake} className="mt-2 flex flex-wrap items-center gap-2">
        <input type="hidden" name="result_id" value={a.id} />
        <input type="hidden" name="paper_id" value={paperId} />
        <input type="hidden" name="proposed" value={JSON.stringify(u.shortlist)} />
        {u.shortlist.map(([c, p]) => (
          <button key={c} className="btn secondary" name="code" value={c} type="submit">
            {label(c)} <span className="text-[11px] text-basalt/55">{Math.round(p * 100)}%</span>
          </button>
        ))}
        {listed.has("NONE") ? null : (
          <button className="btn secondary" name="code" value="NONE" type="submit">None of these</button>
        )}
      </form>
      <form action={nameMistake} className="mt-2 flex flex-wrap items-center gap-2">
        <input type="hidden" name="result_id" value={a.id} />
        <input type="hidden" name="paper_id" value={paperId} />
        <input type="hidden" name="proposed" value={JSON.stringify(u.shortlist)} />
        <select className="select" name="code" aria-label={`Another mistake for question ${a.slot}`} defaultValue="">
          <option value="" disabled>Another named mistake…</option>
          {u.options.filter((c) => !listed.has(c) && c !== "NONE").map((c) => (
            <option key={c} value={c}>{label(c)}</option>
          ))}
        </select>
        <button className="btn secondary" type="submit">Name it</button>
      </form>
    </div>
  );
}
