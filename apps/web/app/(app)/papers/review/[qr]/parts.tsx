import Link from "@/components/link";
import { Panel } from "@/components/shell";
import { Question } from "@/components/question";
import type { ItemRow } from "@/lib/queries-bank";
import { approvePaper, changePaper } from "./actions";

// The review page's parts (goals/paper_review_add_remove.yaml): a question's own words, its Remove button and the one
// confirm some removals ask for, and the chosen bank question with its Add button.

export type Q = {
  id: string;
  item_key: string;
  fmt: string;
  stem: string;
  spec: ItemRow["spec"];
  text: string;
  skill_set: string;
  skill: string | null;
  topic_name: string | null;
  level: string;
  kind: string | null;
  kind_words: string | null;
  days?: number | null;
};
export type Covers = { skill_set: string; name: string; level: string; n: number };
export type Review = {
  qr: string;
  child_id: string | null;
  kind: string;
  state: "waiting" | "approved" | "printed" | "replaced";
  why_not: string;
  newer: string | null;
  approved_by: string | null;
  questions: Q[];
  covers: Covers[];
  min: number;
  max: number;
  pages: number;
};

/** A question drawn as the page prints it, from its own row: the one drawing the bank and the answer key use. */
export function Printed({ q }: { q: Q }) {
  const it: ItemRow = { ...q, responses: [], status: "active", times_used: 0, skill_set_code: q.skill_set, skill_set_name: q.skill, difficulty: q.level };
  return <Question it={it} />;
}

/** What taking this question off would cost, in words; "" when nothing, and no confirm is asked. */
export function costOf(r: Review, q: Q): string {
  const out: string[] = [];
  if (r.questions.length - 1 < r.min) return "";
  if (r.questions.length === 1) out.push("The paper would hold no question.");
  else if (r.covers.find((c) => c.skill_set === q.skill_set && c.level === q.level)?.n === 1)
    out.push(`${q.skill ?? q.skill_set} · ${q.level} would have no question on this paper.`);
  if (r.state === "approved") out.push("Its approval is withdrawn: it waits for approval again before it prints.");
  return out.join(" ");
}

export function RemoveButton({ r, q, confirming }: { r: Review; q: Q; confirming: boolean }) {
  const cost = costOf(r, q);
  if (cost && !confirming)
    return (
      <Link href={`/papers/review/${r.qr}?confirm=${q.id}#q-${q.id}`} className="btn secondary">
        Remove
      </Link>
    );
  return (
    <form action={changePaper} data-confirm={cost ? "" : undefined}>
      <input type="hidden" name="qr" value={r.qr} />
      <input type="hidden" name="item_id" value={q.id} />
      <input type="hidden" name="what" value="remove" />
      {cost ? <p className="mb-1 max-w-[36ch] text-[12.5px] text-terracotta">{cost}</p> : null}
      <button className="btn secondary" type="submit">
        {cost ? "Yes, remove it" : "Remove"}
      </button>
    </form>
  );
}

/** The question chosen in the dropdowns, seen as it prints, and where it goes. */
export function SeeIt({ r, q }: { r: Review; q: Q }) {
  const full = r.questions.length >= r.max;
  return (
    <Panel title="See it" label="The chosen question">
      <div className="text-[14px]" data-item={q.item_key}>
        <Printed q={q} />
      </div>
      <p className="note mt-2">
        {q.skill ?? q.skill_set} · {q.level}
        {q.kind_words ? ` · ${q.kind_words}` : ""}
        {q.days != null ? ` · given ${q.days} ${q.days === 1 ? "day" : "days"} ago` : ""}
      </p>
      {full ? (
        <p className="note mt-2 text-terracotta">
          This paper already holds {r.max} questions, the most a paper may hold. Remove one first.
        </p>
      ) : (
        <form action={changePaper} className="mt-3 flex flex-wrap items-center gap-2">
          <input type="hidden" name="qr" value={r.qr} />
          <input type="hidden" name="item_id" value={q.id} />
          <input type="hidden" name="what" value="add" />
          <label className="flex items-center gap-2 text-[13px]">
            Put it
            <select name="at" defaultValue="" className="select !w-auto">
              <option value="">at the end</option>
              {r.questions.map((_, i) => (
                <option key={i} value={i + 1}>
                  {`before question ${i + 1}`}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit">
            Add
          </button>
          {r.state === "approved" ? <span className="note">Adding it withdraws the approval: it waits for approval again.</span> : null}
        </form>
      )}
    </Panel>
  );
}

export function ApproveButton({ r }: { r: Review }) {
  return (
    <form action={approvePaper}>
      <input type="hidden" name="qr" value={r.qr} />
      <button className="btn" type="submit">
        {r.kind === "focus" ? "Approve this home assessment" : "Approve this paper"}
      </button>
    </form>
  );
}
