import { grades as schoolGrades, levelsOf, type SkillSet, usesLevel } from "@/lib/queries";

// One skill and one of its levels, as a paper asks for them: the levels of every taught skill set that the child's or
// the class's grade uses — its own grade's and those below (goals/f1e-the-grade-plan.yaml) — grouped by grade, its own
// grade first, each with how many questions the bank holds at it. `prefix` goes before
// each value (a child's id, where each child of a class has a line of their own); `form` ties the select to a form
// elsewhere on the page.
export async function SkillLevelSelect({ name, label, value, sets, band, prefix = "", empty = "—", form }: {
  name: string; label: string; value?: string; sets: SkillSet[]; band: string; prefix?: string; empty?: string; form?: string;
}) {
  const g = await schoolGrades();
  const grades = [...g.list].sort((a, b) => Number(b.code === band) - Number(a.code === band));
  return (
    <select className="select" name={name} defaultValue={value ?? ""} aria-label={label} form={form}>
      <option value="">{empty}</option>
      {grades.map(({ code: grade, name: words }) => {
        const here = sets.filter((x) => x.band === grade && levelsOf(x).some((d) => usesLevel(g, x, d, band)));
        return here.length ? (
          <optgroup key={grade} label={words}>
            {here.flatMap((x) =>
              levelsOf(x).filter((d) => usesLevel(g, x, d, band)).map((d) => (
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
