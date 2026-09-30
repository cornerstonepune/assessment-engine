import { Panel } from "@/components/shell";
import { readScan } from "./actions";

// A scan read from its Drive link (N8): the engine fetches the file and reads it after this page has answered, so
// the notice says it has started; the papers appear above as they are read. What the engine would not take, in its
// own words.
export function ReadScan({ from, read, why, pages }: { from: "/papers" | "/capture"; read?: string; why?: string; pages?: string }) {
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
        <button type="submit" className="btn">
          Read it
        </button>
      </form>
      <p className="mt-2 text-[13px] text-ink-soft">
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code is listed, not guessed."}
      </p>
    </Panel>
  );
}
