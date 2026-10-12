import React from "react";
import "./Pages.css";

export default function PrivacyPolicy({ onNavigate }) {
  return (
    <div className="container page-container">
      <header className="page-header">
        <div className="page-kicker-row">
          <span className="mono-sm page-kicker">GOVERNANCE & TELEMETRY</span>
          <span className="mono-sm page-chip">DOCUMENT ID: SEC-GOV-2026</span>
          <span className="mono-sm page-chip">FMCSA 49 CFR COMPLIANT</span>
        </div>
        <h1 className="page-title">Privacy Policy & Telemetry Governance</h1>
        <p className="page-lead">
          Route Radar is engineered with an ephemeral computation model for commercial freight. We process highway coordinates, meteorological data, and vehicle weight thresholds without tracking driver identities or storing proprietary cargo records.
        </p>
      </header>

      <main className="legal-grid">
        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>01 /</span>
            <h3>Scope of Telemetry Collection</h3>
          </div>
          <p>
            Route Radar collects only the operational data parameters required to simulate atmospheric wind, precipitation, and rollover risk thresholds along designated freight corridors:
          </p>
          <ul>
            <li>Origin and destination geographical coordinates (latitude and longitude waypoints).</li>
            <li>Gross combination vehicle weight in pounds (used exclusively for rollover physics calculations).</li>
            <li>Desired departure UTC timestamp and sampling distance resolution (e.g., 5–50 mile intervals).</li>
          </ul>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>02 /</span>
            <h3>Ephemeral Computation & Zero Personal Information</h3>
          </div>
          <p>
            Route Radar does not collect or retain personal identifiers such as driver names, Social Security numbers, commercial driver license (CDL) numbers, or individual fleet operator identities. Route analyses and 49-hour atmospheric scrubbing occur in-memory and are cleared post-session.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>03 /</span>
            <h3>Atmospheric Forecast Sources</h3>
          </div>
          <p>
            Weather models and atmospheric radar data are ingested from authoritative meteorological sources including the National Oceanic and Atmospheric Administration (NOAA), the National Weather Service (NWS), and the Open-Meteo High Resolution Rapid Refresh (HRRR) model. No telemetry is resold to data brokers.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>04 /</span>
            <h3>Encryption & Enforced Transport Security</h3>
          </div>
          <p>
            All communications between client devices and Route Radar dispatch services are encrypted using TLS 1.3 over strictly enforced HTTPS. External APIs are queried exclusively through authenticated backend proxies to ensure no client credentials or secrets are exposed on the frontend.
          </p>
        </article>

        <article className="legal-card">
          <div className="legal-card-header">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>05 /</span>
            <h3>Data Rights & Operational Inquiries</h3>
          </div>
          <p>
            Commercial motor carriers and logistics dispatchers may submit inquiries regarding data handling, corridor coverage, or compliance audits directly to our engineering team at <strong>privacy@routeradar.io</strong> or by calling <strong>+1 (800) 555-7768</strong>.
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
          onClick={() => onNavigate("/terms")}
        >
          VIEW TERMS OF SERVICE
        </button>
      </footer>
    </div>
  );
}
