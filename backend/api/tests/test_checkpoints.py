"""
Test suite for checkpoint sampling, non-linear ETA interpolation, and Voronoi segment miles.
Validates all 10 Phase 2 checkpoint sampling test specifications (CS_01–CS_10).
"""
from services.checkpoints import (
    distance_point_to_polyline_miles,
    sample_checkpoints,
)
from services.data_types import Coord

MILES_TO_METERS = 1609.344


def generate_straight_route(distance_miles: float, num_points: int = 20) -> list[Coord]:
    """Generate coordinate line along latitude (approx 69.0934 miles per degree latitude)."""
    d_lat = distance_miles / 69.0934
    start_lat = 30.0
    start_lng = -96.0
    coords = []
    for i in range(num_points):
        frac = i / (num_points - 1)
        coords.append(Coord(lat=start_lat + frac * d_lat, lng=start_lng))
    return coords


class TestCheckpointSampling:
    """CS_01 – CS_10: Interval sampling, boundary caps, non-linear ETAs, and mile attribution."""

    def test_25mi_interval(self):
        """CS_01: 250 mi route at 25 mi interval -> 11 checkpoints (0, 25, ..., 250)."""
        coords = generate_straight_route(250.0, num_points=50)
        step_dist = [250.0 * MILES_TO_METERS]
        step_dur = [15000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=25
        )
        assert len(cps) == 11
        assert cps[0].cumulative_miles == 0.0
        assert abs(cps[-1].cumulative_miles - 250.0) < 0.5

    def test_10mi_interval(self):
        """CS_02: 50 mi route at 10 mi interval -> 6 checkpoints (0, 10, ..., 50)."""
        coords = generate_straight_route(50.0, num_points=30)
        step_dist = [50.0 * MILES_TO_METERS]
        step_dur = [3600.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=10
        )
        assert len(cps) == 6
        assert cps[0].cumulative_miles == 0.0
        assert abs(cps[-1].cumulative_miles - 50.0) < 0.5

    def test_50mi_interval(self):
        """CS_03: 800 mi route at 50 mi interval -> 17 checkpoints (0, 50, ..., 800)."""
        coords = generate_straight_route(800.0, num_points=100)
        step_dist = [800.0 * MILES_TO_METERS]
        step_dur = [48000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=50
        )
        assert len(cps) == 17
        assert cps[0].cumulative_miles == 0.0
        assert abs(cps[-1].cumulative_miles - 800.0) < 1.0

    def test_minimum_2_checkpoints(self):
        """CS_04: Very short route (5 mi) -> at least 2 checkpoints (origin & destination)."""
        coords = generate_straight_route(5.0, num_points=5)
        step_dist = [5.0 * MILES_TO_METERS]
        step_dur = [300.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=25
        )
        assert len(cps) >= 2
        assert cps[0].cumulative_miles == 0.0
        assert abs(cps[-1].cumulative_miles - 5.0) < 0.2

    def test_maximum_60_checkpoints(self):
        """CS_05: Long route (3,000 mi, 10 mi interval) capped at <= 60 checkpoints."""
        coords = generate_straight_route(3000.0, num_points=200)
        step_dist = [3000.0 * MILES_TO_METERS]
        step_dur = [180000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=10
        )
        assert len(cps) <= 60
        assert cps[0].cumulative_miles == 0.0
        assert abs(cps[-1].cumulative_miles - 3000.0) < 5.0

    def test_segment_miles_sum(self):
        """CS_06: Sum of all checkpoint segment_miles exactly matches total route distance."""
        route_dist = 320.0
        coords = generate_straight_route(route_dist, num_points=60)
        step_dist = [route_dist * MILES_TO_METERS]
        step_dur = [20000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=25
        )
        total_attributed = sum(cp.segment_miles for cp in cps)
        assert abs(total_attributed - cps[-1].cumulative_miles) < 0.05

    def test_eta_per_step_durations(self):
        """CS_07: ETA uses non-linear per-step durations reflecting highway vs urban speeds."""
        # Step 1: 50 mi in 50 min (60 mph)
        # Step 2: 10 mi in 40 min (15 mph urban)
        step_dist = [50.0 * MILES_TO_METERS, 10.0 * MILES_TO_METERS]
        step_dur = [3000.0, 2400.0]
        coords = generate_straight_route(60.0, num_points=40)

        dep_ts = 1760000000
        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=dep_ts, interval_miles=25
        )

        # Checkpoint at 50 mi should have ETA close to dep_ts + 3000
        cp_50 = min(cps, key=lambda cp: abs(cp.cumulative_miles - 50.0))
        elapsed_50 = cp_50.eta_utc - dep_ts
        assert abs(elapsed_50 - 3000) < 180

    def test_eta_varied_speeds(self):
        """
        CS_08: 100 mi route: first 50 mi at 60 mph (50 min), next 50 mi at 30 mph (100 min).
        CP at 50 mi ETA = +50 min (3000 s), CP at 100 mi ETA = +150 min (9000 s).
        """
        step_dist = [50.0 * MILES_TO_METERS, 50.0 * MILES_TO_METERS]
        step_dur = [3000.0, 6000.0]  # 50 min, 100 min
        coords = generate_straight_route(100.0, num_points=50)

        dep_ts = 1760000000
        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=dep_ts, interval_miles=25
        )

        cp_50 = min(cps, key=lambda cp: abs(cp.cumulative_miles - 50.0))
        assert abs((cp_50.eta_utc - dep_ts) - 3000) < 120

        cp_100 = cps[-1]
        assert abs((cp_100.eta_utc - dep_ts) - 9000) < 60

    def test_checkpoints_on_polyline(self):
        """CS_09: All sampled checkpoints lie within 0.1 miles of the decoded polyline."""
        coords = generate_straight_route(150.0, num_points=30)
        step_dist = [150.0 * MILES_TO_METERS]
        step_dur = [9000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=25
        )
        for cp in cps:
            dist_to_line = distance_point_to_polyline_miles(cp.coord, coords)
            assert dist_to_line <= 0.1

    def test_mile_attribution_first_last(self):
        """CS_10: Halfway attribution for start (0 to mid(0,1)) and end (mid(n-2, n-1) to total)."""
        coords = generate_straight_route(100.0, num_points=40)
        step_dist = [100.0 * MILES_TO_METERS]
        step_dur = [6000.0]

        cps = sample_checkpoints(
            coords, step_dist, step_dur, departure_utc=1760000000, interval_miles=25
        )
        # For 0, 25, 50, 75, 100 mi:
        # CP 0 covers 0 to 12.5 -> 12.5 mi
        assert abs(cps[0].segment_miles - 12.5) < 0.5
        # CP 4 covers 87.5 to 100 -> 12.5 mi
        assert abs(cps[-1].segment_miles - 12.5) < 0.5
        # Middle CPs cover 25 mi each
        for mid_cp in cps[1:-1]:
            assert abs(mid_cp.segment_miles - 25.0) < 0.5
