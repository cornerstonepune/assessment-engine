import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { NotYours } from "@/components/not-yours";
import { childSection, isMine, scopeOf } from "@/lib/scope";
import { childEvidence, childHeader, childPapers, grades, misconceptionNames, pendingResults, staffList } from "@/lib/queries";
import { childSheets, childSkills, classLatest, firstStep, repeatedMistakes, summary } from "@/lib/queries-children";
import { ColourKeyLine } from "@/components/colour-key";
import { checkHref, checkLevel, colourRules } from "@/lib/colours";
import { childStates } from "@/lib/states";
import { ChecksPanel, type Check } from "../checks";
import { confirmChild, resolveOne } from "../actions";
import { deadline } from "@/lib/deadline";
import { FocusPanel } from "./focus-panel";
import { AnswerTable, fmtDate } from "./answers";
import { RepeatedMistakes, TheirPapers } from "./panels";
import { SkillsPanel } from "./skills-panel";
import { ParentReportPanel } from "./report-panel";
import { reportOf } from "@/lib/queries-reports";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };
const MACHINE = ["correct", "wrong", "blank"];
const FIRST = 3; // a child's first check: as many skills as one paper holds (the maker's lines)

export default async function ChildPage({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  if (!isMine(scopeOf(me), await deadline(childSection(id)))) return <NotYours what="This child's class" />;
  const q = await searchParams;
  const [child, skills, evidence, pending, papers, names, mistakes, sheets, staff, rules, report, g, states] = await deadline(Promise.all([
    childHeader(id, me.email),
    childSkills(id),
    childEvidence(id),
    pendingResults(id),
    childPapers(id),
    misconceptionNames(),
    repeatedMistakes(id),
    childSheets(id),
    staffList(),
    colourRules(),
    reportOf(id),
    grades(),
    childStates(),
  ]));
  if (!child) notFound();

  const machine = pending.filter((p) => MACHINE.includes(p.status));
  const person = pending.filter((p) => !MACHINE.includes(p.status));
  const read = papers.filter((p) => p.n_results > 0);
  // the sentence, the tiles and the panel count the same skills: the ones the child's checked answers reach
  const shown = skills.filter((s) => s.n_events > 0).map((s) => s.state);
  const notYet = skills.filter((s) => s.n_events === 0).length;
  const staffNames = Object.fromEntries(staff.map((x) => [x.email, x.name]));
  // the skills the colours cannot say yet — too few answers, then none at all — each with the check that would place
  // the child (goals/u11-colours-said.yaml); one check a skill, where a rung that tests two skills gave it two lines
  // (code review, 2026-09-30)
  const unplaced = [
    ...skills.filter((s) => s.n_events > 0 && !states.of(s.state).enough),
    ...skills.filter((s) => s.n_events === 0),
  ].filter((s, i, all) => all.findIndex((x) => x.code === s.code) === i);
  const checks: Check[] = unplaced.map((s) => {
    const level = checkLevel(rules, child.band, s.levels);
    return {
      key: s.code,
      skill: s.name,
      who: s.n_events ? `${s.n_events} answer${s.n_events === 1 ? "" : "s"} so far` : "none yet",
      level,
      n: rules.checkSize,
      href: checkHref(child.section, [id], [{ skill: s.code, level, n: rules.checkSize }]),
      none: s.n_events === 0,
    };
  });
  const back = (
    <>
      <Link href={`/growth/class/${encodeURIComponent(child.section)}`} className="chip">
        ← {child.section}
      </Link>
      <Link href="/growth" className="chip">
        All classes
      </Link>
    </>
  );

  // nothing checked and nothing waiting on a person: one sentence and one action, and nothing else — a page of noughts
  // said nothing (goals/ux4-class-and-child.yaml). The first check is on what the class has answered latest, then the
  // grade's skills in order: where a child new to the class's work stands on it.
  if (!shown.length && !child.n_events && !pending.length) {
    const waits = sheets.filter((s) => s.n_results === 0);
    const latest = waits.length ? [] : await deadline(classLatest(child.section));
    const order = (code: string) => (latest.includes(code) ? latest.indexOf(code) : latest.length);
    const first = [...checks].sort((a, b) => order(a.key) - order(b.key)).slice(0, FIRST);
    const step = firstStep(child.first_name, waits, `/papers?child=${id}`, {
      skills: first.map((c) => c.skill),
      n: rules.checkSize,
      href: checkHref(child.section, [id], first.map((c) => ({ skill: c.key, level: c.level, n: c.n }))),
    });
    return (
      <>
        <PageHeader stage={`Children · ${child.section}`} title={child.first_name} sub={`Roll ${child.roll_no} · ${g.name(child.band)}`} />
        <Body>
          <nav aria-label="Back" className="mb-4 flex flex-wrap gap-2">
            {back}
          </nav>
          <p data-testid="summary" className="mb-4 max-w-[760px] text-[16px] leading-snug">
            {step.said}
          </p>
          {step.action ? (
            <Link href={step.action.href} className="btn">
              {step.action.words}
            </Link>
          ) : null}
        </Body>
      </>
    );
  }

  const waiting = person.length + machine.length;
  return (
    <>
      <PageHeader
        stage={`Children · ${child.section}`}
        title={child.first_name}
        sub={`Roll ${child.roll_no} · ${g.name(child.band)} · ${child.n_events} answers signed off over ${read.length} paper${read.length === 1 ? "" : "s"}.`}
      />
      <Body>
        <nav aria-label="Back" className="mb-4 flex flex-wrap gap-2">
          {back}
          <Link href={`/growth/${id}/report`} className="chip">
            Report card →
          </Link>
          <Link href={`/growth/${id}/parent`} className="chip">
            Parent report →
          </Link>
        </nav>
        <p data-testid="summary" className="mb-2 max-w-[760px] text-[16px] leading-snug">
          {summary(child.first_name, shown, notYet, states)}
        </p>
        {waiting ? (
          <p className="mb-4 text-[13.5px]">
            <a href="#needs-you" className="text-terracotta">
              {[person.length && `${person.length} to check`, machine.length && `${machine.length} to sign off`].filter(Boolean).join(" · ")} ↓
            </a>
          </p>
        ) : (
          <div className="mb-4" />
        )}
        {q.confirmed ? <Notice tone="neem">Signed off {q.confirmed} answers. What their answers show is rebuilt from them.</Notice> : null}
        {q.later ? <Notice tone="terracotta">The engine was not answering, so the answers the reader is now trusted on leave the queue at the next check.</Notice> : null}
        {q.paper && /^CS[0-9A-F]{6}$/.test(q.paper) ? (
          <Notice tone="neem">Approved in your name: paper {q.paper}. Print it from its page.</Notice>
        ) : null}
        {q.resolved ? <Notice tone="neem">Checked. What their answers show is rebuilt.</Notice> : null}
        {q.error === "resolve" ? <Notice tone="terracotta">Pick right, wrong or blank. Nothing was changed.</Notice> : null}

        <div className="grid gap-[18px] xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid content-start gap-[18px]">
            <SkillsPanel skills={skills} answers={evidence} names={names} states={states} />

            <ChecksPanel title={`Checks that would place ${child.first_name}`} unanswered="not assessed yet" checks={checks} />

            <ColourKeyLine rules={rules} states={states} />

            <RepeatedMistakes rows={mistakes} opens={new Set(evidence.map((e) => `${e.rung_code}|${e.skill_code}`))} />

            <div id="needs-you" className="grid gap-[18px]">
              {person.length > 0 ? (
                <Panel title="Answers to check" label="Answers to check" aside={`${person.length} answer${person.length === 1 ? "" : "s"} the marker could not check`}>
                  <ul className="grid gap-3">
                    {person.map((p) => (
                      <li key={p.id} className="grid gap-3 border border-basalt/12 p-4 md:grid-cols-[240px_minmax(0,1fr)_auto]">
                        {/* What the child wrote, as the photograph shows it: a person checks an answer by looking at it. */}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`/api/scan/${p.capture_id}/${p.file_page}${p.box?.length === 4 ? `?box=${p.box.join(",")}` : ""}`}
                          alt={`What the child wrote, page ${p.page}`}
                          className="max-h-[170px] w-full border border-basalt/14 bg-chalk object-contain"
                        />
                        <div className="min-w-0">
                          <div className="label">
                            {fmtDate(p.date)} · {p.paper} · page {p.page} · question {p.item_key.split("/").pop()}
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
                          <Link href={`/capture/${p.paper_id}#a-${p.id}`} className="mt-1 inline-block text-[12.5px]">
                            Open the whole paper
                          </Link>
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
                <Panel title="Marked, waiting to be signed off" label="Answers to sign off" aside={`${machine.length} answers`}>
                  <AnswerTable rows={machine} names={names} />
                  <form action={confirmChild} className="mt-4">
                    <input type="hidden" name="child_id" value={id} />
                    <button className="btn" type="submit">
                      Sign off {machine.length} {machine.length === 1 ? "answer" : "answers"} as {me.name}
                    </button>
                    <p className="note mt-2">
                      Signing off records each answer as evidence in your name and rebuilds the ladder. Evidence is never
                      edited afterwards; a correction is a new row.
                    </p>
                  </form>
                </Panel>
              ) : null}
            </div>
          </div>

          <div className="grid content-start gap-[18px] self-start xl:sticky xl:top-6">
            <FocusPanel childId={id} name={child.first_name} staff={staffNames} />

            <TheirPapers childId={id} sheets={sheets} read={read} failed={papers.length - read.length} staff={staffNames} />

            <ParentReportPanel childId={id} report={report} approver={report.note?.approved_by ? (staffNames[report.note.approved_by] ?? report.note.approved_by) : null} />
          </div>
        </div>
      </Body>
    </>
  );
}

