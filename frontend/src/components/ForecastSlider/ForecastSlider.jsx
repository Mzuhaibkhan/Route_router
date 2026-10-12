import React, { useEffect, useRef, useState } from "react";
import "./ForecastSlider.css";

export default function ForecastSlider({ hourOffset, onChangeHour }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        onChangeHour((h) => (h >= 48 ? 0 : h + 1));
      }, 700);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, onChangeHour]);

  const baseDate = new Date();
  baseDate.setHours(baseDate.getHours() + hourOffset);
  const timeStr = baseDate.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });

  return (
    <div className="forecast-slider-root">
      <div className="slider-header-bar">
        <div>
          <span className="mono-sm slider-tag">TEMPORAL RADAR HORIZON</span>
          <h4 className="slider-heading">+{hourOffset} Hours Forecast Window</h4>
        </div>
        <div className="slider-clock">
          <span className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>ORIGIN LOCAL: </span>
          <span className="mono" style={{ color: "var(--color-primary)" }}>{timeStr}</span>
        </div>
      </div>

      <div className="slider-control-bar">
        <button
          type="button"
          data-testid="slider-play"
          className={`slider-btn ${isPlaying ? "⏸ PAUSE" : "▶ SIMULATE"}`}
          onClick={() => setIsPlaying(!isPlaying)}
        >
          {isPlaying ? "⏸ PAUSE" : "▶ SIMULATE"}
        </button>

        <div className="slider-input-wrapper">
          <input
            type="range"
            min="0"
            max="48"
            step="1"
            value={hourOffset}
            data-testid="forecast-slider"
            onChange={(e) => {
              setIsPlaying(false);
              onChangeHour(Number(e.target.value));
            }}
            className="slider-range-input"
            aria-label="48-hour forecast timeline"
          />
          <div className="slider-ticks">
            <span>Now (0h)</span>
            <span>+12h</span>
            <span>+24h</span>
            <span>+36h</span>
            <span>+48h Max</span>
          </div>
        </div>
      </div>
    </div>
  );
}
