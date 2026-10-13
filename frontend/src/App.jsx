import React, { useState, useEffect, useMemo, useRef } from "react";
import Lenis from "lenis";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Preloader from "./components/Preloader/Preloader";
import Navbar from "./components/Navbar/Navbar";
import Menu from "./components/Menu/Menu";
import RouteForm from "./components/RouteForm/RouteForm";
import MapView from "./components/MapView/MapView";
import ForecastSlider from "./components/ForecastSlider/ForecastSlider";
import RouteCards from "./components/RouteCards/RouteCards";
import LoadingOverlay from "./components/LoadingOverlay/LoadingOverlay";
import WarningBanner from "./components/WarningBanner/WarningBanner";
import CheckpointTable from "./components/CheckpointTable/CheckpointTable";
import RiskSandbox from "./components/RiskSandbox/RiskSandbox";
import PrivacyPolicy from "./components/Pages/PrivacyPolicy";
import TermsAndConditions from "./components/Pages/TermsAndConditions";
import NotFound from "./components/Pages/NotFound";
import { analyzeRoutes, fetchDemo } from "./services/api";

import dallasHoustonFixture from "./fixtures/dallas_houston.json";
import laPhoenixFixture from "./fixtures/la_phoenix.json";
import RectangularTextReveal from "./components/Rectangular_text_reveal/Rectangular_text_reveal";
import SpiderParticles from "./components/Spider-particles-background/Spider_particles";


export default function App() {
  const [currentPath, setCurrentPath] = useState(() => {
    if (typeof window !== "undefined") {
      return window.location.pathname || "/";
    }
    return "/";
  });

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [origin, setOrigin] = useState("Dallas, TX");
  const [destination, setDestination] = useState("Houston, TX");
  const [loadWeight, setLoadWeight] = useState(35000);
  const [interval, setIntervalOption] = useState("auto");

  const [hourOffset, setHourOffset] = useState(0);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStage, setAnalysisStage] = useState(1);
  const [analysisData, setAnalysisData] = useState(dallasHoustonFixture);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSiteReady, setIsSiteReady] = useState(false);
  const lenisRef = useRef(null);

  // Initialize Lenis smooth scroll for the entire website
  useEffect(() => {
    if (typeof window === "undefined") return;

    let lenis;
    try {
      lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        orientation: "vertical",
        gestureOrientation: "vertical",
        smoothWheel: true,
        wheelMultiplier: 1,
        touchMultiplier: 1.5,
        infinite: false,
        autoRaf: true,
        anchors: true,
      });

      lenisRef.current = lenis;
      window.lenis = lenis;

      // Sync Lenis with GSAP ScrollTrigger
      lenis.on("scroll", () => {
        try {
          ScrollTrigger?.update?.();
        } catch {
          // ignore in testing
        }
      });
    } catch {
      // Graceful fallback for non-browser/test environments
    }

    return () => {
      try {
        lenis?.destroy();
      } catch {}
      lenisRef.current = null;
      if (window.lenis === lenis) {
        window.lenis = null;
      }
    };
  }, []);

  // Pause smooth scroll when mobile/fullscreen menu overlay is open
  useEffect(() => {
    if (!lenisRef.current) return;
    if (isMenuOpen) {
      lenisRef.current.stop();
    } else {
      lenisRef.current.start();
    }
  }, [isMenuOpen]);

  // Handle browser back and forward navigation
  useEffect(() => {
    const handlePop = () => {
      setCurrentPath(window.location.pathname || "/");
    };
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  // Clean URL slug navigation with Lenis smooth scrolling
  function navigateTo(path) {
    if (path.startsWith("#")) {
      if (currentPath !== "/") {
        window.history.pushState({}, "", "/" + path);
        setCurrentPath("/");
        setTimeout(() => {
          if (lenisRef.current) {
            lenisRef.current.scrollTo(path, { offset: -88, duration: 1.2 });
          } else {
            const el = document.querySelector(path);
            el?.scrollIntoView({ behavior: "smooth" });
          }
        }, 120);
      } else {
        if (lenisRef.current) {
          lenisRef.current.scrollTo(path, { offset: -88, duration: 1.2 });
        } else {
          const el = document.querySelector(path);
          el?.scrollIntoView({ behavior: "smooth" });
        }
      }
      return;
    }

    window.history.pushState({}, "", path);
    setCurrentPath(path);
    if (lenisRef.current) {
      lenisRef.current.scrollTo(0, { immediate: true });
    } else {
      window.scrollTo({ top: 0, behavior: "instant" });
    }
  }

  // Handle analysis
  async function handleAnalyze(params) {
    setIsAnalyzing(true);
    setErrorMessage("");
    setAnalysisStage(1);

    const stageTimer1 = setTimeout(() => setAnalysisStage(2), 500);
    const stageTimer2 = setTimeout(() => setAnalysisStage(3), 1000);

    try {
      const data = await analyzeRoutes(params);
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      setAnalysisData(data);
      setSelectedRouteIndex(0);
      setHourOffset(0);
    } catch (err) {
      setErrorMessage(err.message || "Failed to analyze routes.");
    } finally {
      setIsAnalyzing(false);
      setAnalysisStage(1);
    }
  }

  // Handle instant demo fixture loading
  async function handleTryDemo(preset = "dallas-houston") {
    if (currentPath !== "/") {
      navigateTo("/");
    }
    setIsAnalyzing(true);
    setAnalysisStage(1);
    setErrorMessage("");

    setTimeout(async () => {
      const data = await fetchDemo(preset);
      setAnalysisData(data);
      setOrigin(data.origin?.name || "Dallas, TX");
      setDestination(data.destination?.name || "Houston, TX");
      setLoadWeight(data.load_weight_lbs || 35000);
      setSelectedRouteIndex(0);
      setHourOffset(0);
      setIsAnalyzing(false);
    }, 400);
  }

  const routes = analysisData.routes || [];

  // Dynamic in-memory route evaluation across hour offset without network requests
  const dynamicallyEvaluatedRoutes = useMemo(() => {
    return routes.map((r) => {
      if (hourOffset === 0) return r;

      const updatedCheckpoints = (r.checkpoints || []).map((cp) => {
        const baseWind = cp.weather?.wind_mph || 20;
        const hourFactor = Math.max(0, 1 - Math.abs(hourOffset - 3) * 0.15);
        const simWind = Math.round(baseWind * (0.8 + 0.4 * hourFactor));

        let lvl = 0;
        if (simWind >= 55) lvl = 4;
        else if (simWind >= 45) lvl = loadWeight > 30000 ? 4 : 3;
        else if (simWind >= 35) lvl = loadWeight > 40000 ? 3 : 2;
        else if (simWind >= 25) lvl = 1;

        const labels = ["Low", "Moderate", "High", "Severe", "No Travel"];
        return {
          ...cp,
          weather: { ...cp.weather, wind_mph: simWind },
          risk: {
            ...cp.risk,
            adjusted_level: lvl,
            label: labels[lvl],
          },
        };
      });

      return {
        ...r,
        checkpoints: updatedCheckpoints,
      };
    });
  }, [routes, hourOffset, loadWeight]);

  const activeRoute = dynamicallyEvaluatedRoutes[selectedRouteIndex] || dynamicallyEvaluatedRoutes[0];
  const hasNoTravel = (activeRoute?.checkpoints || []).some(
    (cp) => (cp.risk?.adjusted_level ?? cp.risk?.adjustedLevel) === 4
  );

  return (
    <>
      <Preloader onComplete={() => setIsSiteReady(true)} />

      <Navbar
        isMenuOpen={isMenuOpen}
        onToggleMenu={() => setIsMenuOpen(!isMenuOpen)}
        onNavigate={navigateTo}
      />

      <Menu
        isOpen={isMenuOpen}
        onClose={() => setIsMenuOpen(false)}
        onSelectPreset={handleTryDemo}
        onNavigate={navigateTo}
      />

      {isAnalyzing && <LoadingOverlay stage={analysisStage} />}

      <main className="main-content" id="top">
        {currentPath === "/privacy" ? (
          <PrivacyPolicy onNavigate={navigateTo} />
        ) : currentPath === "/terms" ? (
          <TermsAndConditions onNavigate={navigateTo} />
        ) : currentPath !== "/" && currentPath !== "" ? (
          <NotFound onNavigate={navigateTo} currentPath={currentPath} />
        ) : (
          <>
            {/* Hero Section */}
            <header className="hero-section">
              <div className="container hero-container">
                <div className="hero-text-card">
                  <div className="hero-kicker-wrapper">
                    <span className="mono-sm hero-kicker">ATMOSPHERIC RADAR &bull; FLEET WEATHER RISK ENGINE</span>
                  </div>
                  <RectangularTextReveal
                    as="h1"
                    className="hero-title"
                    baseColor="#ffc32a"
                    overlayColor="#171717"
                    direction="bottom"
                    ready={isSiteReady}
                    coverDuration={0.4}
                    revealDuration={0.5}
                    overlayEnterDuration={0.35}
                    overlayExitDuration={0.35}
                  >
                    Precision answers for every mile of heavy ground a transport rig crosses.
                  </RectangularTextReveal>
                  <RectangularTextReveal
                    as="p"
                    className="hero-subtitle"
                    baseColor="#ffc32a"
                    overlayColor="#171717"
                    direction="bottom"
                    ready={isSiteReady}
                    delay={0.25}
                    coverDuration={0.4}
                    revealDuration={0.5}
                    overlayEnterDuration={0.35}
                    overlayExitDuration={0.35}
                  >
                    Pre-departure highway telemetry, 49-hour atmospheric radar, and dynamic load stability thresholds for commercial freight.
                  </RectangularTextReveal>
                </div>
              </div>
            </header>

            {/* Advisor Console Section */}
            <section id="advisor-console" className="advisor-console-section">
              <div className="container">
                {/* Warning & Departure Advisory Banners */}
                <WarningBanner
                  hasNoTravel={hasNoTravel}
                  departureAdvice={analysisData.best_departure_window}
                  warnings={analysisData.warnings}
                  onApplyDeparture={() => setHourOffset(3)}
                />

                {/* Input Form */}
                <RouteForm
                  origin={origin}
                  setOrigin={setOrigin}
                  destination={destination}
                  setDestination={setDestination}
                  loadWeight={loadWeight}
                  setLoadWeight={setLoadWeight}
                  interval={interval}
                  setIntervalOption={setIntervalOption}
                  onAnalyze={handleAnalyze}
                  onTryDemo={() => handleTryDemo("dallas-houston")}
                  isAnalyzing={isAnalyzing}
                  errorMessage={errorMessage}
                />

                {/* Interactive Corridor Map */}
                <div id="corridor-radar">
                  <MapView
                    routes={dynamicallyEvaluatedRoutes}
                    selectedRouteIndex={selectedRouteIndex}
                    onSelectRoute={setSelectedRouteIndex}
                    hourOffset={hourOffset}
                    heatmap={analysisData.heatmap || []}
                    riskLegend={analysisData.risk_legend || {}}
                  />
                </div>

                {/* 0-48h In-Memory Forecast Slider */}
                <ForecastSlider
                  hourOffset={hourOffset}
                  onChangeHour={setHourOffset}
                />

                {/* Comparative Alternative Route Cards */}
                <RouteCards
                  routes={dynamicallyEvaluatedRoutes}
                  selectedRouteIndex={selectedRouteIndex}
                  onSelectRoute={setSelectedRouteIndex}
                  riskLegend={analysisData.risk_legend || {}}
                />

                {/* Checkpoint Table Audit Log */}
                <div id="audit-table">
                  <CheckpointTable
                    route={activeRoute}
                    riskLegend={analysisData.risk_legend || {}}
                  />
                </div>

                {/* Interactive Physics Sandbox */}
                <div id="risk-sandbox">
                  <RiskSandbox />
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      <footer className="footer-root">
        <SpiderParticles
          className="footer-particles-bg"
          particleCount={120}
          particleSize={16.0}
          mouseConnectDist={140}
          spotlightRadius={260}
          particleColor={0xffc32a}
          webColor={0xffc32a}
          centerColor={0xffffff}
          glowColor={0xffc32a}
          particlesGlow={true}
          showUI={false}
        />
        <div className="container footer-inner">
          <div className="footer-left">
            <span className="mono-sm">
              &copy; {new Date().getFullYear()} Route Radar &mdash; Truck Route Safety Advisor
            </span>
            <div className="footer-nav-links">
              <button
                type="button"
                className="footer-link-btn"
                onClick={() => navigateTo("/privacy")}
              >
                Privacy Policy
              </button>
              <span className="footer-separator">&bull;</span>
              <button
                type="button"
                className="footer-link-btn"
                onClick={() => navigateTo("/terms")}
              >
                Terms of Service
              </button>
              <span className="footer-separator">&bull;</span>
              <button
                type="button"
                className="footer-link-btn"
                onClick={() => navigateTo("/404")}
              >
                System Status
              </button>
            </div>
          </div>
          <div className="footer-tagline-badge">
            <span className="mono-sm" style={{ color: "var(--color-primary)" }}>
              Engineered for Commercial Motor Carriers
            </span>
          </div>
        </div>
      </footer>

    </>
  );
}
