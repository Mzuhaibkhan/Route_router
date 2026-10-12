"""
Best departure window optimizer.
Scans +1h to +12h horizons against cached weather to discover optimal travel windows
without requiring additional external API calls.
"""
import math

from backend.services.data_types import Route, WeatherReading
from backend.services.risk_engine import apply_load_rules, classify_weather


def find_best_departure(
    routes: list[Route],
    weather_by_coord: dict[tuple[float, float], list[WeatherReading]],
    load_weight_lbs: int,
    original_departure_utc: int,
    window_hours: int = 12,
) -> dict | None:
    """
    Evaluates routes at +1h to +window_hours shifted departures using already fetched weather.
    Returns earliest best departure window or None if initial departure is optimal.
    """
    if not routes or not weather_by_coord:
        return None

    # Focus evaluation on the primary / recommended route
    primary_route = routes[0]
    orig_s = primary_route.summary
    orig_no_travel = orig_s.no_travel_miles
    orig_severe = orig_s.severe_miles
    orig_high = orig_s.high_miles

    best_improvement: dict | None = None
    best_score_diff = 0.0

    for h in range(1, window_hours + 1):
        shift_s = h * 3600
        shift_dep_ts = original_departure_utc + shift_s

        new_no_travel = 0.0
        new_severe = 0.0
        new_high = 0.0

        for cp in primary_route.checkpoints:
            snapped_key = (round(cp.coord.lat, 4), round(cp.coord.lng, 4))
            coarse_key = (round(cp.coord.lat, 2), round(cp.coord.lng, 2))
            readings = weather_by_coord.get(snapped_key) or weather_by_coord.get(coarse_key)
            if not readings:
                continue

            # Target timestamp
            eta_ts = (
                cp.eta_utc.timestamp()
                if hasattr(cp.eta_utc, "timestamp")
                else float(cp.eta_utc)
            )
            target_ts = math.ceil((eta_ts + shift_s) / 3600.0) * 3600

            # Match reading
            if isinstance(readings, dict):
                matched = readings.get(target_ts)
                if matched is None and readings:
                    closest_ts = min(readings.keys(), key=lambda ts: abs(ts - target_ts))
                    if abs(closest_ts - target_ts) <= 3600:
                        matched = readings[closest_ts]
            else:
                matched = min(
                    readings,
                    key=lambda r: abs(r.timestamp_utc - target_ts),
                    default=None,
                )
                if matched and abs(matched.timestamp_utc - target_ts) > 3600:
                    matched = None
            if matched and abs(matched.timestamp_utc - target_ts) <= 3600:
                base_risk = classify_weather(
                    wind_mph=matched.wind_mph,
                    rain_in_hr=matched.rain_in_hr,
                    snow_in_hr=matched.snow_in_hr,
                )
                adj_level, _ = apply_load_rules(
                    base_risk=base_risk,
                    wind_mph=matched.wind_mph,
                    load_weight_lbs=load_weight_lbs,
                )
                if adj_level == 4:
                    new_no_travel += cp.segment_miles
                elif adj_level == 3:
                    new_severe += cp.segment_miles
                elif adj_level == 2:
                    new_high += cp.segment_miles

        # Check if shifted departure produces significant improvements
        # 1. Reduction in No Travel miles
        if orig_no_travel > 0 and (orig_no_travel - new_no_travel) >= 5.0:
            diff = (orig_no_travel - new_no_travel) * 100.0
            if diff > best_score_diff:
                best_score_diff = diff
                best_improvement = {
                    "best_departure_utc": shift_dep_ts,
                    "route_index": primary_route.index,
                    "improvement": (
                        f"Waiting {h}h reduces No Travel miles from "
                        f"{orig_no_travel:.1f} to {new_no_travel:.1f}"
                    ),
                }

        # 2. Reduction in Severe miles
        elif orig_severe >= 5.0 and (orig_severe - new_severe) >= 5.0:
            diff = (orig_severe - new_severe) * 10.0
            if diff > best_score_diff:
                best_score_diff = diff
                best_improvement = {
                    "best_departure_utc": shift_dep_ts,
                    "route_index": primary_route.index,
                    "improvement": (
                        f"Waiting {h}h reduces Severe risk miles from "
                        f"{orig_severe:.0f} to {new_severe:.0f}"
                    ),
                }

        # 3. Reduction in High miles
        elif orig_high >= 15.0 and (orig_high - new_high) >= 10.0:
            diff = orig_high - new_high
            if diff > best_score_diff:
                best_score_diff = diff
                best_improvement = {
                    "best_departure_utc": shift_dep_ts,
                    "route_index": primary_route.index,
                    "improvement": (
                        f"Waiting {h}h reduces High risk miles from "
                        f"{orig_high:.0f} to {new_high:.0f}"
                    ),
                }

    return best_improvement
