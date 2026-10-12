"""
Test suite for Route Radar Corridor Heatmap engine.
Tests HM_01 through HM_05: Corridor bounds, truck load integration, 49h horizons,
and coordinate snapping.
"""
from services.data_types import Coord, WeatherReading
from services.heatmap import (
    compute_heatmap_data,
    generate_corridor_grid,
    min_distance_to_polyline_miles,
)


class TestHeatmapSuite:
    """HM_01 – HM_05: Corridor grid generation and precomputation validation."""

    def test_hm_01_corridor_grid_within_20_miles(self):
        """HM_01: Generated corridor grid cells lie within 20 miles of route polyline."""
        # Route from Dallas to Houston (approx 240 mi along I-45)
        route = [
            Coord(lat=32.7767, lng=-96.7970),
            Coord(lat=31.2500, lng=-96.0000),
            Coord(lat=29.7604, lng=-95.3698),
        ]
        cells = generate_corridor_grid(
            [route], corridor_width_miles=20.0, grid_spacing_degrees=0.25
        )
        assert len(cells) > 0
        for cell in cells:
            dist = min_distance_to_polyline_miles(cell, route)
            assert dist <= 25.0  # Within corridor threshold allowing snap tolerance

    def test_hm_02_excludes_far_bounding_box_corners(self):
        """HM_02: Far points (e.g., perpendicular > 50 mi off) are excluded from the grid."""
        route = [
            Coord(lat=32.0, lng=-96.0),
            Coord(lat=30.0, lng=-96.0),
        ]
        cells = generate_corridor_grid(
            [route], corridor_width_miles=20.0, grid_spacing_degrees=0.25
        )
        # Point far west at -99.0 longitude is > 100 miles away
        far_lng_cells = [c for c in cells if abs(c.lng - (-99.0)) < 0.3]
        assert len(far_lng_cells) == 0

    def test_hm_03_truck_weight_override_applied_to_cells(self):
        """
        HM_03: Heatmap cell risk calculation integrates truck weight override rules
        (e.g., 48 mph wind with load > 30,000 lbs escalates to No Travel = 4).
        """
        cell_coord = Coord(lat=32.0, lng=-96.0)
        start_ts = 1760000000

        # Construct 49 hourly readings with high wind at hour 0
        readings = [
            WeatherReading(
                timestamp_utc=start_ts + h * 3600,
                wind_mph=48.0 if h == 0 else 10.0,
                wind_gusts_mph=55.0,
                rain_in_hr=0.0,
                snow_in_hr=0.0,
                temperature_f=65.0,
            )
            for h in range(49)
        ]
        weather_data = {(32.0, -96.0): readings}

        # Case A: Light load (25,000 lbs) -> 48 mph wind is Severe (level 3)
        cells_light = compute_heatmap_data(
            [cell_coord], weather_data, load_weight_lbs=25000, start_hour_utc=start_ts, num_hours=49
        )
        assert cells_light[0].forecasts[start_ts] == 3

        # Case B: Heavy load (35,000 lbs) -> 48 mph wind escalates to No Travel (level 4)
        cells_heavy = compute_heatmap_data(
            [cell_coord], weather_data, load_weight_lbs=35000, start_hour_utc=start_ts, num_hours=49
        )
        assert cells_heavy[0].forecasts[start_ts] == 4

    def test_hm_04_exactly_49_forecast_hours_per_cell(self):
        """HM_04: Every heatmap cell contains exactly 49 hourly timestamps (0 to 48h)."""
        cell_coord = Coord(lat=32.0, lng=-96.0)
        start_ts = 1760000000
        readings = [
            WeatherReading(
                timestamp_utc=start_ts + h * 3600,
                wind_mph=15.0,
                wind_gusts_mph=20.0,
                rain_in_hr=0.0,
                snow_in_hr=0.0,
                temperature_f=60.0,
            )
            for h in range(49)
        ]
        weather_data = {(32.0, -96.0): readings}

        cells = compute_heatmap_data(
            [cell_coord], weather_data, load_weight_lbs=40000, start_hour_utc=start_ts, num_hours=49
        )
        assert len(cells) == 1
        forecasts = cells[0].forecasts
        assert len(forecasts) == 49
        for h in range(49):
            ts = start_ts + h * 3600
            assert ts in forecasts
            assert 0 <= forecasts[ts] <= 4

    def test_hm_05_grid_coordinates_snapped(self):
        """HM_05: Grid coordinates are snapped to multiples of grid spacing (0.25°)."""
        route = [
            Coord(lat=32.1234, lng=-96.5678),
            Coord(lat=31.4321, lng=-96.1234),
        ]
        spacing = 0.25
        cells = generate_corridor_grid(
            [route], corridor_width_miles=20.0, grid_spacing_degrees=spacing
        )
        assert len(cells) > 0
        for c in cells:
            # Lat and Lng must be very close to integer multiple of 0.25
            lat_rem = abs(c.lat / spacing - round(c.lat / spacing))
            lng_rem = abs(c.lng / spacing - round(c.lng / spacing))
            assert lat_rem < 1e-4
            assert lng_rem < 1e-4
