"""
Test suite for Route Radar Recommendation Engine.
Tests RC_01 through RC_10: 5-mile bucketing, multi-criteria ranking, tags, and explanations.
"""
from services.data_types import Route, RouteSummary
from services.recommendation import (
    bucket_miles,
    rank_routes,
    recommendation_sort_key,
)


def _make_dummy_route(
    index: int,
    duration_s: int,
    no_travel: float = 0.0,
    severe: float = 0.0,
    high: float = 0.0,
    moderate: float = 0.0,
    low: float = 100.0,
    avg_risk: float = 0.5,
) -> Route:
    return Route(
        index=index,
        name=f"Route {index + 1}",
        encoded_geometry="_p~iF~ps|U_ulLnnqC_mqNvxq`@",
        distance_miles=no_travel + severe + high + moderate + low,
        duration_seconds=duration_s,
        duration_display=f"{duration_s // 3600}h {(duration_s % 3600) // 60}m",
        summary=RouteSummary(
            no_travel_miles=no_travel,
            severe_miles=severe,
            high_miles=high,
            moderate_miles=moderate,
            low_miles=low,
            mile_weighted_avg_risk=avg_risk,
        ),
    )


class TestRecommendationEngine:
    """RC_01 – RC_10: Multi-criteria ranking and explanation validation."""

    def test_rc_01_fewest_no_travel_miles_wins(self):
        """RC_01: Route with fewest No Travel miles wins even if longer duration."""
        # Route 1: 0 No Travel miles, 5 hours (18000s)
        # Route 2: 25 No Travel miles, 3 hours (10800s)
        r1 = _make_dummy_route(0, duration_s=18000, no_travel=0.0)
        r2 = _make_dummy_route(1, duration_s=10800, no_travel=25.0)

        ranked = rank_routes([r2, r1])
        assert ranked[0].index == 0
        assert ranked[0].recommendation.is_recommended is True
        assert ranked[0].recommendation.rank == 1

    def test_rc_02_fewest_severe_miles_wins(self):
        """RC_02: Fewest Severe miles wins when No Travel miles are equal."""
        # Route 1: 5 Severe miles, 4 hours
        # Route 2: 30 Severe miles, 3 hours
        r1 = _make_dummy_route(0, duration_s=14400, severe=5.0)
        r2 = _make_dummy_route(1, duration_s=10800, severe=30.0)

        ranked = rank_routes([r2, r1])
        assert ranked[0].index == 0
        assert ranked[0].recommendation.is_recommended is True

    def test_rc_03_high_miles_tiebreaker(self):
        """RC_03: High miles tiebreaker when No Travel and Severe miles are equal."""
        # Route 1: 10 High miles, 4 hours
        # Route 2: 40 High miles, 3 hours
        r1 = _make_dummy_route(0, duration_s=14400, high=10.0)
        r2 = _make_dummy_route(1, duration_s=10800, high=40.0)

        ranked = rank_routes([r2, r1])
        assert ranked[0].index == 0
        assert ranked[0].recommendation.is_recommended is True

    def test_rc_04_5mi_bucketing_favors_fastest(self):
        """
        RC_04: 5-mile bucketing prevents minor weather differences from penalizing
        significantly faster routes (e.g. 2.4 Severe miles rounds to 0).
        """
        assert bucket_miles(2.4) == 0
        assert bucket_miles(0.0) == 0

        # Route A: 2.4 Severe miles, 4 hours (14400s) -> bucketed severe = 0
        # Route B: 0.0 Severe miles, 7 hours (25200s) -> bucketed severe = 0
        r_a = _make_dummy_route(0, duration_s=14400, severe=2.4)
        r_b = _make_dummy_route(1, duration_s=25200, severe=0.0)

        ranked = rank_routes([r_b, r_a])
        # Route A wins because bucketed severe is equal (0) and Route A is 3h faster
        assert ranked[0].index == 0
        assert ranked[0].recommendation.is_recommended is True

    def test_rc_05_average_risk_tiebreaker(self):
        """RC_05: Average risk tiebreaker when bucketed risk miles and duration are equal."""
        r1 = _make_dummy_route(0, duration_s=14400, avg_risk=1.2)
        r2 = _make_dummy_route(1, duration_s=14400, avg_risk=1.8)

        ranked = rank_routes([r2, r1])
        assert ranked[0].index == 0

    def test_rc_06_single_route_edge_case(self):
        """RC_06: Single route correctly assigned rank 1, recommended, and all tags."""
        r = _make_dummy_route(0, duration_s=7200)
        ranked = rank_routes([r])

        assert len(ranked) == 1
        rec = ranked[0].recommendation
        assert rec.is_recommended is True
        assert rec.rank == 1
        assert "★ Recommended" in rec.tags
        assert "Fastest" in rec.tags
        assert "Safest" in rec.tags
        assert "Sole route option" in rec.explanation

    def test_rc_07_all_no_travel_edge_case(self):
        """RC_07: All-No-Travel routes still recommend the least severe with caution warning."""
        r1 = _make_dummy_route(0, duration_s=10000, no_travel=12.0)
        r2 = _make_dummy_route(1, duration_s=10000, no_travel=45.0)

        ranked = rank_routes([r2, r1])
        assert ranked[0].index == 0
        assert ranked[0].recommendation.is_recommended is True
        assert "caution" in ranked[0].recommendation.explanation.lower()

    def test_rc_08_explanation_strings_present(self):
        """RC_08: Explanation strings are generated and non-empty for all routes."""
        r1 = _make_dummy_route(0, duration_s=10000, severe=5.0)
        r2 = _make_dummy_route(1, duration_s=9000, severe=25.0)
        r3 = _make_dummy_route(2, duration_s=12000, severe=40.0)

        ranked = rank_routes([r1, r2, r3])
        for r in ranked:
            assert bool(r.recommendation.explanation)
            assert len(r.recommendation.explanation) > 10

    def test_rc_09_tag_assignments(self):
        """RC_09: Tag assignments ('★ Recommended', 'Fastest', 'Safest') are accurate."""
        # r1: safest (0 severe, 0 high), longer duration (12000s)
        # r2: fastest (8000s), but 30 high miles
        r1 = _make_dummy_route(0, duration_s=12000, high=0.0, avg_risk=0.2)
        r2 = _make_dummy_route(1, duration_s=8000, high=30.0, avg_risk=1.5)

        ranked = rank_routes([r1, r2])
        rec_route = ranked[0]
        other_route = ranked[1]

        assert "★ Recommended" in rec_route.recommendation.tags
        assert "Safest" in rec_route.recommendation.tags
        assert "Fastest" not in rec_route.recommendation.tags

        assert "★ Recommended" not in other_route.recommendation.tags
        assert "Fastest" in other_route.recommendation.tags

    def test_rc_10_rank_ordering_monotonic(self):
        """RC_10: Rank numbers strictly increase (1, 2, 3...) matching sort key order."""
        r1 = _make_dummy_route(0, duration_s=10000, severe=0.0)
        r2 = _make_dummy_route(1, duration_s=11000, severe=15.0)
        r3 = _make_dummy_route(2, duration_s=12000, severe=40.0)

        ranked = rank_routes([r3, r1, r2])
        ranks = [r.recommendation.rank for r in ranked]
        assert ranks == [1, 2, 3]

        # Verify monotonicity of sort key
        keys = [recommendation_sort_key(r) for r in ranked]
        assert keys == sorted(keys)
