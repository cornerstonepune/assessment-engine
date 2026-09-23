import Link from "@/components/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Bar, Body, MarkPill, Notice, PageHeader, Panel, Pill, Tile, TONE_BG } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import {
  STATE_WORDS,
  childEvidence,
  childHeader,
  childMap,
  childPapers,
  misconceptionNames,
  numSkills,
  pendingResults,
  type Evidence,
  type RungState,
  type Skill,
} from "@/lib/queries";
import { confirmChild, resolveOne } from "../actions";
import { deadline } from "@/lib/deadline";
import { FocusPanel } from "./focus-panel";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };
const MACHINE = ["correct", "wrong", "blank"];

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

const groupBy = <T,>(rows: T[], key: (r: T) => string) =>
  rows.reduce<Record<string, T[]>>((acc, r) => ((acc[key(r)] ??= []).push(r), acc), {});

// A rung on the child's map that this skill has no confirmed answers on yet.
const unseen = (rung: RungState, skill: Skill): RungState => ({
  ...rung,
  skill_code: skill.code,
  skill_name: skill.name,
  state: null,
  n_events: 0,
  n_correct: 0,
  repeating_misconception: null,
  last_seen: null,
});

export default async function ChildPage({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const q = await searchParams;
  const [child, map, evidence, pending, papers, names, skills] = await deadline(Promise.all([
    childHeader(id, me.email),
    childMap(id),
    childEvidence(id),
    pendingResults(id),
    childPapers(id),
    misconceptionNames(),
    numSkills(),
  ]));
  if (!child) notFound();

  const machine = pending.filter((p) => MACHINE.includes(p.status));
  const person = pending.filter((p) => !MACHINE.includes(p.status));
  // One lane per skill, holding only the rungs on this child's map: the band's ladder plus any
  // rung a paper has touched. A rung shared by two skills appears in both lanes with its own state.
  const byCode = groupBy(map, (r) => r.rung_code);
  const lanes = skills
    .map((skill) => ({
      skill,
      rows: skill.rungs.filter((c) => c in byCode).map((c) => byCode[c].find((m) => m.skill_code === skill.code) ?? unseen(byCode[c][0], skill)),
    }))
    .filter((l) => l.rows.length && (!evidence.length || l.rows.some((r) => r.last_seen)));
  const read = papers.filter((p) => p.n_results > 0);
  const failed = papers.length - read.length;
  const states = map.map((r) => r.state ?? "not_enough_yet");
  const tally = {
    got: states.filter((s) => s === "secure" || s === "stretch_ready").length,
    practising: states.filter((s) => s === "practising" || s === "emerging").length,
    repeating: states.filter((s) => s === "patterned_error").length,
    unseen: states.filter((s) => s === "not_enough_yet").length,
  };

  return (
    <>
      <PageHeader
        stage={`Stage 4 · Understand · ${child.section}`}
        title={child.first_name}
        sub={`Roll ${child.roll_no} · ${child.band} · ${child.n_events} confirmed answers over ${read.length} paper${read.length === 1 ? "" : "s"}.`}
      />
      <Body>
        <p className="mb-4">
          <Link href="/growth" className="chip">
            ← All children
          </Link>
        </p>
        {q.confirmed ? <Notice tone="neem">Confirmed {q.confirmed} answers. The ladder below is rebuilt from them.</Notice> : null}
        {q.resolved ? <Notice tone="neem">Settled. The ladder is rebuilt.</Notice> : null}
        {q.error === "resolve" ? <Notice tone="terracotta">Pick right, wrong or blank. Nothing was changed.</Notice> : null}

        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-5">
          <Tile tone="neem" n={tally.got} words="got it" />
          <Tile tone="bamboo" n={tally.practising} words="practising" />
          <Tile tone="terracotta" n={tally.repeating} words="same mistake repeating" />
          <Tile tone="monsoon" n={tally.unseen} words="not seen yet" />
          <a href="#needs-you" className="panel flex flex-col justify-between border-l-4 border-l-basalt p-3 no-underline">
            <span className="font-heading text-[26px] leading-none text-basalt">{person.length + machine.length}</span>
            <span className="mt-2 text-[12.5px] text-terracotta">
              {[person.length && `${person.length} to settle`, machine.length && `${machine.length} to confirm`].filter(Boolean).join(" · ") || "nothing waiting"}
            </span>
          </a>
        </div>

        <div className="grid gap-[18px] xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid content-start gap-[18px]">
            <div id="ladder" className="scroll-mt-6">
              <Panel title="The ladder, by skill" aside="from confirmed answers only">
                <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px] text-basalt/62">
                  <Legend state="secure">got it</Legend>
                  <Legend state="stretch_ready">ready to move up</Legend>
                  <Legend state="practising">practising</Legend>
                  <Legend state="patterned_error">same mistake repeating</Legend>
                  <Legend state="not_enough_yet">not seen yet</Legend>
                </div>
                <ol aria-label="The ladder" className="mt-5">
                  {lanes.map(({ skill, rows }) => (
                    <Lane key={skill.code} skill={skill} rows={rows} answers={evidence.filter((a) => a.skill_code === skill.code)} names={names} />
                  ))}
                </ol>
                <p className="note mt-3">
                  Steps run easy to hard, left to right. Click a step to see the answers behind it. Fewer than three
                  confirmed answers is not seen yet; a mistake matched twice is a repeating mistake; under half right is
                  practising; 80 % across two papers is got it; six answers at that rate is ready to move up.
                </p>
              </Panel>
            </div>

            <div id="needs-you" className="grid gap-[18px]">
              {person.length > 0 ? (
                <Panel title="Needs you to settle" aside={`${person.length} answer${person.length === 1 ? "" : "s"} the marker could not check`}>
                  <ul className="grid gap-3">
                    {person.map((p) => (
                      <li key={p.id} className="grid gap-3 border border-basalt/12 p-4 md:grid-cols-[minmax(0,1fr)_auto]">
                        <div className="min-w-0">
                          <div className="label">
                            {fmtDate(p.date)} · question {p.item_key.split("/").pop()}
                          </div>
                          <div className="mt-1 text-[14px] leading-snug">{p.question}</div>
                          <div className="mt-2 flex flex-wrap items-baseline gap-x-2 text-[13px]">
                            <span className="label">child wrote</span>
                            {p.read ? <span className="fact text-[15px]">{p.read}</span> : <span className="text-basalt/45">nothing</span>}
                          </div>
                          {p.working ? <div className="mt-1 text-[12.5px] text-basalt/62">{p.working}</div> : null}
                          <div className="note mt-1">
                            {p.status === "needs_teacher" ? "Not a number the marker can check — read the work and decide." : "The handwriting could not be read."}
                          </div>
                        </div>
                        <form action={resolveOne} className="flex flex-wrap gap-2 self-center">
                          <input type="hidden" name="result_id" value={p.id} />
                          <input type="hidden" name="child_id" value={id} />
                          <button className="btn secondary" name="status" value="correct" type="submit">Right</button>
                          <button className="btn secondary" name="status" value="wrong" type="submit">Wrong</button>
                          <button className="btn secondary" name="status" value="blank" type="submit">Blank</button>
                        </form>
                      </li>
                    ))}
                  </ul>
                </Panel>
              ) : null}

              {machine.length > 0 ? (
                <Panel title="Marked, waiting for your confirm" aside={`${machine.length} answers`}>
                  <AnswerTable rows={machine} names={names} />
                  <form action={confirmChild} className="mt-4">
                    <input type="hidden" name="child_id" value={id} />
                    <button className="btn" type="submit">
                      Confirm these {machine.length} answers as {me.name}
                    </button>
                    <p className="note mt-2">
                      Confirming records each answer as evidence in your name and rebuilds the ladder. Evidence is never
                      edited afterwards; a correction is a new row.
                    </p>
                  </form>
                </Panel>
              ) : null}
            </div>
          </div>

          <div className="grid content-start gap-[18px] self-start xl:sticky xl:top-6">
            <FocusPanel childId={id} name={child.first_name} made={q.paper && /^CS[0-9A-F]{6}$/.test(q.paper) ? q.paper : undefined} />

            <Panel title="Papers read" aside={`${read.length}`}>
              {read.length === 0 ? (
                <p className="note">No paper has been read for this child yet.</p>
              ) : (
                <ul className="grid gap-3">
                  {read.map((p) => (
                    <li key={p.id} className="text-[13px]">
                      <div className="fact">{fmtDate(p.date)}</div>
                      <Link href={`/capture/${p.sheet}`} className="leading-snug">{p.title}</Link>
                      <div className="text-[12px] text-basalt/62">
                        {p.pages} page{p.pages === 1 ? "" : "s"} · {p.n_confirmed} of {p.n_results} answers confirmed
                      </div>
                      {p.narrative ? <p className="mt-1 text-[12.5px] italic text-basalt/75">{p.narrative}</p> : null}
                    </li>
                  ))}
                </ul>
              )}
              {failed > 0 ? <p className="note mt-3">{failed} read{failed === 1 ? "" : "s"} failed and count for nothing.</p> : null}
              <p className="note mt-3">The scans stay on the school&rsquo;s drive; what the child wrote is shown under each step.</p>
            </Panel>
          </div>
        </div>
      </Body>
    </>
  );
}

// One lane per skill, its steps left to right in ladder order. The same slot means the same thing
// in every lane, so a teacher scans positions rather than reading sentences.
function Lane({ skill, rows, answers, names }: { skill: Skill; rows: RungState[]; answers: Evidence[]; names: Record<string, string> }) {
  const seen = rows.filter((r) => r.last_seen).length;
  const repeating = rows.filter((r) => r.repeating_misconception);
  const opened = rows.filter((r) => answers.some((a) => a.rung_code === r.rung_code));
  return (
    <li className="border-t border-basalt/12 py-4 first:border-t-0 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="text-[15px]">{skill.name}</h3>
        <span className="text-[12px] text-basalt/55">
          {seen} of {rows.length} steps seen
        </span>
        {repeating.map((r) => (
          <span key={r.rung_code} className="text-[12.5px] text-terracotta md:ml-auto">
            Same mistake more than once: {names[r.repeating_misconception ?? ""] ?? r.repeating_misconception}
          </span>
        ))}
      </div>
      <ol className="mt-3 flex items-start overflow-x-auto pb-1">
        {rows.map((r, i) => {
          const state = r.state ?? "not_enough_yet";
          const n = answers.filter((a) => a.rung_code === r.rung_code).length;
          const body = (
            <>
              <span className="flex justify-center">
                <Mark state={state} />
              </span>
              <span className="fact mt-1 block text-[13px]">{r.n_events ? `${r.n_correct}/${r.n_events}` : n ? "blank" : "—"}</span>
              <span className="mt-1 flex h-[6px] justify-center">
                {r.n_events ? <Bar tone={STATE_WORDS[state].tone} share={r.n_correct / r.n_events} width={56} /> : null}
              </span>
              <span className="mt-1 line-clamp-2 text-[11px] leading-tight text-basalt/62">{r.descriptor}</span>
            </>
          );
          return (
            <li key={r.rung_code} className="flex items-start">
              {i ? <span className="mt-[13px] h-[2px] w-4 shrink-0 bg-basalt/12" aria-hidden="true" /> : null}
              {n ? (
                <a
                  href={`#ans-${r.rung_code}-${skill.code}`}
                  title={`${r.descriptor} — ${STATE_WORDS[state].words}. ${n} answer${n === 1 ? "" : "s"}.`}
                  className="block w-[108px] shrink-0 p-1 text-center text-basalt no-underline hover:bg-basalt/5"
                >
                  {body}
                </a>
              ) : (
                <span title={`${r.descriptor} — ${STATE_WORDS[state].words}`} className="block w-[108px] shrink-0 p-1 text-center">
                  {body}
                </span>
              )}
            </li>
          );
        })}
      </ol>
      {opened.map((r) => {
        const s = STATE_WORDS[r.state ?? "not_enough_yet"];
        const ans = answers.filter((a) => a.rung_code === r.rung_code);
        const blank = ans.filter((a) => a.status === "blank").length;
        return (
          <div key={r.rung_code} id={`ans-${r.rung_code}-${skill.code}`} className="mt-3 hidden scroll-mt-6 border border-basalt/12 target:block">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-basalt/12 bg-basalt/3 px-4 py-3 text-[12.5px] text-basalt/62">
              <span className="text-[14px] text-basalt">
                {skill.name} · {r.descriptor}
              </span>
              <Pill tone={s.tone}>{s.words}</Pill>
              {r.n_events ? (
                <span>
                  {r.n_correct} of {r.n_events} right
                </span>
              ) : null}
              {blank ? <span>{blank} left blank</span> : null}
              <span>last seen {fmtDate(r.last_seen)}</span>
              <a href="#ladder" className="ml-auto">
                hide
              </a>
            </div>
            <AnswerTable rows={ans} names={names} />
          </div>
        );
      })}
    </li>
  );
}

type AnswerRow = Pick<Evidence, "date" | "item_key" | "question" | "read" | "answer" | "working" | "status" | "misconception_codes"> & { id?: string };

function AnswerTable({ rows, names }: { rows: AnswerRow[]; names: Record<string, string> }) {
  return (
    <div className="overflow-x-auto">
      <table className="grid">
        <thead>
          <tr>
            <th>Date</th>
            <th>Q</th>
            <th>Question</th>
            <th className="text-right">Child wrote</th>
            <th className="text-right">Key</th>
            <th>Mark</th>
            <th>Mistake matched</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a, i) => (
            <tr key={a.id ?? i}>
              <td className="fact whitespace-nowrap">{fmtDate(a.date)}</td>
              <td className="fact">{a.item_key.split("/").pop()}</td>
              <td className="max-w-[300px] text-[13px]">
                {a.question}
                {a.working ? <div className="mt-1 text-[12px] text-basalt/55">{a.working}</div> : null}
              </td>
              <td className="num">{a.read || "—"}</td>
              <td className="num">{a.answer ?? "—"}</td>
              <td>
                <MarkPill status={a.status} working={a.working} />
              </td>
              <td className="text-[12.5px]">{a.misconception_codes.map((c) => names[c] ?? c).join("; ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// One glyph per state, in the state's material: a tick, an arrow, a dot, a bang, an empty ring.
function Mark({ state }: { state: string }) {
  const tone = STATE_WORDS[state].tone;
  if (state === "not_enough_yet") return <span className="block h-7 w-7 rounded-full border-2 border-dashed border-basalt/30" />;
  return (
    <span className={`flex h-7 w-7 items-center justify-center rounded-full text-chalk ${TONE_BG[tone]}`}>
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {state === "stretch_ready" ? <path d="M12 19V5M5 12l7-7 7 7" /> : null}
        {state === "secure" ? <path d="M5 12.5l4.5 4.5L19 7" /> : null}
        {state === "practising" || state === "emerging" ? <circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none" /> : null}
        {state === "patterned_error" ? (
          <>
            <path d="M12 6v7" />
            <circle cx="12" cy="17.5" r="1.4" fill="currentColor" stroke="none" />
          </>
        ) : null}
      </svg>
    </span>
  );
}

function Legend({ state, children }: { state: string; children: ReactNode }) {
  return (
    <span className="flex items-center gap-2">
      <span className="scale-[0.72]">
        <Mark state={state} />
      </span>
      {children}
    </span>
  );
}

