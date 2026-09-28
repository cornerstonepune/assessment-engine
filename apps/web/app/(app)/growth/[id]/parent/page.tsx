// The parent report (goals/w4c-parent-report.yaml): the end of the loop. The educator has it written from the child's
// signed-off answers, reads it, and approves it in their own name; until then it is marked a draft. A report written
// before answers were signed off since says so, and is written again rather than approved.
import Link from "@/components/link";
import { notFound } from "next/navigation";
import { Body, Notice, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { EngineDown, engineGet } from "@/lib/engine";
import { childHeader, staffList } from "@/lib/queries";
import { approveParentReport, writeParentReport } from "../../actions";
import { PrintButton } from "../report/print-button";
import { Letter, type Note } from "./letter";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};
type Got = { note: Note | null; ready: boolean };

const WHY: Record<string, string> = {
  "422":
    "The draft said something its facts do not hold, twice, so it was not kept. Write it again.",
  "409":
    "Nothing to do: no answer has been signed off yet, or this report was already approved.",
  "503":
    "The writer could not be reached, or today's budget for it is spent. Nothing was changed.",
  down: "The engine is not answering. Nothing was changed.",
};

async function newest(id: string): Promise<Got | string> {
  try {
    const r = await engineGet(`/child/${id}/parent-report`);
    return r.ok
      ? ((await r.json()) as Got)
      : `The engine could not find the report (${r.status}).`;
  } catch (e) {
    return e instanceof EngineDown
      ? e.message
      : "The engine could not find the report.";
  }
}

export default async function ParentReport({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const q = await searchParams;
  const [child, got, staff] = await deadline(
    Promise.all([childHeader(id, me.email), newest(id), staffList()]),
  );
  if (!child) notFound();
  const name = child.first_name;
  const note = typeof got === "string" ? null : got.note;
  const approver = note?.approved_by
    ? (staff.find((s) => s.email === note.approved_by)?.name ?? null)
    : null;

  return (
    <>
      <div className="print:hidden">
        <PageHeader
          stage={`Parent report · ${child.section}`}
          title={name}
          sub="Written from the answers an educator signed off, held to them by the engine, and approved by an educator before a parent reads it."
        />
      </div>
      <Body>
        <div className="mb-4 flex flex-wrap items-center gap-2 print:hidden">
          <Link href={`/growth/${id}`} className="chip">
            ← {name}&apos;s page
          </Link>
          <Link href={`/growth/${id}/report`} className="chip">
            Report card
          </Link>
          {typeof got !== "string" && got.ready ? (
            <form action={writeParentReport}>
              <input type="hidden" name="child_id" value={id} />
              <button type="submit" className="chip cursor-pointer">
                {note ? "Write it again" : "Write the report"}
              </button>
            </form>
          ) : null}
          {note && !note.approved_by && !note.stale ? (
            <form action={approveParentReport}>
              <input type="hidden" name="child_id" value={id} />
              <input type="hidden" name="note_id" value={note.id} />
              <button
                type="submit"
                className="chip cursor-pointer !border-neem !bg-neem !text-chalk"
              >
                Approve for {name}&apos;s parents
              </button>
            </form>
          ) : null}
          {note ? <PrintButton /> : null}
        </div>
        <div className="print:hidden">
          {typeof got === "string" ? (
            <Notice tone="terracotta">{got}</Notice>
          ) : null}
          {typeof got !== "string" && !got.ready ? (
            <Notice tone="terracotta">
              The report&apos;s writer has not passed its check yet (engine eval
              parent_report), so nothing can be written until it does.
            </Notice>
          ) : null}
          {q.error ? (
            <Notice tone="terracotta">
              {WHY[q.error] ?? `The engine said no (${q.error}).`}
            </Notice>
          ) : null}
          {q.written ? (
            <Notice tone="neem">
              Written and checked against {name}&apos;s answers. Read it, then
              approve it.
            </Notice>
          ) : null}
          {q.approved ? (
            <Notice tone="neem">
              Approved in your name. It is ready for {name}&apos;s parents.
            </Notice>
          ) : null}
          {note?.stale ? (
            <Notice tone="terracotta">
              Answers of {name}&apos;s have been signed off since this was
              written, so it is out of date. Write it again before approving.
            </Notice>
          ) : null}
        </div>
        {note ? (
          <Letter
            note={note}
            name={name}
            section={child.section}
            approver={approver}
          />
        ) : typeof got !== "string" ? (
          <p className="text-[14px] text-basalt/70">
            No report has been written for {name} yet.
          </p>
        ) : null}
      </Body>
    </>
  );
}
