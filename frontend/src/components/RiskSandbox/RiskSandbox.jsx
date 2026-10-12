import React, { useMemo, useState } from "react";
import "./RiskSandbox.css";

export default function RiskSandbox() {
  const [wind, setWind] = useState(48);
  const [rain, setRain] = useState(0.2);
  const [snow, setSnow] = useState(0.0);
  const [weight, setWeight] = useState(38000);

  // Exact Phase 1 mathematical risk classification
  const result = useMemo(() => {
    const w = Math.round(wind * 10000) / 10000;
    const r = Math.round(rain * 10000) / 10000;
    const s = Math.round(snow * 10000) / 10000;

    let base = 0;
    const factors = [];

    if (w >= 55.0) {
      base = Math.max(base, 4);
      factors.push(`Wind ${w} mph &ge; 55 mph → No Travel`);
    } else if (w >= 45.0) {
      base = Math.max(base, 3);
      factors.push(`Wind ${w} mph → Severe`);
    } else if (w >= 35.0) {
      base = Math.max(base, 2);
      factors.push(`Wind ${w} mph → High`);
    } else if (w >= 25.0) {
      base = Math.max(base, 1);
      factors.push(`Wind ${w} mph → Moderate`);
    }

    if (r > 1.0) {
      base = Math.max(base, 4);
      factors.push(`Rain ${r} in/hr > 1.00 in/hr → No Travel`);
    } else if (r >= 0.5) {
      base = Math.max(base, 3);
      factors.push(`Rain ${r} in/hr → Severe`);
    } else if (r >= 0.25) {
      base = Math.max(base, 2);
      factors.push(`Rain ${r} in/hr → High`);
    } else if (r >= 0.1) {
      base = Math.max(base, 1);
      factors.push(`Rain ${r} in/hr → Moderate`);
    }

    if (s > 3.0) {
      base = Math.max(base, 4);
      factors.push(`Snow ${s} in/hr > 3.0 in/hr → No Travel`);
    } else if (s >= 2.0) {
      base = Math.max(base, 3);
      factors.push(`Snow ${s} in/hr → Severe`);
    } else if (s >= 1.0) {
      base = Math.max(base, 2);
      factors.push(`Snow ${s} in/hr → High`);
    } else if (s >= 0.5) {
      base = Math.max(base, 1);
      factors.push(`Snow ${s} in/hr → Moderate`);
    }

    let adjusted = base;
    let override = false;

    if (w >= 55.0) {
      adjusted = 4;
    } else if (w >= 45.0 && w < 55.0 && weight > 30000) {
      adjusted = 4;
      override = true;
      factors.push(`Load Override: Wind ${w} mph + Load ${weight.toLocaleString()} lbs (>30k lbs) → NO TRAVEL`);
    } else if (w >= 35.0 && w < 45.0 && weight > 40000) {
      if (adjusted < 3) {
        adjusted = 3;
        override = true;
        factors.push(`Load Override: Wind ${w} mph + Load ${weight.toLocaleString()} lbs (>40k lbs) → SEVERE`);
      }
    }

    const labels = ["Low", "Moderate", "High", "Severe", "No Travel"];
    const colors = ["#22c55e", "#eab308", "#f97316", "#ef4444", "#ec4899"];

    return {
      base,
      adjusted,
      label: labels[adjusted] || "Low",
      color: colors[adjusted] || "#22c55e",
      override,
      factors,
    };
  }, [wind, rain, snow, weight]);

  return (
    <div id="risk-sandbox" className="sandbox-root">
      <div className="sandbox-header">
        <div>
          <span className="mono-sm sandbox-tag">PHYSICAL PRINCIPLES</span>
          <h3>Live Vehicle Stability & Risk Matrix Sandbox</h3>
        </div>
        <div className="verdict-banner" style={{ borderColor: result.color, color: result.color }}>
          <span className="mono-sm">STATUS: {result.label.toUpperCase()}</span>
        </div>
      </div>

      <div className="sandbox-grid">
        <div className="sandbox-controls">
          <div className="slider-box">
            <div className="slider-label-line">
              <span className="mono-sm">SUSTAINED CROSSWIND</span>
              <span className="mono">{wind} MPH</span>
            </div>
            <input
              type="range"
              min="0"
              max="70"
              step="1"
              value={wind}
              onChange={(e) => setWind(Number(e.target.value))}
              className="box-slider"
            />
            <div className="box-ticks">
              <span>0 mph</span>
              <span>25 (Mod)</span>
              <span>35 (High)</span>
              <span>45 (Sev)</span>
              <span>55+ (No Travel)</span>
            </div>
          </div>

          <div className="slider-box">
            <div className="slider-label-line">
              <span className="mono-sm">TRUCK GROSS WEIGHT</span>
              <span className="mono">{weight.toLocaleString()} LBS</span>
            </div>
            <input
              type="range"
              min="1000"
              max="80000"
              step="500"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
              className="box-slider"
            />
            <div className="box-ticks">
              <span>1k (Bobtail)</span>
              <span>30k (Limit 1)</span>
              <span>40k (Limit 2)</span>
              <span>80k (Legal Max)</span>
            </div>
          </div>

          <div className="dual-slider-row">
            <div className="slider-box">
              <div className="slider-label-line">
                <span className="mono-sm">RAIN (IN/HR)</span>
                <span className="mono">{rain}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1.5"
                step="0.05"
                value={rain}
                onChange={(e) => setRain(Number(e.target.value))}
                className="box-slider"
              />
            </div>
            <div className="slider-box">
              <div className="slider-label-line">
                <span className="mono-sm">SNOW (IN/HR)</span>
                <span className="mono">{snow}</span>
              </div>
              <input
                type="range"
                min="0"
                max="4.0"
                step="0.1"
                value={snow}
                onChange={(e) => setSnow(Number(e.target.value))}
                className="box-slider"
              />
            </div>
          </div>
        </div>

        <div className="sandbox-results">
          <div className="result-card">
            <span className="mono-sm">CALCULATED VERDICT</span>
            <h2 style={{ color: result.color, margin: "0.5rem 0" }}>
              {result.label}
            </h2>
            <div className="result-details">
              <div>
                <span className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>BASE WEATHER:</span>
                <p className="mono">Level {result.base}</p>
              </div>
              <div>
                <span className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>WEIGHT OVERRIDE:</span>
                <p className="mono">{result.override ? "TRIGGERED (YES)" : "NONE (NO)"}</p>
              </div>
            </div>
          </div>

          <div className="factors-box">
            <span className="mono-sm">EVALUATED FACTORS:</span>
            <ul className="factors-list">
              {result.factors.map((f, i) => (
                <li key={i} style={{ color: result.color }}>
                  • {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
