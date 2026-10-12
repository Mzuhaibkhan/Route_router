"""
Comprehensive test suite for the Spotter AI Risk Classification Engine.
Validates all 44 Phase 1 test specifications (RE_01–RE_33, LR_01–LR_11).
"""
import pytest
from services.risk_engine import (
    apply_load_rules,
    classify_rain,
    classify_snow,
    classify_weather,
    classify_wind,
)


class TestWeatherClassification:
    """RE_01 – RE_15: Basic weather classifications and multi-condition max selection."""

    def test_low_risk_all_clear(self):
        """RE_01: wind=15, rain=0.05, snow=0 -> 0 (Low)."""
        assert classify_weather(15, 0.05, 0) == 0

    def test_wind_moderate(self):
        """RE_02: wind=30, rain=0, snow=0 -> 1 (Moderate)."""
        assert classify_weather(30, 0, 0) == 1

    def test_wind_high(self):
        """RE_03: wind=40, rain=0, snow=0 -> 2 (High)."""
        assert classify_weather(40, 0, 0) == 2

    def test_wind_severe(self):
        """RE_04: wind=50, rain=0, snow=0 -> 3 (Severe)."""
        assert classify_weather(50, 0, 0) == 3

    def test_wind_no_travel(self):
        """RE_05: wind=60, rain=0, snow=0 -> 4 (No Travel)."""
        assert classify_weather(60, 0, 0) == 4

    def test_rain_moderate(self):
        """RE_06: wind=0, rain=0.15, snow=0 -> 1 (Moderate)."""
        assert classify_weather(0, 0.15, 0) == 1

    def test_rain_high(self):
        """RE_07: wind=0, rain=0.30, snow=0 -> 2 (High)."""
        assert classify_weather(0, 0.30, 0) == 2

    def test_rain_severe(self):
        """RE_08: wind=0, rain=0.75, snow=0 -> 3 (Severe)."""
        assert classify_weather(0, 0.75, 0) == 3

    def test_rain_no_travel(self):
        """RE_09: wind=0, rain=1.50, snow=0 -> 4 (No Travel)."""
        assert classify_weather(0, 1.50, 0) == 4

    def test_snow_moderate(self):
        """RE_10: wind=0, rain=0, snow=0.7 -> 1 (Moderate)."""
        assert classify_weather(0, 0, 0.7) == 1

    def test_snow_high(self):
        """RE_11: wind=0, rain=0, snow=1.5 -> 2 (High)."""
        assert classify_weather(0, 0, 1.5) == 2

    def test_snow_severe(self):
        """RE_12: wind=0, rain=0, snow=2.5 -> 3 (Severe)."""
        assert classify_weather(0, 0, 2.5) == 3

    def test_snow_no_travel(self):
        """RE_13: wind=0, rain=0, snow=3.5 -> 4 (No Travel)."""
        assert classify_weather(0, 0, 3.5) == 4

    def test_worst_condition_wins(self):
        """RE_14: wind=30 (Mod), rain=0.30 (High), snow=0 -> 2 (High)."""
        assert classify_weather(30, 0.30, 0) == 2

    def test_all_conditions_severe(self):
        """RE_15: wind=50, rain=0.75, snow=2.5 -> 3 (Severe)."""
        assert classify_weather(50, 0.75, 2.5) == 3


class TestStrictBoundaries:
    """RE_16 – RE_26: Strict boundary transition checks across wind, rain, and snow."""

    def test_boundary_wind_25(self):
        """RE_16: wind=25 -> 1 (Moderate, inclusive lower bound)."""
        assert classify_wind(25) == 1

    def test_boundary_wind_24_99(self):
        """RE_17: wind=24.99 -> 0 (Low, strictly below 25)."""
        assert classify_wind(24.99) == 0

    def test_boundary_wind_55(self):
        """RE_18: wind=55 -> 4 (No Travel, >=55 is No Travel)."""
        assert classify_wind(55) == 4

    def test_boundary_wind_54_99(self):
        """RE_19: wind=54.99 -> 3 (Severe, just below No Travel)."""
        assert classify_wind(54.99) == 3

    def test_boundary_rain_0_10(self):
        """RE_20: rain=0.10 -> 1 (Moderate, inclusive lower bound)."""
        assert classify_rain(0.10) == 1

    def test_boundary_rain_0_25(self):
        """RE_21: rain=0.25 -> 2 (High, inclusive lower bound)."""
        assert classify_rain(0.25) == 2

    def test_boundary_rain_1_00(self):
        """RE_22: rain=1.00 -> 3 (Severe, strict >1.00 for No Travel)."""
        assert classify_rain(1.00) == 3

    def test_boundary_rain_1_01(self):
        """RE_23: rain=1.01 -> 4 (No Travel, strictly >1.00)."""
        assert classify_rain(1.01) == 4

    def test_boundary_snow_3_0(self):
        """RE_24: snow=3.0 -> 3 (Severe, strict >3.0 for No Travel)."""
        assert classify_snow(3.0) == 3

    def test_boundary_snow_3_01(self):
        """RE_25: snow=3.01 -> 4 (No Travel, strictly >3.0)."""
        assert classify_snow(3.01) == 4

    def test_boundary_snow_0_5(self):
        """RE_26: snow=0.5 -> 1 (Moderate, inclusive lower bound)."""
        assert classify_snow(0.5) == 1


class TestMonotonicity:
    """RE_27 – RE_30: Invariant property tests ensuring risk never decreases as severity grows."""

    def test_risk_monotonic_wind(self):
        """RE_27: For any fixed rain/snow, risk never decreases as wind increases."""
        for rain in [0.0, 0.15, 0.35, 0.8, 1.2]:
            for snow in [0.0, 0.6, 1.5, 2.5, 3.5]:
                prev_risk = -1
                for wind in range(0, 80, 2):
                    current_risk = classify_weather(float(wind), rain, snow)
                    assert current_risk >= prev_risk
                    prev_risk = current_risk

    def test_risk_monotonic_rain(self):
        """RE_28: For any fixed wind/snow, risk never decreases as rain increases."""
        for wind in [0.0, 20.0, 30.0, 40.0, 50.0, 60.0]:
            for snow in [0.0, 0.6, 1.5, 2.5, 3.5]:
                prev_risk = -1
                for r_int in range(0, 200, 5):
                    rain = r_int / 100.0
                    current_risk = classify_weather(wind, rain, snow)
                    assert current_risk >= prev_risk
                    prev_risk = current_risk

    def test_risk_monotonic_snow(self):
        """RE_29: For any fixed wind/rain, risk never decreases as snow increases."""
        for wind in [0.0, 20.0, 30.0, 40.0, 50.0, 60.0]:
            for rain in [0.0, 0.15, 0.35, 0.8, 1.2]:
                prev_risk = -1
                for s_int in range(0, 50, 2):
                    snow = s_int / 10.0
                    current_risk = classify_weather(wind, rain, snow)
                    assert current_risk >= prev_risk
                    prev_risk = current_risk

    def test_risk_monotonic_load(self):
        """RE_30: For any fixed weather, adjusted risk never decreases as load increases."""
        for wind in [20.0, 38.0, 48.0, 58.0]:
            base_risk = classify_weather(wind, 0.0, 0.0)
            prev_risk = -1
            for load in range(10_000, 80_000, 5_000):
                adj_risk, _ = apply_load_rules(base_risk, wind, load)
                assert adj_risk >= prev_risk
                prev_risk = adj_risk


class TestFloatPrecision:
    """RE_31 – RE_33: Floating-point precision guard tests at critical boundaries."""

    def test_float_precision_rain_boundary(self):
        """RE_31: rain=1.0000000000000002 -> Severe (3) (not No Travel)."""
        assert classify_rain(1.0000000000000002) == 3

    def test_float_precision_snow_boundary(self):
        """RE_32: snow=3.0000000000000004 -> Severe (3) (not No Travel)."""
        assert classify_snow(3.0000000000000004) == 3

    def test_float_precision_wind_boundary(self):
        """
        RE_33: wind=54.999999999999996 -> No Travel (4).
        Float rounding to 4 decimals restores 55.0 from floating point calculation drift.
        """
        assert classify_wind(54.999999999999996) == 4


class TestLoadRules:
    """LR_01 – LR_11: Truck load weight override rules and boundary conditions."""

    def test_55mph_any_weight(self):
        """LR_01: wind=55, load=10000 -> 4 (No Travel). >=55 always No Travel."""
        base = classify_weather(55, 0, 0)
        adj, _ = apply_load_rules(base, 55, 10000)
        assert adj == 4

    def test_55mph_heavy(self):
        """LR_02: wind=55, load=50000 -> 4 (No Travel)."""
        base = classify_weather(55, 0, 0)
        adj, _ = apply_load_rules(base, 55, 50000)
        assert adj == 4

    def test_50mph_over_30k(self):
        """LR_03: wind=50, load=35000 -> 4 (No Travel). 45-54 + >30,000 -> No Travel."""
        base = classify_weather(50, 0, 0)
        adj, factors = apply_load_rules(base, 50, 35000)
        assert adj == 4
        assert len(factors) == 1
        assert "No Travel" in factors[0]

    def test_50mph_under_30k(self):
        """LR_04: wind=50, load=25000 -> 3 (Severe). No load override."""
        base = classify_weather(50, 0, 0)
        adj, factors = apply_load_rules(base, 50, 25000)
        assert adj == 3
        assert len(factors) == 0

    def test_50mph_exactly_30k(self):
        """LR_05: wind=50, load=30000 -> 3 (Severe). >30k means 30,001+; 30k NOT overridden."""
        base = classify_weather(50, 0, 0)
        adj, factors = apply_load_rules(base, 50, 30000)
        assert adj == 3
        assert len(factors) == 0

    def test_50mph_30001_lbs(self):
        """LR_06: wind=50, load=30001 -> 4 (No Travel). Boundary 30,001 triggers rule."""
        base = classify_weather(50, 0, 0)
        adj, factors = apply_load_rules(base, 50, 30001)
        assert adj == 4
        assert len(factors) == 1

    def test_40mph_over_40k(self):
        """LR_07: wind=40, load=45000 -> 3 (Severe). 35-44 + >40,000 -> Severe."""
        base = classify_weather(40, 0, 0)
        adj, factors = apply_load_rules(base, 40, 45000)
        assert adj == 3
        assert len(factors) == 1
        assert "Severe" in factors[0]

    def test_40mph_under_40k(self):
        """LR_08: wind=40, load=35000 -> 2 (High). No load override."""
        base = classify_weather(40, 0, 0)
        adj, factors = apply_load_rules(base, 40, 35000)
        assert adj == 2
        assert len(factors) == 0

    def test_40mph_exactly_40k(self):
        """LR_09: wind=40, load=40000 -> 2 (High). >40k means 40,001+; 40k NOT overridden."""
        base = classify_weather(40, 0, 0)
        adj, factors = apply_load_rules(base, 40, 40000)
        assert adj == 2
        assert len(factors) == 0

    def test_40mph_40001_lbs(self):
        """LR_10: wind=40, load=40001 -> 3 (Severe). Boundary 40,001 triggers rule."""
        base = classify_weather(40, 0, 0)
        adj, factors = apply_load_rules(base, 40, 40001)
        assert adj == 3
        assert len(factors) == 1

    def test_calm_wind_heavy_load(self):
        """LR_11: wind=20, load=60000 -> 0 (Low). Calm wind not overridden."""
        base = classify_weather(20, 0, 0)
        adj, factors = apply_load_rules(base, 20, 60000)
        assert adj == 0
        assert len(factors) == 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
