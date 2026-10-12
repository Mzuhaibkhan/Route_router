"""
Integration test suite for Route Radar pipeline.
Tests IT_01 through IT_08: End-to-end pipeline, downtime recovery, schema validation,
demo fixtures, cache key consistency, throttling, and cache stampede mutex.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from services.cache_utils import get_or_compute, make_route_cache_key
from services.data_types import RouteResult
from services.weather import WeatherServiceError


@pytest.fixture
def client():
    return APIClient()


class TestIntegrationPipeline:
    """IT_01 – IT_08: End-to-end integration and system resilience."""

    def test_it_01_end_to_end_pipeline(self, client):
        """IT_01: End-to-end pipeline execution returns full analysis response."""
        future_ts = int(datetime.now(timezone.utc).timestamp()) + 7200
        payload = {
            "origin": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
            "destination": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
            "departure_utc": future_ts,
            "load_weight_lbs": 35000,
            "checkpoint_interval_miles": 25,
        }

        # Mock routing provider and weather to return predictable data
        mock_route = RouteResult(
            index=0,
            name="Route 1 (via I-45 S)",
            encoded_geometry="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
            distance_miles=240.0,
            duration_seconds=14000,
            via_roads=["I-45 S"],
            step_distances_m=[240.0 * 1609.34],
            step_durations_s=[14000.0],
        )

        with patch("api.views.DEFAULT_ROUTING_PROVIDER.get_routes", return_value=[mock_route]):
            response = client.post("/api/routes/analyze", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "routes" in data
        assert len(data["routes"]) >= 1
        assert "heatmap" in data
        assert "risk_legend" in data

    def test_it_02_routing_downtime_error_recovery(self, client):
        """IT_02: Routing provider failure returns 502 with structured error."""
        future_ts = int(datetime.now(timezone.utc).timestamp()) + 7200
        payload = {
            "origin": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
            "destination": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
            "departure_utc": future_ts,
        }

        with patch(
            "api.views.DEFAULT_ROUTING_PROVIDER.get_routes",
            side_effect=Exception("ORS upstream connection timeout"),
        ):
            # Clear cache for this key to ensure provider is called
            from django.core.cache import cache
            cache.clear()
            response = client.post("/api/routes/analyze", payload, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "error" in response.json()

    def test_it_03_weather_service_degradation(self, client):
        """IT_03: Weather service failure degrades gracefully with warning and zero-crash."""
        future_ts = int(datetime.now(timezone.utc).timestamp()) + 7200
        payload = {
            "origin": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
            "destination": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
            "departure_utc": future_ts,
        }

        mock_route = RouteResult(
            index=0,
            name="Route 1",
            encoded_geometry="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
            distance_miles=100.0,
            duration_seconds=6000,
            step_distances_m=[100.0 * 1609.34],
            step_durations_s=[6000.0],
        )

        with patch("api.views.DEFAULT_ROUTING_PROVIDER.get_routes", return_value=[mock_route]), \
             patch("api.views.fetch_weather_batch", side_effect=WeatherServiceError("API down")):
            from django.core.cache import cache
            cache.clear()
            response = client.post("/api/routes/analyze", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        warning_codes = [w["code"] for w in data["warnings"]]
        assert "weather_service_degraded" in warning_codes

    def test_it_04_complete_response_schema_validation(self, client):
        """IT_04: Response payload strictly adheres to the complete AnalysisResponse schema."""
        response = client.post("/api/routes/demo", {"fixture": "dallas_houston"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        required_root_keys = [
            "origin", "destination", "departure_utc", "load_weight_lbs",
            "risk_legend", "routes", "heatmap", "best_departure_window", "warnings"
        ]
        for key in required_root_keys:
            assert key in data, f"Missing root key: {key}"

        # Validate route structure
        r0 = data["routes"][0]
        assert "summary" in r0
        assert "recommendation" in r0
        assert "checkpoints" in r0
        assert "distance_miles" in r0
        assert "duration_seconds" in r0

        # Validate summary structure
        s = r0["summary"]
        for sk in ["no_travel_miles", "severe_miles", "high_miles", "moderate_miles", "low_miles"]:
            assert sk in s

    def test_it_05_demo_endpoint_fixture_playback(self, client):
        """IT_05: POST /api/routes/demo returns instant fixture without network requests."""
        response = client.post("/api/routes/demo", {"fixture": "dallas_houston"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["origin"]["name"] == "Dallas, TX"
        assert data["destination"]["name"] == "Houston, TX"
        assert len(data["routes"]) >= 1

    def test_it_06_cache_key_consistency(self):
        """IT_06: Cache key generation normalizes coordinates with 4 decimal places."""
        k1 = make_route_cache_key(32.776712, -96.797034, 29.760411, -95.369822)
        k2 = make_route_cache_key(32.776719, -96.797039, 29.760419, -95.369829)
        assert k1 == k2 == "route:32.7767:-96.7970->29.7604:-95.3698"

    def test_it_07_rate_throttle_enforcement(self):
        """IT_07: RouteAnonThrottle rate is configured to 60/hour."""
        from api.views import RouteAnonThrottle
        throttle = RouteAnonThrottle()
        assert throttle.rate == "60/hour"

    def test_it_08_cache_stampede_mutex(self):
        """
        IT_08: Cache stampede lock guarantees only 1 backend execution
        when multiple concurrent threads request the same un-cached key.
        """
        from django.core.cache import cache
        key = "stampede_test_key"
        cache.delete(key)

        compute_counter = [0]

        def expensive_computation():
            compute_counter[0] += 1
            time.sleep(0.05)  # Simulate expensive work
            return "computed_result"

        def worker():
            return get_or_compute(key, expensive_computation, timeout=60)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker) for _ in range(8)]
            results = [f.result() for f in futures]

        assert all(res == "computed_result" for res in results)
        # Exactly 1 computation executed despite 8 concurrent threads!
        assert compute_counter[0] == 1
