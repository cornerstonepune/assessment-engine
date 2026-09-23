import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, Notice, PageHeader, Panel, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import {
  childEvidence,
  childHeader,
  childMap,
  childPapers,
  misconceptionNames,
  numSkills,
  pendingResults,
  staffList,
  type RungState,
  type Skill,
} from "@/lib/queries";
import { childSheets, repeatedMistakes, summary } from "@/lib/queries-children";
import { rag, RAG_TONE, RAG_WORDS } from "@/lib/rag";
import { confirmChild, resolveOne } from "../actions";
import { deadline } from "@/lib/deadline";
import { FocusPanel } from "./focus-panel";
import { AnswerTable, fmtDate, Lane, Legend } from "./graph";
import { RepeatedMistakes, TheirPapers } from "./panels";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };
const MACHINE = ["correct", "wrong", "blank"];

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
  const [child, map, evidence, pending, papers, names, skills, mistakes, sheets, staff] = await deadline(Promise.all([
    childHeader(id, me.email),
    childMap(id),
    childEvidence(id),
    pendingResults(id),
    childPapers(id),
    misconceptionNames(),
    numSkills(),
    repeatedMistakes(id),
    childSheets(id),
    staffList(),
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
    .filter((l) => l.rows.length && (!map.some((r) => r.last_seen) || l.rows.some((r) => r.last_seen)));
  const read = papers.filter((p) => p.n_results > 0);
  // the sentence, the tiles and the graph count the same steps: the ones the graph below shows
  const shown = lanes.flatMap((l) => l.rows.map((r) => r.state));
  const staffNames = Object.fromEntries(staff.map((x) => [x.email, x.name]));
  const count = (c: string) => shown.filter((s) => rag(s) === c).length;

  return (
    <>
      <PageHeader
        stage={`Children · ${child.section}`}
        title={child.first_name}
        sub={`Roll ${child.roll_no} · ${child.band} · ${child.n_events} confirmed answers over ${read.length} paper${read.length === 1 ? "" : "s"}.`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2">
          <Link href={`/growth/class/${encodeURIComponent(child.section)}`} className="chip">
            ← {child.section}
          </Link>
          <Link href="/growth" className="chip">
            All classes
          </Link>
        </p>
        <p data-testid="summary" className="mb-4 max-w-[760px] text-[16px] leading-snug">
          {summary(child.first_name, shown)}
        </p>
        {q.confirmed ? <Notice tone="neem">Confirmed {q.confirmed} answers. The ladder below is rebuilt from them.</Notice> : null}
        {q.paper && /^CS[0-9A-F]{6}$/.test(q.paper) ? (
          <Notice tone="neem">Approved in your name: paper {q.paper}. Print it from its page.</Notice>
        ) : null}
        {q.resolved ? <Notice tone="neem">Settled. The ladder is rebuilt.</Notice> : null}
        {q.error === "resolve" ? <Notice tone="terracotta">Pick right, wrong or blank. Nothing was changed.</Notice> : null}

        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-5">
          {(["red", "amber", "green", "grey"] as const).map((c) => (
            <Tile key={c} tone={RAG_TONE[c]} n={count(c)} words={RAG_WORDS[c]} />
          ))}
          <a href="#needs-you" className="panel flex flex-col justify-between border-l-4 border-l-basalt p-3 no-underline">
            <span className="font-heading text-[26px] leading-none text-basalt">{person.length + machine.length}</span>
            <span className="mt-2 text-[12.5px] text-terracotta">
              {[person.length && `${person.length} to settle`, machine.length && `${machine.length} to confirm`].filter(Boolean).join(" · ") || "nothing waiting"}
            </span>
          </a>
        </div>

        <div className="grid gap-[18px] xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid content-start gap-[18px]">
            <Panel id="ladder" label="Knowledge graph" title="Knowledge graph" aside="each skill's steps, from checked answers only">
                <div className="flex flex-wrap gap-x-5 gap-y-2 text-[12.5px] text-basalt/62">
                  <Legend state="secure">got it</Legend>
                  <Legend state="stretch_ready">ready to move up</Legend>
                  <Legend state="practising">practising</Legend>
                  <Legend state="patterned_error">same mistake repeating</Legend>
                  <Legend state="emerging">under half right</Legend>
                  <Legend state="not_enough_yet">not enough yet</Legend>
                </div>
                <ol aria-label="The ladder" className="mt-5">
                  {lanes.map(({ skill, rows }) => (
                    <Lane key={skill.code} skill={skill} rows={rows} answers={evidence.filter((a) => a.skill_code === skill.code)} names={names} />
                  ))}
                </ol>
                <p className="note mt-3">
                  Steps run easy to hard, left to right. Click a step to see the answers behind it. Grey: fewer than
                  three checked answers. Red: a mistake matched twice, or under half right. Amber: practising, not yet
                  four in five. Green: four in five across two papers; six answers at that rate is ready to move up.
                </p>
            </Panel>

            <RepeatedMistakes rows={mistakes} opens={new Set(evidence.map((e) => `${e.rung_code}|${e.skill_code}`))} />

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
            <FocusPanel childId={id} name={child.first_name} staff={staffNames} />

            <TheirPapers sheets={sheets} read={read} failed={papers.length - read.length} staff={staffNames} />
          </div>
        </div>
      </Body>
    </>
  );
}

