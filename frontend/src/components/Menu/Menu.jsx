import React from "react";
import "./Menu.css";

export default function Menu({ isOpen, onClose, onSelectPreset, onNavigate }) {
  const menuLinks = [
    { label: "Route Advisor", href: "#advisor-console" },
    { label: "Corridor Radar", href: "#corridor-radar" },
    { label: "Risk Engine", href: "#risk-sandbox" },
    { label: "Fleet Telemetry", href: "#advisor-console" },
    { label: "Audit & Checkpoints", href: "#audit-table" },
  ];

  function handleLinkClick(e, href) {
    e.preventDefault();
    if (onNavigate) {
      onNavigate(href);
    }
    onClose();
  }

  return (
    <div
      className={`menu-overlay ${isOpen ? "menu-open" : ""}`}
      data-lenis-prevent
      aria-hidden={!isOpen}
    >
      <div className="container menu-body">
        <div className="menu-col">
          <div className="menu-links">
            {menuLinks.map((link) => (
              <div key={link.label} className="menu-link-wrapper">
                <h1>
                  <a
                    href={link.href}
                    className="menu-nav-link"
                    onClick={(e) => handleLinkClick(e, link.href)}
                  >
                    {link.label}
                    <span className="menu-underline" />
                  </a>
                </h1>
              </div>
            ))}
          </div>

          <div className="quick-routes-panel">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>
              DIRECT CORRIDOR PRESETS
            </span>
            <div className="quick-routes-buttons">
              <button
                type="button"
                className="quick-route-btn"
                onClick={() => {
                  onSelectPreset("dallas-houston");
                  onClose();
                }}
              >
                Dallas, TX &rarr; Houston, TX (I-45 S Corridor)
              </button>
              <button
                type="button"
                className="quick-route-btn"
                onClick={() => {
                  onSelectPreset("la-phoenix");
                  onClose();
                }}
              >
                Los Angeles, CA &rarr; Phoenix, AZ (I-10 E Corridor)
              </button>
            </div>
          </div>
        </div>

        <div className="menu-footer">
          <div className="menu-sub-col">
            <p className="mono-sm">FLEET RADAR TELEMETRY</p>
            <p className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>
              Commercial Fleet Safety v1.4
            </p>
            <br />
            <p className="mono-sm">CORRIDOR LIMITS</p>
            <p className="mono-sm" style={{ color: "var(--color-mid-grey)" }}>
              &ge; 55 MPH Universal Ground Stop
            </p>
          </div>

          <div className="menu-sub-col">
            <p className="mono-sm">DISPATCH OPERATIONS</p>
            <p className="mono-sm">dispatch@routeradar.io</p>
            <br />
            <p className="mono-sm">LEGAL & REGULATORY</p>
            <div className="menu-legal-links">
              <a
                href="/privacy"
                className="menu-legal-link"
                onClick={(e) => handleLinkClick(e, "/privacy")}
              >
                Privacy Policy
              </a>
              <span className="mono-sm" style={{ color: "var(--color-medium-grey)" }}>&bull;</span>
              <a
                href="/terms"
                className="menu-legal-link"
                onClick={(e) => handleLinkClick(e, "/terms")}
              >
                Terms of Service
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
