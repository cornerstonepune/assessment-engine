// One icon family, one stroke width, 17 px in the menu. Names say what the section is about.
const base = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const Icons = {
  map: () => (
    <svg {...base}>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  ),
  sheet: () => (
    <svg {...base}>
      <path d="M6 2h9l5 5v15H6z" />
      <path d="M15 2v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h6" />
    </svg>
  ),
  bank: () => (
    <svg {...base}>
      <path d="M4 19V5a2 2 0 0 1 2-2h13v16" />
      <path d="M6 17h13" />
      <path d="M6 21h13" />
      <path d="M9 7h6" />
    </svg>
  ),
  camera: () => (
    <svg {...base}>
      <path d="M12 3v12" />
      <path d="M7 8l5-5 5 5" />
      <path d="M4 21h16" />
    </svg>
  ),
  check: () => (
    <svg {...base}>
      <path d="M4 12.5l5 5L20 6" />
    </svg>
  ),
  growth: () => (
    <svg {...base}>
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 6h6v6" />
    </svg>
  ),
  house: () => (
    <svg {...base}>
      <path d="M3 11l9-8 9 8" />
      <path d="M5 10v10h14V10" />
    </svg>
  ),
  flow: () => (
    <svg {...base}>
      <rect x="3" y="4" width="6" height="5" />
      <rect x="15" y="4" width="6" height="5" />
      <rect x="9" y="15" width="6" height="5" />
      <path d="M9 6.5h6" />
      <path d="M18 9v3.5H12V15" />
    </svg>
  ),
};

export type IconName = keyof typeof Icons;
