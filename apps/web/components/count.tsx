// A number of things waiting or held, said one way everywhere (rule 5): the same figure on a page and in the menu, because
// both are given the same `of` and the same value from the one list that counts it (lib/needs-you.ts). `data-count` is what
// the test reads, to fail a page whose figure differs from the menu's.
export function Count({ of, n }: { of: string; n: number }) {
  return (
    <span data-count={of} className="fact tabular-nums">
      {n.toLocaleString("en-IN")}
    </span>
  );
}
