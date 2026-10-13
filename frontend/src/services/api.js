import axios from "axios";
import dallasHoustonFixture from "../fixtures/dallas_houston.json";
import laPhoenixFixture from "../fixtures/la_phoenix.json";

const apiClient = axios.create({
  baseURL: "/",
  timeout: 45000,
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
  const numInterval =
    interval_miles === "auto" || interval_miles == null ? null : Number(interval_miles);
  const payload = {
    origin,
    destination,
    load_weight_lbs: Number(load_weight_lbs),
    departure_utc: Number(departure_utc),
    checkpoint_interval_miles: numInterval,
    interval_miles: numInterval,
  };

  try {
    const res = await apiClient.post(`/api/routes/analyze`, payload);
    return res.data;
  } catch (err) {
    const serverError =
      err.response?.data?.error ||
      (typeof err.response?.data?.origin === "string" ? `Origin error: ${err.response.data.origin}` : null) ||
      (Array.isArray(err.response?.data?.origin) ? `Origin error: ${err.response.data.origin[0]}` : null) ||
      (typeof err.response?.data?.destination === "string" ? `Destination error: ${err.response.data.destination}` : null) ||
      (Array.isArray(err.response?.data?.destination) ? `Destination error: ${err.response.data.destination[0]}` : null) ||
      (typeof err.response?.data?.load_weight_lbs === "string" ? `Weight error: ${err.response.data.load_weight_lbs}` : null) ||
      (Array.isArray(err.response?.data?.non_field_errors) ? err.response.data.non_field_errors[0] : null) ||
      (typeof err.response?.data === "string" ? err.response.data : null) ||
      (err.code === "ECONNABORTED" ? "Route analysis timed out. Long-distance routing or external APIs took longer than 45s." : null) ||
      (err.message === "Network Error" ? "Network Error: Could not connect to backend on port 8000. Please ensure the backend is running." : null) ||
      err.message;

    console.error("API analysis failed:", serverError, err);
    throw new Error(serverError || "Failed to analyze routes.");
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
