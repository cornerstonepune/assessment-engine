---
globs: ["*.tsx", "*.jsx", "*.css", "*.html", "src/components/**", "src/pages/**"]
---
# Frontend + visualization conventions

## Design
- Professional wealth management aesthetic. Not generic Bootstrap
- Ivory paper (#F4F0E5) under frosted glass panes. NOT white-on-white, NOT dark mode
- Accent: deep slate #25394A; secondary ochre #B8860B for marks/rules only
- Tokens are copied from ~/.claude/design/reference/tokens.css — never retyped or invented
- Data density: information-rich screens. Financial professionals want detail
- Mobile responsive but desktop-first (advisors use large screens)

## Visualization libraries
- Recharts: standard 2D charts (default choice)
- D3.js: complex interactive visualizations, force graphs
- Three.js: 3D correlation surfaces, terrain maps, multi-dimensional data
- Plotly: interactive 3D charts with zoom/rotate
- AG Grid: data-heavy tables with sorting, filtering, grouping

## Financial display
- Numbers: Indian lakh/crore (₹1,23,45,678). Never million/billion
- Percentages: always +/- sign. Forest #2C6B41 positive, terracotta #AB4425 negative.
  Muted on purpose — saturated red/green is a retail-app tell. Never colour alone: pair with sign
- Currency: ₹ prefix. 2 decimal display, 4 decimal calculations
- Dates: DD-MMM-YYYY (04-Apr-2026). IST timezone
- Tables: right-align numbers, left-align text. Fixed header on scroll
- Charts: axis labels, legend, data source attribution always

## Interactivity
- Every chart: hover tooltip with exact values
- Every table: sortable, searchable, filterable, CSV export
- Drill-down: click aggregate → see constituent data
- Loading: skeleton screens, not spinners
