import Link from "next/link";
import { notFound } from "next/navigation";
import { Body, PageHeader, Panel, Pill } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import {
  RULE_WORDS,
  childHeader,
  childMap,
  childNext,
  childPapers,
  misconceptionNames,
  pendingResults,
} from "@/lib/queries";
import { confirmChild, resolveOne } from "../actions";
import { ChildGrowthGraph } from "./ChildGrowthGraph";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | undefined>> };

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : "—";

export default async function ChildPage({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const q = await searchParams;
  const [child, map, next, pending, papers, names] = await Promise.all([
    childHeader(id, me.email),
    childMap(id),
    childNext(id),
    pendingResults(id),
    childPapers(id),
    misconceptionNames(),
  ]);
  if (!child) notFound();

  const machine = pending.filter((p) => ["correct", "wrong", "blank"].includes(p.status));
  const person = pending.filter((p) => !["correct", "wrong", "blank"].includes(p.status));
  const withEvidence = map.filter((r) => r.n_events > 0);

  return (
    <>
      <PageHeader
        stage={`Stage 4 · Understand · ${child.section}`}
        title={child.first_name}
        sub={`Roll ${child.roll_no} · band ${child.band} · ${child.n_events} confirmed answers over ${papers.length} paper${papers.length === 1 ? "" : "s"}.`}
      />
      <Body>
        <p className="mb-4">
          <Link href="/growth" className="chip">
            ← All children
          </Link>
        </p>
        {q.confirmed ? <Notice tone="neem">Confirmed {q.confirmed} answers. The map below is rebuilt from them.</Notice> : null}
        {q.resolved ? <Notice tone="neem">Settled. The map is rebuilt.</Notice> : null}
        {q.error === "resolve" ? <Notice tone="terracotta">Pick correct, wrong or blank. Nothing was changed.</Notice> : null}

        <ChildGrowthGraph rungs={map} />

        {person.length > 0 ? (
              <Panel title="Needs a person" aside={`${person.length} answer${person.length === 1 ? "" : "s"} the marker could not settle`}>
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Paper</th>
                      <th>Item</th>
                      <th>Question</th>
                      <th>Read</th>
                      <th>Why</th>
                      <th>Settle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {person.map((p) => (
                      <tr key={p.id}>
                        <td className="fact">{fmtDate(p.date)}</td>
                        <td className="fact">{p.item_key.split("/").pop()}</td>
                        <td className="max-w-[260px] text-[13px]">{p.question}</td>
                        <td className="text-[13px]">
                          {p.read ? <span className="fact">{p.read}</span> : <span className="text-basalt/45">nothing</span>}
                          {p.working ? <div className="text-[12px] text-basalt/55">{p.working}</div> : null}
                        </td>
                        <td className="text-[12px] text-basalt/62">
                          {p.status === "needs_teacher" ? "not a number the marker can check" : "could not be read"}
                        </td>
                        <td>
                          <form action={resolveOne} className="flex flex-wrap gap-1">
                            <input type="hidden" name="result_id" value={p.id} />
                            <input type="hidden" name="child_id" value={id} />
                            {["correct", "wrong", "blank"].map((s) => (
                              <button key={s} className="btn secondary !px-2 !py-1 text-[12px]" name="status" value={s} type="submit">
                                {s}
                              </button>
                            ))}
                          </form>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Panel>
            ) : null}

            {machine.length > 0 ? (
              <Panel title="Marked by lookup, not yet confirmed" aside={`${machine.length} answers`}>
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Paper</th>
                      <th>Item</th>
                      <th>Question</th>
                      <th className="text-right">Read</th>
                      <th className="text-right">Key</th>
                      <th>Marked</th>
                      <th>Mistake matched</th>
                    </tr>
                  </thead>
                  <tbody>
                    {machine.map((p) => (
                      <tr key={p.id}>
                        <td className="fact">{fmtDate(p.date)}</td>
                        <td className="fact">{p.item_key.split("/").pop()}</td>
                        <td className="max-w-[260px] text-[13px]">{p.question}</td>
                        <td className="num">{p.read || "—"}</td>
                        <td className="num">{p.answer ?? "—"}</td>
                        <td>
                          <Pill tone={p.status === "correct" ? "neem" : p.status === "wrong" ? "terracotta" : "monsoon"}>
                            {p.status}
                            {p.status === "wrong" && p.working !== "" ? " · with working" : ""}
                          </Pill>
                        </td>
                        <td className="text-[13px]">{p.misconception_codes.map((c) => names[c] ?? c).join("; ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <form action={confirmChild} className="mt-4">
                  <input type="hidden" name="child_id" value={id} />
                  <button className="btn" type="submit">
                    Confirm these {machine.length} answers as {me.name}
                  </button>
                  <p className="note mt-2">
                    Confirming records each answer as evidence in your name and rebuilds the map. Evidence is never edited
                    afterwards; a correction is a new row.
                  </p>
                </form>
              </Panel>
            ) : null}

        <Panel title="Next step, per skill set">
          <table className="grid">
            <tbody>
              {next.map((n) => (
                <tr key={n.code}>
                  <td>
                    <div className="fact">{n.code}</div>
                    <div className="text-[12px] text-basalt/62">{n.rung_code}</div>
                  </td>
                  <td>
                    <div>{n.difficulty ? <Pill tone={n.rule === "from_state" ? "neem" : "monsoon"}>{n.difficulty}</Pill> : <Pill tone="monsoon">band default</Pill>}</div>
                    <div className="mt-1 text-[12px] text-basalt/62">{RULE_WORDS[n.rule] ?? n.rule}</div>
                    {n.targets.length ? (
                      <div className="mt-1 text-[12px]">aim at: {n.targets.map((t) => names[t] ?? t).join("; ")}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note mt-3">
            80 % right on the set&rsquo;s rung steps the difficulty up; under 50 % steps it down and names the mistake
            to aim at; between, hold. Under three confirmed answers falls back to the band default.
          </p>
        </Panel>

        <Panel title="Papers" aside={`${papers.length}`}>
          {papers.length === 0 ? (
            <p className="note">No paper has been read for this child yet.</p>
          ) : (
            <ul className="grid gap-3">
              {papers.map((p) => (
                <li key={p.id} className="text-[13px]">
                  <div className="fact">{fmtDate(p.date)}</div>
                  <div>{p.title}</div>
                  <div className="text-[12px] text-basalt/62">
                    {p.pages} page{p.pages === 1 ? "" : "s"} · {p.n_confirmed} of {p.n_results} answers confirmed
                    {p.status !== "processed" ? ` · ${p.status}` : ""}
                  </div>
                  {p.narrative ? <p className="mt-1 text-[13px] italic text-basalt/75">{p.narrative}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </Body>
    </>
  );
}

function Notice({ tone, children }: { tone: "neem" | "terracotta"; children: React.ReactNode }) {
  return (
    <p
      className={`mb-4 border p-3 text-[13.5px] ${
        tone === "neem" ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"
      }`}
      role="status"
    >
      {children}
    </p>
  );
}
