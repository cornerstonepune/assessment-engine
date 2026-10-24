import type { ClassFlow } from "@/lib/queries-teaching";
import { count } from "@/lib/todo";

// A topic's flow in one class, as a strip: skills ready → baseline → home assessments → practice after it was taught.
// A step done is a tick and its words; a step not yet is a ring and a quiet word. Never colour alone (docs/ux-rules.md).
function Step({ done, children }: { done: boolean; children: React.ReactNode }) {
  return (
    <li data-step data-done={done ? "yes" : "no"} className={`inline-flex items-center gap-1 whitespace-nowrap ${done ? "text-basalt" : "text-basalt/45"}`}>
      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {done ? <path d="M3.2 8.4l3 3 6.4-6.8" /> : <circle cx="8" cy="8" r="4.6" />}
      </svg>
      {children}
    </li>
  );
}

export function FlowStrip({ cls }: { cls: ClassFlow }) {
  const f = cls.flow;
  return (
    <div data-flow={cls.section} className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px]">
      <b className="min-w-[2.5rem] font-medium">{cls.section}</b>
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1" aria-label={`Flow in ${cls.section}`}>
        <Step done={f.skills.ready}>{f.skills.ready ? "Skills ready" : `Skills ${f.skills.approved} of ${f.skills.total}`}</Step>
        <span aria-hidden="true" className="text-basalt/35">→</span>
        <Step done={f.baseline.done}>Baseline</Step>
        <span aria-hidden="true" className="text-basalt/35">→</span>
        <Step done={f.home.papers > 0}>
          {f.home.papers ? `${count(f.home.papers, "home assessment")}${f.home.repeat ? ` · ${count(f.home.repeat, "child", "children")} more than once` : ""}` : "Home assessments"}
        </Step>
        <span aria-hidden="true" className="text-basalt/35">→</span>
        <Step done={f.practice.papers > 0}>{f.practice.papers ? `${count(f.practice.papers, "practice paper")} since taught` : "Practice"}</Step>
      </ol>
    </div>
  );
}
