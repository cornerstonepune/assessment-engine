# Design language

Canonical. Derived from the founder's Atlas Investor Dashboard (v1.1).
Token source of truth: `reference/tokens.css` — copy it, don't retype it.
Full reference implementation: `reference/atlas-investor-dashboard.html`.

Governs every interface — a one-off artifact or a full platform — unless a project's own
`design-system/PRINCIPLES.md` explicitly overrides a rule and says why.

---

## The surface: ivory paper under frosted glass

Not white-on-white. Not a dark dashboard. The canvas is warm ivory paper (`--paper #F4F0E5`)
lit by three low-alpha washes (slate, ochre, forest). Every panel is a pane of frosted glass
laid on that paper: translucent fill, blurred backdrop, one lit top edge.

- Glass **tints, never stains** — keep wash alphas low. If a panel reads as "coloured", it's wrong.
- Four fills only: `--glass-fill` (default), `-strong` (raised/modal), `-quiet` (recessed),
  `-dark` (inverted panels). Do not invent a fifth.
- Lift is `--shadow-glass` → `--shadow-glass-lift` on hover. Nothing else moves.

## Colour

| Role | Token | Value |
|---|---|---|
| Brand accent | `--accent` | `#25394A` deep slate |
| Secondary accent | `--accent-2` | `#B8860B` ochre — marks and rules only |
| Positive / buy / gain | `--signal-pos` | `#2C6B41` forest |
| Negative / sell / loss | `--signal-neg` | `#AB4425` terracotta |
| Caution / hold | `--signal-warn` | `#9A7008` deep ochre |
| Info / neutral | `--signal-info` | `#3A5872` slate blue |

Signals are **muted on purpose**. Saturated red/green is a retail-app tell; this is a
professional instrument. Each signal has `-strong`, `-soft`, `-rule`, `-glass` variants — use them
rather than mixing your own alpha.

Multi-series charts use `--data-1..10`, ordered for adjacent-hue separation. Never assign chart
colours by hand; never use a signal colour for a data series (it implies a verdict that isn't there).

Ink is warm-neutral, not black: `--ink` (15.8:1) → `--ink-5`. Contrast ratios are recorded in
`tokens.css` and were raised in v1.1 for small text. `--ink-3` is the floor for 13px;
`--ink-4` needs 15px+. Do not go below.

## Type

Three families, each with a job:
- `--font-serif` (Source Serif 4) — display and editorial headings.
- `--font-sans` (Inter) — UI, labels, body.
- `--font-num` (Geist) — **all numerals**. Plain zero, tabular, modern-software rather than
  typewriter. Financial figures never render in the body sans.
- `--font-mono` (Geist Mono) — code, IDs, hashes.

Scale runs `--t-display-xl 72px` → `--t-micro 12px`. **Nothing under 12px, ever.**
`--t-micro` is for labels and eyebrows only — never a sentence. `--t-caption 13px` is the
smallest size a sentence may use.

## Space, radius, motion

4px base (`--s-1` … `--s-12`). Radii are role-named, not size-named: `--r-card 14px` is the
default pane, `--r-panel 18px` for sheets and modals, `--r-btn 9px`, `--r-well 10px`,
`--r-pill` for chips. Pick by role; the number follows.

Motion: `--dur-fast 120ms` / `--dur-base 200ms` / `--dur-slow 360ms`, easing
`--ease-standard` or `--ease-out`. Motion communicates a state change or it doesn't ship.

---

## Three philosophies, each covering a failure mode the others don't

### 1. Feynman — comprehension is the product

If it can't be explained plainly, it isn't understood. The test for any screen:
**could a smart person outside this domain use it without a glossary?**

- **One idea per screen.** A second question is a second screen, or a disclosure.
- **Explain the number next to the number.** `XIRR 14.2%` is jargon;
  `14.2% — your annualised return after cash flows` is an answer.
- **Plain label over correct-but-opaque label.** "Money in vs money out" beats "Net cash position".
- **Progressive disclosure.** Summary first, detail on demand.
- **Name the uncertainty.** Confidence, `data_as_of`, staleness — in the UI, never buried in code.

### 2. Tufte — density without clutter

Financial professionals want detail. They don't want decoration. Dense is right; cluttered is wrong.

- Maximise data-ink. Every pixel either carries information or goes.
- Small multiples beat one overloaded chart.
- Direct-label series where possible; a legend is a lookup task imposed on the reader.
- Tables are a visualisation. Right-align numerals, tabular figures, fixed header on scroll.

**Where Tufte stops.** Tufte's "no gradients, no shadows" is a rule about **data ink** — inside
the plot area. It is not a rule about chrome. The glass surface is the chrome: it separates panes
and establishes depth, which is information. So: gradients and blur on the *surface*, never on the
*data*. No 3-D bars, no gradient-filled series, no drop-shadowed points, no non-functional gridlines.

### 3. Rams — restraint

"As little design as possible." This is the ponytail ladder applied to interface:
**every element must justify existing.**

- Before adding a component, check ≥3 existing ones. Reuse beats creation.
- No decorative animation.
- One accent doing one job. If everything is emphasised, nothing is.
- Empty space is structure, not waste.

---

## Mechanics (non-negotiable)

Detailed rules live in `~/.claude/rules/frontend-viz.md` and load automatically. Summary:

- **Numbers:** Indian lakh/crore (`₹1,23,45,678`), never million/billion. ₹ prefix.
  2 decimals displayed, 4 in calculation. Tabular numerals via `--font-num`.
- **Percentages:** always signed. `--signal-pos` / `--signal-neg` — and never colour alone
  (accessibility: pair with sign or arrow).
- **Dates:** `DD-MMM-YYYY` (04-Apr-2026), IST.
- **Charts:** axis labels, hover tooltip with exact values, source attribution. Always.
- **Tables:** sortable, searchable, filterable, CSV export. Click an aggregate → see constituents.
- **Loading:** skeleton screens, not spinners.

## Build order

1. Copy `reference/tokens.css` into the project. **Once per project**, not per screen.
   Run `design-consultation` only if the project genuinely departs from Atlas.
2. Build with `ui-ux-pro-max` + Tailwind, under the ≥3-component reuse gate.
3. Charts via the `dataviz` skill, using `--data-1..10`.
4. **Verify in a real browser.** Headless has no WebGL — a map or canvas that "passed" headless
   was never actually seen. Glass (`backdrop-filter`) also renders differently headless.
5. `design-review` last — it hunts AI-slop patterns, spacing drift, and hierarchy failures.

## The honesty rule

A UI that hides how a number was produced is a bug, however elegant. Every figure traces to its
source, its date, and its confidence. Trust is the feature; polish only matters after it.
