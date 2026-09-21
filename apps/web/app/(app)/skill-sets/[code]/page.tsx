import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { DIFFICULTIES, misconceptionsFor, skillSet } from "@/lib/queries";
import { ratifySkillSet, saveSkillSet } from "./actions";
import { deadline } from "@/lib/deadline";

const FORMATS: [string, string][] = [
  ["column_grid", "Column calculation"],
  ["bare_sum", "Horizontal sum"],
  ["missing_number", "Missing number"],
  ["word_1step", "One-step word problem"],
];

type Props = { params: Promise<{ code: string }>; searchParams: Promise<Record<string, string | undefined>> };

export default async function SkillSetPage({ params, searchParams }: Props) {
  const { code } = await params;
  const q = await searchParams;
  const s = await deadline(skillSet(code));
  if (!s) notFound();
  const op = String(s.difficulty.Easy?.check?.op ?? "-");
  const mis = await deadline(misconceptionsFor(op));

  return (
    <>
      <PageHeader
        stage="Stage 1 · Input"
        title={s.name}
        sub={`${s.code} · rung ${s.rung_code} (${s.band}) · ${s.descriptor}. What the prompt reads, in words, and what the verifier enforces, as a check.`}
      />
      <Body>
        {q.saved ? <Notice tone="neem">Saved. The next fill for this set reads the new words.</Notice> : null}
        {q.ratified ? <Notice tone="neem">Ratified. A reload of the seed file will not undo this.</Notice> : null}
        {q.error === "required" ? <Notice tone="terracotta">Name and learning objective cannot be empty.</Notice> : null}
        {q.error === "check" ? (
          <Notice tone="terracotta">
            The {q.band} rule needs an operation, digit counts from 1 to 5, and at least one exchange option ticked.
            Nothing was saved.
          </Notice>
        ) : null}

        <form action={saveSkillSet} className="grid gap-[18px]">
          <input type="hidden" name="code" value={s.code} />
          <div className="grid gap-[18px] lg:grid-cols-[1fr_340px]">
            <Panel title="The set">
              <div className="grid gap-4">
                <label className="field">
                  <span className="label">Name</span>
                  <input className="input" name="name" defaultValue={s.name} required />
                </label>
                <label className="field">
                  <span className="label">Learning objective</span>
                  <textarea className="textarea" name="learning_objective" defaultValue={s.learning_objective} required />
                </label>
                <label className="field">
                  <span className="label">Philosophy for this set · one line each</span>
                  <textarea className="textarea" name="philosophy" defaultValue={s.philosophy.join("\n")} />
                  <span className="note">The school-wide lines are added to every set automatically.</span>
                </label>
              </div>
            </Panel>
            <div className="grid gap-[18px] content-start">
              <Panel title="Status">
                <div className="flex flex-wrap items-center gap-3">
                  {s.status === "ratified" ? (
                    <Pill tone="neem">Ratified · {s.ratified_by}</Pill>
                  ) : (
                    <Pill tone="bamboo">Draft</Pill>
                  )}
                  <span className="fact text-[11px] text-basalt/55">updated {new Date(s.updated_at).toLocaleDateString("en-IN")}</span>
                </div>
              </Panel>
              <Panel title="Formats">
                <div className="grid gap-2">
                  {FORMATS.map(([v, labelText]) => (
                    <label key={v} className="flex min-h-11 items-center gap-3 text-[14px]">
                      <input type="checkbox" name="formats" value={v} defaultChecked={s.formats.includes(v)} className="accent-terracotta" />
                      {labelText} <span className="fact text-[11px] text-basalt/55">{v}</span>
                    </label>
                  ))}
                </div>
              </Panel>
            </div>
          </div>

          <Panel title="The four difficulties" aside="your words · the rule the checker uses">
            <p className="note mb-4">
              Say each difficulty in your own words first; that is what the question writer reads. The boxes under it are
              the rule the computer checks on every question before it is kept.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {DIFFICULTIES.map((d) => (
                <BandEditor key={d} band={d} value={s.difficulty[d]} />
              ))}
            </div>
          </Panel>

          <Panel title="Misconceptions the prompt is told about" aside={`${mis.length} in the vocabulary for ${op}`}>
            <div className="grid gap-2 md:grid-cols-2">
              {mis.map((m) => (
                <label key={m.code} className="flex min-h-11 items-start gap-3 text-[13.5px]">
                  <input
                    type="checkbox"
                    name="misconception_codes"
                    value={m.code}
                    defaultChecked={s.misconception_codes.includes(m.code)}
                    className="mt-[5px] accent-terracotta"
                  />
                  <span>
                    <span className="fact">{m.code}</span> · {m.name}
                    <span className="note block">{m.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </Panel>

          <div className="flex flex-wrap items-center gap-3">
            <button className="btn" type="submit">Save</button>
            <Link href="/" className="btn secondary">Back to the map</Link>
          </div>
        </form>

        {s.status !== "ratified" ? (
          <form action={ratifySkillSet} className="mt-[18px] flex items-center gap-3">
            <input type="hidden" name="code" value={s.code} />
            <button className="btn secondary" type="submit">Ratify this set</button>
            <span className="note">Aseem&apos;s step. Records who ratified and when; the seed loader never overwrites it.</span>
          </form>
        ) : null}
      </Body>
    </>
  );
}

// The rule in plain boxes. Keys an engineer added that this form does not know are carried
// through untouched by the action, so the form can stay simple without losing them.
function BandEditor({ band, value }: { band: string; value?: { words: string; check: Record<string, unknown> } }) {
  const c = value?.check ?? {};
  const digits = Array.isArray(c.digits) ? (c.digits as number[]) : [2, 2];
  const regroups = Array.isArray(c.regroups) ? (c.regroups as number[]) : [1];
  const zeros = c.no_zero_top ? "none" : c.across_zero === true ? "across" : c.across_zero === false ? "not_across" : "any";
  const num = "input !w-[74px] text-center fact";
  return (
    <fieldset className="grid gap-3 border border-basalt/14 p-4">
      <legend className="fact px-1">{band}</legend>
      <input type="hidden" name={`existing:${band}`} value={JSON.stringify(c)} />
      <label className="field">
        <span className="label">In your words</span>
        <textarea className="textarea" name={`words:${band}`} defaultValue={value?.words ?? ""} />
      </label>
      <div className="flex flex-wrap items-end gap-3">
        <label className="field">
          <span className="label">Operation</span>
          <select className="select !w-auto" name={`op:${band}`} defaultValue={String(c.op ?? "-")}>
            <option value="+">+ add</option>
            <option value="-">− subtract</option>
            <option value="×">× multiply</option>
          </select>
        </label>
        <label className="field">
          <span className="label">Top digits</span>
          <input className={num} type="number" min={1} max={5} name={`top:${band}`} defaultValue={digits[0]} required />
        </label>
        <label className="field">
          <span className="label">Bottom digits</span>
          <input className={num} type="number" min={1} max={5} name={`bottom:${band}`} defaultValue={digits[1]} required />
        </label>
      </div>
      <div className="field">
        <span className="label">Exchanges allowed</span>
        <div className="flex flex-wrap gap-4">
          {[0, 1, 2, 3].map((n) => (
            <label key={n} className="flex min-h-9 items-center gap-2 text-[13.5px]">
              <input
                type="checkbox"
                name={`regroups:${band}`}
                value={n}
                defaultChecked={regroups.includes(n)}
                className="accent-terracotta"
              />
              {n === 0 ? "none" : n}
            </label>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="field min-w-[180px] flex-1">
          <span className="label">Zeros in the top number</span>
          <select className="select" name={`zeros:${band}`} defaultValue={zeros}>
            <option value="any">Do not mind</option>
            <option value="none">No zero anywhere</option>
            <option value="across">Must exchange across a zero</option>
            <option value="not_across">Must not have a zero to exchange across</option>
          </select>
        </label>
        <label className="field">
          <span className="label">Answer at most</span>
          <input
            className={num}
            type="number"
            min={1}
            name={`max_total:${band}`}
            defaultValue={typeof c.max_total === "number" ? c.max_total : ""}
            placeholder="—"
          />
        </label>
      </div>
    </fieldset>
  );
}

function Notice({ tone, children }: { tone: "neem" | "terracotta"; children: React.ReactNode }) {
  return (
    <div className={`mb-[18px] border p-3 text-[13.5px] ${tone === "neem" ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"}`} role="status">
      {children}
    </div>
  );
}
