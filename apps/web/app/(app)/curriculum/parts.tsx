import Link from "@/components/link";
import { Icon, type IconName } from "@/lib/icons";
import { SLOT_WORDS, type PagePart } from "@/lib/curriculum-screens";
import { answerPart, editPart } from "./actions";

const ORIGIN: Record<string, [IconName, string]> = {
  school: ["from-school", "The school's words"],
  drafted: ["from-draft", "Drafted, check me"],
  person: ["from-person", "Kept by a person"],
};

/** Where a part's words came from: an icon and a word, never colour alone. */
export function Origin({ part }: { part: PagePart }) {
  const [icon, words] = ORIGIN[part.source] ?? ORIGIN.school;
  return (
    <span className="cs-origin" data-source={part.source}>
      <Icon name={icon} size={16} /> {words}
    </span>
  );
}

/** The words of a part: steps as a short list, thinking as the idea and each slip's keyword with how to spot it. */
export function Words({ part }: { part: PagePart }) {
  if (!part.text) return <p className="cs-note">Nothing written yet.</p>;
  if (part.kind === "bullets")
    return (
      <ul className="cs-steps">
        {part.items.map((x) => (
          <li key={x}>{x}</li>
        ))}
      </ul>
    );
  if (part.kind === "thinking" && part.idea !== null)
    return (
      <>
        <p>{part.idea}</p>
        {part.slips.map((s) => (
          <div className="cs-slip" key={s.keyword}>
            <mark>{s.keyword}</mark>
            <small>How to spot it: {s.spot}</small>
          </div>
        ))}
      </>
    );
  return <p>{part.text}</p>;
}

function EditForm({ part, code, back }: { part: PagePart; code: string; back: string }) {
  const slips = [0, 1, 2, 3].map((i) => part.slips[i] ?? { keyword: "", spot: "" });
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
export function PartCard({ part, code, back, editHref, editing }: { part: PagePart; code: string; back: string; editHref: string; editing: boolean }) {
  const drafted = part.source === "drafted";
  return (
    <section className="cs-card" data-card={part.part} data-source={part.source || "empty"}>
      <header>
        <h2>{SLOT_WORDS[part.part]}</h2>
        {part.source ? <Origin part={part} /> : <span className="cs-note">Empty</span>}
      </header>
      {drafted && editing ? <EditForm part={part} code={code} back={back} /> : <Words part={part} />}
      {drafted && !editing ? (
        <div className="cs-actions">
          <form action={answerPart}>
            <input type="hidden" name="code" value={code} />
            <input type="hidden" name="part" value={part.part} />
            <input type="hidden" name="back" value={back} />
            <input type="hidden" name="do" value="keep" />
            <button className="cs-btn" data-main type="submit"><Icon name="confirm" size={16} /> Keep</button>
          </form>
          <Link href={editHref} className="cs-btn"><Icon name="correct" size={16} /> Edit</Link>
          <form action={answerPart}>
            <input type="hidden" name="code" value={code} />
            <input type="hidden" name="part" value={part.part} />
            <input type="hidden" name="back" value={back} />
            <input type="hidden" name="do" value="send-back" />
            <button className="cs-btn" type="submit"><Icon name="send-back" size={16} /> Send back</button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
