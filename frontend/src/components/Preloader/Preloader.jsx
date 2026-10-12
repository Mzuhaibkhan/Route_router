import React, { useEffect, useState } from "react";
import "./Preloader.css";

export default function Preloader({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [rotation, setRotation] = useState(0);
  const [isExiting, setIsExiting] = useState(false);
  const [isHidden, setIsHidden] = useState(false);

  useEffect(() => {
    // 5-step stepped progress bar per design.md specification
    const stepDuration = 350; // ms
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep += 1;
      setProgress((currentStep / 5) * 100);
      setRotation(currentStep * 90);

      if (currentStep >= 5) {
        clearInterval(interval);
        setTimeout(() => {
          setIsExiting(true);
          setTimeout(() => {
            setIsHidden(true);
            onComplete?.();
          }, 800);
        }, 300);
      }
    }, stepDuration);

    return () => clearInterval(interval);
  }, [onComplete]);

  if (isHidden) return null;

  return (
    <div className={`preloader-overlay ${isExiting ? "preloader-exit" : ""}`} aria-hidden="true">
      <div
        className="preloader-progress"
        style={{
          transform: `scaleX(${progress / 100})`,
          transformOrigin: isExiting ? "right center" : "left center",
        }}
      />
      <div className="preloader-center">
        <svg
          width="44"
          height="44"
          viewBox="0 0 40 40"
          className="preloader-radar"
          style={{ transform: `rotate(${rotation}deg)` }}
        >
          <path
            d="M25.5 11.7C23.9 10.6 22 10 20 10V0C24 0 27.8 1.2 31.1 3.4C34.4 5.6 37 8.7 38.5 12.3C40 16 40.4 20 39.6 23.9C38.8 27.8 36.9 31.3 34.1 34.1C31.3 36.9 27.8 38.8 23.9 39.6C20 40.4 16 40 12.3 38.5C8.7 37 5.6 34.4 3.4 31.1C1.2 27.8 0 24 0 20H10C10 22 10.6 23.9 11.7 25.6C12.8 27.2 14.3 28.5 16.2 29.2C18 30 20 30.2 22 29.8C23.9 29.4 25.7 28.5 27.1 27.1C28.5 25.7 29.4 23.9 29.8 22C30.2 20 30 18 29.2 16.2C28.5 14.3 27.2 12.8 25.5 11.7Z"
            fill="var(--color-primary)"
          />
          <path
            d="M10 0C10 1.3 9.7 2.6 9.2 3.8C8.7 5 8 6.1 7.1 7.1C6.1 8 5 8.7 3.8 9.2C2.6 9.7 1.3 10 0 10V20C2.6 20 5.2 19.5 7.7 18.5C10.1 17.5 12.3 16 14.1 14.1C16 12.3 17.5 10.1 18.5 7.7C19.5 5.2 20 2.6 20 0H10Z"
            fill="var(--color-primary)"
          />
        </svg>
        <span className="mono-sm preloader-label">RADAR TELEMETRY</span>
      </div>
    </div>
  );
}
