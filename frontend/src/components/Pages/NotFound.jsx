import React from "react";
import "./Pages.css";

export default function NotFound({ onNavigate, currentPath = "/404" }) {
  return (
    <div className="container not-found-container">
      <div className="not-found-radar-box">
        <svg
          width="96"
          height="96"
          viewBox="0 0 100 100"
          fill="none"
          role="img"
          aria-label="Radar beacon lost indicator"
        >
          <circle cx="50" cy="50" r="46" stroke="rgba(255, 195, 42, 0.2)" strokeWidth="2" strokeDasharray="6 4" />
          <circle cx="50" cy="50" r="32" stroke="rgba(255, 195, 42, 0.4)" strokeWidth="1.5" />
          <circle cx="50" cy="50" r="16" fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" strokeWidth="2" />
          <line x1="50" y1="50" x2="82" y2="18" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" />
          <circle cx="82" cy="18" r="4" fill="var(--color-primary)" />
        </svg>
      </div>

      <h1 className="not-found-code">404</h1>
      <h2 className="not-found-subtitle">WAYPOINT TELEMETRY NOT FOUND</h2>
      <p className="mono-sm not-found-status">
        STATUS: 404_CORRIDOR_OFF_RADAR // COORDINATE RESOLUTION FAILED
      </p>

      <p className="not-found-desc">
        The requested URL slug <code style={{ color: "var(--color-primary)" }}>{currentPath}</code> does not match any active commercial highway corridor, risk audit log, or regulatory policy.
      </p>

      <div className="not-found-actions">
        <button
          type="button"
          className="page-action-btn"
          onClick={() => onNavigate("/")}
        >
          ⚡ RETURN TO ADVISOR CONSOLE
        </button>
        <button
          type="button"
          className="page-secondary-btn"
          onClick={() => onNavigate("/privacy")}
        >
          PRIVACY POLICY
        </button>
        <button
          type="button"
          className="page-secondary-btn"
          onClick={() => onNavigate("/terms")}
        >
          TERMS OF SERVICE
        </button>
      </div>
    </div>
  );
}
