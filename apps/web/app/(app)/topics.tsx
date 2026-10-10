import { Panel } from "@/components/shell";
import type { Topic } from "@/lib/queries-people";
import { switchTopic } from "./topic-actions";

// Which topics are taught, and who said so (goals/ny1-needs-you.yaml). An educator switches one on or off here, in
// their own name; the rows decide a topic only until a person has. A topic not taught yet lists its skills, so a person
// knows what switching it on brings; one taught is switched off from inside a fold, never by a stray click.
export function Topics({ topics, me }: { topics: Topic[]; me: string }) {
  const off = topics.filter((t) => !t.taught);
  const on = topics.filter((t) => t.taught);
  return (
    <div className="mb-[18px] grid gap-[14px]">
      <Panel title="Not taught yet" label="Not taught yet" id="not-taught" aside={`${off.length} ${off.length === 1 ? "topic" : "topics"}`}>
        {off.length ? (
          <ul className="grid gap-3">
            {off.map((t) => (
              <li key={t.code} className="flex flex-wrap items-center justify-between gap-3">
                <span>
                  <b>{t.name}</b>
                  <span className="block text-[13px] text-basalt/70">{t.skills.join(" · ")}</span>
                  {t.taught_by ? <span className="block text-[12px] text-basalt/55">Switched off by {t.taught_by}</span> : null}
                </span>
                <Switch code={t.code} on label={`Switch on, as ${me}`} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="note">Every topic is taught.</p>
        )}
      </Panel>
      <section aria-label="Taught in this school" id="taught" className="panel">
        <details>
          <summary className="panel-head cursor-pointer">
            <h2 className="text-[16px]">Taught in this school</h2>
            <span className="fact text-[11px] text-basalt/55">
              {on.length} {on.length === 1 ? "topic" : "topics"} · open to switch one off
            </span>
          </summary>
          <ul className="panel-body grid gap-3">
            {on.map((t) => (
              <li key={t.code} className="flex flex-wrap items-center justify-between gap-3">
                <span>
                  <b>{t.name}</b>
                  <span className="block text-[12px] text-basalt/55">
                    {t.taught_by ? `Switched on by ${t.taught_by}` : "Taught, as the school's rows say"}
                  </span>
                </span>
                <Switch code={t.code} on={false} label={`Switch off, as ${me}`} />
              </li>
            ))}
          </ul>
        </details>
      </section>
    </div>
  );
}

function Switch({ code, on, label }: { code: string; on: boolean; label: string }) {
  return (
    <form action={switchTopic}>
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="taught" value={on ? "on" : "off"} />
      <button className={on ? "btn" : "chip"} type="submit">
        {label}
      </button>
    </form>
  );
}
