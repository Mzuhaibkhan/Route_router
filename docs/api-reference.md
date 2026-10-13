# API Reference

This document provides the complete API specification for Route Radar. All endpoints return JSON payloads and use standard HTTP response codes.

---

## Base URLs
- **Local Development**: `http://localhost:8000`
- **Production (Render)**: `https://<your-service>.onrender.com`

---

## 1. Route Analysis APIs

### 1.1 Analyze Corridor Routes
**`POST /api/routes/analyze`**

The primary pipeline endpoint. Geocodes origin and destination, requests multi-route alternatives, samples corridor checkpoints, queries Open-Meteo forecasts, applies truck load tipping thresholds, evaluates alternative routes, and calculates optimal departure windows.

#### Request Headers
| Header | Value | Required |
|---|---|:---:|
| `Content-Type` | `application/json` | Yes |

#### Request Body Schema
```json
{
  "origin": "Dallas, TX",
  "destination": "Houston, TX",
  "load_weight_lbs": 38000,
  "departure_time": "2026-10-15T08:00:00",
  "departure_utc": 1792051200,
  "checkpoint_interval_miles": 25
}
```

| Field | Type | Required | Description |
|---|---|:---:|---|
| `origin` | `string` or `object` | **Yes** | US address string or coordinate object `{ "lat": 32.7767, "lng": -96.7970 }`. |
| `destination` | `string` or `object` | **Yes** | US address string or coordinate object `{ "lat": 29.7604, "lng": -95.3698 }`. |
| `load_weight_lbs` | `integer` | No | Gross vehicle weight in pounds. Range: `1000` to `80000` (Default: `40000`). |
| `departure_time` | `string` | No | ISO 8601 string (e.g. `2026-10-15T08:00:00`). |
| `departure_utc` | `integer` | No | Unix timestamp in seconds. Snapped forward if inside a DST transition gap. |
| `checkpoint_interval_miles` | `integer` | No | Sampling resolution: `10`, `25`, or `50` miles (Default: `25`). |

#### Response Schema (`200 OK`)
```json
{
  "origin": { "lat": 32.7767, "lng": -96.7970, "name": "Dallas, TX" },
  "destination": { "lat": 29.7604, "lng": -95.3698, "name": "Houston, TX" },
  "departure_utc": 1792051200,
  "departure_time_iso": "2026-10-15T08:00:00+00:00",
  "vehicle_params": { "load_weight_lbs": 38000 },
  "routes": [
    {
      "route_index": 0,
      "route_name": "I-45 S",
      "summary": "Fastest freight route via I-45 South",
      "distance_miles": 239.4,
      "duration_hours": 3.65,
      "polyline": "encoded_polyline_string",
      "max_risk_level": 2,
      "max_risk_label": "High",
      "is_recommended": true,
      "recommendation_reason": "Lowest total risk exposure across all candidate corridors.",
      "checkpoints": [
        {
          "index": 0,
          "lat": 32.7767,
          "lng": -96.7970,
          "distance_from_origin_miles": 0.0,
          "duration_from_origin_hours": 0.0,
          "eta_utc": 1792051200,
          "eta_local": "2026-10-15 03:00 CDT",
          "weather": {
            "wind_mph": 22.4,
            "wind_gusts_mph": 31.0,
            "rain_in_hr": 0.0,
            "snow_in_hr": 0.0,
            "temperature_f": 68.5
          },
          "risk": {
            "base_level": 0,
            "adjusted_level": 0,
            "label": "Low",
            "contributing_factors": []
          }
        }
      ]
    }
  ],
  "best_departure_window": {
    "recommended_offset_hours": 2,
    "recommended_departure_utc": 1792058400,
    "risk_reduction_summary": "Delaying departure by 2 hours reduces peak crosswind exposure by 16 mph.",
    "hourly_options": [
      { "offset_hours": -2, "max_risk_level": 3, "score": 45.2 },
      { "offset_hours": 0, "max_risk_level": 2, "score": 28.1 },
      { "offset_hours": 2, "max_risk_level": 1, "score": 11.4 }
    ]
  },
  "heatmap": [
    { "lat": 31.5, "lng": -96.2, "risk_level": 2, "intensity": 0.65 }
  ],
  "warnings": []
}
```

---

### 1.2 Geocoding Autocomplete
**`GET /api/geocode/autocomplete?q={query}`**

Queries OpenRouteService Pelican geocoder restricted to US boundaries and returns structured address suggestions.

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|:---:|---|
| `q` | `string` | **Yes** | Text query (min 2 characters, e.g. `Dallas, TX`). |

#### Response Schema (`200 OK`)
```json
{
  "features": [
    {
      "geometry": { "coordinates": [-96.7970, 32.7767] },
      "properties": {
        "name": "Dallas",
        "label": "Dallas, TX, USA",
        "region": "Texas",
        "country": "United States"
      }
    }
  ]
}
```

---

### 1.3 Instant Demo Fixtures
**`POST /api/routes/demo`**

Instantly returns pre-computed route analysis fixtures for high-speed offline testing.

#### Request Body
```json
{
  "preset": "dallas-houston"
}
```
*Supported presets*: `"dallas-houston"`, `"la-phoenix"`.

---

## 2. Multi-Fleet Management APIs

### 2.1 Live Fleet GPS Feed
**`GET /api/fleet/trips/live`**

Returns real-time telemetry for all commercial transport rigs currently in transit across the United States. If fewer than 5 active shipments exist in the database, automatically falls back to the curated 16-truck demonstration fleet feed.

#### Response Schema (`200 OK`)
```json
{
  "count": 8,
  "units": [
    {
      "id": "trk-101",
      "unit_number": "TRK-101",
      "driver_name": "Marcus Vance",
      "fleet_name": "Midwest Express Fleet",
      "origin": "Dallas, TX",
      "destination": "Chicago, IL",
      "corridor": "I-35 -> I-55",
      "current_coords": { "lat": 37.6872, "lng": -97.3301 },
      "trailer_type": "DRY_VAN",
      "load_weight_lbs": 38000,
      "speed_mph": 62,
      "risk_level": "HIGH",
      "wind_mph": 44.0,
      "weather_condition": "Severe Crosswinds",
      "alert": "Strong gust corridor across Kansas Turnpike. 44 mph winds threatening 38k lb dry van.",
      "recommendation": "Drop speed to 45 mph or stage at Emporia, KS travel plaza."
    }
  ]
}
```

---

### 2.2 High-Throughput Batch Corridor Analysis
**`POST /api/fleet/trips/batch-analyze`**

Evaluates up to 500 loads concurrently. Automatically extracts shared highway corridors, batches weather sampling to avoid redundant API queries, and applies aerodynamic trailer sail profiles.

#### Request Body
```json
{
  "trips": [
    {
      "unit_number": "FLT-501",
      "trailer_type": "DRY_VAN",
      "origin": "Dallas, TX",
      "destination": "Chicago, IL",
      "load_weight_lbs": 36000
    },
    {
      "unit_number": "FLT-502",
      "trailer_type": "FLATBED",
      "origin": "Atlanta, GA",
      "destination": "Memphis, TN",
      "load_weight_lbs": 48000
    }
  ]
}
```

#### Response Schema (`200 OK`)
```json
{
  "status": "success",
  "total_trips_analyzed": 2,
  "risk_breakdown": {
    "LOW": 1,
    "MODERATE": 0,
    "HIGH": 1,
    "SEVERE": 0
  },
  "high_risk_flag_count": 1,
  "trips": [
    {
      "trip_index": 1,
      "unit_number": "FLT-501",
      "origin": "Dallas, TX",
      "destination": "Chicago, IL",
      "trailer_type": "DRY_VAN",
      "sail_area_multiplier": 1.0,
      "load_weight_lbs": 36000,
      "risk_level": "HIGH",
      "max_wind_mph": 44.0,
      "action_recommendation": "Delay departure by 2h or reroute around high wind pocket"
    }
  ]
}
```

---

### 2.3 Fleet Resources CRUD Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/fleet/organizations` | `GET`, `POST` | List or register carrier organizations. |
| `/api/fleet/fleets` | `GET`, `POST` | List or create regional operating fleets. |
| `/api/fleet/vehicles` | `GET`, `POST` | List or register commercial tractors. |
| `/api/fleet/trailers` | `GET`, `POST` | List or register trailers (`DRY_VAN`, `REEFER`, `FLATBED`, `TANKER`). |
| `/api/fleet/trips` | `GET`, `POST` | List or schedule freight trips. |
| `/api/fleet/alerts` | `GET` | Retrieve unacknowledged severe weather alerts. |
| `/api/fleet/alerts/{id}/ack` | `POST` | Acknowledge a specific hazard alert. |

---

## 3. System Health Check

### 3.1 Container Healthcheck
**`GET /healthz`**

Lightweight liveness probe used by Docker and Render health monitors. Bypasses database and external network calls for instant sub-millisecond response.

#### Response (`200 OK`)
```text
OK
```
