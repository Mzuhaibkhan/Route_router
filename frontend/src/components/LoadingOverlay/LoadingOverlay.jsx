import React from "react";
import "./LoadingOverlay.css";

export default function LoadingOverlay({ stage = 1 }) {
  const stages = [
    { num: 1, label: "Generating Multi-Tier HGV Routes via OpenRouteService" },
    { num: 2, label: "Sampling 49-Hour Batched Atmospheric Weather (Open-Meteo)" },
    { num: 3, label: "Computing Dynamic Crosswind & Truck Weight Risk Matrix" },
  ];

  return (
    <div className="loading-overlay-root" data-testid="loading-overlay">
      <div className="loading-modal">
        <div className="loading-spinner" />
        <h4 className="loading-title">Analyzing Transport Corridor</h4>
        <p className="mono-sm" style={{ color: "var(--color-mid-grey)", marginTop: "0.25rem" }}>
          Fleet Telemetry Engine v1.4
        </p>

        <div className="stages-list">
          {stages.map((s) => {
            const isDone = stage > s.num;
            const isCurrent = stage === s.num;
            return (
              <div
                key={s.num}
                className={`stage-row ${isCurrent ? "stage-current" : isDone ? "stage-done" : "stage-pending"}`}
              >
                <span className="mono stage-number">
                  {isDone ? "✓" : `[${s.num}/3]`}
                </span>
                <span className="stage-label">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
