import React, { useState, useEffect, useRef } from "react";
import "./Navbar.css";

export default function Navbar({ isMenuOpen, onToggleMenu, onNavigate }) {
  const [isVisible, setIsVisible] = useState(true);
  const [isScrolled, setIsScrolled] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      // Track if page is scrolled past threshold for styling
      setIsScrolled(currentScrollY > 20);

      // If menu is open, keep navbar visible at all times
      if (isMenuOpen) {
        setIsVisible(true);
        lastScrollY.current = currentScrollY;
        return;
      }

      // If near the top of the page, always show header
      if (currentScrollY < 60) {
        setIsVisible(true);
      } else if (currentScrollY > lastScrollY.current + 8) {
        // Scrolling down -> hide header
        setIsVisible(false);
      } else if (currentScrollY < lastScrollY.current - 8) {
        // Scrolling up -> show header
        setIsVisible(true);
      }

      lastScrollY.current = currentScrollY;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isMenuOpen]);

  function handleBrandClick(e) {
    e.preventDefault();
    if (onNavigate) {
      onNavigate("/");
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  return (
    <header
      className={`navbar-root ${isVisible ? "navbar-visible" : "navbar-hidden"} ${
        isScrolled ? "navbar-scrolled" : ""
      } ${isMenuOpen ? "navbar-menu-open" : ""}`}
      role="banner"
    >
      <div className="container navbar-inner">
        <a
          href="/"
          onClick={handleBrandClick}
          className="navbar-brand"
          aria-label="Route Radar Home"
        >
          <div className="brand-logo-frame">
            <svg
              width="28"
              height="28"
              viewBox="0 0 40 40"
              fill="none"
              role="img"
              aria-label="Route Radar Radar Logo"
            >
              <title>Route Radar Radar Logo</title>
              <path
                d="M25.5 11.7C23.9 10.6 22 10 20 10V0C24 0 27.8 1.2 31.1 3.4C34.4 5.6 37 8.7 38.5 12.3C40 16 40.4 20 39.6 23.9C38.8 27.8 36.9 31.3 34.1 34.1C31.3 36.9 27.8 38.8 23.9 39.6C20 40.4 16 40 12.3 38.5C8.7 37 5.6 34.4 3.4 31.1C1.2 27.8 0 24 0 20H10C10 22 10.6 23.9 11.7 25.6C12.8 27.2 14.3 28.5 16.2 29.2C18 30 20 30.2 22 29.8C23.9 29.4 25.7 28.5 27.1 27.1C28.5 25.7 29.4 23.9 29.8 22C30.2 20 30 18 29.2 16.2C28.5 14.3 27.2 12.8 25.5 11.7Z"
                fill="var(--color-primary)"
              />
              <path
                d="M10 0C10 1.3 9.7 2.6 9.2 3.8C8.7 5 8 6.1 7.1 7.1C6.1 8 5 8.7 3.8 9.2C2.6 9.7 1.3 10 0 10V20C2.6 20 5.2 19.5 7.7 18.5C10.1 17.5 12.3 16 14.1 14.1C16 12.3 17.5 10.1 18.5 7.7C19.5 5.2 20 2.6 20 0H10Z"
                fill="var(--color-primary)"
              />
            </svg>
          </div>
          <div className="navbar-brand-titles">
            <span className="mono navbar-title">ROUTE RADAR</span>
            <span className="mono-sm navbar-subtitle">FLEET SAFETY ADVISOR</span>
          </div>
        </a>

        <div className="navbar-actions">
          <div className="navbar-live-status">
            <span className="status-indicator-dot" />
            <span className="mono-sm status-text">SYS ONLINE</span>
          </div>

          <button
            type="button"
            className="navbar-toggle"
            onClick={onToggleMenu}
            aria-label="Toggle menu"
            aria-expanded={isMenuOpen}
          >
            <span className="mono-sm toggle-label">
              Menu
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
