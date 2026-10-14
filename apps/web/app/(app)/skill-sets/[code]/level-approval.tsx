import { Pill } from "@/components/shell";
import type { Difficulty, SkillSet } from "@/lib/queries";
import { approveLevel } from "./actions";

/** One level's approval on its card (goals/f1d-questions-approved-per-level.yaml): who approved its questions and when,
 *  or — for the coordinator — the button that approves this level alone; an educator reads who it waits for. */
export function LevelApproval({ s, d, mayApprove }: { s: SkillSet; d: Difficulty; mayApprove: boolean }) {
  const done = s.level_approved?.[d];
  if (done) {
    return (
      <Pill tone="neem">
        Approved · {done.by.split(" (")[0]} · {new Date(done.at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
      </Pill>
    );
  }
  if (!mayApprove) return <p className="note">Waiting for the coordinator to approve these questions.</p>;
  return (
    <form action={approveLevel}>
      <input type="hidden" name="code" value={s.code} />
      <input type="hidden" name="version" value={s.version} />
      <input type="hidden" name="level" value={d} />
      <button className="btn" type="submit">
        Approve {d}
      </button>
    </form>
  );
}
