"use client";

import { useState } from "react";
import { Panel, Pill } from "@/components/shell";
import { RUNG_NAMES, MISCONCEPTION_NAMES, STATE_LABELS } from "@/lib/labels";
import type { RungState } from "@/lib/queries";

const TONE_COLORS: Record<string, string> = {
  not_enough_yet: "#9ca3af",
  emerging: "#a5b4a1",
  practising: "#a5b4a1",
  patterned_error: "#ab4425",
  secure: "#2c6b41",
  stretch_ready: "#2c6b41",
};

export function ChildGrowthGraph({ rungs }: { rungs: RungState[] }) {
  const [selected, setSelected] = useState<string | null>(rungs[0]?.rung_code ?? null);
  const selectedRung = rungs.find((r) => r.rung_code === selected);

  const nodeRadius = 24;
  const nodeSpacing = 80;
  const width = 280;
  const height = nodeSpacing * (rungs.length - 1) + 60;

  return (
    <div className="grid gap-[18px] lg:grid-cols-[280px_1fr]">
      <div>
        <Panel title="Progression" className="sticky top-[100px]">
          <svg
            width={width}
            height={Math.max(height, 300)}
            className="mx-auto"
            viewBox={`0 0 ${width} ${Math.max(height, 300)}`}
          >
            {/* Connecting lines */}
            {rungs.map((r, i) => {
              if (i === rungs.length - 1) return null;
              const y1 = 30 + i * nodeSpacing;
              const y2 = 30 + (i + 1) * nodeSpacing;
              const color = TONE_COLORS[rungs[i]?.state ?? "not_enough_yet"];
              return (
                <line key={`line-${i}`} x1={width / 2} y1={y1} x2={width / 2} y2={y2} stroke={color} strokeWidth="2" />
              );
            })}

            {/* Nodes */}
            {rungs.map((r, i) => {
              const y = 30 + i * nodeSpacing;
              const isSelected = r.rung_code === selected;
              const tone = r.state ?? "not_enough_yet";
              const color = TONE_COLORS[tone];

              return (
                <g
                  key={r.rung_code}
                  onClick={() => setSelected(r.rung_code)}
                  className="cursor-pointer"
                >
                  {/* Outer ring if selected */}
                  {isSelected && (
                    <circle
                      cx={width / 2}
                      cy={y}
                      r={nodeRadius + 8}
                      fill="none"
                      stroke={color}
                      strokeWidth="3"
                      opacity="0.4"
                    />
                  )}

                  {/* Main circle */}
                  <circle cx={width / 2} cy={y} r={nodeRadius} fill={color} />

                  {/* Evidence indicator */}
                  {r.n_events > 0 && (
                    <text
                      x={width / 2}
                      y={y + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="text-[11px] font-bold"
                      fill="white"
                    >
                      {r.n_correct}/{r.n_events}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </Panel>
      </div>

      <div>
        {selectedRung ? (
          <div className="grid gap-[18px]">
            <Panel title={RUNG_NAMES[selectedRung.rung_code] || selectedRung.rung_code}>
              <div className="grid gap-2 text-[13px]">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-basalt/62">Descriptor</div>
                  <div className="mt-1">{selectedRung.descriptor}</div>
                </div>

                <div>
                  <div className="text-[11px] uppercase tracking-wide text-basalt/62">State</div>
                  <div className="mt-1">
                    <Pill tone={STATE_LABELS[selectedRung.state ?? "not_enough_yet"]?.tone || "monsoon"}>
                      {STATE_LABELS[selectedRung.state ?? "not_enough_yet"]?.words || "not ready yet"}
                    </Pill>
                  </div>
                </div>

                {selectedRung.n_events > 0 && (
                  <div>
                    <div className="text-[11px] uppercase tracking-wide text-basalt/62">Evidence</div>
                    <div className="mt-1">
                      {selectedRung.n_correct} correct out of {selectedRung.n_events} attempts
                      {selectedRung.last_seen && (
                        <div className="mt-1 text-[12px] text-basalt/62">
                          Last seen: {new Date(selectedRung.last_seen).toLocaleDateString("en-IN")}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {selectedRung.repeating_misconception && (
                  <div>
                    <div className="text-[11px] uppercase tracking-wide text-basalt/62">Repeating pattern</div>
                    <div className="mt-1 text-[13px]">
                      {MISCONCEPTION_NAMES[selectedRung.repeating_misconception] ?? selectedRung.repeating_misconception}
                    </div>
                  </div>
                )}

                {selectedRung.n_events === 0 && (
                  <div className="rounded bg-monsoon/10 p-2 text-[12px] text-basalt/75">
                    No evidence yet. This is the starting level for this band.
                  </div>
                )}
              </div>
            </Panel>

            {selectedRung.skill_code && (
              <Panel title="Related skill">
                <div className="text-[13px] text-basalt/75">{selectedRung.skill_code}</div>
              </Panel>
            )}
          </div>
        ) : (
          <Panel title="Select a rung">
            <p className="text-[13px] text-basalt/62">Click a node on the left to see details.</p>
          </Panel>
        )}
      </div>
    </div>
  );
}
