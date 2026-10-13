"""
Corridor heatmap grid generator and precomputation service.
Builds snapped grid cells within 20 miles of route polylines and computes 49-hour risk forecasts.
"""
import math

from services.data_types import Coord, HeatmapCell, WeatherReading
from services.risk_engine import apply_load_rules, classify_weather


def haversine_distance_miles(c1: Coord, c2: Coord) -> float:
    """Calculate the great-circle distance between two points in miles."""
    r_miles = 3958.8
    phi1, phi2 = math.radians(c1.lat), math.radians(c2.lat)
    dphi = math.radians(c2.lat - c1.lat)
    dlambda = math.radians(c2.lng - c1.lng)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * r_miles * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def min_distance_to_polyline_miles(point: Coord, polyline: list[Coord]) -> float:
    """Computes minimum distance from a point to any segment in a polyline with fast bounding box rejection."""
    if not polyline:
        return float("inf")
    if len(polyline) == 1:
        return haversine_distance_miles(point, polyline[0])

    # 1 degree lat is ~69 miles; 1 degree lng in US (lat ~35-40) is ~53 miles
    # For a distance check of <= 20 miles, points with lat diff > 0.35° or lng diff > 0.50° can be safely skipped
    lat_thresh = 0.35
    lng_thresh = 0.50

    min_dist = float("inf")
    # Quick distance check against polyline vertices
    for p in polyline:
        if abs(point.lat - p.lat) > lat_thresh or abs(point.lng - p.lng) > lng_thresh:
            continue
        d = haversine_distance_miles(point, p)
        if d < min_dist:
            min_dist = d
            if min_dist <= 5.0:  # If within 5 miles, already definitely inside the 20-mile corridor
                return min_dist

    return min_dist


def snap_coordinate(value: float, spacing: float) -> float:
    """Snap a coordinate value to nearest grid spacing."""
    return round(round(value / spacing) * spacing, 6)


def generate_corridor_grid(
    route_geometries: list[list[Coord]],
    corridor_width_miles: float = 20.0,
    grid_spacing_degrees: float = 0.25,
    max_cells: int = 150,
) -> list[Coord]:
    """
    Build a grid along the route corridor (within corridor_width_miles of any route).
    Avoids whole-country bounding boxes. Auto-scales spacing to ensure cell count <= max_cells.
    """
    if not route_geometries:
        return []

    # Flatten points to find extent
    all_points: list[Coord] = [pt for route in route_geometries for pt in route if pt]
    if not all_points:
        return []

    # Subsample dense route geometries to at most ~200 points per route for fast corridor proximity checks
    subsampled_geometries: list[list[Coord]] = [
        route[::max(1, len(route) // 200)] for route in route_geometries if route
    ]

    # Calculate bounding box with buffer
    min_lat = min(pt.lat for pt in all_points)
    max_lat = max(pt.lat for pt in all_points)
    min_lng = min(pt.lng for pt in all_points)
    max_lng = max(pt.lng for pt in all_points)

    spacing = grid_spacing_degrees

    def build_candidates(curr_spacing: float) -> list[Coord]:
        # Generate snapped grid ranges
        start_lat = snap_coordinate(min_lat - 0.5, curr_spacing)
        end_lat = snap_coordinate(max_lat + 0.5, curr_spacing)
        start_lng = snap_coordinate(min_lng - 0.5, curr_spacing)
        end_lng = snap_coordinate(max_lng + 0.5, curr_spacing)

        num_lat_steps = int(round((end_lat - start_lat) / curr_spacing)) + 1
        num_lng_steps = int(round((end_lng - start_lng) / curr_spacing)) + 1

        selected: list[Coord] = []
        for i in range(num_lat_steps):
            lat_cand = snap_coordinate(start_lat + i * curr_spacing, curr_spacing)
            for j in range(num_lng_steps):
                lng_cand = snap_coordinate(start_lng + j * curr_spacing, curr_spacing)
                cand = Coord(lat=lat_cand, lng=lng_cand)

                # Check if within corridor_width_miles of ANY route
                is_near = False
                for route in subsampled_geometries:
                    if min_distance_to_polyline_miles(cand, route) <= corridor_width_miles:
                        is_near = True
                        break

                if is_near:
                    selected.append(cand)
        return selected

    cells = build_candidates(spacing)

    # Auto-scale spacing if cells exceed max_cells
    while len(cells) > max_cells and spacing < 2.0:
        spacing *= 2.0
        cells = build_candidates(spacing)

    # If still slightly over max_cells due to granularity, subsample evenly
    if len(cells) > max_cells:
        step = math.ceil(len(cells) / max_cells)
        cells = cells[::step]

    return cells


def compute_heatmap_data(
    grid_coords: list[Coord],
    weather_data: dict[tuple[float, float], list[WeatherReading]],
    load_weight_lbs: int,
    start_hour_utc: int,
    num_hours: int = 49,
) -> list[HeatmapCell]:
    """
    Computes 49 hourly risk forecasts for each grid coordinate with truck load overrides applied.
    weather_data is indexed by snapped (round(lat, 2), round(lng, 2)).
    """
    cells: list[HeatmapCell] = []

    for coord in grid_coords:
        snapped_key = (round(coord.lat, 4), round(coord.lng, 4))
        coarse_key = (round(coord.lat, 2), round(coord.lng, 2))
        readings = weather_data.get(snapped_key) or weather_data.get(coarse_key)
        if not readings:
            if weather_data:
                closest_key = min(
                    weather_data.keys(),
                    key=lambda k: (k[0] - coord.lat) ** 2 + (k[1] - coord.lng) ** 2,
                )
                readings = weather_data[closest_key]
            else:
                readings = {}

        if isinstance(readings, dict):
            by_ts = readings
        else:
            by_ts = {r.timestamp_utc: r for r in readings}

        forecasts: dict[int, int] = {}
        for h in range(num_hours):
            hour_ts = start_hour_utc + h * 3600
            reading = by_ts.get(hour_ts)

            if reading:
                base_risk = classify_weather(
                    wind_mph=reading.wind_mph,
                    rain_in_hr=reading.rain_in_hr,
                    snow_in_hr=reading.snow_in_hr,
                )
                adjusted_level, _ = apply_load_rules(
                    base_risk=base_risk,
                    wind_mph=reading.wind_mph,
                    load_weight_lbs=load_weight_lbs,
                )
                forecasts[hour_ts] = adjusted_level
            else:
                forecasts[hour_ts] = 0

        cells.append(HeatmapCell(coord=coord, forecasts=forecasts))

    return cells
