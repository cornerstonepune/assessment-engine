// A child's report card (goals/u6-report-card.yaml) — one page for the educator and the child's parents: what every
// answer showed, the skill map, what is going well, what they are working on with their own example, and what happens
// next in class and at home. Only answers an educator signed off count; the card says how many are still waiting.
import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, Notice, PageHeader, Panel, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { EngineDown, engineGet } from "@/lib/engine";
import { childHeader } from "@/lib/queries";
import { around, coverage, skillMap } from "@/lib/queries-report";
import { rag, RAG_TONE, RAG_WORDS } from "@/lib/rag";
import { fmtDate } from "../answers";
import { GoingWell, NextSteps, Signals, WorkingOn, type Report } from "./parts";
import { PrintButton } from "./print-button";
import { MapKey, SkillMap } from "./skill-map";

type Props = { params: Promise<{ id: string }> };

async function report(id: string): Promise<Report | string> {
  try {
    const res = await engineGet(`/report/${id}`);
    return res.ok
      ? ((await res.json()) as Report)
      : `The engine could not make the report (${res.status}).`;
  } catch (e) {
    return e instanceof EngineDown
      ? e.message
      : "The engine could not make the report.";
  }
}

export default async function ReportCard({ params }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const [child, all, cov, rep] = await deadline(
    Promise.all([
      childHeader(id, me.email),
      skillMap(id),
      coverage(id),
      report(id),
    ]),
  );
  if (!child) notFound();
  const nodes = around(all, child.band);
  const name = child.first_name;
  const assessed = nodes.filter((n) => n.state);
  const count = (c: string) =>
    assessed.filter((n) => rag(n.state) === c).length;
  const waiting = cov.answers - cov.signed;
  const [first, last] = [fmtDate(cov.first), fmtDate(cov.last)];
  const when = cov.first
    ? first === last
      ? first
      : `${first} – ${last}`
    : "no signed-off answers yet";

  return (
    <>
      <PageHeader
        stage={`Report card · ${child.section}`}
        title={name}
        sub={`Roll ${child.roll_no} · Grade ${child.band.slice(1)} · Maths · ${when}`}
      />
      <Body>
        <p className="mb-4 flex flex-wrap gap-2 print:hidden">
          <Link href={`/growth/${id}`} className="chip">
            ← {name}&apos;s page
          </Link>
          <PrintButton />
        </p>
        {waiting > 0 ? (
          <Notice tone="terracotta">
            {waiting} of {cov.answers} answers on {name}&apos;s papers still
            wait for an educator; this card counts only the {cov.signed} signed
            off.
          </Notice>
        ) : cov.signed ? (
          <Notice tone="neem">
            Every answer on this card was checked and signed off by an educator:{" "}
            {cov.signed} answers on {cov.papers} paper
            {cov.papers === 1 ? "" : "s"}.
          </Notice>
        ) : null}

        <div
          className="mb-5 grid grid-cols-2 gap-[10px] md:grid-cols-4"
          data-testid="tiles"
        >
          {(["green", "amber", "red", "grey"] as const).map((c) => (
            <Tile
              key={c}
              tone={RAG_TONE[c]}
              n={count(c)}
              words={`skill set${count(c) === 1 ? "" : "s"} · ${c === "grey" ? "too few answers yet" : RAG_WORDS[c]}`}
            />
          ))}
        </div>
        <Signals nodes={nodes} />

        <div className="mb-[18px]">
          <Panel
            title="Skill map"
            label="Skill map panel"
            aside={`${assessed.length} of ${nodes.length} skill sets assessed`}
          >
            <SkillMap nodes={nodes} band={child.band} />
            <MapKey />
          </Panel>
        </div>

        {typeof rep === "string" ? (
          <Notice tone="terracotta">{rep}</Notice>
        ) : (
          <>
            <div className="mb-[18px] grid gap-[18px] md:grid-cols-2 print:break-inside-avoid">
              <Panel title="Going well" label="Going well">
                <GoingWell name={name} report={rep} nodes={nodes} />
              </Panel>
              <Panel title="Working on" label="Working on">
                <WorkingOn name={name} report={rep} />
              </Panel>
            </div>
            <h2 className="mb-3 text-[18px]">What happens next</h2>
            <NextSteps id={id} name={name} report={rep} nodes={nodes} />
          </>
        )}
      </Body>
    </>
  );
}
