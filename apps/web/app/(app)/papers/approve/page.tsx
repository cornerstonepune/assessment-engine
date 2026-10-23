import { FilterBar } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { Body, NotYet, PageHeader } from "@/components/shell";
import type { State } from "@/components/status-chip";
import { tableCounts } from "@/lib/queries";
import { spareSheets, unplanned, weekPlan, weeks, type WeekRow } from "@/lib/queries-approve";
import { approvePack } from "./actions";
import { byNeed, PackTable, reasonOf, type PackRow } from "./pack-table";
import { deadline } from "@/lib/deadline";
import { requireStaff } from "@/lib/auth";
import { isMine, reachOf, scopeOf } from "@/lib/scope";
import { weekWords } from "@/lib/week";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Class papers to approve (goals/ui3-curriculum.yaml, goals/ux5-papers-grouped.yaml): a class's week, each child by name
// with the level they are set and why and the paper they were handed, a level changed with its reason; every child of the
// class with no paper, and why; the pack approved and printed in one tap that says what it approves. It is Assessments'
// work; it sat under the worksheet library until 2026-10-11, where Today's "Class papers to approve" opened the
// Curriculum tab.
export default async function ApprovePage({ searchParams }: Props) {
  const me = await requireStaff();
  const scope = scopeOf(me);
  const q = await searchParams;
  // a class asked for by name is listed whoever asks: every class is every member of staff's (goals/ux9c-one-role.yaml)
  const all = await deadline(weeks(q.section ? reachOf(me) : scope));
  // a link to a class's week that is not on the list (another educator's class, or a week with nothing made) says so,
  // rather than opening another class's week unannounced (goals/ux8a-numbers-true.yaml)
  const asked = q.section && q.week && q.kind ? { section: q.section, week: q.week, kind: q.kind } : null;
  const notListed =
    asked && !all.some((w) => w.section === asked.section && w.week === asked.week && w.kind === asked.kind)
      ? `${asked.section} · ${weekWords(asked.week)} · ${asked.kind}: ${
          isMine(reachOf(me), asked.section) ? "no papers have been made for it" : "not one of your classes"
        }.`
      : null;

  if (all.length === 0) {
    const c = await deadline(tableCounts());
    return (
      <>
        <PageHeader stage="Papers to approve" title="Papers to approve" sub="A class's week: each child's paper, the level it is set at and why. Change any child, then approve the pack to print it." />
        <Body>
          {notListed ? <Notice tone="terracotta">{notListed}</Notice> : null}
          <NotYet
            what={[
              "One row per child: the level they are set, and the reason it was chosen.",
              "The pack in handout order: a named paper for each child, spares, one teacher key.",
              "Change one child's level, or approve the whole pack with one tap.",
            ]}
            when="Nothing has been planned for a week yet. A coordinator runs the week from the engine, then it appears here."
            facts={[
              ["children on roll", c.child],
              ["papers made", c.sheet_instance],
              ["weeks planned", 0],
            ]}
          />
        </Body>
      </>
    );
  }

  const current = all.find((w) => w.section === q.section && w.week === q.week && w.kind === q.kind) ?? all[0];
  const [rows, spares, missing] = await deadline(Promise.all([
    weekPlan(current.section, current.week, current.kind, me.email),
    spareSheets(current.section, current.week, current.kind),
    unplanned(current.section, current.week, current.kind, me.email),
  ]));
  const here = `/papers/approve?section=${current.section}&week=${current.week}&kind=${current.kind}`;
  // the children handed a paper; those with none are named in the same table, with why
  const plan = rows.filter((r) => r.qr_code);
  // what one tap approves: the pack's papers still waiting for a person, its spares among them
  const waiting = plan.filter((r) => r.print_status === "new").length;
  const sparesWaiting = spares.filter((s) => s.print_status === "new").length;
  const toApprove = waiting + sparesWaiting;
  const counts = plan.reduce<Record<string, number>>(
    (a, r) => ({ ...a, [r.difficulty]: (a[r.difficulty] ?? 0) + 1 }),
    {},
  );
  const paperState = (status: string | null): State => (status === "printed" ? "done" : "toApprove");
  const pack: PackRow[] = [
    ...plan.map((r) => ({
      key: r.child_id, roll: r.roll_no, who: r.first_name, level: r.difficulty, why: reasonOf(r), qr: r.qr_code,
      worksheet: r.worksheet, state: paperState(r.print_status), prescription: r.prescription_id, difficulty: r.difficulty,
    })),
    ...rows.filter((r) => !r.qr_code).map((r) => ({
      key: r.child_id, roll: r.roll_no, who: r.first_name, level: r.difficulty, why: noPaper(r), qr: null,
      worksheet: null, state: "noPaper" as State, prescription: null, difficulty: null,
    })),
    ...missing.map((c) => ({
      key: c.child_id, roll: c.roll_no, who: c.first_name, level: null,
      why: c.later ? "joined the class after this week was planned" : "not on this week's plan",
      qr: null, worksheet: null, state: "noPaper" as State, prescription: null, difficulty: null,
    })),
    ...spares.map((s) => ({
      key: s.qr_code, roll: "", who: "Spare copy", level: s.difficulty,
      why: "An extra paper with no name on it, for a spoilt page or a child who arrives late.", qr: s.qr_code,
      worksheet: s.worksheet, state: paperState(s.print_status), prescription: null, difficulty: null,
    })),
  ];
  const stage = q.status && q.status in STAGE ? q.status : undefined;
  const shown = pack.filter((r) => !stage || r.state === STAGE[stage]).sort(byNeed);
  const classes = [...new Set(all.map((w) => w.section))];
  const weeksOf = [...new Set(all.map((w) => w.week))];
  const kinds = [...new Set(all.map((w) => w.kind))];
  const page = Math.max(1, Math.floor(Number(q.page)) || 1);
  const pageHref = (n: number) => `${here}${stage ? `&status=${stage}` : ""}&page=${n}`;

  return (
    <PageShell
      stage="Papers to approve"
      title="Papers to approve"
      purpose="A class's week: each child's paper, the level it is set at and why. Change any child, then approve the pack to print it."
      action={
        <form action={approvePack}>
          <input type="hidden" name="section" value={current.section} />
          <input type="hidden" name="week" value={current.week} />
          <input type="hidden" name="kind" value={current.kind} />
          <input type="hidden" name="back" value={here} />
          <button className="btn" type="submit" disabled={toApprove === 0}>
            {toApprove === 0 ? "Nothing left to approve" : approveWords(waiting, sparesWaiting)}
          </button>
        </form>
      }
      next={{ href: "/papers", label: "Assessments: print and give" }}
    >
      {notListed ? (
        <Notice tone="terracotta">
          {notListed} Showing {current.section} · {weekWords(current.week)} · {current.kind} instead.
        </Notice>
      ) : null}
      {q.approved ? <Notice tone="neem">Approved. The pack is marked printed.</Notice> : null}
      {q.changed ? <Notice tone="neem">Changed. That child keeps this level until you change it again.</Notice> : null}
      {q.error === "override" ? <Notice tone="terracotta">A change needs a level and a reason. Nothing was changed.</Notice> : null}

      <p className="note mb-3" aria-label="This pack">
        {rows[0]?.skill_set_name ? `Everyone is working on ${rows[0].skill_set_name.toLowerCase()}. ` : ""}
        What changes per child is how hard their paper is.
        {Object.keys(counts).length ? ` ${Object.entries(counts).map(([d, n]) => `${n} at ${d}`).join(" · ")}.` : ""}
        {toApprove === 0 && plan.length > 0 ? " This pack is approved and marked printed." : ""}
      </p>

      <FilterBar
        action="/papers/approve"
        keep={{}}
        filters={[
          { name: "section", label: "Class", value: current.section, all: "First class", options: classes.map((c) => [c, c] as const) },
          { name: "week", label: "Week", value: current.week, all: "Latest week", options: weeksOf.map((w) => [w, weekWords(w)] as const) },
          { name: "kind", label: "Kind", value: current.kind, all: "Any kind", options: kinds.map((k) => [k, k] as const) },
          { name: "status", label: "Status", value: stage, all: "Any status", options: Object.keys(STAGE).map((k) => [k, STAGE_WORDS[k]] as const) },
        ]}
      />
      <section aria-label="This week's pack">
        <PackTable rows={shown} back={here} page={page} pageHref={pageHref} />
        {shown.length === 0 ? <p className="note mt-2">Nothing matches these filters.</p> : null}
      </section>
    </PageShell>
  );
}

const STAGE: Record<string, State> = { toApprove: "toApprove", approved: "done", noPaper: "noPaper" };
const STAGE_WORDS: Record<string, string> = { toApprove: "To approve", approved: "Approved", noPaper: "No paper" };

/** What one tap approves, the children's papers and the spares apart: Today counts the children's (goals/ux2). */
const approveWords = (papers: number, spares: number) =>
  `Approve ${[papers && `${papers} paper${papers === 1 ? "" : "s"}`, spares && `${spares} spare${spares === 1 ? "" : "s"}`].filter(Boolean).join(" and ")}`;

/** Why a child on the plan has no paper: the reason the week's assembly found, or that it has not run yet. */
const noPaper = (r: WeekRow) => r.no_paper ?? "the class's papers are not made yet";

function Notice({ tone, children }: { tone: "neem" | "terracotta"; children: React.ReactNode }) {
  return (
    <div
      className={`mb-[18px] border p-3 text-[13.5px] ${
        tone === "neem" ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"
      }`}
      role="status"
    >
      {children}
    </div>
  );
}
