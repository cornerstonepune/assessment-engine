// The child's knowledge graph, drawn: one lane per skill, its steps easy to hard, each step the graph's own state in
// its colour (lib/rag.ts), opening onto the answers behind it.
import type { ReactNode } from "react";
import { Bar, MarkPill, Pill, TONE_BG } from "@/components/shell";
import { STATE_WORDS, type Evidence, type RungState, type Skill } from "@/lib/queries";
import { rag } from "@/lib/rag";

export const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

// One lane per skill, its steps left to right in ladder order. The same slot means the same thing
// in every lane, so a teacher scans positions rather than reading sentences.
export function Lane({ skill, rows, answers, names }: { skill: Skill; rows: RungState[]; answers: Evidence[]; names: Record<string, string> }) {
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
            <li key={r.rung_code} data-rag={rag(r.state)} className="flex items-start">
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

export function AnswerTable({ rows, names }: { rows: AnswerRow[]; names: Record<string, string> }) {
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

export function Legend({ state, children }: { state: string; children: ReactNode }) {
  return (
    <span className="flex items-center gap-2">
      <span className="scale-[0.72]">
        <Mark state={state} />
      </span>
      {children}
    </span>
  );
}

