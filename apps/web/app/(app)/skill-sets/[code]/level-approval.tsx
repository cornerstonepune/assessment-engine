import { Pill } from "@/components/shell";
import type { Difficulty, SkillSet } from "@/lib/queries";
import { approveLevel } from "./actions";
import { dateWords } from "@/lib/week";

/** One level's approval on its card (goals/f1d-questions-approved-per-level.yaml): who approved its questions and when,
 *  or — for the coordinator — the button that approves this level alone; an educator reads who it waits for. A level whose
 *  samples changed after the page was opened keeps waiting (goals/edt_edit_samples_and_kinds.yaml). */
export function LevelApproval({ s, d, mayApprove, opened }: { s: SkillSet; d: Difficulty; mayApprove: boolean; opened?: string }) {
  const done = s.approved?.[d];
  if (done) {
    return (
      <Pill tone="neem">
        Approved · {done.by.split(" (")[0]} · {dateWords(done.at)}
      </Pill>
    );
  }
  if (!mayApprove) return <p className="note">Waiting for the coordinator to approve these questions.</p>;
  return (
    <form action={approveLevel} className="flex flex-wrap items-center gap-2">
      <Pill tone="bamboo">Waiting for approval</Pill>
      <input type="hidden" name="code" value={s.code} />
      {/* when this page was drawn: an approval lands only if the level's samples and kinds did not change since */}
      <input type="hidden" name="opened" value={opened ?? ""} />
      <input type="hidden" name="version" value={s.version} />
      <input type="hidden" name="level" value={d} />
      <button className="btn" type="submit">
        Approve {d}
      </button>
    </form>
  );
}
