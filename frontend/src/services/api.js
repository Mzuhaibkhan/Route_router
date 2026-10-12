import axios from "axios";
import dallasHoustonFixture from "../fixtures/dallas_houston.json";
import laPhoenixFixture from "../fixtures/la_phoenix.json";

const apiClient = axios.create({
  baseURL: "/",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Autocomplete address query via backend proxy
 */
export async function getAutocomplete(query) {
  if (!query || query.length < 2) return [];
  try {
    const res = await apiClient.get(`/api/geocode/autocomplete`, {
      params: { q: query },
    });
    return res.data?.features || [];
  } catch (err) {
    // Graceful fallback for offline demo
    return [
      { properties: { label: `${query}, USA`, name: query } },
    ];
  }
}

/**
 * Executes route analysis pipeline
 */
export async function analyzeRoutes({
  origin,
  destination,
  load_weight_lbs = 35000,
  departure_utc = Math.floor(Date.now() / 1000),
  interval_miles = null,
}) {
  const payload = {
    origin,
    destination,
    load_weight_lbs: Number(load_weight_lbs),
    departure_utc: Number(departure_utc),
    interval_miles: interval_miles === "auto" ? null : Number(interval_miles),
  };

  try {
    const res = await apiClient.post(`/api/routes/analyze`, payload);
    return res.data;
  } catch (err) {
    console.warn("API request failed or backend offline. Serving demo fixture fallback.", err);
    // Return appropriate fixture matching origin/destination
    if (
      (origin && origin.toLowerCase().includes("phoenix")) ||
      (destination && destination.toLowerCase().includes("phoenix"))
    ) {
      return laPhoenixFixture;
    }
    return dallasHoustonFixture;
  }
}

/**
 * Instant demo fixture loader
 */
export async function fetchDemo(preset = "dallas-houston") {
  try {
    const res = await apiClient.post(`/api/routes/demo`, { preset });
    return res.data;
  } catch {
    return preset === "la-phoenix" ? laPhoenixFixture : dallasHoustonFixture;
  }
}
