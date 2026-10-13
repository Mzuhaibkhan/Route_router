import React, { useState } from "react";
import "./RouteForm.css";

export default function RouteForm({
  origin,
  setOrigin,
  destination,
  setDestination,
  loadWeight,
  setLoadWeight,
  interval,
  setIntervalOption,
  onAnalyze,
  onTryDemo,
  isAnalyzing,
  errorMessage,
}) {
  const [localError, setLocalError] = useState("");

  const weightPresets = [
    { label: "Empty Bobtail", value: 15000 },
    { label: "General Dry Van", value: 35000 },
    { label: "Heavy Freight", value: 45000 },
    { label: "Permitted Superload", value: 65000 },
  ];

  function handleSubmit(e) {
    e.preventDefault();
    if (!origin || !origin.trim()) {
      setLocalError("Origin location is required.");
      return;
    }
    if (!destination || !destination.trim()) {
      setLocalError("Destination terminal is required.");
      return;
    }
    if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      setLocalError("Origin and destination cannot be identical.");
      return;
    }
    setLocalError("");
    onAnalyze({
      origin: origin.trim(),
      destination: destination.trim(),
      load_weight_lbs: Number(loadWeight),
      interval_miles: interval,
    });
  }

  const activeError = localError || errorMessage;

  return (
    <form className="route-form-root" onSubmit={handleSubmit} noValidate>
      {activeError && (
        <div className="form-error-banner" data-testid="error-message">
          <span className="mono-sm">VALIDATION ERROR:</span> {activeError}
        </div>
      )}

      <div className="form-sections-grid">
        {/* Panel 1: Route Locations */}
        <div className="form-panel">
          <span className="mono-sm panel-legend">01 / CORRIDOR ROUTE</span>
          <div className="field-group">
            <label htmlFor="origin-input" className="mono-sm">
              ORIGIN CITY / ADDRESS
            </label>
            <input
              id="origin-input"
              data-testid="origin-input"
              type="text"
              value={origin}
              onChange={(e) => {
                setOrigin(e.target.value);
                setLocalError("");
              }}
              placeholder="e.g. Dallas, TX"
              className="field-input"
              required
            />
          </div>

          <div className="field-group">
            <label htmlFor="destination-input" className="mono-sm">
              DESTINATION TERMINAL
            </label>
            <input
              id="destination-input"
              data-testid="destination-input"
              type="text"
              value={destination}
              onChange={(e) => {
                setDestination(e.target.value);
                setLocalError("");
              }}
              placeholder="e.g. Houston, TX"
              className="field-input"
              required
            />
          </div>

          <div className="corridor-pills">
            <button
              type="button"
              className="corridor-preset-pill"
              onClick={() => {
                setOrigin("Dallas, TX");
                setDestination("Houston, TX");
                setLocalError("");
              }}
            >
              Dallas &rarr; Houston
            </button>
            <button
              type="button"
              className="corridor-preset-pill"
              onClick={() => {
                setOrigin("Los Angeles, CA");
                setDestination("Phoenix, AZ");
                setLocalError("");
              }}
            >
              LA &rarr; Phoenix
            </button>
          </div>
        </div>

        {/* Panel 2: Vehicle Dynamics */}
        <div className="form-panel">
          <div className="panel-header-row">
            <span className="mono-sm panel-legend">02 / VEHICLE WEIGHT</span>
            <span className="mono weight-readout">
              {Number(loadWeight).toLocaleString()} LBS
            </span>
          </div>

          <div className="field-group">
            <label htmlFor="weight-input" className="mono-sm">
              GROSS COMBINATION WEIGHT (1,000 to 80,000 LBS)
            </label>
            <input
              id="weight-input"
              data-testid="weight-input"
              type="number"
              min="1000"
              max="80000"
              step="100"
              value={loadWeight}
              onChange={(e) => setLoadWeight(Number(e.target.value))}
              className="field-input weight-number-input"
            />
            <input
              type="range"
              min="1000"
              max="80000"
              step="500"
              value={loadWeight}
              onChange={(e) => setLoadWeight(Number(e.target.value))}
              className="weight-slider"
              aria-label="Load weight range"
            />
          </div>

          <div className="weight-presets-grid">
            {weightPresets.map((wp) => (
              <button
                key={wp.value}
                type="button"
                className={`weight-pill ${loadWeight === wp.value ? "weight-pill-active" : ""}`}
                onClick={() => setLoadWeight(wp.value)}
              >
                {wp.label} ({wp.value / 1000}k)
              </button>
            ))}
          </div>

          {loadWeight > 30000 && (
            <div className="load-rule-notice">
              <span className="mono-sm">
                {loadWeight > 40000
                  ? "[OVER-40k LB RULE] Wind 35-44 mph triggers SEVERE risk."
                  : "[OVER-30k LB RULE] Wind 45-54 mph triggers NO TRAVEL advisory."}
              </span>
            </div>
          )}
        </div>

        {/* Panel 3: Sampling & Execution */}
        <div className="form-panel">
          <span className="mono-sm panel-legend">03 / SAMPLING & AUDIT</span>

          <div className="field-group">
            <label className="mono-sm">SAMPLING RESOLUTION</label>
            <div className="interval-buttons-row">
              {["auto", "10", "25", "50", "75", "100"].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  data-testid={`interval-${opt}`}
                  className={`interval-pill ${interval === opt ? "interval-pill-active" : ""}`}
                  onClick={() => setIntervalOption(opt)}
                >
                  {opt === "auto" ? "AUTO" : `${opt} MI`}
                </button>
              ))}
            </div>
          </div>

          <div className="form-actions-stack">
            <button
              type="submit"
              data-testid="analyze-button"
              className="action-submit-btn"
              disabled={isAnalyzing}
            >
              <span>{isAnalyzing ? "EVALUATING RADAR..." : "ANALYZE CORRIDOR ROUTES"}</span>
            </button>

            <button
              type="button"
              data-testid="demo-button"
              className="action-demo-btn"
              onClick={onTryDemo}
            >
              <span>⚡ TRY DEMO (INSTANT FIXTURES)</span>
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
