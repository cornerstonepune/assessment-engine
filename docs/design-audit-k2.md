# Audit of the K2 screens against docs/design-tokens.md (D-073)

Rules R1 to R9 are in `docs/design-tokens.md`. **How this was done:** the built screens (Record, Confirm, form) were read from the code on `origin/main` (6ee6e79),
not run: Tailwind sizes are taken as 0.25 rem per step on a 16 px root (**unverified** in the repo's config). The seven wireframe screens were measured in a browser
(Playwright, 1360 px, desktop frames). Contrast is computed with the WCAG formula; blends assume each chip fill sits on the app's lime canvas. Nothing was changed.

## A. Built K2 screens (code read, not run)
| Screen | Rule | Breach | Fix |
|---|---|---|---|
| Record (`voice/record/recorder.tsx`) | R3 | Instruction line `text-[15px]` | 16 px (`--text-body`) |
| Record | R5 | Error text terracotta on lime, 4.12:1 | `--link` (clay-700), 5.47:1 |
| Record | pass | Record, Stop and Send buttons `min-h-14` = 56 px; text 17 px | none (17 is off the new scale: use 18 or 16) |
| Confirm (`voice/notes/[id]/page.tsx`) | R2 | `<audio controls className="h-9">` = 36 px | `h-11` (44 px) |
| Confirm | R3, R5 | Per-line notes `text-[12.5px] text-basalt/62`: off the scale, under 14, and 4.21:1 | 14 px in `--text-muted` (5.93:1 on lime) |
| Confirm | R3 | Lines `text-[15px]`, meta `text-[14px]` | 16 and 14 |
| Form (`voice/board.tsx`) | R2 | Level buttons use `.chip min-w-11`: about 36 px high (7+7 padding, 20 line, 2 border) | `min-h-11`, 44 px |
| Form | R2 | Child tiles `min-h-12` = 48 px | pass |
| Form | R3, R5 | Labels `text-[13px] text-basalt/70`; problem text terracotta 14 px, 4.12:1 | 14 px; `--link` |
| Form | R1 | Mixed gaps 2, 6, 8, 12, 16 px (`gap-0.5`, `gap-1.5`, `px-3`) | 4, 8, 16 only |

## B. Shared parts: `globals.css`, `components/status-chip.tsx`
| Where | Rule | Breach | Fix |
|---|---|---|---|
| body | R3 | 15 px / 1.55 | 16 / 24 |
| `.label` | R3, R5 | 11 px capitals, `ink-55` on lime = 3.46:1 | 14 px, weight 500, `--text-muted` |
| `.fact`, `.chip`, `.btn`, `.pill` | R3 | 13, 13, 13.5, 11.5 px | 14 px (`--text-label`) |
| `.btn`, `.chip` | R2 | `.btn` about 41 px high (10+10 padding, 21 line); `.chip` about 36 px | `min-height: var(--tap)` |
| `StatusChip` tones | R5 | Text on its own 12% fill: ok neem 4.24, act terracotta 3.56, quiet monsoon 3.15 (all under 4.5); wait mud 4.73 passes | The five chip pairs in `tokens.css` (4.86 to 15.50) |
| `STATES` | D-062 | `doNow` is tone `act` (terracotta); `late` is tone `quiet` (grey); no "coming up" (only "this week", "next") | Do now = basalt fill; Late = clay; add `comingUp`. Needs two new tones, `ink` and `late`, beside ok, wait, act, quiet |
| fonts | R4 | Source Serif 4 only | Decision 1 in the tokens doc |
| corners | R9 | `--radius: 0` | Decision 2 |
| focus | R9 | Not checked (I did not read the focus styles) | check with Playwright, then 3 px ring |
| `.btn` | R5 | Chalk on terracotta 4.68 | pass; clay-500 button text must stay at 16 px bold or larger |

## C. The seven wireframe screens (measured)
| Rule | Breach | Fix |
|---|---|---|
| R2 | 15 `.btn` at 30 px high; 7 pencil buttons 29 x 29; 7 "have it" boxes 24 x 24; the Day/Week toggle 37 px; 7 `summary` rows 39 px; "Materials" link 28 px; 7 "from" links 19 px | all `min-height: 44px`; the 24 px box sits inside a 44 px hit area; the "from" link becomes a 44 px row |
| R3 | 267 of 426 text nodes are under 14 px (11.5, 12, 12.5, 13, 13.5); only 73 sit on the new scale (12, 14, 16) | re-set on the scale; no status or action under 14 |
| R4 | `system-ui` on 1064 elements, Georgia on 5 | Jost, Cormorant Garamond at 24 and above |
| R1 | 120 of 164 spacing values are off the scale (6, 10, 12, 14, 9, 11, 13, 18, 20) | tokens `--space-*` |
| R5 | Grey hints at 62% on chalk 4.46; "Not written yet" monsoon 4.06; the old Late chip, clay-500 on a pale fill, 3.76 | `--text-muted`; `--brand-monsoon-deep`; the new Late pair 5.61 |
| R6 | A dark palette exists but its pairs were never contrast-checked | use the checked dark tokens |
| R7 | Checked at 390 px in the phone frame (no sideways scroll at 1360); not at 640 or 320 px | run R7 |
| R8 | pass: icon, colour and word on every chip; no clay on a child; Late is clay on work only | none |
| R9 | Square corners; no focus ring designed; native `summary` focus | radius 12/20; 3 px ring |
Two things in the wireframes also follow from the tokens: the chip colours change (Do now basalt, To confirm bamboo, Coming up monsoon-deep, Done olive, Late clay) and the origin badges move to the new pairs.
**Not audited:** the library, papers, school and staff screens; only the K2 screens and the wireframes were in scope.
