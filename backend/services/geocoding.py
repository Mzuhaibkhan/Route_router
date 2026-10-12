"""
Geocoding service using OpenRouteService Geocode API.
Restricted to US boundary with result caching and autocomplete support.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache
from services.data_types import Coord

logger = logging.getLogger(__name__)

ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
ORS_AUTOCOMPLETE_URL = "https://api.openrouteservice.org/geocode/autocomplete"


class GeocodingError(Exception):
    """Exception raised when geocoding fails or location is invalid."""
    pass


class GeocodingService:
    """Provides forward geocoding and autocomplete restricted to the United States."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "ORS_API_KEY", "")

    def geocode(self, query: str) -> dict:
        """
        Geocode a location query string to a US coordinate.
        Returns dict: {"name": str, "lat": float, "lng": float}
        """
        query_clean = query.strip()
        if not query_clean:
            raise GeocodingError("Location query cannot be empty.")

        cache_key = f"geocode_{query_clean.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            # Fallback for local demo/testing without API key
            return self._mock_fallback_geocode(query_clean)

        headers = {"Authorization": self.api_key}
        params = {
            "text": query_clean,
            "boundary.country": "US",
            "size": 1,
        }

        try:
            response = requests.get(
                ORS_GEOCODE_URL,
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            features = data.get("features", [])
            if not features:
                raise GeocodingError(f"Location not found in the United States: '{query_clean}'")

            feature = features[0]
            props = feature.get("properties", {})
            country = props.get("country", "")
            if country and country.upper() not in ("UNITED STATES", "USA", "US"):
                raise GeocodingError(f"Location '{query_clean}' is outside the United States.")

            coords = feature.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                raise GeocodingError(f"Invalid geometry returned for '{query_clean}'")

            result = {
                "name": props.get("label", query_clean),
                "lat": float(coords[1]),
                "lng": float(coords[0]),
            }
            cache.set(cache_key, result, timeout=86400)  # 24 hours
            return result

        except requests.RequestException as exc:
            logger.error("ORS Geocoding request failed: %s", exc)
            raise GeocodingError(f"Geocoding service unavailable: {exc}") from exc

    def forward_geocode(self, query: str) -> list[dict]:
        """Forward geocode query returning a list of matched US places."""
        res = self.geocode(query)
        return [res] if res else []

    def autocomplete(self, text: str, limit: int = 5) -> list[dict]:
        """
        Autocomplete search query for UI inputs, restricted to US boundary.
        """
        text_clean = text.strip()
        if len(text_clean) < 2:
            return []

        cache_key = f"autocomplete_{text_clean.lower()}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        if not self.api_key:
            cities = {
                "dallas": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
                "houston": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
                "los angeles": {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437},
                "phoenix": {"name": "Phoenix, AZ", "lat": 33.4484, "lng": -112.0740},
            }
            matches = [
                {"label": c["name"], "lat": c["lat"], "lng": c["lng"]}
                for k, c in cities.items()
                if text_clean.lower() in k or text_clean.lower() in c["name"].lower()
            ][:limit]
            return matches

        headers = {"Authorization": self.api_key}
        params = {
            "text": text_clean,
            "boundary.country": "US",
            "size": limit,
        }

        try:
            response = requests.get(
                ORS_AUTOCOMPLETE_URL,
                headers=headers,
                params=params,
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            features = data.get("features", [])

            results = []
            for feat in features:
                coords = feat.get("geometry", {}).get("coordinates", [0, 0])
                props = feat.get("properties", {})
                results.append({
                    "label": props.get("label", ""),
                    "lat": float(coords[1]),
                    "lng": float(coords[0]),
                })

            cache.set(cache_key, results, timeout=3600)
            return results
        except requests.RequestException as exc:
            logger.warning("ORS Autocomplete request failed: %s", exc)
            return []

    def _mock_fallback_geocode(self, query: str) -> dict:
        """Deterministic fallback coordinates for common testing cities when ORS key is unset."""
        cities = {
            "dallas": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
            "houston": {"name": "Houston, TX", "lat": 29.7604, "lng": -95.3698},
            "los angeles": {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437},
            "phoenix": {"name": "Phoenix, AZ", "lat": 33.4484, "lng": -112.0740},
            "chicago": {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298},
            "new york": {"name": "New York, NY", "lat": 40.7128, "lng": -74.0060},
        }
        for city_name, coord in cities.items():
            if city_name in query.lower():
                return coord

        if any(non_us in query.lower() for non_us in ["paris", "london", "tokyo", "berlin"]):
            raise GeocodingError(f"Location '{query}' is outside the United States.")

        # Default US center fallback if unknown
        return {"name": query, "lat": 39.8283, "lng": -98.5795}


def is_us_coordinate(coord: Coord) -> bool:
    """Check if coordinate falls within continental US, Alaska, or Hawaii bounding boxes."""
    # Continental US + Alaska + Hawaii broad envelope
    lat, lng = coord.lat, coord.lng
    conus = (24.396308 <= lat <= 49.384358) and (-125.0 <= lng <= -66.93457)
    alaska = (51.214183 <= lat <= 71.365162) and (-179.148909 <= lng <= -129.979506)
    hawaii = (18.910361 <= lat <= 28.402123) and (-178.334698 <= lng <= -154.806773)
    return conus or alaska or hawaii


DEFAULT_GEOCODING_SERVICE = GeocodingService()


def validate_us_coordinates(lat: float, lng: float) -> bool:
    """Validate whether lat, lng falls within US geographic boundaries."""
    return is_us_coordinate(Coord(lat=lat, lng=lng))

