import React from "react";
import "./Pages.css";

export default function TermsAndConditions({ onNavigate }) {
  return (
    <div className="container page-container">
      <header className="page-header">
        <div className="page-kicker-row">
          <span className="mono-sm page-kicker">CARRIER AGREEMENT</span>
          <span className="mono-sm page-chip">TERMS REV: 2026.4</span>
          <span className="mono-sm page-chip">49 CFR § 392.14 JURISDICTION</span>
        </div>
        <h1 className="page-title">Terms of Carrier Service</h1>
        <p className="page-lead">
          These Terms of Service govern the use of the Route Radar freight weather risk engine. By using this service, commercial motor carriers, dispatchers, and operators agree to the operational guidelines and advisory disclaimers outlined below.
        </p>
      </header>

      <main className="legal-grid">
        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>01 /</span>
            <h3>Advisory Decision Support Nature</h3>
          </div>
          <p>
            Route Radar provides advanced predictive telemetry for commercial freight routing. All risk classifications, color-coded corridor segments, and departure recommendations are decision-support tools. Pursuant to Federal Motor Carrier Safety Regulations (49 CFR § 392.14), the driver of a commercial motor vehicle exercises final operating authority regarding whether conditions permit safe operation.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>02 /</span>
            <h3>Load Stability & Rollover Overrides</h3>
          </div>
          <p>
            Route Radar calculates vehicle tipping risks based on standard commercial freight aerodynamic coefficients:
          </p>
          <ul>
            <li><strong>Universal Ground Stop:</strong> Sustained winds &ge; 55 mph trigger an automatic No-Travel advisory regardless of vehicle weight.</li>
            <li><strong>Over-30,000 lb Rule:</strong> Crosswinds between 45–54 mph trigger No-Travel for loads exceeding 30,000 lbs.</li>
            <li><strong>Over-40,000 lb Rule:</strong> Winds between 35–44 mph trigger Severe risk warnings for loads exceeding 40,000 lbs.</li>
          </ul>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>03 /</span>
            <h3>Meteorological Model Variance Disclaimer</h3>
          </div>
          <p>
            Atmospheric conditions can evolve rapidly due to localized convective microbursts, sudden squall lines, and elevation microclimates. Route Radar ingests High-Resolution Rapid Refresh forecasts, but cannot guarantee that localized weather will perfectly match numerical weather predictions.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>04 /</span>
            <h3>Limitation of Carrier Liability</h3>
          </div>
          <p>
            In no event shall Route Radar, its developers, or its data providers be liable for direct, indirect, incidental, or consequential damages resulting from highway detours, weather delays, cargo damage, or carrier decisions influenced by this engine.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>05 /</span>
            <h3>API Fair Use & Automated Dispatch Access</h3>
          </div>
          <p>
            Automated querying of Route Radar endpoints must respect rate limiting thresholds. Commercial fleet operators utilizing enterprise telemetry webhooks must maintain active dispatch credentials.
          </p>
        </article>
      </main>

      <footer className="page-back-row">
        <button
          type="button"
          className="page-action-btn"
          onClick={() => onNavigate("/")}
        >
          &larr; RETURN TO ADVISOR CONSOLE
        </button>
        <button
          type="button"
          className="page-secondary-btn"
          onClick={() => onNavigate("/privacy")}
        >
          VIEW PRIVACY POLICY
        </button>
      </footer>
    </div>
  );
}
