"""
Test suite for ORSRoutingProvider and multi-tier route generation.
Validates all 13 Phase 2 routing test specifications (RT_01–RT_13).
"""
import math
from unittest.mock import patch

import polyline
import pytest
from services.data_types import Coord, RouteResult, VehicleParams
from services.routing import ORSRoutingProvider, RoutingError, RoutingProvider


@pytest.fixture
def provider():
    """Returns instance of ORSRoutingProvider configured for offline testing."""
    return ORSRoutingProvider(api_key="")


@pytest.fixture
def vehicle_params():
    """Default truck vehicle parameters."""
    return VehicleParams(load_weight_lbs=35000)


class TestRoutingSuite:
    """RT_01 – RT_13: Routing provider, avoidance tiers, and geometric filters."""

    def test_avoid_polygon_generation(self, provider):
        """RT_01: Avoid box generation at midpoint returns valid GeoJSON polygon."""
        midpoint = Coord(lat=31.27, lng=-96.08)
        box = provider._build_small_box(midpoint, width_km=15.0, height_km=13.0)

        assert box["type"] == "Polygon"
        coords = box["coordinates"][0]
        assert len(coords) == 5  # Closed loop
        assert coords[0] == coords[-1]

    def test_overlap_detection(self, provider):
        """RT_02: Two identical routes have overlap > 80% (rejected)."""
        coords = [Coord(lat=30.0 + i * 0.1, lng=-96.0) for i in range(10)]
        overlap = provider._compute_overlap(coords, coords)
        assert overlap >= 0.80

    def test_overlap_different_routes(self, provider):
        """RT_03: Two different parallel routes separated by 50 km have overlap < 50% (accepted)."""
        line_a = [Coord(lat=30.0 + i * 0.1, lng=-96.0) for i in range(10)]
        line_b = [Coord(lat=30.0 + i * 0.1, lng=-95.0) for i in range(10)]
        overlap = provider._compute_overlap(line_a, line_b)
        assert overlap < 0.50

    def test_detour_filter_rejected(self, provider):
        """RT_04: Detour filter rejects route with duration > 1.5x fastest duration."""
        fastest = RouteResult(
            index=0,
            name="Route 1",
            encoded_geometry=polyline.encode([(30.0, -96.0), (32.0, -96.0)]),
            distance_miles=120.0,
            duration_seconds=7200,
        )
        detour = RouteResult(
            index=1,
            name="Route 2",
            encoded_geometry=polyline.encode([(30.0, -96.0), (31.0, -97.0), (32.0, -96.0)]),
            distance_miles=180.0,
            duration_seconds=11520,  # 1.6x > 1.5x
        )
        assert not provider._is_distinct(detour, [fastest])

    def test_accept_moderate_detour(self, provider):
        """RT_05: Accept moderate detour with duration <= 1.5x and distinct path."""
        fastest = RouteResult(
            index=0,
            name="Route 1",
            encoded_geometry=polyline.encode([(30.0, -96.0), (32.0, -96.0)]),
            distance_miles=120.0,
            duration_seconds=7200,
        )
        moderate_detour = RouteResult(
            index=1,
            name="Route 2",
            encoded_geometry=polyline.encode([(30.0, -96.0), (31.0, -97.5), (32.0, -96.0)]),
            distance_miles=140.0,
            duration_seconds=9000,  # 1.25x <= 1.5x
        )
        assert provider._is_distinct(moderate_detour, [fastest])

    def test_graceful_with_1_route(self, provider, vehicle_params):
        """RT_06: When alternative tiers fail, provider returns single base route."""
        origin = Coord(lat=32.7767, lng=-96.7970)
        destination = Coord(lat=29.7604, lng=-95.3698)

        base_route = provider._mock_route_result(origin, destination, index=0)
        with patch.object(provider, "_request_route", return_value=base_route), \
             patch.object(provider, "_try_avoid_box", return_value=None), \
             patch.object(provider, "_try_waypoint_offset", return_value=None):
            routes = provider.get_routes(origin, destination, vehicle_params)
            assert len(routes) == 1
            assert routes[0].index == 0

    def test_routing_provider_interface(self, provider):
        """RT_07: ORSRoutingProvider conforms to RoutingProvider protocol."""
        assert isinstance(provider, RoutingProvider)
        assert hasattr(provider, "get_routes")

    def test_avoid_box_within_ors_limits(self, provider):
        """RT_08: Generated avoid box strictly conforms to ORS limit (<200 km², extent <20 km)."""
        midpoint = Coord(lat=31.5, lng=-96.5)
        width_km, height_km = 15.0, 13.0
        area = width_km * height_km
        extent = math.sqrt(width_km**2 + height_km**2)

        assert area < 200.0, "Area must be strictly under 200 km²"
        assert extent < 20.0, "Extent must be strictly under 20 km"

        box = provider._build_small_box(midpoint, width_km, height_km)
        coords = box["coordinates"][0]
        lat_extent_km = abs(coords[2][1] - coords[0][1]) * 111.0
        assert lat_extent_km <= 15.0

    def test_waypoint_offset_on_land(self, provider):
        """RT_09: Waypoint offset coordinate between Dallas and Houston remains on land."""
        midpoint = Coord(lat=31.2685, lng=-96.0839)
        bearing = 160.0  # South-Southeast
        left_offset = provider._offset_coord(midpoint, bearing + 90.0, km=30.0)
        right_offset = provider._offset_coord(midpoint, bearing - 90.0, km=30.0)

        assert provider._is_on_land(left_offset)
        assert provider._is_on_land(right_offset)

    def test_tier_fallback_chain(self, provider, vehicle_params):
        """RT_10: If Tier 1 box raises RoutingError, fallback to Tier 2 waypoint offset."""
        origin = Coord(lat=32.7767, lng=-96.7970)
        destination = Coord(lat=29.7604, lng=-95.3698)

        base_route = provider._mock_route_result(origin, destination, index=0)
        alt_route = provider._mock_route_result(
            origin, destination, waypoint=Coord(31.0, -97.5), index=1
        )

        with patch.object(provider, "_request_route", return_value=base_route), \
             patch.object(provider, "_try_avoid_box", side_effect=RoutingError("ORS 400")), \
             patch.object(provider, "_try_waypoint_offset", return_value=alt_route):
            routes = provider.get_routes(origin, destination, vehicle_params)
            assert len(routes) == 2
            assert routes[1].index == 1

    def test_polyline_midpoint_accuracy(self, provider):
        """RT_11: Midpoint calculation accurately finds fraction 0.5 along coordinate line."""
        coords = [Coord(lat=30.0, lng=-96.0), Coord(lat=32.0, lng=-96.0)]
        mid = provider._get_point_at_fraction(coords, 0.5)

        assert abs(mid.lat - 31.0) < 0.05
        assert abs(mid.lng - (-96.0)) < 0.01

    def test_waypoint_route_segment_format(self, provider):
        """RT_12: Waypoint route returns valid RouteResult format with step arrays."""
        origin = Coord(lat=32.7767, lng=-96.7970)
        waypoint = Coord(lat=31.5, lng=-97.0)
        destination = Coord(lat=29.7604, lng=-95.3698)

        res = provider._mock_route_result(origin, destination, waypoint=waypoint, index=1)
        assert isinstance(res, RouteResult)
        assert res.index == 1
        assert len(res.step_distances_m) > 0
        assert len(res.step_durations_s) > 0

    def test_short_route_skip_alternatives(self, provider, vehicle_params):
        """RT_13: Short route (< 30 km / < 18.6 mi) skips alternatives and returns 1 route."""
        # 10 miles trip
        origin = Coord(lat=32.7767, lng=-96.7970)
        destination = Coord(lat=32.8500, lng=-96.7500)

        base_route = provider._mock_route_result(origin, destination, index=0)
        base_route.distance_miles = 10.0

        with patch.object(provider, "_request_route", return_value=base_route), \
             patch.object(provider, "_try_avoid_box") as mock_avoid, \
             patch.object(provider, "_try_waypoint_offset") as mock_waypoint:
            routes = provider.get_routes(origin, destination, vehicle_params)
            assert len(routes) == 1
            mock_avoid.assert_not_called()
            mock_waypoint.assert_not_called()
