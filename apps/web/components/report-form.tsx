"use client";

import { useActionState, useState } from "react";
import { submitNote, type Said } from "@/lib/feedback-actions";
import { HOW_OFTEN, KINDS, WARNING } from "@/lib/feedback-words";

// The form of "Report a problem or suggest something" (goals/feed_report_from_the_tool.yaml). A client component only so
// the words stay in the boxes when a note is refused, and the boxes empty once it is kept. React empties a form once its
// action has run, so each answer opens the form afresh (`key`) holding what came back.
export function ReportForm({ from, maxChars }: { from: string; maxChars: number }) {
  const [said, action, pending] = useActionState<Said, FormData>(submitNote, null);
  const [kind, setKind] = useState<string>("bug");
  const kept = said?.kept ?? {};
  return (
    <form action={action} key={JSON.stringify(said)} className="grid max-w-[620px] gap-4">
      {said ? (
        <p role="status" className={`border p-3 text-[13.5px] ${said.ok ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"}`}>
          {said.words}
        </p>
      ) : null}
      <input type="hidden" name="from" value={from} />
      <fieldset className="field">
        <legend className="label">What kind?</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[14px]">
          {Object.entries(KINDS).map(([k, v]) => (
            <label key={k} className="inline-flex min-h-11 items-center gap-2">
              <input type="radio" name="kind" value={k} checked={kind === k} onChange={() => setKind(k)} />
              {v.words}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="field">
        <span className="label">What were you doing?</span>
        <textarea className="input min-h-20" name="doing" maxLength={maxChars} required defaultValue={kept.doing} />
      </label>
      <label className="field">
        <span className="label">What did you expect, and what happened?</span>
        <textarea className="input min-h-28" name="happened" maxLength={maxChars} required defaultValue={kept.happened} aria-describedby="report-warning" />
      </label>
      <p id="report-warning" className="note -mt-2">
        {WARNING}
      </p>
      {kind === "bug" ? (
        <label className="field max-w-[260px]">
          <span className="label">How often? (if you know)</span>
          <select className="input" name="how_often" defaultValue={kept.how_often ?? ""}>
            <option value="">Not sure</option>
            {HOW_OFTEN.map((h) => (
              <option key={h} value={h}>
                {h[0].toUpperCase() + h.slice(1)}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <p className="note -mt-2">The page you came from and the time are added for you.</p>
      <button className="btn justify-self-start" type="submit" disabled={pending}>
        {pending ? "Sending…" : "Send"}
      </button>
    </form>
  );
}
