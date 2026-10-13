"""
Open-Meteo weather integration service with multi-location batching,
response validation, preceding-hour precip matching, and linear wind interpolation.
"""
import logging
import math
from datetime import datetime

import requests
from services.data_types import Checkpoint, CheckpointRisk, Coord, WeatherReading
from services.risk_engine import compute_checkpoint_risk, get_risk_label

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(Exception):
    """Exception raised when weather retrieval or validation fails."""
    pass


def snap_coordinate(coord: Coord, grid_deg: float = 0.01) -> tuple[float, float]:
    """Snap coordinate to grid (default 0.01°) for caching and batch deduplication."""
    snapped_lat = round(round(coord.lat / grid_deg) * grid_deg, 4)
    snapped_lng = round(round(coord.lng / grid_deg) * grid_deg, 4)
    return (snapped_lat, snapped_lng)


def fetch_weather_batch(
    coords: list[Coord],
    start_date: str,
    end_date: str,
    timeout_seconds: int = 12,
) -> dict[tuple[float, float], dict[int, WeatherReading]]:
    """
    Fetch hourly weather for multiple coordinates in batched HTTP calls.
    Returns: {(snapped_lat, snapped_lng): {unix_timestamp: WeatherReading, ...}}
    """
    if not coords:
        return {}

    # Deduplicate coordinates by snapped grid position
    unique_snapped = list(dict.fromkeys([snap_coordinate(c) for c in coords]))
    results: dict[tuple[float, float], dict[int, WeatherReading]] = {}

    # Batch in chunks of up to 100 coordinates
    chunk_size = 100
    for i in range(0, len(unique_snapped), chunk_size):
        chunk = unique_snapped[i : i + chunk_size]
        lats = ",".join(str(c[0]) for c in chunk)
        lngs = ",".join(str(c[1]) for c in chunk)

        params = {
            "latitude": lats,
            "longitude": lngs,
            "hourly": "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall,temperature_2m",
            "precipitation_unit": "inch",
            "windspeed_unit": "mph",
            "temperature_unit": "fahrenheit",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_date": start_date,
            "end_date": end_date,
        }

        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Open-Meteo request failed: %s", exc)
            raise WeatherServiceError(f"Open-Meteo API error: {exc}") from exc

        # Normalize single dict vs list responses
        if isinstance(data, dict):
            data = [data]

        # Validate count
        if len(data) != len(chunk):
            logger.warning(
                "Open-Meteo returned %d locations for %d requested. Missing will be interpolated.",
                len(data),
                len(chunk),
            )

        # Validate units on the first response item
        if data and "hourly_units" in data[0]:
            units = data[0]["hourly_units"]
            rain_unit = units.get("rain")
            snow_unit = units.get("snowfall")
            if rain_unit != "inch":
                raise WeatherServiceError(f"Expected rain unit 'inch', got '{rain_unit}'")
            if snow_unit != "inch":
                raise WeatherServiceError(f"Expected snowfall unit 'inch', got '{snow_unit}'")

        # Parse timelines per coordinate
        for loc_idx, loc_data in enumerate(data):
            if loc_idx >= len(chunk):
                break
            snapped_key = chunk[loc_idx]
            timeline = parse_weather_timeline(loc_data)
            results[snapped_key] = timeline

    return results


def parse_weather_timeline(loc_data: dict) -> dict[int, WeatherReading]:
    """Parse a single Open-Meteo location dict into a {unix_ts: WeatherReading} timeline."""
    hourly = loc_data.get("hourly", {})
    timestamps = hourly.get("time", [])
    if not timestamps:
        return {}

    winds = hourly.get("wind_speed_10m", [])
    gusts = hourly.get("wind_gusts_10m", [])
    rains = hourly.get("rain", [])
    showers = hourly.get("showers", [])
    snowfalls = hourly.get("snowfall", [])
    temperatures = hourly.get("temperature_2m", [])

    timeline = {}
    for idx, ts in enumerate(timestamps):
        w = float(winds[idx]) if idx < len(winds) and winds[idx] is not None else 0.0
        g = float(gusts[idx]) if idx < len(gusts) and gusts[idx] is not None else w
        r = float(rains[idx]) if idx < len(rains) and rains[idx] is not None else 0.0
        sh = float(showers[idx]) if idx < len(showers) and showers[idx] is not None else 0.0
        sn = float(snowfalls[idx]) if idx < len(snowfalls) and snowfalls[idx] is not None else 0.0
        t = float(temperatures[idx]) if idx < len(temperatures) and temperatures[idx] else 65.0

        w = max(0.0, w)
        g = max(0.0, g)
        r = max(0.0, r)
        sh = max(0.0, sh)
        sn = max(0.0, sn)

        # Sum rain + showers combined for total liquid precip
        total_rain = round(r + sh, 4)

        reading = WeatherReading(
            timestamp_utc=int(ts),
            wind_mph=round(w, 2),
            wind_gusts_mph=round(g, 2),
            rain_in_hr=total_rain,
            snow_in_hr=round(sn, 4),
            temperature_f=round(t, 1),
        )
        timeline[int(ts)] = reading

    return timeline


def match_weather_to_eta(
    weather_timeline: dict[int, WeatherReading],
    eta_unix: int,
) -> WeatherReading | None:
    """
    Match checkpoint ETA to weather readings:
      - Rain/Snow/Gusts: Preceding-hour bucket ceil(eta / 3600) * 3600 (covers (T-1, T]).
        If ETA is exactly on the hour, uses that hour's bucket.
      - Wind & Temp: Linear interpolation between floor and ceil hourly buckets.
    """
    if not weather_timeline:
        return None

    min_ts = min(weather_timeline.keys())
    max_ts = max(weather_timeline.keys())

    # Preceding hour bucket for precipitation
    if eta_unix % 3600 == 0:
        precip_ts = eta_unix
    else:
        precip_ts = math.ceil(eta_unix / 3600.0) * 3600

    # If precipitation timestamp is beyond forecast horizon, return None
    if precip_ts > max_ts or eta_unix < min_ts:
        return None

    precip_reading = weather_timeline.get(precip_ts)
    if not precip_reading:
        return None

    # Linear interpolation for sustained wind and temperature
    t_floor = (eta_unix // 3600) * 3600
    t_ceil = math.ceil(eta_unix / 3600.0) * 3600

    r_floor = weather_timeline.get(t_floor)
    r_ceil = weather_timeline.get(t_ceil)

    if r_floor and r_ceil and t_floor != t_ceil:
        frac = (eta_unix - t_floor) / 3600.0
        interp_wind = r_floor.wind_mph + frac * (r_ceil.wind_mph - r_floor.wind_mph)
        interp_temp = r_floor.temperature_f + frac * (r_ceil.temperature_f - r_floor.temperature_f)
    elif r_floor:
        interp_wind = r_floor.wind_mph
        interp_temp = r_floor.temperature_f
    else:
        interp_wind = precip_reading.wind_mph
        interp_temp = precip_reading.temperature_f

    return WeatherReading(
        timestamp_utc=precip_ts,
        wind_mph=round(max(0.0, interp_wind), 2),
        wind_gusts_mph=precip_reading.wind_gusts_mph,
        rain_in_hr=precip_reading.rain_in_hr,
        snow_in_hr=precip_reading.snow_in_hr,
        temperature_f=round(interp_temp, 1),
    )


def apply_weather_and_risk_to_checkpoints(
    checkpoints: list[Checkpoint],
    weather_by_coord: dict[tuple[float, float], dict[int, WeatherReading]],
    load_weight_lbs: int,
) -> None:
    """Populate weather and risk for each checkpoint, interpolating missing neighbors."""
    for cp in checkpoints:
        snapped = snap_coordinate(cp.coord)
        timeline = weather_by_coord.get(snapped, {})
        eta = int(cp.eta_utc.timestamp()) if isinstance(cp.eta_utc, datetime) else int(cp.eta_utc)
        reading = match_weather_to_eta(timeline, eta)
        cp.weather = reading

        if reading is not None:
            risk_dict = compute_checkpoint_risk(
                wind_mph=reading.wind_mph,
                rain_in_hr=reading.rain_in_hr,
                snow_in_hr=reading.snow_in_hr,
                load_weight_lbs=load_weight_lbs,
                segment_miles=cp.segment_miles,
                data_available=True,
            )
            cp.risk = CheckpointRisk(**risk_dict)

    # Neighbor interpolation for checkpoints missing weather
    interpolate_missing_checkpoint_risks(checkpoints)


def interpolate_missing_checkpoint_risks(checkpoints: list[Checkpoint]) -> None:
    """Interpolate risk level from nearest valid neighbors for checkpoints lacking data."""
    valid_indices = [i for i, cp in enumerate(checkpoints) if cp.risk is not None]

    if not valid_indices:
        # All weather offline: default to moderate alert with data_available=False
        for cp in checkpoints:
            cp.risk = CheckpointRisk(
                base_level=1,
                adjusted_level=1,
                label=get_risk_label(1),
                segment_miles=cp.segment_miles,
                contributing_factors=["Weather data offline; interpolated baseline."],
                data_available=False,
            )
        return

    for i, cp in enumerate(checkpoints):
        if cp.risk is None:
            # Find closest valid neighbor index
            closest_idx = min(valid_indices, key=lambda idx: abs(idx - i))
            donor_risk = checkpoints[closest_idx].risk
            cp.risk = CheckpointRisk(
                base_level=donor_risk.base_level,
                adjusted_level=donor_risk.adjusted_level,
                label=donor_risk.label,
                segment_miles=cp.segment_miles,
                contributing_factors=["Interpolated from adjacent checkpoint."],
                data_available=False,
            )
