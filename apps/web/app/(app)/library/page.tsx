import Link from "next/link";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { DIFFICULTIES, itemFacets, items, misconceptionNames, type ItemRow } from "@/lib/queries";
import { flagItem } from "./actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

const FMT_LABEL: Record<string, string> = {
  column_grid: "column",
  bare_sum: "horizontal",
  missing_number: "missing number",
  word_1step: "word problem",
};

function question(it: ItemRow): string {
  const sp = it.spec;
  if (it.fmt === "word_1step") return it.stem;
  if (it.fmt === "missing_number") return sp.text ?? it.stem;
  return `${sp.a} ${sp.op === "-" ? "−" : sp.op} ${sp.b}`;
}

export default async function LibraryPage({ searchParams }: Props) {
  const q = await searchParams;
  const filter = { set: q.set, difficulty: q.difficulty, fmt: q.fmt, status: q.status };
  const [rows, facets, names] = await Promise.all([items(filter), itemFacets(), misconceptionNames()]);
  const here = "/library?" + new URLSearchParams(Object.entries(q).filter((e): e is [string, string] => !!e[1])).toString();

  const link = (key: string, value?: string) => {
    const p = new URLSearchParams(Object.entries(q).filter((e): e is [string, string] => !!e[1] && e[0] !== key));
    if (value) p.set(key, value);
    const s = p.toString();
    return "/library" + (s ? `?${s}` : "");
  };
  const Chip = ({ k, v, label }: { k: string; v?: string; label: string }) => (
    <Link href={link(k, v)} className={`chip ${(q[k] ?? "") === (v ?? "") ? "on" : ""}`}>
      {label}
    </Link>
  );

  return (
    <>
      <PageHeader
        stage="Stage 2 · The bank"
        title="Question bank"
        sub="Every question that is ready to print, already checked by the computer. Nobody has to approve them. If one looks wrong, remove it here."
      />
      <Body>
        <Panel title="Questions" aside={`${rows.length} shown${rows.length === 200 ? " · first 200" : ""}`}>
          <div className="mb-3 flex flex-wrap gap-2">
            <Chip k="set" label="All sets" />
            {facets.sets.map((s) => (
              <Chip key={s} k="set" v={s} label={s} />
            ))}
          </div>
          <div className="mb-3 flex flex-wrap gap-2">
            <Chip k="difficulty" label="Any difficulty" />
            {DIFFICULTIES.map((d) => (
              <Chip key={d} k="difficulty" v={d} label={d} />
            ))}
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            <Chip k="fmt" label="Any format" />
            {facets.fmts.map((f) => (
              <Chip key={f} k="fmt" v={f} label={FMT_LABEL[f] ?? f} />
            ))}
            <span className="w-3" />
            <Chip k="status" label="Active" />
            <Chip k="status" v="retired" label="Retired" />
          </div>

          {rows.length === 0 ? (
            <p className="note">No questions match these choices. Try a different set or difficulty.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Format</th>
                    <th>Set · band</th>
                    <th className="text-right">Answer</th>
                    <th>Mistakes it can spot · the answer each one gives</th>
                    <th className="text-right">Used</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((it) => {
                    const r = it.responses.find((x) => x.rid === "ans") ?? it.responses[0];
                    const mis = Object.entries(r?.misconceptions ?? {});
                    return (
                      <tr key={it.item_key}>
                        <td className={it.fmt === "word_1step" ? "max-w-[360px]" : "fact"}>{question(it)}</td>
                        <td className="fact">{FMT_LABEL[it.fmt] ?? it.fmt}</td>
                        <td className="fact">
                          {it.skill_set_code} <span className="text-basalt/55">· {it.difficulty}</span>
                        </td>
                        <td className="num">{r?.answer}</td>
                        <td className="max-w-[320px] text-[12px] leading-[1.6]">
                          {mis.slice(0, 3).map(([code, v]) => (
                            <div key={code}>
                              <span className="fact">{v}</span>
                              <span className="text-basalt/62"> · {names[code] ?? code}</span>
                            </div>
                          ))}
                          {mis.length > 3 ? <div className="note">and {mis.length - 3} more</div> : null}
                        </td>
                        <td className="num">{it.times_used}</td>
                        <td>{it.status === "active" ? <Pill tone="neem">active</Pill> : <Pill tone="terracotta">{it.status}</Pill>}</td>
                        <td>
                          {it.status === "active" ? (
                            <details>
                              <summary className="cursor-pointer whitespace-nowrap text-[12.5px] text-terracotta">
                                Something wrong?
                              </summary>
                              <form action={flagItem} className="mt-2 grid w-[220px] gap-2">
                                <input type="hidden" name="item_key" value={it.item_key} />
                                <input type="hidden" name="back" value={here} />
                                <label className="field">
                                  <span className="label">What is wrong with it</span>
                                  <input className="input" name="note" maxLength={300} required />
                                </label>
                                <button className="btn" type="submit">Remove this question</button>
                              </form>
                            </details>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
        <p className="note mt-[14px]">
          A removed question never prints again. Your name and reason are kept with it, so the question writer learns from
          it.
        </p>
      </Body>
    </>
  );
}
