import { TONE_BG } from "@/components/shell";
import type { ColourRules } from "@/lib/colours";
import { RAG_TONE, RAG_WORDS, type Rag } from "@/lib/rag";

const pc = (x: number) => `${Math.round(x * 100)}%`;

/** The swatch a colour is drawn with, wherever a skill's colour shows. */
export function Swatch({ colour, label }: { colour: Rag; label?: string }) {
  return (
    <span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={`inline-block h-4 w-4 shrink-0 rounded-[3px] ${TONE_BG[RAG_TONE[colour]]} ${colour === "grey" ? "opacity-40" : ""}`}
    />
  );
}

// What each colour means (goals/u11-colours-said.yaml): when a skill is that colour, in the rule's own numbers, and what
// the engine does about it. The order is the rule's (`rebuild_child_skill_state`): too few answers is grey before
// anything else; a mistake that repeats is red whatever the share right.
export function ColourKey({ rules }: { rules: ColourRules }) {
  const rows: [Rag, string, string][] = [
    [
      "red",
      `The same mistake twice or more, or under ${pc(rules.demote)} right.`,
      "Home assessments work on it first, at a level where the mistake can show.",
    ],
    [
      "amber",
      `${pc(rules.demote)} up to ${pc(rules.promote)} right, or ${pc(rules.promote)} and more but on fewer than ${rules.minPapers} papers so far.`,
      "Worked on once nothing is red, at its level.",
    ],
    [
      "green",
      `${pc(rules.promote)} or more right, across ${rules.minPapers} papers or more; ready to move up from ${2 * rules.minAnswers} answers.`,
      "When nothing is red or amber, a stretch paper one level up.",
    ],
    ["grey", `Fewer than ${rules.minAnswers} checked answers: not enough to say.`, `A ${rules.checkSize}-question check places the child.`],
  ];
  return (
    <section aria-label="What the colours mean" className="panel">
      <div className="panel-head">
        <h2 className="text-[16px]">What the colours mean</h2>
        <div className="fact text-[11px] text-basalt/55">from checked answers only, skill by skill</div>
      </div>
      <div className="overflow-x-auto">
        <table className="grid">
          <thead>
            <tr>
              <th>Colour</th>
              <th>A skill is this colour when</th>
              <th>What comes next</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([c, when, next]) => (
              <tr key={c} data-rag={c}>
                <td className="whitespace-nowrap">
                  <span className="inline-flex items-center gap-2 font-medium">
                    <Swatch colour={c} />
                    {RAG_WORDS[c]}
                  </span>
                </td>
                <td>{when}</td>
                <td className="text-basalt/70">{next}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
