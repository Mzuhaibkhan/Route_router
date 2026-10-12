import React, { useMemo, useState } from "react";
import polyline from "@mapbox/polyline";
import "./MapView.css";

// Map bounds for default US corridor (Texas / Southwest)
const MAP_BOUNDS = {
  minLat: 29.2,
  maxLat: 33.2,
  minLng: -97.6,
  maxLng: -94.8,
};

export default function MapView({
  routes = [],
  selectedRouteIndex = 0,
  onSelectRoute,
  hourOffset = 0,
  heatmap = [],
  riskLegend = {},
}) {
  const [activeCheckpoint, setActiveCheckpoint] = useState(null);

  const selectedRoute = routes[selectedRouteIndex] || routes[0];

  // Helper projection function from lat/lng to SVG percentage (width 800, height 650)
  function project(lat, lng) {
    const x = ((lng - MAP_BOUNDS.minLng) / (MAP_BOUNDS.maxLng - MAP_BOUNDS.minLng)) * 800;
    const y = ((MAP_BOUNDS.maxLat - lat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat)) * 650;
    return {
      x: Math.max(30, Math.min(770, x)),
      y: Math.max(30, Math.min(620, y)),
    };
  }

  // Decode polylines or use checkpoint coordinates
  const decodedPaths = useMemo(() => {
    return routes.map((r) => {
      if (r.encoded_geometry) {
        try {
          const coords = polyline.decode(r.encoded_geometry);
          return coords.map(([lat, lng]) => project(lat, lng));
        } catch {
          // fallback to checkpoints
        }
      }
      return (r.checkpoints || []).map((cp) => {
        const c = cp.coord || cp;
        return project(c.lat, c.lng);
      });
    });
  }, [routes]);

  // Interpolated Truck Position along selected route based on hourOffset
  const truckPos = useMemo(() => {
    if (!selectedRoute || !selectedRoute.checkpoints || selectedRoute.checkpoints.length === 0) {
      return null;
    }
    const cps = selectedRoute.checkpoints;
    const totalDurationMin = (selectedRoute.duration_seconds || 14400) / 60;
    const elapsedMinutes = (hourOffset % 5) * 60;
    const ratio = Math.min(1, Math.max(0, elapsedMinutes / totalDurationMin));

    const targetMin = ratio * totalDurationMin;
    for (let i = 0; i < cps.length - 1; i++) {
      const c1 = cps[i];
      const c2 = cps[i + 1];
      const m1 = c1.cumulative_miles || c1.mile || i * 25;
      const m2 = c2.cumulative_miles || c2.mile || (i + 1) * 25;
      if (m1 <= targetMin && targetMin <= m2) {
        const segRatio = (targetMin - m1) / Math.max(1, m2 - m1);
        const p1 = project(c1.coord?.lat || c1.lat, c1.coord?.lng || c1.lng);
        const p2 = project(c2.coord?.lat || c2.lat, c2.coord?.lng || c2.lng);
        return {
          x: p1.x + (p2.x - p1.x) * segRatio,
          y: p1.y + (p2.y - p1.y) * segRatio,
        };
      }
    }
    const last = cps[cps.length - 1];
    return project(last.coord?.lat || last.lat, last.coord?.lng || last.lng);
  }, [selectedRoute, hourOffset]);

  // Legend fallback
  const legend = {
    0: { label: "Low", color: "#22c55e" },
    1: { label: "Moderate", color: "#eab308" },
    2: { label: "High", color: "#f97316" },
    3: { label: "Severe", color: "#ef4444" },
    4: { label: "No Travel", color: "#ec4899" },
    ...riskLegend,
  };

  return (
    <div className="map-view-root" data-testid="leaflet-map">
      <div className="map-view-header">
        <div className="map-title-row">
          <span className="mono-sm map-tag">CORRIDOR RADAR</span>
          <h4>Texas Freight Corridor & Atmospheric Risk Telemetry</h4>
        </div>

        <div className="map-legend-row">
          {Object.entries(legend).map(([lvl, item]) => (
            <div key={lvl} className="legend-chip">
              <span className="legend-chip-dot" style={{ background: item.color }} />
              <span className="mono-sm">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="map-canvas-container">
        <svg
          viewBox="0 0 800 650"
          className="map-svg"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Interactive route map and weather heatmap"
        >
          <defs>
            <pattern id="mapGridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 195, 42, 0.04)" strokeWidth="1" />
            </pattern>
            <filter id="radarGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Dark Cartographic Base */}
          <rect width="800" height="650" fill="var(--color-surface-black)" />
          <rect width="800" height="650" fill="url(#mapGridPattern)" />

          {/* Geographic Metro Anchor Labels */}
          <circle cx="210" cy="80" r="40" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="4 4" />
          <text x="210" y="80" className="metro-label">DALLAS METRO</text>

          <circle cx="630" cy="580" r="45" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="4 4" />
          <text x="630" y="580" className="metro-label">HOUSTON TERMINAL</text>

          {/* 49-Hour Corridor Heatmap Grid Cells */}
          {heatmap.map((cell, idx) => {
            const p = project(cell.coord?.lat || cell.lat, cell.coord?.lng || cell.lng);
            const riskLvl = typeof cell.forecasts === "object" ? Object.values(cell.forecasts)[0] || 0 : cell.riskLevel || 0;
            const color = legend[riskLvl]?.color || "#22c55e";
            return (
              <rect
                key={idx}
                x={p.x - 26}
                y={p.y - 26}
                width="52"
                height="52"
                rx="6"
                fill={color}
                fillOpacity="0.12"
                stroke={color}
                strokeWidth="0.8"
                strokeOpacity="0.4"
                className="heatmap-cell"
              />
            );
          })}

          {/* Alternative Routes (Inactive) */}
          {routes.map((route, i) => {
            if (i === selectedRouteIndex) return null;
            const pts = (decodedPaths[i] || []).map((p) => `${p.x},${p.y}`).join(" ");
            return (
              <polyline
                key={i}
                points={pts}
                fill="none"
                stroke="rgba(255, 255, 255, 0.18)"
                strokeWidth="3.5"
                strokeDasharray="6 4"
                className="inactive-route-poly"
                onClick={() => onSelectRoute(i)}
                style={{ cursor: "pointer" }}
              />
            );
          })}

          {/* Selected Route Risk-Colored Segment Lines */}
          {selectedRoute &&
            (selectedRoute.checkpoints || []).map((cp, idx, arr) => {
              if (idx === arr.length - 1) return null;
              const next = arr[idx + 1];
              const p1 = project(cp.coord?.lat || cp.lat, cp.coord?.lng || cp.lng);
              const p2 = project(next.coord?.lat || next.lat, next.coord?.lng || next.lng);
              const lvl = cp.risk?.adjusted_level ?? cp.risk?.adjustedLevel ?? 0;
              const color = legend[lvl]?.color || "#22c55e";

              return (
                <line
                  key={`seg-${idx}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke={color}
                  strokeWidth="6"
                  strokeLinecap="round"
                  filter="url(#radarGlow)"
                />
              );
            })}

          {/* Checkpoint Circles */}
          {selectedRoute &&
            (selectedRoute.checkpoints || []).map((cp, idx) => {
              const p = project(cp.coord?.lat || cp.lat, cp.coord?.lng || cp.lng);
              const lvl = cp.risk?.adjusted_level ?? cp.risk?.adjustedLevel ?? 0;
              const color = legend[lvl]?.color || "#22c55e";
              const isSelected = activeCheckpoint?.index === cp.index;

              return (
                <g
                  key={idx}
                  onClick={() => setActiveCheckpoint(cp)}
                  className="checkpoint-group"
                  style={{ cursor: "pointer" }}
                >
                  {lvl >= 3 && (
                    <circle cx={p.x} cy={p.y} r="16" fill="none" stroke={color} strokeWidth="1" className="radar-ping" />
                  )}
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={isSelected ? "9" : "6.5"}
                    fill={color}
                    stroke="#080808"
                    strokeWidth="2"
                  />
                  <circle cx={p.x} cy={p.y} r="2.5" fill="#ffffff" />
                  <text x={p.x + 10} y={p.y + 4} className="node-text">
                    MP {Math.round(cp.cumulative_miles || cp.mile || idx * 25)}
                  </text>
                </g>
              );
            })}

          {/* Animated Moving Truck Marker */}
          {truckPos && (
            <g transform={`translate(${truckPos.x - 14}, ${truckPos.y - 14})`} className="truck-marker-group">
              <circle cx="14" cy="14" r="18" fill="rgba(255, 195, 42, 0.2)" stroke="var(--color-primary)" strokeWidth="1.5" />
              <circle cx="14" cy="14" r="10" fill="var(--color-dark-charcoal)" />
              <text x="14" y="18" textAnchor="middle" fill="var(--color-primary)" fontSize="10" fontFamily="sans-serif">&#9654;</text>
            </g>
          )}
        </svg>

        {/* Checkpoint Detail Pop-over Card */}
        {activeCheckpoint && (
          <div className="checkpoint-popover">
            <div className="popover-header">
              <div>
                <span className="mono-sm" style={{ color: "var(--color-primary)" }}>
                  NODE #{activeCheckpoint.index} &bull; MP {(activeCheckpoint.cumulative_miles || activeCheckpoint.mile || 0).toFixed(1)}
                </span>
                <h5>{activeCheckpoint.name || `Checkpoint Mile ${activeCheckpoint.index * 25}`}</h5>
              </div>
              <button type="button" className="popover-close-btn" onClick={() => setActiveCheckpoint(null)} aria-label="Close details">&times;</button>
            </div>

            <div className="popover-grid">
              <div className="popover-item">
                <span className="mono-sm">WIND</span>
                <p><strong>{activeCheckpoint.weather?.wind_mph || 18} mph</strong></p>
              </div>
              <div className="popover-item">
                <span className="mono-sm">GUSTS</span>
                <p><strong>{activeCheckpoint.weather?.wind_gusts_mph || 25} mph</strong></p>
              </div>
              <div className="popover-item">
                <span className="mono-sm">RAIN</span>
                <p><strong>{activeCheckpoint.weather?.rain_in_hr || 0} in/hr</strong></p>
              </div>
              <div className="popover-item">
                <span className="mono-sm">TEMP</span>
                <p><strong>{activeCheckpoint.weather?.temperature_f || 70}&deg;F</strong></p>
              </div>
            </div>

            <div className="popover-risk">
              <span className="mono-sm">STATUS: </span>
              <strong style={{ color: legend[activeCheckpoint.risk?.adjusted_level ?? activeCheckpoint.risk?.adjustedLevel ?? 0]?.color }}>
                {activeCheckpoint.risk?.label || "Low"}
              </strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
