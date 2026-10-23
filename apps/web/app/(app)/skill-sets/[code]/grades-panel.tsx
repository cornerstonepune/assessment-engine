import { Notice, Panel } from "@/components/shell";
import { gradeOf, levelsOf, type Grades, type SkillSet } from "@/lib/queries";
import { dateWords } from "@/lib/week";
import { saveGrades } from "./actions";

/** Which grade each level of a skill belongs to: one each, kept apart from the level's words so the approval stays. */
export function GradesPanel({ s, grades, saved }: { s: SkillSet; grades: Grades; saved: boolean }) {
  return (
      <Panel
        title="Which grade each level belongs to"
        label="Which grade each level belongs to"
        aside="each level to one grade; a child is given a level of their grade or below"
      >
        {saved ? <Notice tone="neem">Saved: each level is now taught in the grade shown.</Notice> : null}
        <form action={saveGrades} className="flex flex-wrap items-end gap-4">
          <input type="hidden" name="code" value={s.code} />
          {levelsOf(s).map((d) => (
            <label key={d} className="grid gap-1 text-[13px]">
              <span className="label">{d}</span>
              <select name={`grade:${d}`} defaultValue={gradeOf(s, d)} className="border border-basalt/20 bg-white px-2 py-1">
                {grades.list.map((x) => (
                  <option key={x.code} value={x.code}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button className="btn secondary" type="submit">
            Save the grades
          </button>
        </form>
        <p className="note mt-2">
          A level in another grade shows under that grade on the Curriculum too. Moving a level does not change its
          words, so the skill keeps its approval.
          {s.moved_by && s.moved_at
            ? ` Last moved by ${s.moved_by}, ${dateWords(s.moved_at)}.`
            : null}
        </p>
      </Panel>
  );
}
