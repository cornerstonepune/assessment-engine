import { Panel } from "@/components/shell";
import type { Scan } from "@/lib/queries-scans";
import { readScan } from "./actions";
import { ScansTable } from "./scans-table";
import { UploadScans } from "./upload-scans";

// Scans in (N8): put in from this page, or by a Drive link the engine fetches. Either way the engine reads the file after
// it has answered, so the notice says it has started; the papers appear above as they are read. What the engine would
// not take, in its own words. Under it, the last files read, what each held and came to, and what each lacks: a page
// with no code, a page not in the file, a page in it twice, a copy not read (goals/l11-a-scan-is-read-whole.yaml).
export function ReadScan({ from, read, why, pages, scans = [] }: { from: "/papers" | "/capture"; read?: string; why?: string; pages?: string; scans?: Scan[] }) {
  const said = {
    started: `Reading ${Number(pages) || ""} pages. The papers appear here as they are read — a minute or two.`,
    refused: `The engine would not take that: ${why ?? ""}`,
    "not-a-link": "Paste the link to the scan on Google Drive (drive.google.com/…).",
    engine: "The engine is not answering; nothing was read.",
    given: `Page ${Number(pages) || ""} is being read now as the paper of the child you gave it to.`,
    again: `Reading ${Number(pages) || ""} pages again. Answers a person has checked stay as they left them; the rest are read anew — a minute or two.`,
  }[read ?? ""];
  return (
    <Panel title="Read a scan" label="Read a scan" id="read-scan">
      <UploadScans reading={scans.some((s) => s.status === "running")} />
      <p className="mb-1 text-[13px] text-ink-soft">Or paste the link to a scan on Google Drive:</p>
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
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code, or a page whose code cannot be read, is listed, never guessed."}
      </p>
      {scans.length ? (
        <div className="mt-3 border-t border-line pt-3">
          <ScansTable scans={scans} from={from} />
        </div>
      ) : null}
    </Panel>
  );
}
