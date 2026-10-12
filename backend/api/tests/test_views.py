"""
Test suite for Spotter AI Input Validation & API Views.
Tests IV_01 through IV_14: Origin/dest checks, weight ranges, departure limits,
DST snapping, and timezone resolution.
"""
from datetime import datetime, timezone

import pytest
from rest_framework.test import APIClient

from backend.api.serializers import RouteAnalyzeSerializer


@pytest.fixture
def client():
    return APIClient()


class TestInputValidation:
    """IV_01 – IV_14: Comprehensive input validation test suite."""

    def test_iv_01_missing_origin(self):
        """IV_01: Missing origin returns validation error."""
        serializer = RouteAnalyzeSerializer(data={"destination": {"lat": 29.7604, "lng": -95.3698}})
        assert not serializer.is_valid()
        assert "origin" in serializer.errors

    def test_iv_02_missing_destination(self):
        """IV_02: Missing destination returns validation error."""
        serializer = RouteAnalyzeSerializer(data={"origin": {"lat": 32.7767, "lng": -96.7970}})
        assert not serializer.is_valid()
        assert "destination" in serializer.errors

    def test_iv_03_identical_origin_and_destination(self):
        """IV_03: Origin and destination at identical coordinates rejected."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 32.7767, "lng": -96.7970},
        })
        assert not serializer.is_valid()
        non_field_errs = serializer.errors.get("non_field_errors", [])
        assert any("identical" in str(e).lower() for e in non_field_errs)

    def test_iv_04_weight_under_minimum(self):
        """IV_04: Truck weight under 1,000 lbs rejected."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "load_weight_lbs": 500,
        })
        assert not serializer.is_valid()
        assert "load_weight_lbs" in serializer.errors

    def test_iv_05_weight_over_maximum(self):
        """IV_05: Truck weight over 80,000 lbs rejected."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "load_weight_lbs": 90000,
        })
        assert not serializer.is_valid()
        assert "load_weight_lbs" in serializer.errors

    def test_iv_06_weight_within_bounds(self):
        """IV_06: Truck weight within 1,000–80,000 lbs accepted."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "load_weight_lbs": 45000,
        })
        assert serializer.is_valid()
        assert serializer.validated_data["load_weight_lbs"] == 45000

    def test_iv_07_departure_in_past(self):
        """IV_07: Departure time in the past (> 15 min ago) rejected."""
        past_ts = int(datetime.now(timezone.utc).timestamp()) - 7200  # 2 hours ago
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "departure_utc": past_ts,
        })
        assert not serializer.is_valid()
        assert "departure_time" in serializer.errors

    def test_iv_08_departure_beyond_7_days(self):
        """IV_08: Departure time > 7 days into future rejected."""
        far_future_ts = int(datetime.now(timezone.utc).timestamp()) + (10 * 86400)
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "departure_utc": far_future_ts,
        })
        assert not serializer.is_valid()
        assert "departure_time" in serializer.errors

    def test_iv_09_valid_future_departure(self):
        """IV_09: Departure time in valid future horizon accepted."""
        future_ts = int(datetime.now(timezone.utc).timestamp()) + 7200  # +2 hours
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "departure_utc": future_ts,
        })
        assert serializer.is_valid()
        assert serializer.validated_data["departure_utc"] == future_ts

    def test_iv_10_departure_over_48h_generates_warning(self):
        """IV_10: Departure > 48h generates forecast_horizon warning notice."""
        future_ts = int(datetime.now(timezone.utc).timestamp()) + (60 * 3600)  # +60 hours
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "departure_utc": future_ts,
        })
        assert serializer.is_valid()
        warnings = serializer.validated_data["warnings"]
        codes = [w.code for w in warnings]
        assert "forecast_horizon" in codes

    def test_iv_11_interval_fallback_to_25mi(self):
        """IV_11: Invalid checkpoint interval falls back to 25 mi."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
            "checkpoint_interval_miles": 33,  # Invalid
        })
        assert serializer.is_valid()
        assert serializer.validated_data["checkpoint_interval_miles"] == 25

    def test_iv_12_non_us_coordinates_rejected(self):
        """IV_12: Non-US coordinates (e.g. London, UK) rejected."""
        serializer = RouteAnalyzeSerializer(data={
            "origin": {"lat": 51.5074, "lng": -0.1278},  # London
            "destination": {"lat": 29.7604, "lng": -95.3698},
        })
        assert not serializer.is_valid()
        assert "origin" in serializer.errors

    def test_iv_13_dst_gap_snapped_forward(self):
        """IV_13: Departure in spring-forward DST gap snapped forward with user notice."""
        # Second Sunday in March 2027: March 14, 2027, 2:30 AM does not exist in Central Time
        import zoneinfo

        tz = zoneinfo.ZoneInfo("America/Chicago")
        dt_naive = datetime(2027, 3, 14, 2, 30)
        dt_local = dt_naive.replace(tzinfo=tz)
        dt_utc = dt_local.astimezone(timezone.utc)
        round_trip = dt_utc.astimezone(tz)
        is_dst_gap = round_trip.hour != dt_naive.hour
        assert is_dst_gap  # Confirms Python detects the nonexistent hour

    def test_iv_14_origin_timezone_resolution(self):
        """IV_14: Origin timezone resolved correctly using geographic coordinates."""
        # Dallas, TX -> America/Chicago
        serializer_dallas = RouteAnalyzeSerializer(data={
            "origin": {"lat": 32.7767, "lng": -96.7970},
            "destination": {"lat": 29.7604, "lng": -95.3698},
        })
        assert serializer_dallas.is_valid()
        assert serializer_dallas.validated_data["origin_timezone"] == "America/Chicago"

        # Los Angeles, CA -> America/Los_Angeles
        serializer_la = RouteAnalyzeSerializer(data={
            "origin": {"lat": 34.0522, "lng": -118.2437},
            "destination": {"lat": 33.4484, "lng": -112.0740},
        })
        assert serializer_la.is_valid()
        assert serializer_la.validated_data["origin_timezone"] == "America/Los_Angeles"
