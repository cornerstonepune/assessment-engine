// The child's skill map (goals/u6-report-card.yaml): every skill set of their grade and the grades either side, placed
// by `layout` — a column per grade, a row per registry skill, the school's ladder left to right — each coloured by the
// graph's own state and carrying the child's answers on it in the three signals. Drawn on the server; no library.
import { layout, type MapNode } from "@/lib/queries-report";
import { rag, RAG_WORDS, type Rag } from "@/lib/rag";

const W = 168; // a skill set's box
const H = 66;
const GAP_X = 26;
const ROW = 96;
const LEFT = 128; // the lane names
const TOP = 34; // the grade names

const FILL: Record<Rag | "none", string> = {
  green: "var(--neem)",
  amber: "var(--bamboo)",
  red: "var(--terracotta)",
  grey: "var(--monsoon)",
  none: "var(--chalk)",
};
const INK: Record<Rag | "none", string> = {
  green: "#fff",
  amber: "var(--basalt)",
  red: "#fff",
  grey: "#fff",
  none: "var(--basalt)",
};

/** A name in at most two lines of about `n` characters, the second cut short with an ellipsis. */
export function lines(name: string, n = 24): string[] {
  const out = [""];
  for (const w of name.split(" ")) {
    const last = out[out.length - 1];
    if (!last || (last + " " + w).length <= n)
      out[out.length - 1] = last ? `${last} ${w}` : w;
    else out.push(w);
  }
  return out.length <= 2 ? out : [out[0], `${out[1].slice(0, n - 1)}…`];
}

function Signals({
  n,
  x,
  y,
  w,
}: {
  n: MapNode;
  x: number;
  y: number;
  w: number;
}) {
  const total = n.right + n.wrong + n.wrong_working + n.blank;
  if (!total) return null;
  let at = x;
  const parts = [
    [n.right, "var(--neem)"],
    [n.wrong_working, "var(--bamboo)"],
    [n.wrong, "var(--terracotta)"],
    [n.blank, "var(--monsoon)"],
  ] as const;
  return (
    <g>
      <rect x={x} y={y} width={w} height={6} fill="#fff" opacity={0.85} />
      {parts.map(([k, fill], i) => {
        const width = (k / total) * w;
        const r = (
          <rect key={i} x={at} y={y} width={width} height={6} fill={fill} />
        );
        at += width;
        return r;
      })}
    </g>
  );
}

export function SkillMap({ nodes, band }: { nodes: MapNode[]; band: string }) {
  const { placed, edges, lanes, columns } = layout(nodes);
  const slots = columns.reduce((s, c) => s + c.width, 0);
  const width = LEFT + slots * (W + GAP_X) + GAP_X;
  const height = TOP + lanes.length * ROW + 8;
  const at = Object.fromEntries(placed.map((p) => [p.code, p]));
  const px = (x: number) => LEFT + GAP_X + x * (W + GAP_X);
  const py = (y: number) => TOP + y * ROW + (ROW - H) / 2;

  return (
    <div className="overflow-x-auto">
      <svg
        role="img"
        aria-label="Skill map"
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto"
        // fits the panel on a laptop and on paper; on a phone it keeps its words readable and scrolls in its panel
        style={{
          fontFamily: "inherit",
          width: "100%",
          minWidth: 760,
          maxWidth: width,
        }}
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 8 8"
            refX="7"
            refY="4"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M0 0L8 4L0 8z" fill="var(--basalt)" opacity={0.45} />
          </marker>
        </defs>
        {columns.map((c) => (
          <g key={c.band} data-grade={c.band}>
            <rect
              x={px(c.from) - GAP_X / 2}
              y={0}
              width={c.width * (W + GAP_X)}
              height={height}
              fill={c.band === band ? "var(--lime)" : "transparent"}
              stroke="var(--basalt)"
              strokeOpacity={0.08}
            />
            <text
              x={px(c.from) - GAP_X / 2 + 10}
              y={22}
              fontSize={13}
              fontWeight={600}
              fill="var(--basalt)"
            >
              {`Grade ${c.band.slice(1)}${c.band === band ? " · this year" : ""}`}
            </text>
          </g>
        ))}
        {lanes.map((l, y) => (
          <text
            key={l}
            x={10}
            y={TOP + y * ROW + ROW / 2 + 4}
            fontSize={12.5}
            fill="var(--basalt)"
            opacity={0.7}
          >
            {lines(l, 17).map((t, i) => (
              <tspan key={i} x={10} dy={i ? 15 : 0}>
                {t}
              </tspan>
            ))}
          </text>
        ))}
        {edges.map((e) => {
          const a = at[e.from];
          const b = at[e.to];
          return (
            <line
              key={`${e.from}-${e.to}`}
              data-edge={`${e.from}>${e.to}`}
              x1={px(a.x) + W}
              y1={py(a.y) + H / 2}
              x2={px(b.x) - 3}
              y2={py(b.y) + H / 2}
              stroke="var(--basalt)"
              strokeOpacity={0.35}
              strokeWidth={1.5}
              markerEnd="url(#arrow)"
            />
          );
        })}
        {placed.map((n) => {
          const c = n.state ? rag(n.state) : "none";
          const answered = n.right + n.wrong + n.wrong_working;
          const words = n.state ? RAG_WORDS[rag(n.state)] : "not assessed yet";
          return (
            <g key={n.code} data-node={n.code} data-rag={n.state ? c : "none"}>
              <title>{`${n.name} — ${words}${n.objective ? `. ${n.objective}` : ""}`}</title>
              <rect
                x={px(n.x)}
                y={py(n.y)}
                width={W}
                height={H}
                rx={6}
                fill={FILL[c]}
                stroke="var(--basalt)"
                strokeOpacity={n.state ? 0 : 0.3}
                strokeDasharray={n.state ? undefined : "4 3"}
              />
              <text
                x={px(n.x) + 10}
                y={py(n.y) + 19}
                fontSize={12.5}
                fontWeight={600}
                fill={INK[c]}
              >
                {lines(n.name).map((t, i) => (
                  <tspan key={i} x={px(n.x) + 10} dy={i ? 15 : 0}>
                    {t}
                  </tspan>
                ))}
              </text>
              <text
                x={px(n.x) + 10}
                y={py(n.y) + H - 16}
                fontSize={11}
                fill={INK[c]}
                opacity={0.9}
              >
                {answered || n.blank
                  ? `${n.right} of ${answered} right${n.blank ? ` · ${n.blank} blank` : ""}`
                  : words}
              </text>
              <Signals n={n} x={px(n.x) + 10} y={py(n.y) + H - 10} w={W - 20} />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function MapKey() {
  const keys: [string, string, boolean?][] = [
    ["var(--neem)", `${RAG_WORDS.green} — secure, or ready to move up`],
    ["var(--bamboo)", RAG_WORDS.amber],
    [
      "var(--terracotta)",
      `${RAG_WORDS.red} — a repeating mistake, or under half right`,
    ],
    ["var(--monsoon)", `${RAG_WORDS.grey} — fewer than three answers`],
    ["var(--chalk)", "not assessed yet", true],
  ];
  return (
    <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[12.5px] text-basalt/75">
      {keys.map(([fill, words, dashed]) => (
        <li key={words} className="flex items-center gap-2">
          <span
            className={`inline-block h-3 w-5 rounded-sm ${dashed ? "border border-dashed border-basalt/40" : ""}`}
            style={{ background: fill }}
          />
          {words}
        </li>
      ))}
      <li className="flex items-center gap-2">
        → the order the school teaches them in
      </li>
    </ul>
  );
}
