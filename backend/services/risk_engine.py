"""
Risk classification engine for weather conditions and load weight.

Authoritative Rules:
1. Boundary handling (per spec):
   - Wind:  >= 55.0 mph -> No Travel (inclusive lower bound)
   - Rain:  > 1.00 in/hr -> No Travel (STRICT — exactly 1.00 is Severe: 0.50 <= rain <= 1.00)
   - Snow:  > 3.0 in/hr -> No Travel (STRICT — exactly 3.0 is Severe: 2.0 <= snow <= 3.0)
   - All other bands: >= lower, < upper

2. Floating-point precision:
   - _round_weather(val, 4) rounds values to 4 decimal places and clamps negatives to 0.0.
   - Eliminates IEEE 754 precision drift (e.g., 1.0000000000000002 -> 1.00 -> Severe,
     3.0000000000000004 -> 3.00 -> Severe, 54.999999999999996 -> 55.0 -> No Travel).

3. Truck load override rules:
   - Wind >= 55 mph -> No Travel for ANY load (handled directly by weather & verified).
   - Wind 45–54 mph and Load > 30,000 lbs -> No Travel (>30,000 means 30,001+).
   - Wind 35–44 mph and Load > 40,000 lbs -> Severe (>40,000 means 40,001+).
"""
from services.data_types import RISK_LEVELS


def _round_weather(value: float, decimals: int = 4) -> float:
    """
    Round to API output precision to prevent float drift at boundaries,
    and clamp any numerical model negative artifacts to 0.0.
    """
    return max(0.0, round(float(value), decimals))


def classify_wind(wind_mph: float) -> int:
    """
    Classify sustained wind risk. Uses >= for all lower bounds per spec:
      - < 25 mph  : Low (0)
      - 25–34 mph : Moderate (1)
      - 35–44 mph : High (2)
      - 45–54 mph : Severe (3)
      - >= 55 mph : No Travel (4)
    """
    w = _round_weather(wind_mph)
    if w >= 55.0:
        return 4  # No Travel
    if w >= 45.0:
        return 3  # Severe
    if w >= 35.0:
        return 2  # High
    if w >= 25.0:
        return 1  # Moderate
    return 0      # Low


def classify_rain(rain_in_hr: float) -> int:
    """
    Classify rain risk (rain + showers):
      - < 0.10 in/hr     : Low (0)
      - 0.10–0.2499 in/hr: Moderate (1)
      - 0.25–0.4999 in/hr: High (2)
      - 0.50–1.00 in/hr  : Severe (3)
      - > 1.00 in/hr     : No Travel (4) [STRICT — exactly 1.00 is Severe]
    """
    r = _round_weather(rain_in_hr)
    if r > 1.00:
        return 4  # No Travel
    if r >= 0.50:
        return 3  # Severe
    if r >= 0.25:
        return 2  # High
    if r >= 0.10:
        return 1  # Moderate
    return 0      # Low


def classify_snow(snow_in_hr: float) -> int:
    """
    Classify snowfall accumulation depth risk:
      - < 0.5 in/hr     : Low (0)
      - 0.5–0.9999 in/hr: Moderate (1)
      - 1.0–1.9999 in/hr: High (2)
      - 2.0–3.0 in/hr   : Severe (3)
      - > 3.0 in/hr     : No Travel (4) [STRICT — exactly 3.0 is Severe]
    """
    s = _round_weather(snow_in_hr)
    if s > 3.0:
        return 4  # No Travel
    if s >= 2.0:
        return 3  # Severe
    if s >= 1.0:
        return 2  # High
    if s >= 0.5:
        return 1  # Moderate
    return 0      # Low


def classify_weather(wind_mph: float, rain_in_hr: float, snow_in_hr: float) -> int:
    """
    Return the worst (max) risk level across sustained wind, rain, and snow.
    """
    return max(
        classify_wind(wind_mph),
        classify_rain(rain_in_hr),
        classify_snow(snow_in_hr),
    )


def apply_load_rules(
    base_risk: int,
    wind_mph: float,
    load_weight_lbs: int,
) -> tuple[int, list[str]]:
    """
    Override risk based on truck load weight. Returns (adjusted_risk, factors).

    Rules (per spec):
    - >= 55 mph wind -> No Travel (ANY load).
    - 45–54 mph wind + > 30,000 lbs -> No Travel (>30,000 means 30,001+).
    - 35–44 mph wind + > 40,000 lbs -> Severe (>40,000 means 40,001+).
    """
    w = _round_weather(wind_mph)
    factors: list[str] = []
    adjusted = base_risk

    if w >= 55.0:
        adjusted = max(adjusted, 4)

    if 45.0 <= w < 55.0 and load_weight_lbs > 30_000:
        adjusted = max(adjusted, 4)  # No Travel
        factors.append(
            f"Wind {w:.0f} mph + load {load_weight_lbs:,} lb (>30,000) → No Travel"
        )

    if 35.0 <= w < 45.0 and load_weight_lbs > 40_000:
        adjusted = max(adjusted, 3)  # Severe
        factors.append(
            f"Wind {w:.0f} mph + load {load_weight_lbs:,} lb (>40,000) → Severe"
        )

    return adjusted, factors


def get_risk_label(level: int) -> str:
    """Convert numeric risk level (0-4) to human-readable label."""
    return RISK_LEVELS.get(level, "Unknown")


def compute_checkpoint_risk(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lbs: int,
    segment_miles: float,
    data_available: bool = True,
) -> dict:
    """
    Full risk computation for a single checkpoint.
    Returns dict matching CheckpointRisk fields.
    """
    base_level = classify_weather(wind_mph, rain_in_hr, snow_in_hr)
    adjusted_level, factors = apply_load_rules(base_level, wind_mph, load_weight_lbs)

    # Add descriptive contributing factor tags for transparency when elevated
    w_level = classify_wind(wind_mph)
    r_level = classify_rain(rain_in_hr)
    s_level = classify_snow(snow_in_hr)

    if w_level >= 2:
        factors.insert(0, f"Wind {wind_mph:.0f} mph → {get_risk_label(w_level)}")
    if r_level >= 2:
        factors.insert(0, f"Rain {rain_in_hr:.2f} in/hr → {get_risk_label(r_level)}")
    if s_level >= 2:
        factors.insert(0, f"Snow {snow_in_hr:.1f} in/hr → {get_risk_label(s_level)}")

    return {
        "base_level": base_level,
        "adjusted_level": adjusted_level,
        "label": get_risk_label(adjusted_level),
        "segment_miles": segment_miles,
        "contributing_factors": factors,
        "data_available": data_available,
    }
