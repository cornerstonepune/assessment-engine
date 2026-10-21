import { Panel } from "@/components/shell";
import type { Scan } from "@/lib/queries-scans";
import { readScan } from "./actions";

// A scan read from its Drive link (N8): the engine fetches the file and reads it after this page has answered, so
// the notice says it has started; the papers appear above as they are read. What the engine would not take, in its
// own words. Under it, the last files read, and what each lacks: a page not in the file, a page in it twice, a copy not
// read (goals/l11-a-scan-is-read-whole.yaml).
export function ReadScan({ from, read, why, pages, scans = [] }: { from: "/papers" | "/capture"; read?: string; why?: string; pages?: string; scans?: Scan[] }) {
  const said = {
    started: `Reading ${Number(pages) || ""} pages. The papers appear here as they are read — a minute or two.`,
    refused: `The engine would not take that: ${why ?? ""}`,
    "not-a-link": "Paste the link to the scan on Google Drive (drive.google.com/…).",
    engine: "The engine is not answering; nothing was read.",
  }[read ?? ""];
  return (
    <Panel title="Read a scan" label="Read a scan" id="read-scan">
      <form action={readScan} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="from" value={from} />
        <input
          type="url"
          name="url"
          required
          placeholder="https://drive.google.com/file/d/…/view"
          aria-label="Link to the scan on Google Drive"
          className="min-w-0 flex-1 rounded border border-line bg-chalk px-3 py-2 text-[14px]"
        />
        <button type="submit" className="btn secondary">
          Read it
        </button>
      </form>
      <p className="mt-2 text-[13px] text-ink-soft">
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code is listed, not guessed."}
      </p>
      {scans.length ? (
        <ul aria-label="Scans read last" className="mt-3 grid gap-2 border-t border-line pt-3 text-[13px]">
          {scans.map((s) => (
            <li key={s.id} className="min-w-0">
              <p>
                <strong>{s.file}</strong> · {s.when} ·{" "}
                {s.status === "running"
                  ? "reading now"
                  : s.status === "error"
                    ? `the reading stopped: ${s.error ?? ""}`
                    : `${s.read} ${s.read === 1 ? "copy" : "copies"} read, ${s.answers} ${s.answers === 1 ? "answer" : "answers"}`}
              </p>
              {s.lines.length ? (
                <ul aria-label={`What ${s.file} lacks`} className="ml-5 mt-1 list-disc text-terracotta">
                  {s.lines.map((l, i) => (
                    <li key={i}>
                      {l.who}: {l.said}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </Panel>
  );
}
