"""The strand ladder (R1–R14 + X1/X2) mapped to the Skill Map registry (built 2026-09-15)."""

BANDS = ["G1", "G2", "G3", "G4"]

RUNGS = {
 "R1":  dict(band="G1", skills=["NUM.OPS.01"], desc="Adds within 10 by combining two sets; reads + and ="),
 "R2":  dict(band="G1", skills=["NUM.OPS.01"], desc="Adds within 20 (crossing 10); part-part-whole; +1/+10 patterns"),
 "R3":  dict(band="G1", skills=["NUM.OPS.02"], desc="Subtracts within 20 as take-away and 'how many more'"),
 "R4":  dict(band="G2", skills=["NUM.OPS.01","NUM.OPS.02"], desc="2-digit ± without regrouping in place-value columns"),
 "R5":  dict(band="G2", skills=["NUM.OPS.01"], desc="2-digit addition with one regrouping"),
 "R6":  dict(band="G2", skills=["NUM.OPS.02"], desc="2-digit subtraction with exchange"),
 "R7":  dict(band="G2", skills=["NUM.OPS.05"], desc="Mental strategies: bridging, friendly numbers, missing numbers, equality"),
 "R8":  dict(band="G2", skills=["NUM.PRB.02","NUM.MEAS.04"], desc="One- and two-step word problems in ₹ / objects"),
 "R9":  dict(band="G3", skills=["NUM.OPS.01","NUM.OPS.02"], desc="3-digit ± with one or two regroupings"),
 "R10": dict(band="G3", skills=["NUM.OPS.02"], desc="Subtraction across zero"),
 "R11": dict(band="G3", skills=["NUM.PV.03","NUM.PRB.03"], desc="Estimate first (round to 10), judge reasonableness"),
 "R12": dict(band="G4", skills=["NUM.OPS.01","NUM.OPS.02"], desc="4-digit addition with multiple addends; 4-digit subtraction across zeros"),
 "R13": dict(band="G4", skills=["NUM.OPS.05","NUM.PRB.03"], desc="Chooses an efficient strategy; place-value reasoning under constraint"),
 "R14": dict(band="G4", skills=["NUM.PRB.02","NUM.MEAS.04"], desc="Multi-step ₹ problems under a budget constraint"),
 "X1":  dict(band="G2+", skills=["NUM.PRB.03"], desc="Explains the procedure / judges a claim"),
 "X2":  dict(band="G2+", skills=["NUM.PRB.03"], desc="Finds the mistake in a worked example"),
}

ORDER = ["R1","R2","R3","R4","R5","R6","R7","R8","R9","R10","R11","R12","R13","R14"]

# Taught-in bands (Neha's pedagogy pack, confirmed by the July diagnostic) — the level rule uses these.
LEVELS = {
  # grade: (L-, L0, L+) as lists of primary rungs; foundational = first rung of L-; probe = first rung of L+
  "G1": dict(Lm=["R1"],        L0=["R2","R3"],        Lp=["R4"]),
  "G2": dict(Lm=["R3","R4"],   L0=["R5","R6","R7"],   Lp=["R9"]),
  "G3": dict(Lm=["R5","R6","R7"], L0=["R9","R10","R11"], Lp=["R12","R13"]),
  "G4": dict(Lm=["R9","R10","R11"], L0=["R12","R13","R14"], Lp=["R13"]),
}

SIGNALS = ["Foundational","Conceptual","Procedural","Application","Stretch"]
