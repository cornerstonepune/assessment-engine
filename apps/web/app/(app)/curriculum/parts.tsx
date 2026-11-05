import Link from "@/components/link";
import { PartView } from "@/components/page-part/part";
import { Icon } from "@/lib/icons";
import { slipsMax } from "@/lib/curriculum-screens";
import type { PagePart } from "@/lib/page-part";
import { answerPart, editPart } from "./actions";

async function EditForm({ part, code, back }: { part: PagePart; code: string; back: string }) {
  const room = Math.max(await slipsMax(), part.slips.length);
  const slips = Array.from({ length: room }, (_, i) => part.slips[i] ?? { keyword: "", spot: "" });
  return (
    <form action={editPart}>
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="part" value={part.part} />
      <input type="hidden" name="back" value={back} />
      {part.part === "thinking" ? (
        <>
          <label htmlFor="idea">The idea, in one line</label>
          <input id="idea" type="text" name="idea" defaultValue={part.idea ?? part.text.split("\n")[0]} />
          {slips.map((s, i) => (
            <div key={i} className="cs-grid">
              <div className="cs-col-4">
                <label htmlFor={`keyword${i}`}>Slip {i + 1}, the keyword</label>
                <input id={`keyword${i}`} type="text" name={`keyword${i}`} defaultValue={s.keyword} />
              </div>
              <div className="cs-col-8">
                <label htmlFor={`spot${i}`}>How to spot it</label>
                <input id={`spot${i}`} type="text" name={`spot${i}`} defaultValue={s.spot} />
              </div>
            </div>
          ))}
        </>
      ) : (
        <>
          <label htmlFor="words">{part.part === "steps" ? "One step on each line" : "Words"}</label>
          <textarea id="words" name="words" rows={part.part === "steps" ? 6 : 3} defaultValue={part.part === "steps" ? part.items.join("\n") : part.text} />
        </>
      )}
      <div className="cs-actions">
        <button className="cs-btn" data-main type="submit">
          <Icon name="confirm" size={16} /> Save
        </button>
        <Link href={back} className="cs-btn">Cancel</Link>
      </div>
    </form>
  );
}

/** One part of a page. A drafted part carries Keep, Edit and Send back; `editing` swaps the words for the editor. */
export function PartCard({ part, code, back, editHref, editing, readOnly }: { part: PagePart; code: string; back: string; editHref: string; editing: boolean; readOnly?: boolean }) {
  if (part.source !== "drafted" || readOnly) return <PartView part={part} />;
  if (editing) return <PartView part={part} editor={<EditForm part={part} code={code} back={back} />} />;
  return (
    <PartView
      part={part}
      actions={
        <form action={answerPart} className="cs-actions">
          <input type="hidden" name="code" value={code} />
          <input type="hidden" name="part" value={part.part} />
          <input type="hidden" name="back" value={back} />
          <button className="cs-btn" data-main type="submit" name="do" value="keep"><Icon name="confirm" size={16} /> Keep</button>
          <Link href={editHref} className="cs-btn"><Icon name="correct" size={16} /> Edit</Link>
          <button className="cs-btn" type="submit" name="do" value="send-back"><Icon name="send-back" size={16} /> Send back</button>
        </form>
      }
    />
  );
}
