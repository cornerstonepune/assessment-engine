import type { SampleChoices, WaysRow } from "@/lib/queries-skills";
import { removeKind } from "./sample-actions";
import { KindForm } from "./sample-form";

// The kinds of question one level asks — "the nature of the question" (Nimish, 2026-10-24) — changed on the skill's page
// (goals/edt_edit_samples_and_kinds.yaml): a kind taken off, or one added from the approved kinds, with the three
// samples a level shows of each. Either sends the level back for approval.

type Props = {
  code: string;
  level: string;
  ways: WaysRow[];
  choices: SampleChoices;
  /** the kind being added to this level (`?addkind=<level>~<kind>`), and how many samples it still needs */
  adding: { kind: string; need: number } | null;
};

export function LevelKinds({ code, level, ways, choices, adding }: Props) {
  const here = ways.filter((w) => w.levels.includes(level));
  const offered = choices.kinds.filter((k) => !here.some((w) => w.code === k.code));
  const chosen = adding ? choices.kinds.find((k) => k.code === adding.kind) : undefined;
  return (
    <div className="grid gap-2 text-[13px]" aria-label={`Kinds of question at ${level}`}>
      <span className="label">Kinds of question at this level</span>
      <ul className="grid gap-1">
        {here.map((w) => (
          <li key={w.code} data-level-kind={w.code} className="flex flex-wrap items-center gap-2">
            <span>
              {w.words}
              {w.open ? " · a person checks every answer" : ""}
            </span>
            {here.length > 1 ? (
              <form action={removeKind}>
                <input type="hidden" name="code" value={code} />
                <input type="hidden" name="level" value={level} />
                <input type="hidden" name="kind" value={w.code} />
                <button className="chip" type="submit" aria-label={`Take “${w.words}” off ${level}`}>
                  Take off
                </button>
              </form>
            ) : null}
          </li>
        ))}
      </ul>
      {offered.length ? (
        <form method="get" action={`/skill-sets/${code}`} className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor={`addkind-${level}`}>
            Add a kind of question to {level}
          </label>
          <select id={`addkind-${level}`} name="addkind" className="select !w-auto" defaultValue={adding ? `${level}~${adding.kind}` : ""}>
            <option value="">Add an approved kind …</option>
            {offered.map((k) => (
              <option key={k.code} value={`${level}~${k.code}`}>
                {k.words}
              </option>
            ))}
          </select>
          <button className="chip" type="submit">
            Add to {level}
          </button>
        </form>
      ) : null}
      {adding && chosen ? (
        <KindForm code={code} level={level} kind={chosen.code} kindWords={chosen.words} open={chosen.open} choices={choices} n={adding.need} />
      ) : null}
    </div>
  );
}
