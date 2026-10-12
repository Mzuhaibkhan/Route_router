import React from "react";
import "./RouteCards.css";

export default function RouteCards({
  routes = [],
  selectedRouteIndex = 0,
  onSelectRoute,
  riskLegend = {},
}) {
  return (
    <div className="route-cards-root">
      <div className="cards-header-row">
        <div>
          <span className="mono-sm" style={{ color: "var(--color-primary)" }}>
            MULTI-CRITERIA DECISION MATRIX
          </span>
          <h3>Alternative Route Candidates</h3>
        </div>
        <p className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>
          Ranked by Lexicographic 5-Mile Risk Bucketing
        </p>
      </div>

      <div className="cards-grid">
        {routes.map((route, idx) => {
          const isSelected = idx === selectedRouteIndex;
          const summary = route.summary || {};
          const isRec = route.recommendation?.is_recommended || idx === 0;

          return (
            <div
              key={idx}
              data-testid={`route-card-${idx}`}
              className={`route-card-item ${isSelected ? "✓ CURRENTLY DISPLAYED" : "CLICK TO VIEW ROUTE ON MAP →"}`}
              onClick={() => onSelectRoute(idx)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelectRoute(idx);
              }}
            >
              <div className="card-top-badges">
                {isRec && (
                  <span className="rec-badge" data-testid="recommended-badge">
                    ★ RECOMMENDED
                  </span>
                )}
                {route.recommendation?.tags?.map((tag, tIdx) => (
                  <span key={tIdx} className="mono-sm tag-pill">
                    {tag}
                  </span>
                ))}
                <span className="mono-sm rank-text">
                  RANK #{route.recommendation?.rank || idx + 1}
                </span>
              </div>

              <h4 className="card-route-title">{route.name}</h4>
              <p className="card-via-roads">
                Via: {route.via_roads?.join(" &bull; ") || "Interstate Corridor"}
              </p>

              <div className="card-metrics-grid">
                <div className="metric-cell">
                  <span className="mono-sm">DISTANCE</span>
                  <span className="mono metric-val">{route.distance_miles} mi</span>
                </div>
                <div className="metric-cell">
                  <span className="mono-sm">TIME</span>
                  <span className="mono metric-val">{route.duration_display}</span>
                </div>
                <div className="metric-cell">
                  <span className="mono-sm">MAX RISK</span>
                  <span
                    className="mono metric-val"
                    style={{
                      color: summary.severe_miles > 0 || summary.no_travel_miles > 0 ? "#ef4444" : "var(--color-primary)",
                    }}
                  >
                    {summary.max_risk_label || "Low"}
                  </span>
                </div>
              </div>

              {/* Segmented Risk Breakdown */}
              <div className="card-risk-bar-wrapper">
                <div className="bar-labels">
                  <span className="mono-sm">CORRIDOR RISK PROFILE</span>
                  <span className="mono-sm" style={{ color: summary.severe_miles > 0 ? "#ef4444" : "var(--color-mid-grey)" }}>
                    {summary.severe_miles || 0} mi Severe
                  </span>
                </div>
                <div className="segmented-bar">
                  <div style={{ flex: summary.low_miles || 1, background: "#22c55e" }} title={`Low: ${summary.low_miles} mi`} />
                  {summary.moderate_miles > 0 && (
                    <div style={{ flex: summary.moderate_miles, background: "#eab308" }} title={`Moderate: ${summary.moderate_miles} mi`} />
                  )}
                  {summary.high_miles > 0 && (
                    <div style={{ flex: summary.high_miles, background: "#f97316" }} title={`High: ${summary.high_miles} mi`} />
                  )}
                  {summary.severe_miles > 0 && (
                    <div style={{ flex: summary.severe_miles, background: "#ef4444" }} title={`Severe: ${summary.severe_miles} mi`} />
                  )}
                  {summary.no_travel_miles > 0 && (
                    <div style={{ flex: summary.no_travel_miles, background: "#ec4899" }} title={`No Travel: ${summary.no_travel_miles} mi`} />
                  )}
                </div>
              </div>

              <p className="card-explanation">
                {route.recommendation?.explanation || "Analyzed alternative route."}
              </p>

              <div className="card-click-cta">
                <span className="mono-sm">
                  {isSelected ? "✓ CURRENTLY DISPLAYED" : "CLICK TO VIEW ROUTE ON MAP →"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
