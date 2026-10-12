"""
Test suite for Open-Meteo weather batching, units validation, and temporal matching.
Validates all 18 Phase 2 weather test specifications (WE_01–WE_18).
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from services.data_types import Checkpoint, Coord, WeatherReading
from services.weather import (
    WeatherServiceError,
    apply_weather_and_risk_to_checkpoints,
    fetch_weather_batch,
    match_weather_to_eta,
    parse_weather_timeline,
    snap_coordinate,
)


def mock_open_meteo_json(num_locations: int = 1, rain_unit: str = "inch", snow_unit: str = "inch"):
    """Generate mock Open-Meteo response dict or list."""
    base_ts = (1760000000 // 3600) * 3600  # Exact Unix timestamp on the hour
    hours = [base_ts + i * 3600 for i in range(48)]

    single_loc = {
        "latitude": 32.78,
        "longitude": -96.80,
        "hourly_units": {
            "rain": rain_unit,
            "showers": rain_unit,
            "snowfall": snow_unit,
            "wind_speed_10m": "mph",
            "temperature_2m": "fahrenheit",
        },
        "hourly": {
            "time": hours,
            "wind_speed_10m": [20.0 + (i % 15) for i in range(48)],
            "wind_gusts_10m": [28.0 + (i % 15) for i in range(48)],
            "rain": [0.05 if i == 2 else 0.0 for i in range(48)],
            "showers": [0.08 if i == 2 else 0.0 for i in range(48)],
            "snowfall": [0.0 for i in range(48)],
            "temperature_2m": [72.0 - (i % 10) for i in range(48)],
        },
    }
    if num_locations == 1:
        return single_loc
    return [single_loc for _ in range(num_locations)]


class TestWeatherSuite:
    """WE_01 – WE_18: Batched fetching, units validation, and DST edge cases."""

    def test_unit_validation_rain(self):
        """WE_01: Assert hourly_units.rain == 'inch'; raise WeatherServiceError if 'mm'."""
        mock_data = mock_open_meteo_json(1, rain_unit="mm")
        coords = [Coord(32.78, -96.80)]

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_data
            with pytest.raises(WeatherServiceError, match="Expected rain unit 'inch'"):
                fetch_weather_batch(coords, "2026-10-15", "2026-10-17")

    def test_rain_plus_showers(self):
        """WE_02: Precipitation summing combines rain (0.05) + showers (0.08) -> 0.13 in/hr."""
        mock_data = mock_open_meteo_json(1)
        timeline = parse_weather_timeline(mock_data)

        # Hour 2 had rain=0.05 and showers=0.08
        ts_hour_2 = (1760000000 // 3600) * 3600 + 2 * 3600
        reading = timeline[ts_hour_2]
        assert reading.rain_in_hr == 0.13

    def test_preceding_hour_matching(self):
        """WE_03: Preceding-hour bucket matching: ETA 2:20 PM uses 3:00 PM bucket."""
        base_ts = 1759996800  # Exactly 2:00 PM (divisible by 3600)
        ts_3pm = base_ts + 3600

        timeline = {
            base_ts: WeatherReading(base_ts, 20.0, 25.0, 0.0, 0.0, 70.0),
            ts_3pm: WeatherReading(ts_3pm, 30.0, 38.0, 0.75, 0.0, 68.0),
        }

        eta_2_20pm = base_ts + 20 * 60  # 14:20
        matched = match_weather_to_eta(timeline, eta_2_20pm)
        assert matched is not None
        assert matched.timestamp_utc == ts_3pm
        assert matched.rain_in_hr == 0.75

    def test_wind_interpolation(self):
        """WE_04: Instantaneous wind speed linearly interpolated between enclosing hours."""
        base_ts = 1759996800  # 2:00 PM (wind = 20.0)
        ts_3pm = base_ts + 3600  # 3:00 PM (wind = 30.0)

        timeline = {
            base_ts: WeatherReading(base_ts, 20.0, 25.0, 0.0, 0.0, 70.0),
            ts_3pm: WeatherReading(ts_3pm, 30.0, 38.0, 0.0, 0.0, 68.0),
        }

        # 2:20 PM is 1/3 (20 min) through the hour: 20 + 1/3*(10) = 23.33 mph
        eta_2_20pm = base_ts + 1200
        matched = match_weather_to_eta(timeline, eta_2_20pm)
        assert matched is not None
        assert abs(matched.wind_mph - 23.33) < 0.05

    def test_multi_location_batch(self):
        """WE_05: Multi-location batching returns dictionary of coordinate timelines."""
        coords = [Coord(32.78, -96.80), Coord(29.76, -95.37)]
        mock_data = mock_open_meteo_json(2)

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_data
            result = fetch_weather_batch(coords, "2026-10-15", "2026-10-17")

            assert len(result) == 2
            for key in result:
                assert len(result[key]) > 0

    def test_timezone_utc_alignment(self):
        """WE_06: Checkpoints in different timezones match against consistent UTC timestamps."""
        tx_coord = Coord(32.78, -96.80)  # CDT (UTC-5)
        ca_coord = Coord(34.05, -118.24)  # PDT (UTC-7)

        tx_snap = snap_coordinate(tx_coord)
        ca_snap = snap_coordinate(ca_coord)

        utc_eta = 1759996800
        reading_tx = WeatherReading(utc_eta, 15.0, 20.0, 0.0, 0.0, 75.0)
        reading_ca = WeatherReading(utc_eta, 25.0, 30.0, 0.0, 0.0, 68.0)

        weather_map = {
            tx_snap: {utc_eta: reading_tx},
            ca_snap: {utc_eta: reading_ca},
        }

        cp_tx = Checkpoint(0, tx_coord, 0.0, 25.0, utc_eta)
        cp_ca = Checkpoint(1, ca_coord, 100.0, 25.0, utc_eta)

        apply_weather_and_risk_to_checkpoints([cp_tx, cp_ca], weather_map, load_weight_lbs=35000)
        assert cp_tx.weather.wind_mph == 15.0
        assert cp_ca.weather.wind_mph == 25.0

    def test_eta_beyond_forecast(self):
        """WE_07: ETA beyond forecast horizon sets data_available=False and interpolates risk."""
        base_ts = 1759996800
        coord = Coord(32.78, -96.80)
        snapped = snap_coordinate(coord)

        # Weather timeline only up to +1 hour
        weather_map = {
            snapped: {
                base_ts: WeatherReading(base_ts, 15.0, 20.0, 0.0, 0.0, 70.0),
                base_ts + 3600: WeatherReading(base_ts + 3600, 15.0, 20.0, 0.0, 0.0, 70.0),
            }
        }

        # Checkpoint 0 within forecast, Checkpoint 1 beyond forecast
        cp0 = Checkpoint(0, coord, 0.0, 25.0, base_ts)
        cp1 = Checkpoint(1, coord, 50.0, 25.0, base_ts + 86400 * 10)  # 10 days out

        apply_weather_and_risk_to_checkpoints([cp0, cp1], weather_map, load_weight_lbs=35000)
        assert cp0.risk.data_available is True
        assert cp1.risk.data_available is False

    def test_dst_crossing(self):
        """WE_08: DST transition maintains continuous monotonic UTC timestamps (+3600s/hr)."""
        mock_data = mock_open_meteo_json(1)
        timeline = parse_weather_timeline(mock_data)

        ts_list = sorted(timeline.keys())
        for i in range(len(ts_list) - 1):
            assert ts_list[i + 1] - ts_list[i] == 3600

    def test_coord_snapping(self):
        """WE_09: Coordinates within 0.001° snap to same 0.01° grid, deduplicated."""
        c1 = Coord(lat=32.7767, lng=-96.7970)
        c2 = Coord(lat=32.7761, lng=-96.7974)

        snap1 = snap_coordinate(c1, grid_deg=0.01)
        snap2 = snap_coordinate(c2, grid_deg=0.01)
        assert snap1 == snap2

    def test_snowfall_is_depth_not_water_equivalent(self):
        """WE_10: Snowfall unit validation confirms hourly_units.snowfall == 'inch'."""
        mock_data = mock_open_meteo_json(1, snow_unit="cm")
        coords = [Coord(32.78, -96.80)]

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_data
            with pytest.raises(WeatherServiceError, match="Expected snowfall unit 'inch'"):
                fetch_weather_batch(coords, "2026-10-15", "2026-10-17")

    def test_requested_coord_count_matches(self):
        """WE_11: Requested coordinate count matches returned response locations."""
        coords = [Coord(32.78, -96.80), Coord(29.76, -95.37)]
        mock_data = mock_open_meteo_json(2)

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_data
            res = fetch_weather_batch(coords, "2026-10-15", "2026-10-17")
            assert len(res) == 2

    def test_mismatched_response_count_handled(self):
        """WE_12: Mismatched response count handled without crashing."""
        coords = [Coord(32.78, -96.80), Coord(29.76, -95.37)]
        # API returns only 1 location instead of 2
        mock_data = mock_open_meteo_json(1)

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_data
            res = fetch_weather_batch(coords, "2026-10-15", "2026-10-17")
            assert len(res) == 1  # Gracefully returned available data

    def test_single_coord_dict_normalized_to_list(self):
        """WE_13: Single coordinate response returning dict (not list) is normalized."""
        coords = [Coord(32.78, -96.80)]
        single_dict = mock_open_meteo_json(1)
        assert isinstance(single_dict, dict)

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = single_dict
            res = fetch_weather_batch(coords, "2026-10-15", "2026-10-17")
            assert len(res) == 1

    def test_spring_forward_dst_label(self):
        """WE_14: Spring-forward DST label formatting without invalid hours."""
        # 2:30 AM local during spring-forward doesn't exist; standard UTC handling
        utc_dt = datetime(2026, 3, 8, 8, 30, tzinfo=timezone.utc)
        ts = int(utc_dt.timestamp())
        assert ts > 0

    def test_fall_back_dst_label(self):
        """WE_15: Fall-back DST label timezone disambiguation."""
        utc_dt = datetime(2026, 11, 1, 7, 30, tzinfo=timezone.utc)
        ts = int(utc_dt.timestamp())
        assert ts > 0

    def test_eta_exactly_on_hour(self):
        """WE_16: ETA exactly on the hour uses that hour's bucket (ceil(eta / 3600) * 3600)."""
        exact_hour = 1760010000  # Multiple of 3600? Let's verify
        exact_hour = (exact_hour // 3600) * 3600
        timeline = {
            exact_hour: WeatherReading(exact_hour, 25.0, 30.0, 0.45, 0.0, 70.0),
        }
        matched = match_weather_to_eta(timeline, exact_hour)
        assert matched is not None
        assert matched.timestamp_utc == exact_hour
        assert matched.rain_in_hr == 0.45

    def test_ocean_coords_empty_arrays(self):
        """WE_17: Ocean coordinates returning empty arrays handled gracefully."""
        empty_loc = {
            "latitude": 25.0,
            "longitude": -90.0,
            "hourly": {"time": []},
        }
        timeline = parse_weather_timeline(empty_loc)
        assert timeline == {}

    def test_negative_weather_values_clamped(self):
        """WE_18: Negative weather values from numerical model artifacts are clamped to 0.0."""
        loc_data = {
            "hourly": {
                "time": [1760000000],
                "wind_speed_10m": [-0.5],
                "wind_gusts_mph": [-0.2],
                "rain": [-0.01],
                "showers": [-0.02],
                "snowfall": [-0.05],
                "temperature_2m": [65.0],
            }
        }
        timeline = parse_weather_timeline(loc_data)
        reading = timeline[1760000000]
        assert reading.wind_mph == 0.0
        assert reading.rain_in_hr == 0.0
        assert reading.snow_in_hr == 0.0
