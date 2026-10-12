import React, { useState } from "react";
import "./CheckpointTable.css";

export default function CheckpointTable({ route, riskLegend = {} }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!route || !route.checkpoints || route.checkpoints.length === 0) {
    return null;
  }

  const legend = {
    0: { label: "Low", color: "#22c55e" },
    1: { label: "Moderate", color: "#eab308" },
    2: { label: "High", color: "#f97316" },
    3: { label: "Severe", color: "#ef4444" },
    4: { label: "No Travel", color: "#ec4899" },
    ...riskLegend,
  };

  return (
    <div className="checkpoint-table-root" data-testid="checkpoint-table">
      <button
        type="button"
        className="checkpoint-toggle-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="toggle-info">
          <span className="mono-sm toggle-tag">AUDIT LOG</span>
          <h4 className="toggle-heading">
            Checkpoint Telemetry Log ({route.checkpoints.length} Sampling Points)
          </h4>
          <p className="mono-sm toggle-sub">
            {route.name} • Total Distance: {route.distance_miles} mi
          </p>
        </div>

        <span className="mono-sm toggle-indicator">
          {isOpen ? "▲ HIDE CHECKPOINTS" : "▼ EXPAND CHECKPOINTS"}
        </span>
      </button>

      {isOpen && (
        <div className="table-scroll-wrapper">
          <table className="telemetry-table">
            <thead>
              <tr>
                <th><span className="mono-sm">#</span></th>
                <th><span className="mono-sm">LOCATION</span></th>
                <th><span className="mono-sm">MILE</span></th>
                <th><span className="mono-sm">WIND</span></th>
                <th><span className="mono-sm">GUSTS</span></th>
                <th><span className="mono-sm">RAIN</span></th>
                <th><span className="mono-sm">TEMP</span></th>
                <th><span className="mono-sm">BASE</span></th>
                <th><span className="mono-sm">LOAD OVERRIDE</span></th>
                <th><span className="mono-sm">STATUS</span></th>
              </tr>
            </thead>
            <tbody>
              {route.checkpoints.map((cp, idx) => {
                const weather = cp.weather || {};
                const risk = cp.risk || {};
                const lvl = risk.adjusted_level ?? risk.adjustedLevel ?? 0;
                const statusMeta = legend[lvl] || legend[0];

                return (
                  <tr key={idx}>
                    <td className="mono">{String(cp.index ?? idx).padStart(2, "0")}</td>
                    <td>
                      <strong>{cp.name || `Node ${idx}`}</strong>
                      <div className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>
                        {(cp.coord?.lat || cp.lat)?.toFixed(4)}, {(cp.coord?.lng || cp.lng)?.toFixed(4)}
                      </div>
                    </td>
                    <td className="mono">
                      MP {(cp.cumulative_miles ?? cp.mile ?? idx * 25).toFixed(1)}
                    </td>
                    <td className="mono">{weather.wind_mph || 0} mph</td>
                    <td className="mono">{weather.wind_gusts_mph || 0} mph</td>
                    <td className="mono">{weather.rain_in_hr || 0} in/hr</td>
                    <td className="mono">{weather.temperature_f || 70}&deg;F</td>
                    <td className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>
                      Lvl {risk.base_level ?? risk.baseLevel ?? 0}
                    </td>
                    <td>
                      {risk.contributing_factors?.some((f) => f.includes("Load")) || risk.loadOverrideApplied ? (
                        <span className="override-flag">WEIGHT OVERRIDE</span>
                      ) : (
                        <span className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>Standard</span>
                      )}
                    </td>
                    <td>
                      <span
                        className="verdict-pill"
                        style={{
                          color: statusMeta.color,
                          borderColor: statusMeta.color,
                        }}
                      >
                        {statusMeta.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
