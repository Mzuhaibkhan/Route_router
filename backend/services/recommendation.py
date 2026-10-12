"""
Recommendation engine for Spotter AI routes.
Implements bucketed multi-criteria ranking, tag assignment, and natural-language explanations.
"""
from backend.services.data_types import Route, RouteRecommendation

BUCKET_SIZE = 5  # Round miles to nearest 5 before comparing


def bucket_miles(miles: float) -> int:
    """Round miles to nearest BUCKET_SIZE (e.g. 5 miles)."""
    return int(round(miles / BUCKET_SIZE) * BUCKET_SIZE)


def recommendation_sort_key(route: Route) -> tuple:
    """
    Sort key for route ranking (ascending = better):
      1. Bucketed no_travel_miles
      2. Bucketed severe_miles
      3. Bucketed high_miles
      4. Mile-weighted average risk (to 1 decimal)
      5. Duration (seconds)
    """
    s = route.summary
    return (
        bucket_miles(s.no_travel_miles),
        bucket_miles(s.severe_miles),
        bucket_miles(s.high_miles),
        round(s.mile_weighted_avg_risk, 1),
        route.duration_seconds,
    )


def generate_explanation(
    recommended: Route,
    current: Route,
    fastest: Route,
    safest: Route,
    total_routes: int,
) -> str:
    """Generate human-readable explanation of why this route is ranked where it is."""
    if total_routes <= 1:
        return "Sole route option analyzed with optimal weather profile."

    is_rec = current is recommended
    all_no_travel = recommended.summary.no_travel_miles > 0

    if is_rec:
        if all_no_travel:
            return (
                f"Recommended route with fewest No Travel miles "
                f"({current.summary.no_travel_miles:.1f} mi). Extreme caution advised."
            )
        if current is fastest and current is safest:
            return "Fastest and safest route with optimal weather conditions."
        if current is fastest:
            return "Fastest route with minimal weather risk across the corridor."
        if current is safest:
            if fastest is not current:
                diff_min = max(1, round((current.duration_seconds - fastest.duration_seconds) / 60))
                diff_sev = fastest.summary.severe_miles - current.summary.severe_miles
                if diff_sev >= 1.0:
                    return (
                        f"{diff_sev:.0f} fewer Severe miles than fastest route, "
                        f"only {diff_min} min longer."
                    )
                diff_high = fastest.summary.high_miles - current.summary.high_miles
                if diff_high >= 1.0:
                    return (
                        f"{diff_high:.0f} fewer High miles than fastest route, "
                        f"only {diff_min} min longer."
                    )
                return f"Safest route with lowest overall risk, only {diff_min} min longer."
            return "Safest route with minimal weather disruption."
        return "Best balance of travel time and weather risk along the route corridor."

    # Non-recommended routes
    if current is fastest:
        sev_diff = current.summary.severe_miles - recommended.summary.severe_miles
        if sev_diff >= 1.0:
            return f"Fastest route, but has {sev_diff:.0f} more Severe miles than recommended."
        high_diff = current.summary.high_miles - recommended.summary.high_miles
        if high_diff >= 1.0:
            return f"Fastest route, but has {high_diff:.0f} more High miles than recommended."
        return "Fastest route, but higher overall weather risk than recommended."

    rank = getattr(current.recommendation, "rank", 2)
    return (
        f"Alternative route (Rank {rank}). "
        f"Higher risk profile or longer travel time than recommended."
    )


def rank_routes(routes: list[Route]) -> list[Route]:
    """
    Ranks routes using 5-mile bucketed multi-criteria sorting.
    Assigns rank, recommendation flags, tags, and human-readable explanation strings.
    """
    if not routes:
        return []

    sorted_routes = sorted(routes, key=recommendation_sort_key)
    fastest = min(routes, key=lambda r: r.duration_seconds)
    safest = min(
        routes,
        key=lambda r: (
            r.summary.no_travel_miles,
            r.summary.severe_miles,
            r.summary.high_miles,
            r.summary.mile_weighted_avg_risk,
        ),
    )

    for i, route in enumerate(sorted_routes):
        is_rec = i == 0
        tags: list[str] = []
        if is_rec:
            tags.append("★ Recommended")
        if route is fastest:
            tags.append("Fastest")
        if route is safest:
            tags.append("Safest")

        explanation = generate_explanation(
            recommended=sorted_routes[0],
            current=route,
            fastest=fastest,
            safest=safest,
            total_routes=len(sorted_routes),
        )

        route.recommendation = RouteRecommendation(
            is_recommended=is_rec,
            rank=i + 1,
            tags=tags,
            explanation=explanation,
        )

    return sorted_routes
