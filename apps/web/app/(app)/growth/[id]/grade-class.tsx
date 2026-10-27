// "Grade and class" on a child's page (goals/mov_move_a_child.yaml): where the child is, the two things a coordinator can
// do about it (change their grade; move them to another class), what was done, and the history. The coordinator reviews
// the change in a sentence, then confirms it; a teacher reads the same section and has no buttons. The check is on the
// server (`moveChild`), not in this page.
import Link from "@/components/link";
import { Notice, Panel } from "@/components/shell";
import type { Session } from "@/lib/auth";
import { mayUse } from "@/lib/access";
import { classChoices, HISTORY_SHOWN, moveHistory, moveSentence, refusedWords, rollIsTaken, ROLL, type MoveRow, type Place } from "@/lib/move-child";
import { grades, type ChildRow, type Grades } from "@/lib/queries";
import { dateWords } from "@/lib/week";
import { moveChild } from "./move-actions";

type Q = Record<string, string | undefined>;

const said = (p: Place) => `${p.section} roll ${p.roll}`;

function History({ rows, total, g, staff }: { rows: MoveRow[]; total: number; g: Grades; staff: Record<string, string> }) {
  if (!rows.length) return <p className="note">No change has been made here yet.</p>;
  return (
    <>
      <ul data-testid="move-history" className="grid gap-2 text-[13.5px]">
        {rows.map((m) => (
          <li key={m.id} className="border-l-4 border-l-monsoon pl-3">
            <span className="fact">{dateWords(m.day)}</span> · {staff[m.moved_by] ?? m.moved_by} ·{" "}
            {m.from_section === m.to_section && m.from_roll_no === m.to_roll_no
              ? `${g.name(m.from_band)} → ${g.name(m.to_band)} in ${m.to_section}, roll ${m.to_roll_no}`
              : `${m.from_section} roll ${m.from_roll_no} → ${m.to_section} roll ${m.to_roll_no}${m.from_band === m.to_band ? "" : `, ${g.name(m.from_band)} → ${g.name(m.to_band)}`}`}
            {m.reason ? <div className="text-[12.5px] text-basalt/62">{m.reason}</div> : null}
          </li>
        ))}
      </ul>
      {total > HISTORY_SHOWN ? <p className="note mt-2">The latest {HISTORY_SHOWN} of {total} changes.</p> : null}
    </>
  );
}

/** What the coordinator has chosen so far, read from the address and checked again here (nothing is trusted): the place
 *  the child would be in, or why not. */
async function review(child: ChildRow, q: Q, g: Grades): Promise<{ to: Place } | { asks: { section: string; roll: string; classBand: string } } | { refused: string } | null> {
  const here: Place = { band: child.band, section: child.section, roll: child.roll_no };
  if (q.act === "grade") {
    if (!g.list.some((x) => x.code === q.band) || q.band === here.band) return { refused: q.band === here.band ? "nothing_changes" : "no_such_grade" };
    return { to: { ...here, band: q.band! } };
  }
  if (q.act !== "class") return null;
  const section = (q.section ?? "").trim();
  const roll = (q.roll ?? "").trim();
  if (!ROLL.test(roll)) return { refused: "bad_roll" };
  const classes = await classChoices();
  const target = classes.find((c) => c.section === section);
  if (!target) return { refused: "no_such_class" };
  if (await rollIsTaken(section, roll, child.id)) return { refused: "roll_taken" };
  // a class may work at another grade than the child: ask which grade they work at, rather than deciding it for them
  if (!q.band && target.band && target.band !== here.band) return { asks: { section, roll, classBand: target.band } };
  const band = q.band ?? here.band;
  if (!g.list.some((x) => x.code === band)) return { refused: "no_such_grade" };
  return { to: { band, section, roll } };
}

export async function GradeClassPanel({ me, child, q, staff }: { me: Session; child: ChildRow; q: Q; staff: Record<string, string> }) {
  const g = await grades();
  const may = mayUse(me, "move_child");
  const [{ rows, total }, classes, step] = await Promise.all([moveHistory(child.id), may ? classChoices() : Promise.resolve([]), may ? review(child, q, g) : Promise.resolve(null)]);
  const here: Place = { band: child.band, section: child.section, roll: child.roll_no };
  const other = classes.filter((c) => c.section !== child.section);
  const to = { section: q.section ?? "", roll: q.roll ?? "" };
  const move = (extra: Record<string, string>) => `/growth/${child.id}?${new URLSearchParams(extra)}#grade-class`;

  return (
    <Panel id="grade-class" label="Grade and class" title="Grade and class" aside={may ? undefined : "the coordinator changes these"}>
      {q.moved ? (
        <Notice tone="neem">
          Done. {child.first_name} is in {said(here)}, working at {g.name(child.band)}. Their answers and results stay with them.
          {Number(q.withdrawn) ? ` ${q.withdrawn} plan${q.withdrawn === "1" ? "" : "s"} for coming weeks will be made again at this grade.` : ""} Papers already printed stay as they are.
        </Notice>
      ) : null}
      {q.refused ? <Notice tone="terracotta">{refusedWords(q.refused, { section: q.section ?? "", roll: q.roll ?? "" })}</Notice> : null}

      <p data-testid="where" className="mb-3 text-[14px]">
        {child.first_name} is in <b>{child.section}</b>, roll <b>{child.roll_no}</b>, and works at <b>{g.name(child.band)}</b>.
      </p>

      {!may ? (
        <p className="note mb-3">Only the coordinator changes a child&apos;s grade or class.</p>
      ) : step && "refused" in step ? (
        <Notice tone="terracotta">{refusedWords(step.refused, to)}</Notice>
      ) : step && "asks" in step ? (
        <form method="get" action={`/growth/${child.id}`} className="mb-3 grid gap-2 border border-basalt/12 p-3" data-testid="ask-grade">
          <input type="hidden" name="act" value="class" />
          <input type="hidden" name="section" value={step.asks.section} />
          <input type="hidden" name="roll" value={step.asks.roll} />
          <p className="text-[13.5px]">
            {step.asks.section} works at {g.name(step.asks.classBand)}; {child.first_name} works at {g.name(child.band)}. Which grade should {child.first_name} work at?
          </p>
          <label className="label" htmlFor="ask-band">Grade</label>
          <select id="ask-band" className="input" name="band" defaultValue={step.asks.classBand}>
            {g.list.map((x) => (
              <option key={x.code} value={x.code}>{x.name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button className="btn secondary" type="submit">Review the move</button>
            <Link href={move({})} className="btn secondary">Cancel</Link>
          </div>
        </form>
      ) : step && "to" in step ? (
        <form action={moveChild} className="mb-3 grid gap-2 border border-basalt/12 p-3" data-testid="confirm-move">
          <input type="hidden" name="child_id" value={child.id} />
          <input type="hidden" name="band" value={step.to.band} />
          <input type="hidden" name="section" value={step.to.section} />
          <input type="hidden" name="roll" value={step.to.roll} />
          <p data-testid="move-sentence" className="text-[14px]">
            {moveSentence({ name: child.first_name, from: here, to: step.to, gradeName: g.name })}
          </p>
          <label className="label" htmlFor="move-reason">Reason (optional)</label>
          <input id="move-reason" className="input" name="reason" maxLength={500} />
          <div className="flex gap-2">
            <button className="btn" type="submit">Confirm</button>
            <Link href={move({})} className="btn secondary">Cancel</Link>
          </div>
        </form>
      ) : null}

      {may && !(step && ("to" in step || "asks" in step)) ? (
        <div className="mb-3 grid gap-4 md:grid-cols-2">
          <form method="get" action={`/growth/${child.id}`} className="grid content-start gap-2" data-testid="change-grade">
            <input type="hidden" name="act" value="grade" />
            <b className="text-[13.5px]">Change grade</b>
            <p className="note">{child.first_name} stays in {child.section} and works at the grade you pick.</p>
            <label className="label" htmlFor="grade-band">Grade</label>
            <select id="grade-band" className="input" name="band" defaultValue={child.band}>
              {g.list.map((x) => (
                <option key={x.code} value={x.code}>{x.name}</option>
              ))}
            </select>
            <button className="btn secondary" type="submit">Review the change</button>
          </form>
          <form method="get" action={`/growth/${child.id}`} className="grid content-start gap-2" data-testid="move-class">
            <input type="hidden" name="act" value="class" />
            <b className="text-[13.5px]">Move to another class</b>
            <p className="note">{child.first_name} keeps every answer and result.</p>
            <label className="label" htmlFor="move-section">Class</label>
            <select id="move-section" className="input" name="section" defaultValue={q.section && other.some((c) => c.section === q.section) ? q.section : other[0]?.section}>
              {other.map((c) => (
                <option key={c.section} value={c.section}>{c.section}{c.band ? ` · ${g.name(c.band)}` : ""}</option>
              ))}
            </select>
            <label className="label" htmlFor="move-roll">Roll number in that class</label>
            <input id="move-roll" className="input" name="roll" required maxLength={8} defaultValue={q.act === "class" ? q.roll : undefined} />
            <button className="btn secondary" type="submit">Review the move</button>
          </form>
        </div>
      ) : null}

      <div className="label mb-2">Changes made here</div>
      <History rows={rows} total={total} g={g} staff={staff} />
    </Panel>
  );
}
