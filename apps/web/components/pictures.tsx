// The questions a child answers from a drawing, drawn as they print (engine/assess/pictures.py): the website shows
// the child's question, never a code or a description of it.

// A tally: bundles of four lines crossed by a fifth, then the lines left over.
export function Tally({ n }: { n: number }) {
  const bundles = Math.floor(n / 5);
  const ones = n % 5;
  const x = (b: number, i: number) => 6 + b * 41 + i * 7;
  const width = x(bundles, ones) + 6;
  return (
    <svg width={width} height={32} viewBox={`0 0 ${width} 32`} stroke="currentColor" strokeWidth={2} aria-label={`a tally of ${n}`}>
      {Array.from({ length: bundles }, (_, b) => (
        <g key={b}>
          {[0, 1, 2, 3].map((i) => (
            <line key={i} x1={x(b, i)} y1={4} x2={x(b, i)} y2={28} />
          ))}
          <line x1={x(b, 0) - 4} y1={24} x2={x(b, 3) + 4} y2={8} />
        </g>
      ))}
      {Array.from({ length: ones }, (_, i) => (
        <line key={i} x1={x(bundles, i)} y1={4} x2={x(bundles, i)} y2={28} />
      ))}
    </svg>
  );
}

// Where a die puts 1 to 6 dots, in steps from the middle of its ring.
const DIE: Record<number, [number, number][]> = {
  1: [[0, 0]],
  2: [[-1, -1], [1, 1]],
  3: [[-1, -1], [0, 0], [1, 1]],
  4: [[-1, -1], [1, -1], [-1, 1], [1, 1]],
  5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]],
  6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]],
};

// Equal groups: a ring per group, its dots laid out as a die shows them.
export function Rings({ groups, size }: { groups: number; size: number }) {
  return (
    <svg width={groups * 46} height={44} viewBox={`0 0 ${groups * 46} 44`} fill="currentColor" aria-label={`${groups} groups of ${size}`}>
      {Array.from({ length: groups }, (_, g) => (
        <g key={g}>
          <circle cx={22 + g * 46} cy={22} r={19} fill="none" stroke="currentColor" strokeWidth={1.5} />
          {(DIE[size] ?? []).map(([dx, dy], i) => (
            <circle key={i} cx={22 + g * 46 + dx * 9} cy={22 + dy * 9} r={3.2} />
          ))}
        </g>
      ))}
    </svg>
  );
}
