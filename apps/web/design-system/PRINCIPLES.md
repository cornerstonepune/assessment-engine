# Design principles — the assessment app

This product uses the **Cornerstone brand** (Brand Book, Edition 02, September 2026, in
`cornerstone-brain`), not the Atlas house language in `~/.claude/design/`. Atlas is a wealth
management instrument: ivory paper, frosted glass, slate and ochre. This is a school's tool, seen
by educators and, later, parents, and the school has a brand built from its own building. The
approved six-screen mockup (`claude.ai/artifact/SB7tvaiUEpcdFZBParNGWW`) already applies it.
Where this file and the mockup disagree, the brand book wins.

## Colour — the material library

Every colour is a material the campus is made of. Mostly ground, a little ink, one colour allowed
to speak: **lime wash 70 % · basalt 20 % · everything else 10 %.**

| Token | Hex | Material | Use here |
|---|---|---|---|
| `--lime` | `#F3EEE4` | lime-washed walls | the canvas. Never bright white |
| `--basalt` | `#26241F` | the rock Pune stands on | all type; the sidebar; never pure black |
| `--terracotta` | `#B8562F` | filler-slab tiles | the one loud colour: one block per page — the primary action, the active nav |
| `--neem` | `#5F6B45` | the courtyard tree | secure / confirmed / ratified |
| `--bamboo` | `#C9A96A` | the pavilion | warm neutral: nav text, drafts, tags |
| `--mud` | `#7A5A3E` | the mud kitchen | text on bamboo |
| `--monsoon` | `#6F7F8C` | the swale, the pond | data, charts, quiet and waiting states |
| `--chalk` | `#FFFDF8` | the chalkboard wall | panels on lime; the hand-drawn line |

Semantic states map to materials, never to red/green: **secure → neem, draft/attention → bamboo,
error/retired → terracotta, waiting → monsoon.** Terracotta is rationed: if two things on a screen
are terracotta, one of them is wrong.

## Type — one simple serif family

**Source Serif 4** for everything — body, headings, labels and facts. Nimish, 2026-09-21, on the live
site: *"This font, I don't like. Let's use a simple serif family font."* It replaced a triad
(Atkinson Hyperlegible body, Young Serif headings, JetBrains Mono facts) whose monospace made every
table read like code.

| Use | Rule |
|---|---|
| body | 15 px, 1.55 leading; 13 px in dense tables |
| headings | weight 600, never all-caps |
| labels | 11 px letter-spaced capitals, weight 600 |
| facts — ids, counts, dates | tabular lining figures, so numbers line up in a column |

## Graphic language

- **The courtyard grid.** Content rings the edge; the centre is left for air. Panels are chalk on
  lime with a hairline basalt border at low alpha. No shadows, no rounded corners beyond 0, no
  gradients — rule 10 of the brief: nothing decorative.
- **The chalk line.** One hand-made stroke per surface: the short rule under a page title. Rationed
  to one.
- **The label.** Every thing carries its facts as a five-line label at most; the last line is what
  to do.
- Never: gradients, outlines, drop shadows, a face in the mark, exclamation marks, stock imagery.

## Voice — quiet rigour

Warm, told, plain, evidenced, unhurried. "Educators", never "teachers", in anything a parent sees.
"Exchange" or "regroup", never "borrow". Short sentences and concrete nouns in every empty state,
error and button. Words we do not use: best, holistic, world-class, future-ready, nurturing,
fun-filled, state-of-the-art, fearless, exclamation marks.

## Layout facts from the mockup

Sidebar 230 px basalt, bamboo nav text, terracotta wash on the active item. Top bar: letter-spaced
stage eyebrow, 26 px title, 13.5 px sub in basalt at 62 %, then the chalk line. Body padding
22 × 36 px. Tables: uppercase letter-spaced headers, 11 × 14 px cells, hairline rows. Pills: 11.5 px
with a material tint and border. Chips: 7 × 13 px, basalt when on.

## Tokens

`app/globals.css` holds these as CSS variables and Tailwind theme tokens. Nothing is retyped in a
component; a component that needs a colour names the material.
