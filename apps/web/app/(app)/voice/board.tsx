"use client";

import { useMemo, useState, useTransition } from "react";
import { StatusChip } from "@/components/status-chip";
import { ICON_SIZE, Icon, MARK_ICON } from "@/lib/icons";
import { activityWords, countLine, findActivities, listsOf, moveTo, paint, problemsOf, type Activity, type Draft, type Problem, type Work } from "@/lib/voice-check";
import { MARKS, type MarkKey, W } from "@/lib/voice-words";

// The K2 board (task M1-04): pick a mark, then tap the children; the activity by its number; the level; the day; "the
// rest did as expected" a single toggle that starts as she left it (off on the form). The red problems are pinned on
// top, each with its fix, and the one button stays off while one remains. A child is a square cell with its Sr. No. and
// its mark's icon; nothing is ticked for her, and a child not named is never red. Not a table (docs/ux-rules.md, rule 3).

export type Sent = { activity: string; level: number; day: string; rest: boolean; lists: Record<MarkKey, string[]> };

const MARK_TONE: Record<MarkKey | "as_expected", string> = {
  above: "border-neem bg-neem/15 text-neem",
  below: "border-bamboo bg-bamboo/25 text-mud",
  not_willing: "border-monsoon bg-monsoon/15 text-monsoon",
  absent: "border-monsoon border-dashed bg-chalk text-monsoon",
  as_expected: "border-neem/40 bg-neem/6 text-neem",
};

export function Board({
  start,
  enrolled,
  klass,
  activities,
  today,
  draft,
  button,
  send,
}: {
  start: Work;
  enrolled: string[];
  klass: string;
  activities: Activity[];
  today: string;
  draft?: Draft;
  button: string;
  send: (s: Sent) => Promise<{ error: string } | void>;
}) {
  const [w, setW] = useState<Work>(start);
  const [mark, setMark] = useState<MarkKey | "clear">("above");
  const [fixing, setFixing] = useState<string | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const [pending, go] = useTransition();
  const problems = useMemo(() => problemsOf(w, { enrolled, klass, activities, today, draft }), [w, enrolled, klass, activities, today, draft]);
  const tap = (roll: string) => {
    if (fixing) {
      setW(moveTo(w, fixing, roll));
      setFixing(null);
    } else setW(paint(w, roll, mark));
  };
  const submit = () =>
    go(async () => {
      setSaid(null);
      const out = await send({ activity: w.activity!, level: w.level!, day: w.day, rest: w.rest, lists: listsOf(w) });
      if (out?.error) setSaid(out.error);
    });
  return (
    <div className="grid gap-4" data-board>
      {problems.length ? (
        <ol className="grid gap-2" aria-label="Problems" data-problems={problems.length}>
          {problems.map((p) => (
            <ProblemRow key={p.key} p={p} w={w} setW={setW} fixing={fixing} setFixing={setFixing} />
          ))}
        </ol>
      ) : null}
      <section className="panel grid gap-3 p-4" aria-label="The activity">
        <ActivityPicker w={w} setW={setW} activities={activities} />
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div className="flex items-center gap-2" role="group" aria-label={W.level.label}>
            <span className="text-[13px] text-basalt/70">{W.level.label}</span>
            {W.level.values.map((n) => (
              <button key={n} type="button" aria-pressed={w.level === n} onClick={() => setW({ ...w, level: n })} className={`chip min-w-11 justify-center ${w.level === n ? "on" : ""}`}>
                {n}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-[13px] text-basalt/70">
            {W.day.label}
            <input type="date" className="input !w-auto" value={w.day} max={today} onChange={(e) => setW({ ...w, day: e.target.value, dayPicked: true })} />
          </label>
        </div>
      </section>
      <section className="panel grid gap-3 p-4" aria-label={W.confirm.children}>
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label={W.pick}>
          {([...MARKS, "clear"] as const).map((m) => (
            <button key={m} type="button" aria-pressed={mark === m} data-mark-pick={m} onClick={() => setMark(m)} className={`chip ${mark === m ? "on" : ""}`}>
              <span className="inline-flex items-center gap-1.5">
                <Icon name={MARK_ICON[m]} />
                {W.marks[m]}
              </span>
            </button>
          ))}
        </div>
        {fixing ? <p className="text-[14px] font-medium text-terracotta">{W.problems.stranger_fix(fixing)}</p> : null}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(3.25rem,1fr))] gap-2" role="group" aria-label={`${klass}, by Sr. No.`} data-grid>
          {enrolled.map((roll) => (
            <Cell key={roll} roll={roll} marks={w.marks[roll]} rest={w.rest} onTap={() => tap(roll)} />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" role="switch" aria-checked={w.rest} onClick={() => setW({ ...w, rest: !w.rest })} className={`chip ${w.rest ? "on" : ""}`} data-rest={w.rest}>
            <span className="inline-flex items-center gap-1.5">
              <Icon name="as-expected" />
              {W.rest.label}: {w.rest ? W.rest.on : W.rest.off}
            </span>
          </button>
        </div>
      </section>
      <div className="flex flex-wrap items-center gap-3 border-t border-basalt/12 py-3" data-count-strip>
        <span className="text-[15px] font-medium" data-count-line>
          {countLine(w, enrolled)}
        </span>
        <button type="button" className="btn ml-auto" disabled={problems.length > 0 || pending} onClick={submit} data-submit>
          {button}
        </button>
        {said ? (
          <p role="alert" className="w-full text-[14px] text-terracotta">
            {said}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function Cell({ roll, marks, rest, onTap }: { roll: string; marks?: MarkKey[]; rest: boolean; onTap: () => void }) {
  const m: MarkKey | "as_expected" | null = marks?.length ? marks[0] : rest ? "as_expected" : null;
  const tone = m ? MARK_TONE[m] : "border-basalt/30 border-dashed bg-chalk text-basalt/70";
  const words = m ? W.marks[m] : W.notSeen;
  return (
    <button type="button" onClick={onTap} data-roll={roll} data-cell-mark={m ?? "none"} aria-label={`#${roll}: ${words}`} className={`flex min-h-12 flex-col items-center justify-center gap-0.5 border-2 text-[15px] font-semibold tabular-nums ${tone}`}>
      #{roll}
      {m ? <Icon name={MARK_ICON[m]} size={ICON_SIZE.table} /> : <span className="h-4" />}
    </button>
  );
}

function ProblemRow({ p, w, setW, fixing, setFixing }: { p: Problem; w: Work; setW: (w: Work) => void; fixing: string | null; setFixing: (r: string | null) => void }) {
  return (
    <li className="flex flex-wrap items-center gap-3 border border-terracotta/35 bg-terracotta/8 px-3 py-2" data-problem={p.kind}>
      <StatusChip state="fixThis" round />
      <span className="min-w-[12rem] flex-1 text-[15px]">{p.text}</span>
      {p.kind === "stranger" ? (
        <>
          <button type="button" className="btn secondary" aria-pressed={fixing === p.roll} onClick={() => setFixing(fixing === p.roll ? null : p.roll)}>
            {W.problems.stranger_fix(p.roll)}
          </button>
          <button type="button" className="btn secondary" onClick={() => setW(paint(w, p.roll, "clear"))}>
            {W.problems.remove(p.roll)}
          </button>
        </>
      ) : null}
      {p.kind === "two"
        ? p.marks.map((m) => (
            <button key={m} type="button" className="btn secondary inline-flex items-center gap-1.5" onClick={() => setW({ ...w, marks: { ...w.marks, [p.roll]: [m] } })}>
              <Icon name={MARK_ICON[m]} />
              {W.problems.keep(W.marks[m])}
            </button>
          ))
        : null}
      {p.kind === "line" ? (
        <button type="button" className="btn secondary" onClick={() => setW({ ...w, settled: [...w.settled, p.section] })}>
          {W.problems.asItIs}
        </button>
      ) : null}
    </li>
  );
}

function ActivityPicker({ w, setW, activities }: { w: Work; setW: (w: Work) => void; activities: Activity[] }) {
  const chosen = activities.find((a) => a.code === w.activity);
  const [q, setQ] = useState("");
  const found = findActivities(activities, q);
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[13px] text-basalt/70">{W.activity.label}</span>
        {chosen ? (
          <span className="text-[16px] font-medium" data-activity={chosen.code}>
            {activityWords(chosen)}
          </span>
        ) : null}
        <label className="relative">
          <span className="sr-only">{W.activity.placeholder}</span>
          <Icon name="search" size={ICON_SIZE.table} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-basalt/50" />
          <input className="input !w-56 !pl-9" inputMode="search" placeholder={W.activity.placeholder} value={q} onChange={(e) => setQ(e.target.value)} data-activity-search />
        </label>
      </div>
      {q.trim() ? (
        found.length ? (
          <div className="flex flex-wrap gap-2">
            {found.map((a) => (
              <button
                key={a.code}
                type="button"
                className="chip"
                onClick={() => {
                  setW({ ...w, activity: a.code });
                  setQ("");
                }}
              >
                {activityWords(a)}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-[14px] text-basalt/70">{W.activity.noMatch}</p>
        )
      ) : null}
    </div>
  );
}
