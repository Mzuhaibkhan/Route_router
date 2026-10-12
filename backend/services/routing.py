"""
Multi-tier alternative routing provider for commercial heavy goods vehicles.
Complies with OpenRouteService public API polygon limits (<200 km² area, <20 km extent).
"""
import logging
import math
from typing import Protocol, runtime_checkable

import polyline
import requests
from django.conf import settings
from services.data_types import Coord, RouteResult, VehicleParams
from shapely.geometry import LineString

logger = logging.getLogger(__name__)

ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-hgv"


class RoutingError(Exception):
    """Exception raised when routing calculation fails."""
    pass


@runtime_checkable
class RoutingProvider(Protocol):
    """Protocol defining the interface for route generation engines."""

    def get_routes(
        self,
        origin: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
    ) -> list[RouteResult]:
        """Generate 1 to 3 distinct commercial truck routes."""
        ...


class ORSRoutingProvider:
    """
    Three-tier routing provider for heavy goods vehicles (HGV):
      Tier 1: Small targeted avoid box (≤195 km² < 200 km², extent < 20 km) at midpoint.
      Tier 2: Perpendicular waypoint offsets (±30 km left/right from midpoint).
      Tier 3: Gracefully accepts viable distinct routes (1–3 routes).
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "ORS_API_KEY", "")

    def get_routes(
        self,
        origin: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
    ) -> list[RouteResult]:
        """
        Produce 1 to 3 distinct routes using the multi-tier avoidance strategy.
        """
        base_route = self._request_route(origin, destination, vehicle_params)
        routes = [base_route]

        # Short routes (< 30 km / ~18.6 mi) bypass alternative generation
        if base_route.distance_miles < 18.64:
            return routes

        # Tier 1: Small avoid box at midpoint (only attempted if route distance <= 150 km)
        if base_route.distance_miles <= 93.2:  # 150 km in miles
            alt_route_1 = self._try_avoid_box(base_route, origin, destination, vehicle_params)
            if alt_route_1 and self._is_distinct(alt_route_1, routes):
                routes.append(alt_route_1)

        # Tier 2: Perpendicular waypoint offsets (left/right) if fewer than 3 routes
        if len(routes) < 3:
            alt_route_2 = self._try_waypoint_offset(
                base_route, origin, destination, vehicle_params, existing_routes=routes
            )
            if alt_route_2 and self._is_distinct(alt_route_2, routes):
                routes.append(alt_route_2)

        # Tier 3: Accept 1-3 routes gracefully
        return routes

    def _try_avoid_box(
        self,
        base_route: RouteResult,
        origin: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
    ) -> RouteResult | None:
        """
        Generate a small avoid box centered at the route midpoint:
        15 km × 13 km = 195 km² (< 200 km² limit, extent 19.8 km < 20 km).
        """
        decoded = [Coord(lat=p[0], lng=p[1]) for p in polyline.decode(base_route.encoded_geometry)]
        midpoint = self._get_point_at_fraction(decoded, 0.5)
        avoid_box = self._build_small_box(midpoint, width_km=15.0, height_km=13.0)

        try:
            return self._request_route(
                origin, destination, vehicle_params, avoid_polygons=avoid_box, index=1
            )
        except RoutingError as exc:
            logger.info("Tier 1 avoid box route failed or unroutable: %s", exc)
            return None

    def _try_waypoint_offset(
        self,
        base_route: RouteResult,
        origin: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
        existing_routes: list[RouteResult],
    ) -> RouteResult | None:
        """
        Generate candidate route with an intermediate waypoint offset ~30 km perpendicular
        to route bearing at the midpoint. Tries left (+90°), then right (-90°).
        """
        decoded = [Coord(lat=p[0], lng=p[1]) for p in polyline.decode(base_route.encoded_geometry)]
        midpoint = self._get_point_at_fraction(decoded, 0.5)
        bearing = self._route_bearing_at(decoded, 0.5)

        for offset_angle in [90.0, -90.0]:
            offset_pt = self._offset_coord(midpoint, bearing + offset_angle, km=30.0)
            if not self._is_on_land(offset_pt):
                continue

            try:
                candidate = self._request_route_via(
                    origin, offset_pt, destination, vehicle_params, index=len(existing_routes)
                )
                if self._is_distinct(candidate, existing_routes):
                    return candidate
            except RoutingError:
                continue

        return None

    def _is_distinct(self, candidate: RouteResult, existing_routes: list[RouteResult]) -> bool:
        """
        Validate distinctness:
        1. Reject if candidate duration > 1.5× fastest existing duration.
        2. Reject if geometry overlap with any existing route > 80% (0.80).
        """
        fastest_duration = min(r.duration_seconds for r in existing_routes)
        if candidate.duration_seconds > fastest_duration * 1.5:
            return False

        candidate_coords = [
            Coord(lat=p[0], lng=p[1]) for p in polyline.decode(candidate.encoded_geometry)
        ]

        for existing in existing_routes:
            existing_coords = [
                Coord(lat=p[0], lng=p[1]) for p in polyline.decode(existing.encoded_geometry)
            ]
            overlap = self._compute_overlap(existing_coords, candidate_coords)
            if overlap > 0.80:
                return False

        return True

    def _build_small_box(
        self,
        midpoint: Coord,
        width_km: float = 15.0,
        height_km: float = 13.0,
    ) -> dict:
        """
        Build GeoJSON Polygon bounded by width_km and height_km.
        Enforces strict ORS limits: Area < 200 km² and Extent < 20 km.
        """
        # 1 degree latitude is approx 111.0 km
        d_lat = (height_km / 2.0) / 111.0
        # 1 degree longitude depends on latitude
        cos_lat = math.cos(math.radians(midpoint.lat))
        d_lng = (width_km / 2.0) / (111.0 * max(0.1, abs(cos_lat)))

        min_lat = midpoint.lat - d_lat
        max_lat = midpoint.lat + d_lat
        min_lng = midpoint.lng - d_lng
        max_lng = midpoint.lng + d_lng

        # GeoJSON coordinates format: [[[lng, lat], [lng, lat], ...]] (closed polygon)
        coordinates = [[
            [round(min_lng, 6), round(min_lat, 6)],
            [round(max_lng, 6), round(min_lat, 6)],
            [round(max_lng, 6), round(max_lat, 6)],
            [round(min_lng, 6), round(max_lat, 6)],
            [round(min_lng, 6), round(min_lat, 6)],
        ]]

        # Validate area & extent
        area = width_km * height_km
        extent = math.sqrt(width_km**2 + height_km**2)
        assert area < 200.0, f"Avoid box area {area} exceeds 200 km²"
        assert extent < 20.0, f"Avoid box extent {extent} exceeds 20 km"

        return {
            "type": "Polygon",
            "coordinates": coordinates,
        }

    def _compute_overlap(self, geom_a: list[Coord], geom_b: list[Coord]) -> float:
        """
        Compute percentage of geom_b length that overlaps within 0.01° of geom_a.
        Uses Shapely LineString buffer and intersection length.
        """
        if len(geom_a) < 2 or len(geom_b) < 2:
            return 0.0

        line_a = LineString([(c.lng, c.lat) for c in geom_a])
        line_b = LineString([(c.lng, c.lat) for c in geom_b])

        if line_b.length == 0.0:
            return 0.0

        # Buffer line A by ~1 km in degrees (~0.01 degrees)
        buffered_a = line_a.buffer(0.01)
        intersection = line_b.intersection(buffered_a)

        overlap_fraction = intersection.length / line_b.length
        return max(0.0, min(1.0, overlap_fraction))

    def _get_point_at_fraction(self, coords: list[Coord], fraction: float) -> Coord:
        """
        Walk coordinate sequence and return point at the given fractional distance (0.0 to 1.0).
        """
        if not coords:
            return Coord(lat=0.0, lng=0.0)
        if len(coords) == 1 or fraction <= 0.0:
            return coords[0]
        if fraction >= 1.0:
            return coords[-1]

        # Calculate cumulative distance along segments
        segment_lengths = []
        total_len = 0.0
        for i in range(len(coords) - 1):
            d = self._haversine_distance_km(coords[i], coords[i + 1])
            segment_lengths.append(d)
            total_len += d

        if total_len == 0.0:
            return coords[0]

        target_len = total_len * fraction
        accumulated = 0.0

        for i, length in enumerate(segment_lengths):
            if accumulated + length >= target_len:
                seg_fraction = (target_len - accumulated) / max(1e-9, length)
                p1, p2 = coords[i], coords[i + 1]
                lat = p1.lat + seg_fraction * (p2.lat - p1.lat)
                lng = p1.lng + seg_fraction * (p2.lng - p1.lng)
                return Coord(lat=round(lat, 6), lng=round(lng, 6))
            accumulated += length

        return coords[-1]

    def _route_bearing_at(self, coords: list[Coord], fraction: float) -> float:
        """Compute route bearing in degrees (0–360) at fractional distance."""
        p1 = self._get_point_at_fraction(coords, max(0.0, fraction - 0.02))
        p2 = self._get_point_at_fraction(coords, min(1.0, fraction + 0.02))

        lat1, lon1 = math.radians(p1.lat), math.radians(p1.lng)
        lat2, lon2 = math.radians(p2.lat), math.radians(p2.lng)
        d_lon = lon2 - lon1

        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0

    def _offset_coord(self, point: Coord, bearing_deg: float, km: float) -> Coord:
        """Compute new coordinate offset by distance and bearing."""
        earth_radius = 6371.0
        lat_rad = math.radians(point.lat)
        lng_rad = math.radians(point.lng)
        bearing_rad = math.radians(bearing_deg)

        dist_ratio = km / earth_radius
        new_lat = math.asin(
            math.sin(lat_rad) * math.cos(dist_ratio)
            + math.cos(lat_rad) * math.sin(dist_ratio) * math.cos(bearing_rad)
        )
        new_lng = lng_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(dist_ratio) * math.cos(lat_rad),
            math.cos(dist_ratio) - math.sin(lat_rad) * math.sin(new_lat),
        )
        return Coord(lat=round(math.degrees(new_lat), 6), lng=round(math.degrees(new_lng), 6))

    def _is_on_land(self, coord: Coord) -> bool:
        """Basic bounding check ensuring waypoint coordinate is within US land boundaries."""
        # Simple US mainland bounding check
        return (24.0 <= coord.lat <= 50.0) and (-125.0 <= coord.lng <= -66.0)

    def _haversine_distance_km(self, c1: Coord, c2: Coord) -> float:
        """Great circle distance in kilometers."""
        r = 6371.0
        d_lat = math.radians(c2.lat - c1.lat)
        d_lng = math.radians(c2.lng - c1.lng)
        a = (
            math.sin(d_lat / 2.0) ** 2
            + math.cos(math.radians(c1.lat)) * math.cos(math.radians(c2.lat))
            * math.sin(d_lng / 2.0) ** 2
        )
        return 2.0 * r * math.asin(math.sqrt(max(0.0, a)))

    def _request_route(
        self,
        origin: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
        avoid_polygons: dict | None = None,
        index: int = 0,
    ) -> RouteResult:
        """Make ORS directions API call for [origin, destination]."""
        if not self.api_key:
            return self._mock_route_result(origin, destination, index=index)

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "coordinates": [[origin.lng, origin.lat], [destination.lng, destination.lat]],
            "profile": "driving-hgv",
            "instructions": True,
        }
        if avoid_polygons:
            body["options"] = {"avoid_polygons": avoid_polygons}

        try:
            resp = requests.post(ORS_DIRECTIONS_URL, json=body, headers=headers, timeout=15)
            if resp.status_code == 400:
                raise RoutingError("ORS 400: Route rejected or avoid polygon exceeds API limits.")
            resp.raise_for_status()
            data = resp.json()
            return self._parse_ors_response(data, index=index)
        except requests.RequestException as exc:
            logger.error("ORS routing request failed: %s", exc)
            raise RoutingError(f"ORS routing error: {exc}") from exc

    def _request_route_via(
        self,
        origin: Coord,
        waypoint: Coord,
        destination: Coord,
        vehicle_params: VehicleParams,
        index: int = 1,
    ) -> RouteResult:
        """Make ORS directions API call via intermediate waypoint."""
        if not self.api_key:
            return self._mock_route_result(origin, destination, waypoint=waypoint, index=index)

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "coordinates": [
                [origin.lng, origin.lat],
                [waypoint.lng, waypoint.lat],
                [destination.lng, destination.lat],
            ],
            "profile": "driving-hgv",
            "instructions": True,
        }

        try:
            resp = requests.post(ORS_DIRECTIONS_URL, json=body, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_ors_response(data, index=index)
        except requests.RequestException as exc:
            raise RoutingError(f"ORS via-waypoint route error: {exc}") from exc

    def _parse_ors_response(self, data: dict, index: int) -> RouteResult:
        """Parse raw ORS GeoJSON response into a RouteResult dataclass."""
        routes = data.get("routes", [])
        if not routes:
            raise RoutingError("No route returned by OpenRouteService.")

        r = routes[0]
        summary = r.get("summary", {})
        distance_m = summary.get("distance", 0.0)
        duration_s = summary.get("duration", 0.0)
        geometry = r.get("geometry", "")

        step_distances_m = []
        step_durations_s = []
        via_roads = []

        segments = r.get("segments", [])
        for seg in segments:
            for step in seg.get("steps", []):
                step_distances_m.append(float(step.get("distance", 0.0)))
                step_durations_s.append(float(step.get("duration", 0.0)))
                road_name = step.get("name", "").strip()
                if road_name and road_name != "-" and road_name not in via_roads:
                    via_roads.append(road_name)

        name = f"Route {index + 1}"
        if via_roads:
            name += f" (via {via_roads[0]})"

        distance_miles = round(distance_m / 1609.344, 2)
        return RouteResult(
            index=index,
            name=name,
            encoded_geometry=geometry,
            distance_miles=distance_miles,
            duration_seconds=int(duration_s),
            via_roads=via_roads[:4],
            step_distances_m=step_distances_m,
            step_durations_s=step_durations_s,
        )

    def _mock_route_result(
        self,
        origin: Coord,
        destination: Coord,
        waypoint: Coord | None = None,
        index: int = 0,
    ) -> RouteResult:
        """Generate reproducible synthetic route for offline tests and development."""
        pts = [(origin.lat, origin.lng)]
        if waypoint:
            pts.append((waypoint.lat, waypoint.lng))
        else:
            # Intermediate curvature point
            lat_mid = (origin.lat + destination.lat) / 2.0 + (index * 0.15)
            lng_mid = (origin.lng + destination.lng) / 2.0 + (index * 0.15)
            pts.append((lat_mid, lng_mid))
        pts.append((destination.lat, destination.lng))

        encoded = polyline.encode(pts)
        dist_km = self._haversine_distance_km(origin, destination) * (1.0 + index * 0.08)
        dist_mi = round(dist_km * 0.621371, 2)
        dur_s = int(dist_mi / 55.0 * 3600)

        step_dist = [dist_mi * 1609.344 / 3.0] * 3
        step_dur = [dur_s / 3.0] * 3
        roads = [f"Interstate {45 + index * 10}"]

        return RouteResult(
            index=index,
            name=f"Route {index + 1} (via {roads[0]})",
            encoded_geometry=encoded,
            distance_miles=dist_mi,
            duration_seconds=dur_s,
            via_roads=roads,
            step_distances_m=step_dist,
            step_durations_s=step_dur,
        )


DEFAULT_ROUTING_PROVIDER = ORSRoutingProvider()

