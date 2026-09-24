import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Answers, KIND, Question } from "@/components/question";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { requireStaff } from "@/lib/auth";
import { childrenOnRoll, gradeWords, type ChildRow } from "@/lib/queries";
import { worksheetCases } from "@/lib/queries-taxonomy";
import { libraryWorksheet, worksheetItems } from "@/lib/queries-worksheets";
import { kindsInWords } from "../library";

export const LIBRARY_CODE = /^[RMX]\d{1,2}-[EMHA]\d{2,3}$/;

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-");

// One worksheet from the library: what it practises, its twelve questions as the child meets them
// with their answers, and the printed paper one press away.
export async function LibraryWorksheetPage({ code }: { code: string }) {
  const me = await requireStaff();
  const [w, questions, cases, kids] = await deadline(
    Promise.all([libraryWorksheet(code), worksheetItems(code), worksheetCases(code), childrenOnRoll(me.email)]),
  );
  if (!w) notFound();
  const kinds = questions.reduce<Record<string, number>>((a, q) => ({ ...a, [q.fmt]: (a[q.fmt] ?? 0) + 1 }), {});

  return (
    <>
      <PageHeader
        stage={`Stage 2 · Print · ${gradeWords(w.band)} · ${w.skill} · ${w.difficulty}`}
        title={`Worksheet ${w.code}`}
        sub={w.outcome}
      />
      <Body>
        {w.retired_at ? (
          <Notice tone="terracotta">
            Retired on {fmtDate(w.retired_at)}: a question on it left the bank, and a new worksheet replaced it. It is
            kept so a paper already printed from it still matches its answers.
          </Notice>
        ) : null}
        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          <Link href={`/skill-sets/${w.skill_set_code}?level=${w.difficulty}#worksheets`} className="chip">
            ← {w.skill} · {w.difficulty}
          </Link>
          <Link href={`/worksheets?set=${w.skill_set_code}&level=${w.difficulty}#library`} className="chip">
            All worksheets
          </Link>
          {/* To look at, not to hand out: every copy of it carries the same code, and no row says whose it is. */}
          <a href={`/api/worksheet/${w.code}`} className="chip" target="_blank" rel="noopener">
            See the worksheet
          </a>
        </div>

        <PrintFor code={w.code} kids={kids} />

        <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_320px]">
          <Panel title="Its questions, as the child meets them" aside={`${questions.length} questions`}>
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Questions and answers">
                <thead>
                  <tr>
                    <th className="text-right">#</th>
                    <th>Question</th>
                    <th>Answer</th>
                    <th>Kind</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((it, i) => (
                    <tr key={it.item_key}>
                      <td className="num align-top">{i + 1}</td>
                      <td className="min-w-[220px]">
                        <Link href={`/library/${it.item_key}`} className="text-basalt no-underline">
                          <Question it={it} />
                        </Link>
                      </td>
                      <td className="align-top">
                        <Answers it={it} />
                      </td>
                      <td className="align-top text-[12.5px] whitespace-nowrap text-basalt/70">
                        {KIND[it.fmt] ?? it.fmt}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="About it">
            <dl className="grid gap-3 text-[13.5px]">
              <div>
                <dt className="label mb-[3px]">Skill</dt>
                <dd>
                  <Link href={`/skill-sets/${w.skill_set_code}`}>{w.outcome}</Link>
                </dd>
              </div>
              <div>
                <dt className="label mb-[3px]">Level</dt>
                <dd>
                  {w.difficulty}
                  {w.level_words ? <span className="note block">{w.level_words}</span> : null}
                </dd>
              </div>
              <div>
                <dt className="label mb-[3px]">Kinds of question</dt>
                <dd>{kindsInWords(kinds)}</dd>
              </div>
              <div>
                <dt className="label mb-[3px]">Taxonomy cases</dt>
                <dd>
                  {cases.length === 0 ? (
                    <span className="note">None: this skill sits outside the addition and subtraction taxonomy.</span>
                  ) : (
                    <ul aria-label="Taxonomy cases on this worksheet" className="grid gap-1">
                      {cases.map((c) => (
                        <li key={c.code}>
                          <Link href={`/worksheets/taxonomy?ch=${c.section.split(".")[0]}`} className="font-mono">
                            {c.code}
                          </Link>{" "}
                          {c.label} <span className="text-basalt/62">· {c.n} of the questions</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </dd>
              </div>
              <div>
                <dt className="label mb-[3px]">Made</dt>
                <dd>{fmtDate(w.created_at)}, from the bank&rsquo;s own checked questions</dd>
              </div>
            </dl>
          </Panel>
        </div>
      </Body>
    </>
  );
}

// Printing is for children, never for a pile: each ticked child gets a copy with its own code, recorded as theirs,
// so the scan of the class reads itself onto each child. The copy prints their name; the code carries none.
function PrintFor({ code, kids }: { code: string; kids: ChildRow[] }) {
  const sections = [...new Set(kids.map((k) => k.section))];
  return (
    <Panel title="Print for children" aside="one copy each, each with its own code">
      <form method="post" action={`/api/worksheet/${code}/for`} target="_blank" className="grid gap-3">
        {sections.map((s) => (
          <fieldset key={s} className="flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
            <legend className="label mb-1">{s}</legend>
            {kids
              .filter((k) => k.section === s)
              .map((k) => (
                <label key={k.id} className="inline-flex items-center gap-1">
                  <input type="checkbox" name="child" value={k.id} /> {k.roll_no} · {k.first_name}
                </label>
              ))}
          </fieldset>
        ))}
        <button type="submit" className="btn justify-self-start">
          Print for the children ticked (PDF)
        </button>
      </form>
    </Panel>
  );
}
