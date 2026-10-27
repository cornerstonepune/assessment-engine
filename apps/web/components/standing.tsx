import { StatusChip, type State } from "./status-chip";
import type { Rag } from "@/lib/rag";
import type { States } from "@/lib/states";
import type { Signals, Spread } from "@/lib/queries-results";

// How a topic or a skill stands, said the same way on Class results and on a child's page (goals/res_results_by_topic.yaml):
// a colour is always its row's words beside a number or in a chip, never colour alone (docs/ux-rules.md, rule 10).

export type Standing = Rag | "none";
/** Needs the educator first, and nothing checked last. */
export const ORDER: Standing[] = ["red", "amber", "green", "grey", "none"];
export const NOT_ASSESSED = "not assessed yet";
const CHIP: Record<Standing, State> = { red: "needsHelp", amber: "practising", green: "secure", grey: "tooFew", none: "notAssessed" };
const BAR: Record<Standing, string> = { red: "bg-terracotta", amber: "bg-bamboo", green: "bg-neem", grey: "bg-monsoon/45", none: "bg-basalt/10" };

export const standingWords = (states: States, s: Standing) => (s === "none" ? NOT_ASSESSED : states.colours[s].count_words);

/** A colour (or no answer at all) in its chip, in its row's words. */
export function StandingChip({ standing, states }: { standing: Standing; states: States }) {
  return <StatusChip state={CHIP[standing]} words={standingWords(states, standing)} />;
}

/** A group of children counted by where they stand: a thin bar for the eye, and each count in words beside it. */
export function SpreadCell({ spread, states }: { spread: Spread; states: States }) {
  const total = ORDER.reduce((n, s) => n + spread[s], 0);
  const shown = ORDER.filter((s) => spread[s]);
  return (
    <div className="grid gap-1">
      <div aria-hidden="true" className="flex h-[7px] w-full max-w-[220px] overflow-hidden bg-basalt/5">
        {shown.map((s) => (
          <span key={s} className={BAR[s]} style={{ width: `${(100 * spread[s]) / Math.max(1, total)}%` }} />
        ))}
      </div>
      <span className="text-[12.5px] leading-snug">
        {shown.map((s, i) => (
          <span key={s} data-standing={s} className="whitespace-nowrap">
            {spread[s]} {standingWords(states, s)}
            {i < shown.length - 1 ? " · " : ""}
          </span>
        ))}
      </span>
    </div>
  );
}

/** Answers in the three signals (rule 5): right of those attempted, then wrong, wrong with working and blank apart. */
export function Score({ s }: { s: Signals }) {
  const attempted = s.right + s.wrong + s.wrong_working;
  if (!attempted && !s.blank) return null;
  const rest = [
    s.wrong ? `${s.wrong} wrong` : "",
    s.wrong_working ? `${s.wrong_working} wrong with working` : "",
    s.blank ? `${s.blank} blank` : "",
  ].filter(Boolean);
  return (
    <span className="leading-snug">
      <span className="fact">{attempted ? `${s.right} of ${attempted} right` : "nothing attempted"}</span>
      {rest.length ? <span className="block text-[12px] text-basalt/65">{rest.join(" · ")}</span> : null}
    </span>
  );
}
