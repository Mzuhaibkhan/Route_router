"""
REST API Views and route analysis pipeline controller for Spotter AI.
Coordinates geocoding, multi-tier routing, checkpoint sampling, weather fetching,
ranking, heatmap precomputation, and departure window optimization.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import polyline
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from backend.api.serializers import RouteAnalyzeSerializer
from backend.services.cache_utils import (
    get_or_compute,
    make_route_cache_key,
    make_weather_cache_key,
)
from backend.services.checkpoints import (
    sample_checkpoints,
)
from backend.services.data_types import (
    RISK_LEGEND,
    RISK_LEVELS,
    AnalysisResponse,
    Coord,
    Notice,
    Route,
    RouteSummary,
    VehicleParams,
)
from backend.services.departure import find_best_departure
from backend.services.geocoding import DEFAULT_GEOCODING_SERVICE
from backend.services.heatmap import compute_heatmap_data, generate_corridor_grid
from backend.services.recommendation import rank_routes
from backend.services.routing import DEFAULT_ROUTING_PROVIDER
from backend.services.weather import (
    WeatherServiceError,
    apply_weather_and_risk_to_checkpoints,
    fetch_weather_batch,
)


class RouteAnonThrottle(AnonRateThrottle):
    """Anonymous rate throttle for API queries."""
    rate = "60/hour"


def format_duration(seconds: int) -> str:
    """Format duration in seconds into 'Xh Ym' string."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def serialize_analysis_response(res: AnalysisResponse) -> dict:
    """Serializes AnalysisResponse dataclass into JSON-serializable dictionary."""
    data = {
        "origin": res.origin,
        "destination": res.destination,
        "departure_utc": res.departure_utc,
        "load_weight_lbs": res.load_weight_lbs,
        "risk_legend": res.risk_legend,
        "best_departure_window": res.best_departure_window,
        "warnings": [
            {"level": w.level, "code": w.code, "message": w.message}
            for w in res.warnings
        ],
        "routes": [],
        "heatmap": [],
    }

    for r in res.routes:
        r_dict = {
            "index": r.index,
            "name": r.name,
            "encoded_geometry": r.encoded_geometry,
            "distance_miles": round(r.distance_miles, 1),
            "duration_seconds": r.duration_seconds,
            "duration_display": r.duration_display,
            "via_roads": r.via_roads,
            "summary": {
                "no_travel_miles": round(r.summary.no_travel_miles, 1),
                "severe_miles": round(r.summary.severe_miles, 1),
                "high_miles": round(r.summary.high_miles, 1),
                "moderate_miles": round(r.summary.moderate_miles, 1),
                "low_miles": round(r.summary.low_miles, 1),
                "mile_weighted_avg_risk": round(r.summary.mile_weighted_avg_risk, 2),
                "data_coverage_pct": round(r.summary.data_coverage_pct, 1),
                "max_risk_label": r.summary.max_risk_label,
            },
            "recommendation": {
                "is_recommended": r.recommendation.is_recommended,
                "rank": r.recommendation.rank,
                "tags": r.recommendation.tags,
                "explanation": r.recommendation.explanation,
            },
            "checkpoints": [],
        }

        for cp in r.checkpoints:
            cp_dict = {
                "index": cp.index,
                "coord": {"lat": cp.coord.lat, "lng": cp.coord.lng},
                "cumulative_miles": round(cp.cumulative_miles, 1),
                "segment_miles": round(cp.segment_miles, 1),
                "eta_utc": (
                    int(cp.eta_utc.timestamp())
                    if hasattr(cp.eta_utc, "timestamp")
                    else int(cp.eta_utc)
                ),
            }
            if cp.weather:
                cp_dict["weather"] = {
                    "timestamp_utc": cp.weather.timestamp_utc,
                    "wind_mph": round(cp.weather.wind_mph, 1),
                    "wind_gusts_mph": round(cp.weather.wind_gusts_mph, 1),
                    "rain_in_hr": round(cp.weather.rain_in_hr, 2),
                    "snow_in_hr": round(cp.weather.snow_in_hr, 2),
                    "temperature_f": round(cp.weather.temperature_f, 1),
                }
            else:
                cp_dict["weather"] = None

            if cp.risk:
                cp_dict["risk"] = {
                    "base_level": cp.risk.base_level,
                    "adjusted_level": cp.risk.adjusted_level,
                    "label": cp.risk.label,
                    "segment_miles": round(cp.risk.segment_miles, 1),
                    "contributing_factors": cp.risk.contributing_factors,
                    "data_available": cp.risk.data_available,
                }
            else:
                cp_dict["risk"] = None

            r_dict["checkpoints"].append(cp_dict)

        data["routes"].append(r_dict)

    for cell in res.heatmap:
        # Format forecast timestamp keys as strings for clean JSON
        cell_dict = {
            "coord": {"lat": cell.coord.lat, "lng": cell.coord.lng},
            "forecasts": {str(k): v for k, v in cell.forecasts.items()},
        }
        data["heatmap"].append(cell_dict)

    return data


@api_view(["GET"])
def geocode_autocomplete(request):
    """Proxied autocomplete with US boundary filter."""
    text = request.query_params.get("text", "").strip()
    if not text:
        return Response([])

    results = DEFAULT_GEOCODING_SERVICE.autocomplete(text)
    return Response(results)


@api_view(["POST"])
def demo_fixture(request):
    """Zero-quota fixture playback for instant interactive testing."""
    fixture_name = request.data.get("fixture", "dallas_houston")
    fixtures_dir = Path(__file__).resolve().parent / "tests" / "fixtures"
    fixture_file = fixtures_dir / f"{fixture_name}.json"

    if not fixture_file.exists():
        fixture_file = fixtures_dir / "dallas_houston.json"

    try:
        with open(fixture_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Response(data)
    except Exception as e:
        return Response(
            {"error": f"Failed to load demo fixture: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def analyze_routes(request):
    """
    Main route analysis pipeline.
    POST /api/routes/analyze
    """
    serializer = RouteAnalyzeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated = serializer.validated_data
    origin_info = validated["parsed_origin"]
    dest_info = validated["parsed_destination"]
    origin_coord: Coord = origin_info["coord"]
    dest_coord: Coord = dest_info["coord"]
    dep_utc: int = validated["departure_utc"]
    weight_lbs: int = validated["load_weight_lbs"]
    interval_mi: int = validated["checkpoint_interval_miles"]
    warnings: list[Notice] = list(validated.get("warnings", []))

    # 1. Routing
    route_key = make_route_cache_key(
        origin_coord.lat, origin_coord.lng, dest_coord.lat, dest_coord.lng
    )

    def compute_routes():
        return DEFAULT_ROUTING_PROVIDER.get_routes(
            origin=origin_coord,
            destination=dest_coord,
            vehicle_params=VehicleParams(load_weight_lbs=weight_lbs),
        )

    try:
        route_results = get_or_compute(route_key, compute_routes, timeout=1800)
    except Exception as e:
        return Response(
            {"error": f"Routing service failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not route_results:
        return Response(
            {"error": "No viable route found between origin and destination."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Decode geometries and sample checkpoints for all routes
    decoded_geometries: list[list[Coord]] = []
    routes: list[Route] = []

    for r_res in route_results:
        decoded_tuples = polyline.decode(r_res.encoded_geometry)
        decoded_coords = [Coord(lat=lat, lng=lng) for lat, lng in decoded_tuples]
        decoded_geometries.append(decoded_coords)

        cps = sample_checkpoints(
            decoded_coords=decoded_coords,
            step_distances_m=r_res.step_distances_m,
            step_durations_s=r_res.step_durations_s,
            departure_utc=dep_utc,
            interval_miles=interval_mi,
        )

        routes.append(
            Route(
                index=r_res.index,
                name=r_res.name,
                encoded_geometry=r_res.encoded_geometry,
                distance_miles=r_res.distance_miles,
                duration_seconds=r_res.duration_seconds,
                duration_display=format_duration(r_res.duration_seconds),
                via_roads=r_res.via_roads,
                step_distances_m=r_res.step_distances_m,
                step_durations_s=r_res.step_durations_s,
                checkpoints=cps,
                effective_interval_miles=interval_mi,
            )
        )

    # 2. Heatmap corridor grid
    heatmap_coords = generate_corridor_grid(
        route_geometries=decoded_geometries,
        corridor_width_miles=20.0,
        grid_spacing_degrees=0.25,
        max_cells=150,
    )

    # 3. Weather data fetching
    all_weather_coords: list[Coord] = []
    for r in routes:
        all_weather_coords.extend(cp.coord for cp in r.checkpoints)
    all_weather_coords.extend(heatmap_coords)

    # Start hour floored to 3600
    start_hour_utc = (dep_utc // 3600) * 3600
    weather_key = make_weather_cache_key(origin_coord.lat, origin_coord.lng, start_hour_utc)

    start_dt = datetime.fromtimestamp(start_hour_utc, timezone.utc).strftime("%Y-%m-%d")
    end_dt = datetime.fromtimestamp(start_hour_utc + (49 * 3600), timezone.utc).strftime("%Y-%m-%d")

    def compute_weather():
        return fetch_weather_batch(
            coords=all_weather_coords,
            start_date=start_dt,
            end_date=end_dt,
        )

    try:
        weather_by_coord = get_or_compute(weather_key, compute_weather, timeout=3600)
    except WeatherServiceError as e:
        warnings.append(
            Notice(
                level="error",
                code="weather_service_degraded",
                message=f"Weather service partially unavailable: {str(e)}",
            )
        )
        weather_by_coord = {}

    # 4. Checkpoint weather matching and risk scoring
    for r in routes:
        total_mi = r.distance_miles or 1.0
        apply_weather_and_risk_to_checkpoints(r.checkpoints, weather_by_coord, weight_lbs)

        no_trav_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.adjusted_level == 4
        )
        sev_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.adjusted_level == 3
        )
        hi_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.adjusted_level == 2
        )
        mod_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.adjusted_level == 1
        )
        low_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.adjusted_level == 0
        )
        weighted_risk_sum = sum(
            cp.segment_miles * (cp.risk.adjusted_level if cp.risk else 0)
            for cp in r.checkpoints
        )
        covered_mi = sum(
            cp.segment_miles for cp in r.checkpoints if cp.risk and cp.risk.data_available
        )

        max_risk_lvl = max((cp.risk.adjusted_level for cp in r.checkpoints), default=0)
        cov_pct = (covered_mi / total_mi) * 100.0 if total_mi > 0 else 100.0

        r.summary = RouteSummary(
            no_travel_miles=no_trav_mi,
            severe_miles=sev_mi,
            high_miles=hi_mi,
            moderate_miles=mod_mi,
            low_miles=low_mi,
            mile_weighted_avg_risk=weighted_risk_sum / total_mi if total_mi > 0 else 0.0,
            data_coverage_pct=cov_pct,
            max_risk_label=RISK_LEVELS.get(max_risk_lvl, "Low"),
        )

        if cov_pct < 80.0:
            warnings.append(
                Notice(
                    level="warning",
                    code="low_coverage",
                    message=(
                        f"{r.name} has only {cov_pct:.0f}% weather coverage; "
                        "uncovered segments assumed calm."
                    ),
                )
            )

    # 5. Route Recommendation
    ranked_routes = rank_routes(routes)

    # Check for all-No-Travel alert
    if all(r.summary.no_travel_miles > 0 for r in ranked_routes):
        warnings.append(
            Notice(
                level="warning",
                code="all_no_travel",
                message="All routes encounter No Travel weather conditions. Travel not advised.",
            )
        )

    # 6. Heatmap precomputation
    heatmap_cells = compute_heatmap_data(
        grid_coords=heatmap_coords,
        weather_data=weather_by_coord,
        load_weight_lbs=weight_lbs,
        start_hour_utc=start_hour_utc,
        num_hours=49,
    )

    # 7. Best departure window
    best_dep = find_best_departure(
        routes=ranked_routes,
        weather_by_coord=weather_by_coord,
        load_weight_lbs=weight_lbs,
        original_departure_utc=dep_utc,
        window_hours=12,
    )

    # Build AnalysisResponse
    response_obj = AnalysisResponse(
        origin={"name": origin_info["name"], "lat": origin_coord.lat, "lng": origin_coord.lng},
        destination={"name": dest_info["name"], "lat": dest_coord.lat, "lng": dest_coord.lng},
        departure_utc=dep_utc,
        load_weight_lbs=weight_lbs,
        routes=ranked_routes,
        heatmap=heatmap_cells,
        risk_legend=RISK_LEGEND,
        best_departure_window=best_dep,
        warnings=warnings,
    )

    return Response(serialize_analysis_response(response_obj))


@api_view(["POST"])
def plan_route(request):
    """
    Two-stage routing endpoint: creates routing plan and caches with plan_id.
    POST /api/routes/plan
    """
    serializer = RouteAnalyzeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated = serializer.validated_data
    origin_info = validated["parsed_origin"]
    dest_info = validated["parsed_destination"]
    origin_coord: Coord = origin_info["coord"]
    dest_coord: Coord = dest_info["coord"]
    weight_lbs: int = validated["load_weight_lbs"]

    route_key = make_route_cache_key(
        origin_coord.lat, origin_coord.lng, dest_coord.lat, dest_coord.lng
    )

    def compute_routes():
        return DEFAULT_ROUTING_PROVIDER.get_routes(
            origin=origin_coord,
            destination=dest_coord,
            vehicle_params=VehicleParams(load_weight_lbs=weight_lbs),
        )

    try:
        route_results = get_or_compute(route_key, compute_routes, timeout=1800)
    except Exception as e:
        return Response(
            {"error": f"Routing failed: {str(e)}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    plan_id = str(uuid.uuid4())
    cache.set(f"plan:{plan_id}", validated, timeout=1800)

    routes_out = [
        {
            "index": r.index,
            "name": r.name,
            "encoded_geometry": r.encoded_geometry,
            "distance_miles": round(r.distance_miles, 1),
            "duration_seconds": r.duration_seconds,
            "duration_display": format_duration(r.duration_seconds),
            "via_roads": r.via_roads,
        }
        for r in route_results
    ]

    return Response({
        "plan_id": plan_id,
        "origin": {"name": origin_info["name"], "lat": origin_coord.lat, "lng": origin_coord.lng},
        "destination": {"name": dest_info["name"], "lat": dest_coord.lat, "lng": dest_coord.lng},
        "origin_timezone": validated["origin_timezone"],
        "routes": routes_out,
    })


@api_view(["POST"])
def assess_risk(request):
    """
    Two-stage risk assessment endpoint using cached plan_id.
    POST /api/routes/risk
    """
    plan_id = request.data.get("plan_id")
    if not plan_id:
        return Response({"error": "plan_id required."}, status=status.HTTP_400_BAD_REQUEST)

    cached_plan = cache.get(f"plan:{plan_id}")
    if not cached_plan:
        return Response(
            {"error": "Plan expired or not found. Please re-plan route."},
            status=status.HTTP_410_GONE,
        )

    # Merge request data with cached plan and run analyze_routes logic
    merged_data = dict(request.data)
    merged_data["origin"] = cached_plan["parsed_origin"]["name"]
    merged_data["destination"] = cached_plan["parsed_destination"]["name"]

    request._full_data = merged_data
    return analyze_routes(request)
