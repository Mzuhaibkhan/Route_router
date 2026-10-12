import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../App";
import * as api from "../services/api";
import dallasHoustonFixture from "../fixtures/dallas_houston.json";

describe("Route Radar Frontend Test Suite (FE_01 - FE_14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
  });

  // FE_01: Form renders with origin and destination inputs
  it("FE_01: renders origin and destination form inputs", () => {
    render(<App />);
    expect(screen.getByTestId("origin-input")).toBeInTheDocument();
    expect(screen.getByTestId("destination-input")).toBeInTheDocument();
  });

  // FE_02: Shows validation error when required fields are empty
  it("FE_02: displays error when origin or destination is empty on submit", () => {
    render(<App />);
    const originInput = screen.getByTestId("origin-input");
    const submitBtn = screen.getByTestId("analyze-button");

    fireEvent.change(originInput, { target: { value: "" } });
    fireEvent.click(submitBtn);

    expect(screen.getByTestId("error-message")).toBeInTheDocument();
    expect(screen.getByTestId("error-message")).toHaveTextContent(/Origin location is required/i);
  });

  // FE_03: Weight input enforces numeric type
  it("FE_03: weight input is of numeric type with range bounds", () => {
    render(<App />);
    const weightInput = screen.getByTestId("weight-input");
    expect(weightInput).toHaveAttribute("type", "number");
    expect(weightInput).toHaveAttribute("min", "1000");
    expect(weightInput).toHaveAttribute("max", "80000");
  });

  // FE_04: Staged loading overlay displays during analysis
  it("FE_04: staged loading overlay appears when analyzing routes", async () => {
    vi.spyOn(api, "analyzeRoutes").mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(dallasHoustonFixture), 500))
    );

    render(<App />);
    const submitBtn = screen.getByTestId("analyze-button");
    fireEvent.click(submitBtn);

    expect(screen.getByTestId("loading-overlay")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByTestId("loading-overlay")).not.toBeInTheDocument();
    });
  });

  // FE_05: Route cards display summary metrics
  it("FE_05: displays comparative route cards with distance and duration", () => {
    render(<App />);
    expect(screen.getByTestId("route-card-0")).toBeInTheDocument();
    expect(screen.getByText("239.5 mi")).toBeInTheDocument();
    expect(screen.getByText("3h 39m")).toBeInTheDocument();
  });

  // FE_06: Recommended route displays the recommended badge
  it("FE_06: displays recommended badge on the top route candidate", () => {
    render(<App />);
    expect(screen.getByTestId("recommended-badge")).toBeInTheDocument();
    expect(screen.getByTestId("recommended-badge")).toHaveTextContent(/RECOMMENDED/i);
  });

  // FE_07: Map canvas renders
  it("FE_07: initializes and renders the interactive map element", () => {
    render(<App />);
    expect(screen.getByTestId("leaflet-map")).toBeInTheDocument();
  });

  // FE_08: Forecast slider renders with 0-48h bounds
  it("FE_08: renders 0-48h forecast slider", () => {
    render(<App />);
    const slider = screen.getByTestId("forecast-slider");
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute("min", "0");
    expect(slider).toHaveAttribute("max", "48");
  });

  // FE_09: Scrubbing slider performs zero network requests
  it("FE_09: forecast slider scrubs client-side without calling backend", () => {
    const apiSpy = vi.spyOn(api, "analyzeRoutes");
    render(<App />);

    const slider = screen.getByTestId("forecast-slider");
    fireEvent.change(slider, { target: { value: "12" } });

    expect(slider.value).toBe("12");
    expect(screen.getByText(/\+12 Hours Forecast Window/i)).toBeInTheDocument();
    expect(apiSpy).not.toHaveBeenCalled();
  });

  // FE_10: Error banner displays backend errors
  it("FE_10: displays error banner when backend analysis fails", async () => {
    vi.spyOn(api, "analyzeRoutes").mockRejectedValue(new Error("ORS Gateway Timeout"));
    render(<App />);

    const submitBtn = screen.getByTestId("analyze-button");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toBeInTheDocument();
      expect(screen.getByTestId("error-message")).toHaveTextContent(/ORS Gateway Timeout/i);
    });
  });

  // FE_11: No Travel warning banner
  it("FE_11: renders No Travel alert when severe weather triggers vehicle limit", () => {
    render(<App />);
    const slider = screen.getByTestId("forecast-slider");
    // Hour 3 has simulated severe storm in dynamic evaluator
    fireEvent.change(slider, { target: { value: "3" } });

    expect(screen.getByTestId("no-travel-banner")).toBeInTheDocument();
  });

  // FE_12: Departure advice banner
  it("FE_12: renders departure window recommendation banner", () => {
    render(<App />);
    expect(screen.getByTestId("departure-advice")).toBeInTheDocument();
    expect(screen.getByTestId("departure-advice")).toHaveTextContent(/Waiting 3h reduces High risk miles/i);
  });

  // FE_13: Displays pipeline warnings
  it("FE_13: displays pipeline warnings and timezone notices", () => {
    render(<App />);
    expect(screen.getByText(/Departure interpreted as 8:00 AM CDT/i)).toBeInTheDocument();
  });

  // FE_14: Try Demo button populates UI instantly from fixtures
  it("FE_14: try demo button populates UI instantly from fixtures", async () => {
    render(<App />);
    const demoBtn = screen.getByTestId("demo-button");

    fireEvent.click(demoBtn);

    await waitFor(() => {
      expect(screen.getByTestId("origin-input")).toHaveValue("Dallas, TX");
      expect(screen.getByTestId("destination-input")).toHaveValue("Houston, TX");
      expect(screen.getByTestId("route-card-0")).toBeInTheDocument();
    });
  });
  // FE_15: Privacy Policy page renders via routing
  it("FE_15: renders Privacy Policy page when navigating to /privacy", () => {
    window.history.pushState({}, "", "/privacy");
    render(<App />);
    expect(screen.getByText(/Privacy Policy & Telemetry Governance/i)).toBeInTheDocument();
    expect(screen.getByText(/Scope of Telemetry Collection/i)).toBeInTheDocument();
  });

  // FE_16: Terms of Service page renders via routing
  it("FE_16: renders Terms of Service page when navigating to /terms", () => {
    window.history.pushState({}, "", "/terms");
    render(<App />);
    expect(screen.getByText(/Terms of Carrier Service/i)).toBeInTheDocument();
    expect(screen.getByText(/Advisory Decision Support Nature/i)).toBeInTheDocument();
  });

  // FE_17: Custom 404 page renders for unknown route
  it("FE_17: renders custom 404 page for unknown route slug", () => {
    window.history.pushState({}, "", "/invalid-corridor-path");
    render(<App />);
    expect(screen.getByRole("heading", { name: "404" })).toBeInTheDocument();
    expect(screen.getByText(/WAYPOINT TELEMETRY NOT FOUND/i)).toBeInTheDocument();
  });
});
