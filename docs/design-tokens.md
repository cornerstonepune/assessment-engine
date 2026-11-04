# Design tokens and rules (D-073): the school's own palette, one type system, numbers that can be checked

Machine-readable: `apps/web/design-system/tokens.css` (CSS variables; nothing imports it yet). Audit of what exists: `docs/design-audit-k2.md`.
Brand values come from cornerstoneschool.in, read 2026-11-04: 22 colours from the brief and 3 more read from its CSS variables (clay-200, olive-lt, monsoon-lt) are in its homepage HTML, with the four font names
(the 12/20 radius and the 44 px tap size are the orchestrator's brief; I did not re-check those two).

## Names and collisions
Brand colours are `--brand-*` (the site calls them `--color-*`; that prefix is the app's Tailwind theme, where `--color-bamboo` is #C9A96A and `--color-basalt` already exist). Semantic names (`--chip-*`, `--origin-*`, `--space-*`, `--tap`, `--text-*`, `--font-*`, `--radius-*`, `--bg`, `--surface`, `--border`, `--link`, `--focus`) are unchanged.
Check run on 4 Nov: every CSS variable defined in `apps/web` (27 outside `tokens.css`: `--lime --basalt --terracotta --neem --bamboo --mud --monsoon --chalk --ink-*`, their `--color-*` twins, `--font-body --font-heading --radius`) against the 85 names in `tokens.css`. Result: no exact clash except **`--font-body`**, which the app sets to Source Serif 4; importing `tokens.css` changes it to Jost. That is decision 1, not a bug to rename around. Every `var(--x)` in `tokens.css` resolves.
`--font-*`, `--text-*` and `--radius-*` sit in Tailwind's theme namespaces. They are declared in plain `:root`, so no utility is made; if anyone moves them into `@theme`, Tailwind will make `font-body`, `text-h1` and similar classes. Tailwind's own default names were **not** checked (it is not installed in this session).

## Decisions this needs (they conflict with the app today; I have not chosen)
1. **Fonts.** `design-system/PRINCIPLES.md` says one serif, Source Serif 4 (Nimish, 21 Sep: "a simple serif family"). D-073 says Jost, Cormorant Garamond, Young Serif, Eczar.
2. **Corners.** PRINCIPLES: "no rounded corners beyond 0". The site: radius 12 and 20.
3. **Colour.** PRINCIPLES: neem #5F6B45, bamboo #C9A96A, lime #F3EEE4. The site: olive, bamboo #9A7A3A, paper-warm. Terracotta is the same hex as clay-500.
4. **Terracotta is "rationed: one block per page"** in PRINCIPLES; Late, errors and links now use clay. Links use clay-700, the text colour.
D-073 is newer, so these tokens follow it. A person edits PRINCIPLES.md if D-073 stands.

## The five chips (D-062): round, icon + colour + one word. Contrast is text on fill (needs 4.5:1) and border on paper (needs 3:1)
| Chip | Icon | Text on fill | Border |
|---|---|---|---|
| Do now | play | paper on basalt 15.50 | basalt |
| To confirm | clock | bamboo-deep on bamboo-lt 4.86 | bamboo 4.02 |
| Coming up | ring | monsoon-deep on paper 8.74 | monsoon-deep 8.74 |
| Done | tick in circle | olive-deep on olive-tint 8.27 | olive 8.04 |
| Late | hourglass | clay-700 on clay-100 5.61 | clay-500 4.76 |
Late is clay (the app's terracotta), for work only. It is never used on a child. The icon in clay-500 on clay-100 is 4.22:1 (needs 3:1).
Clay-500 as *text* on clay-100 fails (4.22), so text is always clay-700.
Origin badges (24 px round, icon only; the legend gives the word): School = book-open, olive-deep on olive-tint 8.27 · Drafted = sparkles, bamboo-deep on
bamboo-lt 4.86 · Edited = pencil, monsoon-deep on monsoon-wash 6.90. Dark values are derived (not on the site) and all pass: text pairs 8.80 to 13.70, borders 5.20 to 12.18.

## Rules. Each has a number, a check, and where the number comes from
| # | Rule | Check | Source |
|---|---|---|---|
| R1 | Space: 4, 8, 16, 24, 32, 48, 64 px only. 4 only between an icon and its label or inside a chip. Every margin, padding and gap is a `--space-*`. | Grep CSS and Tailwind for any other px value; Playwright reads computed padding, margin and gap and fails off the list. | The 8 px grid is **unverified** as an Apple rule: the HIG Layout page states no spacing number (only "Use consistent spacing"). |
| R2 | Anything tappable is at least 44 x 44 px, with at least 8 px between neighbours. | Playwright: `boundingBox()` of every `a, button, input, summary, [role=button]` is at least 44 both ways. | Apple HIG, Buttons: "at least 44x44 pt". Accessibility: iOS default 44x44 pt, minimum 28x28 pt. 1 pt = 1 CSS px is an assumption. The 8 px gap is ours, **unverified**. |
| R3 | One type scale. Sizes 32/24/20/18/16/14/12; weights 400/500/600; line heights 40/32/28/28/24/20/16. Body 16/24. Under 14 px never carries a status, a label or an action; 12 is for timestamps. Cormorant only at 24 and above (a thin face). | Playwright: collect `font-size` of every text node; fail off the scale, fail body under 16. | Apple HIG, Typography: iOS default 17 pt, minimum 11 pt, "aim for larger" with thin weights. The 16 floor is the school's rule, not Apple's. |
| R4 | One font system: Jost for the interface, Cormorant Garamond for headings, Young Serif for the wordmark, Eczar for Devanagari. A generic fallback only: no `system-ui`, no Georgia. | Playwright: the set of computed `font-family` first names is within those four. | D-073. |
| R5 | Contrast, measured: text under 18 pt at least 4.5:1; 18 pt or bold at least 3:1. Icons and control borders at least 3:1. Decorative lines (`--border`, 1.45:1) never form the edge of a control; that is `--border-control`. | The WCAG relative-luminance formula over every token pair, in both modes. The results are the table above. Re-run after any token change. | Apple HIG, Accessibility: "Up to 17 pts 4.5:1; 18 pts 3:1; Bold 3:1". WCAG 1.4.3 states the same ratios (read at w3.org). The 3:1 for icons and borders is WCAG 1.4.11, **unverified**: I did not fetch it. |
| R6 | Dark mode follows the system. No in-app switch. Contrast checked in both modes. A page may be held light with `data-scheme="light"` on `<html>`, set by the layout and not by the person, until the site has a dark mode (orchestrator, 4 Nov); dropping the attribute turns dark on. | `prefers-color-scheme: dark` run of R5; Playwright `colorScheme: "dark"`: a page without the attribute is dark, a page with `data-scheme="light"` stays light. | Apple HIG, Dark Mode: "Avoid offering an app-specific appearance setting"; Accessibility: check contrast in light and dark. |
| R7 | Text survives 200%: no fixed height on a text box, no horizontal scroll, nothing clipped at 640 px wide (200% of 1280) and at 320 px. | Playwright at 640 and 320 px: `scrollWidth <= clientWidth`; no `overflow: hidden` on text. | Apple HIG, Accessibility: "enlarge text by at least 200 percent". WCAG 1.4.4 "up to 200 percent" (read). The 320 px width is WCAG 1.4.10, **unverified**. |
| R8 | Colour never alone, and no clay on a child. A work state is icon + colour + word. A child is a square without an icon. Clay marks work (Late, errors). | The `STATES` table is the only source; Playwright finds no clay-coloured element inside a child cell. | The site's `ux-rules` (rules 2, 9) and D-062. |
| R9 | Corners 12 on controls and cards, 20 on large panels, pill on chips. Focus ring: 3 px, basalt (haldi in dark), offset 2 px, on every focusable element. | Playwright tabs through each screen; every focused element has a visible outline of at least 3 px. | The 12/20 are the brief's. The 3 px ring is our choice, **unverified**. |
No gradients, no stock illustration, no emoji as icons, no shadows. Icons: Lucide only (design/ in teacher-os). New icons need a gallery entry and a yes.

## What I verified and what I did not
- Verified by reading: Apple's HIG Accessibility, Buttons, Typography, Layout and Dark Mode pages (their published data on developer.apple.com, 4 Nov 2026); WCAG 2.2 criteria 1.4.3 and 1.4.4 (w3.org).
- Verified by script: every contrast number above (WCAG formula). In the new token set the only failures are the two uses R5 forbids: clay-500 as text on clay-100 (4.22) and the decorative line as a control edge (1.45). The other failures are in the existing app and my wireframes (audit). Not verified: WCAG 1.4.10, 1.4.11, 2.5.8 (its text was cut off in my fetch).
- Not done: tokens are not wired into the app; fonts are not loaded; no screen was changed.
