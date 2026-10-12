"""
Data types for the Route Radar route analysis pipeline.
All structured data uses dataclasses with type hints — no string-keyed dicts.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Coord:
    """A geographic coordinate."""
    lat: float
    lng: float


@dataclass
class VehicleParams:
    """Truck parameters that affect risk."""
    load_weight_lbs: int


@dataclass
class Notice:
    """Structured notification, warning, or operational notice."""
    level: str      # "info" | "warning" | "error"
    code: str       # partial_routes, short_route, low_coverage, best_departure, etc.
    message: str


# Alias for compatibility across plan revisions
PipelineWarning = Notice


@dataclass
class WeatherReading:
    """Weather at a specific point and time."""
    timestamp_utc: int          # Unix timestamp of the forecast bucket
    wind_mph: float             # Sustained wind at 10m
    wind_gusts_mph: float       # For display only — not used in risk calc
    rain_in_hr: float           # rain + showers combined (inches/hr)
    snow_in_hr: float           # snowfall depth accumulation (inches/hr)
    temperature_f: float        # 2m temperature for display


@dataclass
class CheckpointRisk:
    """Risk assessment for a single checkpoint."""
    base_level: int             # 0-4 from weather classification only
    adjusted_level: int         # After applying load-weight rules
    label: str                  # "Low" | "Moderate" | "High" | "Severe" | "No Travel"
    segment_miles: float        # Miles this checkpoint covers (halfway-to-neighbours)
    contributing_factors: list[str] = field(default_factory=list)
    data_available: bool = True # False if weather was interpolated from neighbours


@dataclass
class Checkpoint:
    """A sampled point along a route with weather and risk data."""
    index: int
    coord: Coord
    cumulative_miles: float
    segment_miles: float        # Miles this checkpoint is responsible for
    eta_utc: int | datetime     # Unix timestamp (or datetime) of estimated arrival
    weather: WeatherReading | None = None
    risk: CheckpointRisk | None = None


@dataclass
class RouteSummary:
    """Aggregated risk statistics for a route."""
    no_travel_miles: float = 0.0
    severe_miles: float = 0.0
    high_miles: float = 0.0
    moderate_miles: float = 0.0
    low_miles: float = 0.0
    mile_weighted_avg_risk: float = 0.0  # 0.0–4.0, weighted by segment_miles
    data_coverage_pct: float = 100.0     # % of miles with actual weather data
    max_risk_label: str = "Low"


@dataclass
class RouteRecommendation:
    """Why this route was recommended (or not)."""
    is_recommended: bool = False
    rank: int = 0
    tags: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class RouteResult:
    """Output of /plan (routing without weather yet)."""
    index: int
    name: str                       # e.g., "Route 1 (via I-45 S)"
    encoded_geometry: str           # ORS-encoded polyline
    distance_miles: float
    duration_seconds: int
    via_roads: list[str] = field(default_factory=list)
    step_distances_m: list[float] = field(default_factory=list)
    step_durations_s: list[float] = field(default_factory=list)


@dataclass
class Route(RouteResult):
    """A complete route with checkpoints and risk analysis."""
    duration_display: str = ""
    summary: RouteSummary = field(default_factory=RouteSummary)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    recommendation: RouteRecommendation = field(default_factory=RouteRecommendation)
    effective_interval_miles: int = 25


@dataclass
class HeatmapCell:
    """A single grid cell in the corridor heatmap."""
    coord: Coord
    forecasts: dict[int, int] = field(default_factory=dict)  # {unix_ts: risk_level}


@dataclass
class Heatmap:
    """Precomputed 49-hour corridor heatmap."""
    hours_utc: list[int] = field(default_factory=list)
    cells: list[dict] = field(default_factory=list)


# Risk level constants
RISK_LEVELS: dict[int, str] = {
    0: "Low",
    1: "Moderate",
    2: "High",
    3: "Severe",
    4: "No Travel",
}

RISK_LEGEND: dict[str, dict[str, str]] = {
    "0": {"label": "Low", "color": "#22c55e"},
    "1": {"label": "Moderate", "color": "#f59e0b"},
    "2": {"label": "High", "color": "#f97316"},
    "3": {"label": "Severe", "color": "#ef4444"},
    "4": {"label": "No Travel", "color": "#7c2d12"},
}


@dataclass
class AnalysisResponse:
    """The complete response from the route analysis pipeline."""
    origin: dict                    # {name, lat, lng}
    destination: dict
    departure_utc: int              # Unix timestamp
    load_weight_lbs: int
    routes: list[Route] = field(default_factory=list)
    heatmap: list[HeatmapCell] = field(default_factory=list)
    risk_legend: dict = field(default_factory=lambda: RISK_LEGEND)
    best_departure_window: dict | None = None
    warnings: list[Notice] = field(default_factory=list)


# Alias for compatibility
AnalysisResult = AnalysisResponse
