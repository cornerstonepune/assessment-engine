import Link from "@/components/link";
import { Body, PageHeader, Panel, Pill, Tile } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { HANDOVERS, SHARED, STEPS, WORKFLOWS, handsOnTo, measures, type Measure, type Step } from "@/lib/workflows";

// Nimish, 2026-09-22: "a frontend representation … that shows each of the steps as a proper workflow,
// what is working, and how things are connected." Drawn from `workflows.json`, the map the engine's code
// is held to by `tests/test_layout.py`, with each step's live number from the database.
const BUILT: Record<Step["built"], { tone: "neem" | "bamboo" | "monsoon"; words: string }> = {
  live: { tone: "neem", words: "working" },
  partly: { tone: "bamboo", words: "partly built" },
  "not built": { tone: "monsoon", words: "not built yet" },
};
const byNumber = (a: Step, b: Step) => Number(a.code.slice(1)) - Number(b.code.slice(1));
const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }).replace(/ /g, "-") : null;

export default async function HowItWorks() {
  await requireStaff();
  const live = await deadline(measures());
  const count = (b: Step["built"]) => STEPS.filter((s) => s.built === b).length;

  return (
    <>
      <PageHeader
        stage="The engine"
        title="How it works"
        sub="The twelve steps agreed with the school, as four workflows: what each step does, what it hands to the next, what it has produced so far, and whether it works for any subject or only maths."
      />
      <Body>
        <div className="mb-[18px] grid grid-cols-2 gap-[10px] md:grid-cols-4">
          <Tile tone="neem" n={count("live")} words="steps working" />
          <Tile tone="bamboo" n={count("partly")} words="steps partly built" />
          <Tile tone="monsoon" n={count("not built")} words="steps not built yet" />
          <Tile tone="terracotta" n={STEPS.filter((s) => !s.subject.any).length} words="steps that are maths only today" />
        </div>

        <div className="grid min-w-0 gap-[18px]">
          {WORKFLOWS.map((w) => (
            <section key={w.code} aria-labelledby={`wf-${w.code}`} className="grid gap-[10px]">
              <div>
                <h2 id={`wf-${w.code}`} className="text-[18px]">
                  {w.code} · {w.name}
                </h2>
                <p className="text-[14px] text-basalt/75">
                  {w.does} <span className="fact text-[12px] text-basalt/55">{w.folder ?? "no code yet"}</span>
                </p>
              </div>
              <div className="grid gap-[12px] lg:grid-cols-2">
                {STEPS.filter((s) => s.workflow === w.code)
                  .sort(byNumber)
                  .map((s) => (
                    <StepCard key={s.code} s={s} m={live[s.code]} />
                  ))}
              </div>
            </section>
          ))}

          <Panel title="What every workflow stands on" aside="shared, not a step">
            <ul className="grid gap-2 text-[13.5px]">
              {SHARED.map((p) => (
                <li key={p.code}>
                  <b>{p.name}</b> <span className="fact text-[12px] text-basalt/55">{p.folder}</span> — {p.does}
                  {!p.subject.any ? <span className="text-basalt/70"> Maths only: {p.subject.note}</span> : null}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="How the code connects" aside={`${HANDOVERS.length} connections, each checked`}>
            <p className="note mb-3">
              A workflow reaches another only through one of these. Any other connection fails the engine&rsquo;s layout check before it can be merged.
            </p>
            <ul className="grid gap-2 text-[13.5px]">
              {HANDOVERS.map((h) => (
                <li key={`${h.from}-${h.to}`}>
                  <span className="fact text-[12px]">{h.from}</span> → <span className="fact text-[12px]">{h.to}</span>: {h.why}
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </Body>
    </>
  );
}

function StepCard({ s, m }: { s: Step; m: Measure | undefined }) {
  const next = handsOnTo(s);
  const built = BUILT[s.built];
  return (
    <article id={s.code} aria-labelledby={`step-${s.code}`} className="panel scroll-mt-6 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="label">{s.code}</span>
        <h3 id={`step-${s.code}`} className="text-[16px]">
          {s.name}
        </h3>
        <Pill tone={built.tone}>{built.words}</Pill>
        <Pill tone={s.subject.any ? "neem" : "bamboo"}>{s.subject.any ? "any subject" : "maths only"}</Pill>
      </div>
      <p className="mt-2 text-[14px] leading-snug">{s.does}</p>
      <p className="mt-1 text-[12.5px] text-basalt/65">Who: {s.who}</p>
      {m ? (
        <p className="mt-3 text-[14px]" data-measure={s.code}>
          <span className="font-heading text-[22px]">{m.n.toLocaleString("en-IN")}</span> {m.words}
          {fmtDate(m.when) ? <span className="text-basalt/55"> · last {fmtDate(m.when)}</span> : null}
        </p>
      ) : (
        <p className="mt-3 text-[13px] text-basalt/55">Nothing to count yet.</p>
      )}
      <p className="mt-2 text-[12.5px] text-basalt/75">
        Takes <span className="fact">{s.takes.join(", ")}</span> · gives <span className="fact">{s.gives.join(", ")}</span>
      </p>
      {next.length ? (
        <p className="mt-1 text-[12.5px]">
          Hands on to{" "}
          {next.map((n, i) => (
            <span key={n.code}>
              {i ? ", " : ""}
              <a href={`#${n.code}`}>
                {n.code} {n.name}
              </a>
            </span>
          ))}
        </p>
      ) : null}
      {!s.subject.any || s.built !== "live" ? <p className="mt-2 text-[12.5px] text-basalt/70">{s.subject.note}</p> : null}
      {s.files.length || s.commands.length || s.screens.length ? (
        <details className="mt-3 text-[12.5px]">
          <summary className="cursor-pointer text-basalt/75">Files, commands and screens</summary>
          <ul className="mt-2 grid gap-1">
            {s.files.map((f) => (
              <li key={f} className="fact">
                packages/engine/{f}
              </li>
            ))}
            {s.commands.map((c) => (
              <li key={c} className="fact">
                {c}
              </li>
            ))}
            {s.screens
              .filter((sc) => !sc.includes("[") && !sc.startsWith("/api/"))
              .map((sc) => (
                <li key={sc}>
                  <Link href={sc}>{sc}</Link>
                </li>
              ))}
          </ul>
        </details>
      ) : null}
    </article>
  );
}
