import React, { useMemo, useState, useEffect, useCallback } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  Tooltip,
  ZoomControl,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./MapView.css";
import polyline from "@mapbox/polyline";

// Continental United States geographic bounds
const USA_BOUNDS = [
  [24.5, -125.0], // Southwest (Key West / Baja)
  [49.5, -66.5],  // Northeast (Maine / Pacific NW)
];

const USA_CENTER = [38.5, -96.5];
const USA_DEFAULT_ZOOM = 4;

/**
 * Controller component inside MapContainer to handle dynamic auto-fitting
 * and manual zoom/recenter interactions.
 */
function MapViewBoundsController({ routes, selectedRouteIndex }) {
  const map = useMap();

  const fitActiveRoute = useCallback(() => {
    const selected = routes[selectedRouteIndex] || routes[0];
    if (!selected) return;

    let points = [];
    if (selected.encoded_geometry) {
      try {
        points = polyline.decode(selected.encoded_geometry);
      } catch {
        // fallback
      }
    }
    if (points.length === 0 && selected.checkpoints?.length) {
      points = selected.checkpoints.map((cp) => [
        cp.coord?.lat ?? cp.lat,
        cp.coord?.lng ?? cp.lng,
      ]);
    }

    if (points.length > 0) {
      try {
        map.fitBounds(points, {
          padding: [45, 45],
          maxZoom: 9,
          animate: true,
        });
      } catch {
        // Safe fallback in test environments
      }
    }
  }, [routes, selectedRouteIndex, map]);

  const fitUSA = useCallback(() => {
    try {
      map.fitBounds(USA_BOUNDS, { padding: [20, 20], animate: true });
    } catch {
      // Safe fallback
    }
  }, [map]);

  // Automatically fit new route whenever route or selection changes
  useEffect(() => {
    fitActiveRoute();
  }, [fitActiveRoute]);

  return (
    <div className="leaflet-custom-controls leaflet-top leaflet-right">
      <div className="leaflet-bar map-view-quick-actions">
        <button
          type="button"
          className="map-action-btn"
          onClick={fitActiveRoute}
          title="Fit Corridor Route in View"
          aria-label="Fit Route"
        >
          ROUTE
        </button>
        <button
          type="button"
          className="map-action-btn"
          onClick={fitUSA}
          title="Reset to Full USA Map"
          aria-label="View Full USA"
        >
          USA
        </button>
      </div>
    </div>
  );
}

/**
 * Interactive Polyline component for concurrent route display and hover highlight.
 */
function InteractiveRouteLine({
  route,
  index,
  positions,
  isSelected,
  onSelectRoute,
}) {
  const [isHovered, setIsHovered] = useState(false);

  const eventHandlers = useMemo(
    () => ({
      mouseover: () => setIsHovered(true),
      mouseout: () => setIsHovered(false),
      click: () => onSelectRoute(index),
    }),
    [index, onSelectRoute]
  );

  const shouldHighlight = isSelected || isHovered;
  const strokeColor = isSelected
    ? "#ffc32a"
    : isHovered
    ? "#ffffff"
    : "rgba(255, 255, 255, 0.28)";

  return (
    <Polyline
      positions={positions}
      pathOptions={{
        color: strokeColor,
        weight: shouldHighlight ? 6 : 3.5,
        opacity: isSelected ? 0.95 : isHovered ? 0.9 : 0.45,
        dashArray: isSelected ? undefined : "6 6",
        lineCap: "round",
        lineJoin: "round",
      }}
      eventHandlers={eventHandlers}
    >
      <Tooltip sticky className="route-hover-tooltip">
        <div className="route-tooltip-content">
          <strong>{route.name || `Route ${index + 1}`}</strong>
          <span>
            {route.distance_miles ? `${route.distance_miles} mi` : ""}{" "}
            {route.duration_display ? `• ${route.duration_display}` : ""}
          </span>
          {!isSelected && <span className="tooltip-action">Click to view on radar →</span>}
        </div>
      </Tooltip>
    </Polyline>
  );
}

export default function MapView({
  routes = [],
  selectedRouteIndex = 0,
  onSelectRoute,
  hourOffset = 0,
  heatmap = [],
  riskLegend = {},
}) {
  const selectedRoute = routes[selectedRouteIndex] || routes[0];

  // Decode polylines for all routes concurrently
  const decodedPaths = useMemo(() => {
    return routes.map((route) => {
      if (route.encoded_geometry) {
        try {
          const coords = polyline.decode(route.encoded_geometry);
          return coords.map(([lat, lng]) => [lat, lng]);
        } catch {
          // fallback
        }
      }
      return (route.checkpoints || []).map((cp) => {
        const c = cp.coord || cp;
        return [c.lat, c.lng];
      });
    });
  }, [routes]);

  // Legend fallback
  const legend = useMemo(() => {
    return {
      0: { label: "Low", color: "#22c55e" },
      1: { label: "Moderate", color: "#eab308" },
      2: { label: "High", color: "#f97316" },
      3: { label: "Severe", color: "#ef4444" },
      4: { label: "No Travel", color: "#ec4899" },
      ...riskLegend,
    };
  }, [riskLegend]);

  const getRiskColor = (lvl) => {
    return legend[lvl]?.color || "#22c55e";
  };

  const corridorTitle = selectedRoute?.name
    ? `${selectedRoute.name} Telemetry`
    : "Commercial Freight Corridor & Atmospheric Risk Telemetry";

  return (
    <div className="map-view-root" data-testid="leaflet-map">
      {/* Map Header with Corridor Tag and Risk Legend */}
      <div className="map-view-header">
        <div className="map-title-row">
          <span className="mono-sm map-tag">CORRIDOR RADAR</span>
          <h4>{corridorTitle}</h4>
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

      {/* Main Leaflet Map Viewport */}
      <div className="map-canvas-container">
        <MapContainer
          center={USA_CENTER}
          zoom={USA_DEFAULT_ZOOM}
          minZoom={3}
          maxZoom={14}
          zoomControl={false} // Custom zoom buttons positioned on right side
          scrollWheelZoom={false} // Disabled so trackpad/wheel scrolling moves page normally
          dragging={true} // Drag to pan
          doubleClickZoom={true}
          boxZoom={true}
          keyboard={true}
          className="leaflet-map"
        >
          {/* 100% Free OpenStreetMap Base Tiles (No API key required) */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
            className="osm-dark-tiles"
          />

          {/* Zoom controls placed on the right side */}
          <ZoomControl position="topright" />

          {/* Dynamic route auto-fitter and Quick Navigation controls */}
          <MapViewBoundsController
            routes={routes}
            selectedRouteIndex={selectedRouteIndex}
          />

          {/* 1. Heatmap density overlay cells */}
          {heatmap.map((cell, idx) => {
            const riskLvl =
              typeof cell.forecasts === "object"
                ? Object.values(cell.forecasts)[0] || 0
                : cell.riskLevel || 0;
            const color = getRiskColor(riskLvl);
            const lat = cell.coord?.lat ?? cell.lat;
            const lng = cell.coord?.lng ?? cell.lng;
            if (lat == null || lng == null) return null;

            return (
              <CircleMarker
                key={`heat-${idx}`}
                center={[lat, lng]}
                radius={20}
                pathOptions={{
                  color: color,
                  fillColor: color,
                  fillOpacity: 0.12,
                  weight: 0.8,
                  opacity: 0.35,
                }}
              />
            );
          })}

          {/* 2. All Routes Rendered Concurrently with Hover Highlighting */}
          {routes.map((route, idx) => {
            const positions = decodedPaths[idx];
            if (!positions || positions.length === 0) return null;

            return (
              <InteractiveRouteLine
                key={`route-${idx}-${route.index ?? idx}`}
                route={route}
                index={idx}
                positions={positions}
                isSelected={idx === selectedRouteIndex}
                onSelectRoute={onSelectRoute}
              />
            );
          })}

          {/* 3. Selected Route Risk-Colored Segments */}
          {selectedRoute?.checkpoints && (
            <>
              {selectedRoute.checkpoints.map((cp, idx, arr) => {
                if (idx === arr.length - 1) return null;
                const next = arr[idx + 1];
                const p1 = [cp.coord?.lat ?? cp.lat, cp.coord?.lng ?? cp.lng];
                const p2 = [next.coord?.lat ?? next.lat, next.coord?.lng ?? next.lng];
                const lvl = cp.risk?.adjusted_level ?? cp.risk?.adjustedLevel ?? 0;
                const color = getRiskColor(lvl);

                return (
                  <Polyline
                    key={`risk-seg-${idx}`}
                    positions={[p1, p2]}
                    pathOptions={{
                      color: color,
                      weight: 7,
                      opacity: 0.85,
                      lineCap: "round",
                    }}
                  />
                );
              })}
            </>
          )}

          {/* 4. Checkpoints along Selected Route with Lat/Lng & Weather Popup */}
          {selectedRoute?.checkpoints && (
            <>
              {selectedRoute.checkpoints.map((cp, idx) => {
                const lat = cp.coord?.lat ?? cp.lat;
                const lng = cp.coord?.lng ?? cp.lng;
                if (lat == null || lng == null) return null;

                const lvl = cp.risk?.adjusted_level ?? cp.risk?.adjustedLevel ?? 0;
                const riskColor = getRiskColor(lvl);
                const riskLabel = cp.risk?.label || legend[lvl]?.label || "Low";
                const mile = Math.round(cp.cumulative_miles || cp.mile || idx * 25);
                const locationName = cp.name || `Checkpoint Mile ${mile}`;

                return (
                  <CircleMarker
                    key={`cp-${idx}-${cp.index ?? idx}`}
                    center={[lat, lng]}
                    radius={lvl >= 3 ? 8 : 6.5}
                    pathOptions={{
                      color: "#080808",
                      fillColor: riskColor,
                      fillOpacity: 1.0,
                      weight: 2,
                    }}
                  >
                    {/* Hover Tooltip */}
                    <Tooltip direction="top" offset={[0, -8]} className="checkpoint-tooltip">
                      <span>MP {mile} • {locationName}</span>
                    </Tooltip>

                    {/* Click Popup with Detailed Coordinates, Weather & Risk */}
                    <Popup className="checkpoint-leaflet-popup">
                      <div className="popup-card">
                        <div className="popup-card-header">
                          <span className="mono-sm node-badge" style={{ color: "#ffc32a" }}>
                            NODE #{cp.index ?? idx} • MP {mile}
                          </span>
                          <h5>{locationName}</h5>
                        </div>

                        {/* Latitude & Longitude Block */}
                        <div className="popup-coords-block">
                          <div className="coord-chip">
                            <span className="mono-sm coord-label">LATITUDE</span>
                            <span className="mono coord-val">{Number(lat).toFixed(4)}° N</span>
                          </div>
                          <div className="coord-chip">
                            <span className="mono-sm coord-label">LONGITUDE</span>
                            <span className="mono coord-val">{Number(lng).toFixed(4)}° W</span>
                          </div>
                        </div>

                        {/* Weather Data Grid */}
                        <div className="popup-weather-grid">
                          <div className="weather-item">
                            <span className="mono-sm">WIND</span>
                            <strong>{cp.weather?.wind_mph ?? 18} mph</strong>
                          </div>
                          <div className="weather-item">
                            <span className="mono-sm">GUSTS</span>
                            <strong>{cp.weather?.wind_gusts_mph ?? 24} mph</strong>
                          </div>
                          <div className="weather-item">
                            <span className="mono-sm">RAIN</span>
                            <strong>{cp.weather?.rain_in_hr ?? 0} in/hr</strong>
                          </div>
                          <div className="weather-item">
                            <span className="mono-sm">TEMP</span>
                            <strong>{cp.weather?.temperature_f ?? 68}°F</strong>
                          </div>
                        </div>

                        {/* Risk Status */}
                        <div className="popup-risk-row">
                          <span className="mono-sm">RISK ASSESSMENT:</span>
                          <span
                            className="risk-pill-badge"
                            style={{
                              background: `${riskColor}22`,
                              color: riskColor,
                              border: `1px solid ${riskColor}66`,
                            }}
                          >
                            {riskLabel.toUpperCase()}
                          </span>
                        </div>

                        {/* Contributing Factors */}
                        {cp.risk?.contributing_factors?.length > 0 && (
                          <div className="popup-factors">
                            {cp.risk.contributing_factors.map((f, fIdx) => (
                              <span key={fIdx} className="factor-item">
                                • {f}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </>
          )}
        </MapContainer>
      </div>
    </div>
  );
}
