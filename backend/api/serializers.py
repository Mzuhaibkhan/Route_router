"""
DRF Serializers and comprehensive input validation for Route Radar API endpoints.
Validates origin, destination, truck weight, departure time, DST gaps, and coordinate boundaries.
"""
import zoneinfo
from datetime import datetime, timezone

from rest_framework import serializers
from services.data_types import Coord, Notice
from services.geocoding import (
    DEFAULT_GEOCODING_SERVICE,
    GeocodingError,
    validate_us_coordinates,
)
from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

US_BOUNDS = {
    "min_lat": 18.0,
    "max_lat": 72.0,
    "min_lng": -180.0,
    "max_lng": -65.0,
}


def parse_and_validate_location(loc_input: str | dict, field_name: str) -> tuple[Coord, str]:
    """Parse string address or coordinate dict into Coord and display name, validating US bounds."""
    if isinstance(loc_input, dict):
        lat = loc_input.get("lat")
        lng = loc_input.get("lng")
        if lat is None or lng is None:
            raise serializers.ValidationError({field_name: "Latitude and longitude required."})
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                {field_name: "Latitude and longitude must be numbers."}
            )

        if not (US_BOUNDS["min_lat"] <= lat <= US_BOUNDS["max_lat"] and
                US_BOUNDS["min_lng"] <= lng <= US_BOUNDS["max_lng"]):
            raise serializers.ValidationError(
                {field_name: "Location must be within the United States."}
            )

        name = loc_input.get("name") or f"{lat:.4f}, {lng:.4f}"
        return Coord(lat=lat, lng=lng), name

    elif isinstance(loc_input, str):
        cleaned = loc_input.strip()
        if not cleaned:
            raise serializers.ValidationError(
                {field_name: f"{field_name.capitalize()} is required."}
            )

        # Geocode using ORS service
        try:
            results = DEFAULT_GEOCODING_SERVICE.forward_geocode(cleaned)
            if not results:
                raise serializers.ValidationError(
                    {field_name: f"Could not find US location for '{cleaned}'."}
                )
            first = results[0]
            lat, lng = first["lat"], first["lng"]
            if not validate_us_coordinates(lat, lng):
                raise serializers.ValidationError(
                    {field_name: f"Location '{cleaned}' resolved outside the United States."}
                )
            return Coord(lat=lat, lng=lng), first.get("name", cleaned)
        except GeocodingError as e:
            raise serializers.ValidationError({field_name: str(e)})

    raise serializers.ValidationError(
        {field_name: "Location must be an address string or a {lat, lng} dictionary."}
    )


class RouteAnalyzeSerializer(serializers.Serializer):
    """Serializer for POST /api/routes/analyze and POST /api/routes/plan."""
    origin = serializers.JSONField(required=True)
    destination = serializers.JSONField(required=True)
    departure_time = serializers.CharField(required=False, default=None)
    departure_utc = serializers.IntegerField(required=False, default=None)
    load_weight_lbs = serializers.IntegerField(required=False, default=40000)
    checkpoint_interval_miles = serializers.IntegerField(required=False, default=25)

    def validate_load_weight_lbs(self, value):
        if not (1000 <= value <= 80000):
            raise serializers.ValidationError(
                f"Weight {value} lbs is out of bounds. Must be between 1,000 and 80,000 lbs."
            )
        return value

    def validate_checkpoint_interval_miles(self, value):
        if value not in (10, 25, 50):
            # Fall back to 25 mi
            return 25
        return value

    def validate(self, attrs):
        origin_raw = attrs.get("origin")
        dest_raw = attrs.get("destination")

        if not origin_raw:
            raise serializers.ValidationError({"origin": "Origin is required."})
        if not dest_raw:
            raise serializers.ValidationError({"destination": "Destination is required."})

        origin_coord, origin_name = parse_and_validate_location(origin_raw, "origin")
        dest_coord, dest_name = parse_and_validate_location(dest_raw, "destination")

        # Non-identical check (address strings or coordinate proximity < 0.1 miles)
        from services.heatmap import haversine_distance_miles
        dist_between = haversine_distance_miles(origin_coord, dest_coord)
        if dist_between < 0.1:
            raise serializers.ValidationError(
                "Origin and destination cannot be identical locations."
            )

        # Determine origin timezone
        tz_name = tf.timezone_at(lat=origin_coord.lat, lng=origin_coord.lng) or "America/Chicago"
        try:
            origin_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            origin_tz = zoneinfo.ZoneInfo("UTC")

        warnings: list[Notice] = []
        warnings.append(
            Notice(
                level="info",
                code="tz_interpretation",
                message=f"Departure interpreted using origin timezone ({tz_name}).",
            )
        )

        # Parse departure time
        now_utc = datetime.now(timezone.utc)
        dep_input = attrs.get("departure_time")
        dep_utc_input = attrs.get("departure_utc")
        effective_dep_utc: int

        if dep_utc_input is not None:
            effective_dep_utc = int(dep_utc_input)
        elif dep_input:
            dep_str = str(dep_input).strip()
            # Try parsing timestamp integer
            if dep_str.isdigit():
                effective_dep_utc = int(dep_str)
            else:
                # Try parsing ISO/local datetime string in origin_tz
                try:
                    # Replace ISO separator if needed
                    dep_str_clean = dep_str.replace("T", " ")
                    dt_naive = datetime.fromisoformat(dep_str_clean)
                except ValueError:
                    raise serializers.ValidationError(
                        {"departure_time": f"Invalid datetime format '{dep_input}'."}
                    )

                # Check DST gap: interpret in origin_tz
                dt_local = dt_naive.replace(tzinfo=origin_tz)
                dt_utc = dt_local.astimezone(timezone.utc)

                # Round-trip check to detect nonexistent spring-forward DST gap
                round_trip = dt_utc.astimezone(origin_tz)
                if round_trip.hour != dt_naive.hour or round_trip.minute != dt_naive.minute:
                    # Snap forward by 1 hour
                    dt_utc = (dt_utc.timestamp() + 3600)
                    dt_utc = datetime.fromtimestamp(dt_utc, timezone.utc)
                    warnings.append(
                        Notice(
                            level="info",
                            code="dst_gap_snapped",
                            message="Departure was in DST gap; snapped forward 1 hour.",
                        )
                    )
                effective_dep_utc = int(dt_utc.timestamp())
        else:
            # Default to now + 1 hour floored to hour
            effective_dep_utc = int(now_utc.timestamp()) + 3600

        # Validate departure range:
        # 1. Past check (allow 15-minute grace period for in-flight requests)
        if effective_dep_utc < int(now_utc.timestamp()) - 900:
            raise serializers.ValidationError(
                {"departure_time": "Departure time cannot be in the past."}
            )

        # 2. Maximum limit: max 7 days into future
        max_future_utc = int(now_utc.timestamp()) + (7 * 86400)
        if effective_dep_utc > max_future_utc:
            raise serializers.ValidationError(
                {"departure_time": "Departure time cannot exceed 7 days into the future."}
            )

        # 3. Forecast horizon warning if > 48h
        if effective_dep_utc > int(now_utc.timestamp()) + (48 * 3600):
            warnings.append(
                Notice(
                    level="warning",
                    code="forecast_horizon",
                    message="Departure is > 48 hours away; weather forecast accuracy may decrease.",
                )
            )

        attrs["parsed_origin"] = {"name": origin_name, "coord": origin_coord}
        attrs["parsed_destination"] = {"name": dest_name, "coord": dest_coord}
        attrs["origin_timezone"] = tz_name
        attrs["departure_utc"] = effective_dep_utc
        attrs["warnings"] = warnings

        return attrs
