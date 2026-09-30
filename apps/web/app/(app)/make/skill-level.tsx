import { GRADE_GROUPS, levelsOf, type SkillSet } from "@/lib/queries";

// One skill and one of its levels, as a paper asks for them: every taught skill set's levels grouped by grade, the
// child's or the class's own grade first, each with how many questions the bank holds at it. `prefix` goes before
// each value (a child's id, where each child of a class has a line of their own); `form` ties the select to a form
// elsewhere on the page.
export function SkillLevelSelect({ name, label, value, sets, band, prefix = "", empty = "—", form }: {
  name: string; label: string; value?: string; sets: SkillSet[]; band: string; prefix?: string; empty?: string; form?: string;
}) {
  const grades = [...GRADE_GROUPS].sort(([a], [b]) => Number(b === band) - Number(a === band));
  return (
    <select className="select" name={name} defaultValue={value ?? ""} aria-label={label} form={form}>
      <option value="">{empty}</option>
      {grades.map(([grade, words]) => {
        const here = sets.filter((x) => x.band === grade);
        return here.length ? (
          <optgroup key={grade} label={words}>
            {here.flatMap((x) =>
              levelsOf(x).map((d) => (
                <option key={`${x.code}~${d}`} value={`${prefix}${x.code}~${d}`}>
                  {x.name} · {d} ({x.counts[d] ?? 0} questions)
                </option>
              )),
            )}
          </optgroup>
        ) : null;
      })}
    </select>
  );
}
