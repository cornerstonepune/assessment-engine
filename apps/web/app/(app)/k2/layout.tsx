// The ground of the K2 pictures is white (D-075). One place, so the later shell swap is one change.
//
// It is the app's own white, not `--surface` from design-system/tokens.css, on purpose: the app does not import the tokens,
// and importing them for these pages changes the body font of every page after the first visit (measured by the browser
// test: the font becomes Jost, because both files define `--font-body`). docs/design-tokens.md, decision 1, says whether the
// app takes Jost; that is not this task's to settle. When it is, this wrapper imports the tokens and uses `--surface`.
export default function K2Layout({ children }: { children: React.ReactNode }) {
  return (
    <div data-ground="surface" className="min-h-full bg-white">
      {children}
    </div>
  );
}
