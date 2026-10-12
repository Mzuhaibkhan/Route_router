import React from "react";
import "./WarningBanner.css";

export default function WarningBanner({
  departureAdvice,
  hasNoTravel = false,
  warnings = [],
  onApplyDeparture,
}) {
  return (
    <div className="warning-banners-root">
      {/* No Travel Alert Banner */}
      {hasNoTravel && (
        <div className="banner-item no-travel-banner" data-testid="no-travel-banner">
          <div className="banner-icon" aria-hidden="true">&#9888;</div>
          <div className="banner-body">
            <span className="mono-sm banner-type">CRITICAL DISPATCH GROUND STOP</span>
            <h4>NO TRAVEL: Route traverses crosswind / atmospheric conditions exceeding safe vehicle threshold.</h4>
            <p>
              Sustained winds exceeding 55 mph or 45–54 mph crosswinds with vehicle load &gt; 30,000 lbs detected. Dispatch hold recommended until squall front clears.
            </p>
          </div>
        </div>
      )}

      {/* Best Departure Window Advice */}
      {departureAdvice && (
        <div className="banner-item departure-advice-banner" data-testid="departure-advice">
          <div className="banner-icon" aria-hidden="true">&#9888;</div>
          <div className="banner-body">
            <span className="mono-sm banner-type">OPTIMAL DEPARTURE WINDOW</span>
            <h4>{departureAdvice.improvement || "Better departure horizon available."}</h4>
            <p>
              Adjusting departure time allows the vehicle to safely navigate after the squall line moves past the corridor.
            </p>
          </div>
          {onApplyDeparture && (
            <button
              type="button"
              className="apply-departure-btn"
              onClick={onApplyDeparture}
            >
              APPLY RECOMMENDED WINDOW
            </button>
          )}
        </div>
      )}

      {/* Pipeline Notices & Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="pipeline-warnings-container">
          {warnings.map((w, idx) => (
            <div key={idx} className={`pipeline-warning-row warning-${w.level || "info"}`}>
              <span className="mono-sm">[{w.code || "NOTICE"}]:</span>
              <span>{w.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
