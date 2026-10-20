# Design standard

Open this before building or changing anything a person looks at: a screen, a dashboard, a report, a website, a deck, a diagram.

## The language

Nimish's design language is `design-language.md` in this folder: ivory paper under frosted glass, muted signals, its own type pairing, and the Feynman, Tufte and Rams tests. It governs every interface unless the repository's own `design-system/PRINCIPLES.md` overrides a rule and says why. The mechanics (number formats, tables, charts, loading states) are in `rules/frontend-viz.md`.

Tokens come from `tokens.css`, copied once per project and never retyped. It lives on Nimish's Mac (`~/.claude/design/reference/`), not in this harness. If the repository doesn't have it yet, ask Nimish for it; never invent tokens.

## Build order

1. Tokens first.
2. Compose from existing components; check at least three before making a new one.
3. Charts with the `dataviz` skill, on `--data-1..10`.
4. Look at it in a real browser at desktop and phone width. Headless screenshots miss blur, canvas and maps.
5. Review it last against the list below (gstack's `design-review` where it's installed).

Skills: `frontend-design` for direction, `dataviz` for charts, `archify` for architecture and flow diagrams, plus `ui-ux-pro-max` and `design-review` where installed on the Mac.

## Never ship the AI look

- Untouched framework defaults: the stock shadcn, Tailwind or Bootstrap look.
- Purple-to-blue gradients, glowing borders, neon accents, effects on the data itself.
- A centred hero, three feature cards and a "Get started" button as the default layout.
- Emoji as icons or section markers.
- Saturated red and green for gain and loss, or colour as the only signal.
- Placeholder copy or numbers ("Lorem", "John Doe", "+23%"): show real data or a clear empty state.
- Decorative motion. Every animation shows a change of state.
- Copy that sounds generated: see `WRITING.md`.
