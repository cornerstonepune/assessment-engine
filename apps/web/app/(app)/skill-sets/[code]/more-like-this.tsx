import { sql } from "@/lib/db";
import { moreEnglish, moreMaths } from "./more-actions";

// More questions like a sample (goals/gen_from_a_sample.yaml). Nimish, 2026-10-26: "putting in the sample questions, and
// the ability for the system to then generate a certain number of questions of that pattern." English: a model writes
// them and code checks every one; Maths: code makes them from the sample's kind of sum. Either is a draft until the
// level is approved again. How many is the educator's, up to the `generate.max_per_request` row.

function HowMany({ most }: { most: number }) {
  return (
    <label className="flex items-center gap-2">
      How many
      <input type="number" name="n" min={1} max={most} defaultValue={Math.min(10, most)} className="input !w-20" required />
    </label>
  );
}

/** Under an English sample: make more like it. */
export function EnglishMore({ code, level, kind, ord, most }: { code: string; level: string; kind: string; ord: number; most: number }) {
  return (
    <details className="text-[13px]">
      <summary className="cursor-pointer">Make more like this</summary>
      <form action={moreEnglish} className="mt-2 flex flex-wrap items-center gap-2">
        <input type="hidden" name="code" value={code} />
        <input type="hidden" name="level" value={level} />
        <input type="hidden" name="kind" value={kind} />
        <input type="hidden" name="ord" value={ord} />
        <HowMany most={most} />
        <button className="btn" type="submit" aria-label={`Make questions like sample ${ord}`}>
          Make questions like this
        </button>
      </form>
      <p className="note mt-1">Each one is checked before you see it; any that fails is thrown away, and you are told why.</p>
    </details>
  );
}

/** Under a Maths level: a sum typed as an example, and how many more of its kind code should make. */
export async function MathsMore({ code, level }: { code: string; level: string }) {
  const [{ most }] = await sql<{ most: number }[]>`
    select coalesce((select value::int from threshold where key = 'generate.max_per_request'), 20) as most`;
  return (
    <details className="text-[13px]" data-more={level}>
      <summary className="cursor-pointer">More questions like a sample</summary>
      <form action={moreMaths} className="mt-2 grid gap-2">
        <input type="hidden" name="code" value={code} />
        <input type="hidden" name="level" value={level} />
        <label className="grid gap-1">
          A question like the ones you want
          <input name="text" className="input" placeholder="47 + 38" required maxLength={40} aria-label={`A sample question at ${level}`} />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-1">
            <input type="radio" name="layout" value="line" defaultChecked /> In a line
          </label>
          <label className="flex items-center gap-1">
            <input type="radio" name="layout" value="columns" /> In columns
          </label>
          <HowMany most={most} />
          <button className="btn" type="submit">
            Make questions like this
          </button>
        </div>
      </form>
    </details>
  );
}
