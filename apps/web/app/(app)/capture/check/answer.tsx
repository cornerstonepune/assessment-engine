import { correctRead, judgeOne } from "../actions";
import type { CheckItem } from "@/lib/queries-read";

// The ways a person settles one answer (goals/s4-validation-queue.yaml). The page names which is its one main action; the
// others stay beside the picture. Every form carries the answer, its paper and where the queue stands, so the next one
// opens after the save.
type Props = { a: CheckItem; next: string };

function Ids({ a, next }: Props) {
  return (
    <>
      <input type="hidden" name="result_id" value={a.id} />
      <input type="hidden" name="paper_id" value={a.paper_id} />
      <input type="hidden" name="next" value={next} />
    </>
  );
}

/** Right, wrong or blank: the child's writing is read; only a person can say which. */
export function Judge({ a, next }: Props) {
  return (
    <form action={judgeOne} className="flex flex-wrap items-center gap-2">
      <Ids a={a} next={next} />
      <span>
        The child wrote <strong className="fact">{a.human_read ?? a.read}</strong>. Is it
      </span>
      <button className="btn" name="status" value="correct" type="submit">
        Right
      </button>
      <button className="btn secondary" name="status" value="wrong" type="submit">
        Wrong
      </button>
      <button className="btn secondary" name="status" value="blank" type="submit">
        Blank
      </button>
    </form>
  );
}

/** The reader's reading is what the child wrote. */
export function Confirm({ a, next, says }: Props & { says: string }) {
  return (
    <form action={correctRead}>
      <Ids a={a} next={next} />
      <input type="hidden" name="human_read" value={says} />
      <button className="btn" type="submit">
        Yes, the child wrote {says || "nothing"}
      </button>
    </form>
  );
}

/** What the child wrote, typed; the engine marks it again. */
export function TypeIt({ a, next, label, primary }: Props & { label: string; primary?: boolean }) {
  return (
    <form action={correctRead} className="flex flex-wrap items-end gap-2">
      <Ids a={a} next={next} />
      <label className="field">
        <span className="label">{label}</span>
        <input className="input w-[160px]" name="human_read" required maxLength={40} />
      </label>
      <button className={primary ? "btn" : "btn secondary"} type="submit">
        Save
      </button>
    </form>
  );
}

/** Nothing is written here. */
export function Nothing({ a, next }: Props) {
  return (
    <form action={correctRead}>
      <Ids a={a} next={next} />
      <input type="hidden" name="human_read" value="" />
      <button className="btn secondary" type="submit">
        Nothing is written here
      </button>
    </form>
  );
}
