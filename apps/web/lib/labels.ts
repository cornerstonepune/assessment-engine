export const RUNG_NAMES: Record<string, string> = {
  R1: "Understanding ones",
  R2: "Understanding tens and ones",
  R3: "Adding ones (no regrouping)",
  R4: "Adding 2-digit numbers without regrouping",
  R5: "Adding 2-digit numbers with regrouping",
  R6: "Subtracting 2-digit numbers without regrouping",
  R7: "Subtracting 2-digit numbers with regrouping",
  R8: "Multiplying by single digits",
  R9: "Division with remainders",
  R10: "Fractions and equivalents",
  R11: "Word problems with two steps",
  R12: "Multi-digit operations",
  R13: "Reasoning about shapes and space",
  R14: "Patterns and sequences",
  X1: "Stretch: complex reasoning",
  X2: "Stretch: applying across contexts",
};

export const MISCONCEPTION_NAMES: Record<string, string> = {
  M_NOCARRY: "Forgets to carry when adding",
  M_FACT_PM10: "Off by 10 in basic facts",
  M_EXCHANGE_NEED: "Doesn't exchange when subtracting",
  M_REGROUP_OVER: "Regroups incorrectly",
  M_PLACE_VALUE: "Misunderstands place value",
  M_SKIP_ZERO: "Skips zero in place value",
  M_INVERSE_OP: "Confuses addition with subtraction",
  M_REMAINDER: "Doesn't understand remainders",
  M_FRAC_PARTS: "Thinks fraction parts must be equal",
  M_COUNT_ERROR: "Miscounts by ones",
};

export const STATE_LABELS: Record<string, { words: string; tone: "neem" | "bamboo" | "terracotta" | "monsoon" }> = {
  not_enough_yet: { words: "not enough yet", tone: "monsoon" },
  emerging: { words: "emerging", tone: "bamboo" },
  practising: { words: "practising", tone: "bamboo" },
  patterned_error: { words: "repeating mistake", tone: "terracotta" },
  secure: { words: "secure", tone: "neem" },
  stretch_ready: { words: "ready to move up", tone: "neem" },
};
