"""
Checkpoint sampling service along route polyline.
Enforces non-linear ETA interpolation using ORS step durations and Voronoi halfway mile attribution.
"""
import math
from datetime import datetime

from shapely.geometry import LineString, Point

from services.data_types import Checkpoint, Coord

METERS_TO_MILES = 0.000621371
MILES_TO_METERS = 1609.344


def sample_checkpoints(
    decoded_coords: list[Coord],
    step_distances_m: list[float],
    step_durations_s: list[float],
    departure_utc: int | datetime,
    interval_miles: int = 25,
) -> list[Checkpoint]:
    """
    Sample checkpoints every `interval_miles` along the route polyline.

    Key guarantees:
    1. Checkpoint 0 is at origin (0.0 cumulative miles).
    2. Final checkpoint is at destination (total route miles).
    3. Minimum 2 checkpoints, maximum capped at 60 checkpoints.
    4. Attributed segment_miles uses Voronoi halfway split; sum equals total miles.
    5. Non-linear ETA computed using cumulative ORS step durations.
    """
    if not decoded_coords:
        return []

    # Normalize departure to integer unix timestamp
    if isinstance(departure_utc, datetime):
        dep_ts = int(departure_utc.timestamp())
    else:
        dep_ts = int(departure_utc)

    # 1. Calculate cumulative distances along decoded polyline in miles
    polyline_cum_miles = [0.0]
    for i in range(len(decoded_coords) - 1):
        c1, c2 = decoded_coords[i], decoded_coords[i + 1]
        dist_m = haversine_distance_m(c1, c2)
        polyline_cum_miles.append(polyline_cum_miles[-1] + dist_m * METERS_TO_MILES)

    total_miles = polyline_cum_miles[-1]

    # Handle tiny routes (< 0.1 mile)
    if total_miles <= 0.001 or len(decoded_coords) < 2:
        return [
            Checkpoint(
                index=0,
                coord=decoded_coords[0],
                cumulative_miles=0.0,
                segment_miles=total_miles,
                eta_utc=dep_ts,
            ),
            Checkpoint(
                index=1,
                coord=decoded_coords[-1],
                cumulative_miles=total_miles,
                segment_miles=0.0,
                eta_utc=dep_ts,
            ),
        ]

    # 2. Build cumulative step distances (in miles) and cumulative durations (in seconds)
    step_cum_miles = [0.0]
    step_cum_seconds = [0.0]
    for dist_m, dur_s in zip(step_distances_m, step_durations_s, strict=False):
        step_cum_miles.append(step_cum_miles[-1] + dist_m * METERS_TO_MILES)
        step_cum_seconds.append(step_cum_seconds[-1] + dur_s)

    # Fallback if step data is empty or shorter than total distance
    if len(step_cum_miles) <= 1 or step_cum_miles[-1] <= 0:
        # Assume standard 55 mph baseline
        step_cum_miles = [0.0, total_miles]
        step_cum_seconds = [0.0, (total_miles / 55.0) * 3600.0]

    total_step_miles = step_cum_miles[-1]
    total_step_seconds = step_cum_seconds[-1]

    def get_eta_for_mile(target_mile: float) -> int:
        """Interpolate elapsed duration from step arrays."""
        if target_mile <= 0.0:
            return dep_ts
        if target_mile >= total_miles:
            return dep_ts + int(total_step_seconds)

        # Scale target mile to step coordinate space if total distances differ slightly
        scale = total_step_miles / max(1e-9, total_miles)
        scaled_mile = target_mile * scale

        for k in range(len(step_cum_miles) - 1):
            s_start = step_cum_miles[k]
            s_end = step_cum_miles[k + 1]
            if s_start <= scaled_mile <= s_end:
                seg_d = max(1e-9, s_end - s_start)
                ratio = (scaled_mile - s_start) / seg_d
                t_start = step_cum_seconds[k]
                t_end = step_cum_seconds[k + 1]
                elapsed = t_start + ratio * (t_end - t_start)
                return dep_ts + int(elapsed)

        return dep_ts + int(total_step_seconds)

    # 3. Determine sampling mile marks
    effective_interval = float(interval_miles)
    # Enforce cap of 60 checkpoints
    if total_miles / effective_interval > 58.0:
        effective_interval = total_miles / 58.0

    target_miles = [0.0]
    curr_m = effective_interval
    while curr_m < total_miles - (effective_interval * 0.25):
        target_miles.append(round(curr_m, 3))
        curr_m += effective_interval

    if target_miles[-1] != total_miles:
        target_miles.append(round(total_miles, 3))

    # Ensure minimum 2 checkpoints
    if len(target_miles) < 2:
        target_miles = [0.0, round(total_miles, 3)]

    # 4. Interpolate coordinates for each target mile mark along polyline
    sampled_coords = []
    for m in target_miles:
        coord = interpolate_coord_at_mile(decoded_coords, polyline_cum_miles, m)
        sampled_coords.append(coord)

    # 5. Halfway / Voronoi segment mile attribution
    n = len(target_miles)
    segment_miles_list = []
    for i in range(n):
        if n == 1:
            segment_miles_list.append(target_miles[0])
        elif i == 0:
            # First checkpoint covers 0 to midpoint(0, 1)
            mid = (target_miles[0] + target_miles[1]) / 2.0
            segment_miles_list.append(mid)
        elif i == n - 1:
            # Last checkpoint covers midpoint(n-2, n-1) to total_miles
            mid = (target_miles[n - 2] + target_miles[n - 1]) / 2.0
            segment_miles_list.append(target_miles[-1] - mid)
        else:
            # Middle checkpoints cover midpoint(i-1, i) to midpoint(i, i+1)
            mid_prev = (target_miles[i - 1] + target_miles[i]) / 2.0
            mid_next = (target_miles[i] + target_miles[i + 1]) / 2.0
            segment_miles_list.append(mid_next - mid_prev)

    rounded_segments = [round(s, 2) for s in segment_miles_list]
    diff_round = round(round(target_miles[-1], 2) - sum(rounded_segments), 2)
    rounded_segments[-1] = round(rounded_segments[-1] + diff_round, 2)

    # 6. Assemble checkpoints
    checkpoints = []
    for idx in range(n):
        m = target_miles[idx]
        eta = get_eta_for_mile(m)
        cp = Checkpoint(
            index=idx,
            coord=sampled_coords[idx],
            cumulative_miles=round(m, 2),
            segment_miles=rounded_segments[idx],
            eta_utc=eta,
        )
        checkpoints.append(cp)

    return checkpoints


def interpolate_coord_at_mile(
    coords: list[Coord],
    polyline_cum_miles: list[float],
    target_mile: float,
) -> Coord:
    """Interpolate Coord along coordinate polyline at specific cumulative mile."""
    if target_mile <= 0.0 or len(coords) == 1:
        return coords[0]
    if target_mile >= polyline_cum_miles[-1]:
        return coords[-1]

    for i in range(len(polyline_cum_miles) - 1):
        m1 = polyline_cum_miles[i]
        m2 = polyline_cum_miles[i + 1]
        if m1 <= target_mile <= m2:
            seg_len = max(1e-9, m2 - m1)
            fraction = (target_mile - m1) / seg_len
            c1 = coords[i]
            c2 = coords[i + 1]
            lat = c1.lat + fraction * (c2.lat - c1.lat)
            lng = c1.lng + fraction * (c2.lng - c1.lng)
            return Coord(lat=round(lat, 6), lng=round(lng, 6))

    return coords[-1]


def haversine_distance_m(c1: Coord, c2: Coord) -> float:
    """Great-circle distance in meters between two coordinates."""
    earth_radius = 6371000.0  # meters
    lat1, lon1 = math.radians(c1.lat), math.radians(c1.lng)
    lat2, lon2 = math.radians(c2.lat), math.radians(c2.lng)
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1

    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2.0) ** 2
    )
    return 2.0 * earth_radius * math.asin(math.sqrt(max(0.0, a)))


def distance_point_to_polyline_miles(point: Coord, polyline_coords: list[Coord]) -> float:
    """Compute shortest perpendicular distance from point to polyline in miles."""
    if len(polyline_coords) < 2:
        return 0.0
    line = LineString([(c.lng, c.lat) for c in polyline_coords])
    pt = Point(point.lng, point.lat)
    # Degrees to approx miles (1 degree ~ 69 miles)
    dist_deg = pt.distance(line)
    return dist_deg * 69.0
