"""Unit tests for the media response maths, the simulator's truth and the budget optimiser."""
from __future__ import annotations

import numpy as np
import pytest

from mmm.core import adstock, hill, steady_state_response
from mmm.optimise import optimise, weekly_revenue
from mmm.simulate import CHANNELS, LIFT_TESTS, lift_tests, simulate


def test_adstock_carries_over_geometrically():
    assert np.allclose(adstock(np.array([100.0, 0, 0, 0]), 0.5), [100, 50, 25, 12.5])


def test_hill_is_half_saturated_at_k_and_bounded():
    x = np.array([0.0, 10.0, 1e9])
    y = hill(x, 10.0, 2.0)
    assert y[0] == 0 and y[1] == pytest.approx(0.5) and y[2] == pytest.approx(1.0)


def test_steady_state_matches_a_long_constant_flight():
    long = adstock(np.full(400, 1000.0), 0.6)[-1]
    assert long == pytest.approx(1000 / (1 - 0.6))
    assert steady_state_response(1000.0, 0.6, 2000.0, 1.5, 10.0) == pytest.approx(10 * hill(np.array([long]), 2000.0, 1.5)[0])


def test_simulated_truth_hits_each_channels_target_roi():
    df, truth = simulate()
    assert len(df) == 156
    for c, (_, _, _, _, roi) in CHANNELS.items():
        assert truth["channels"][c]["roi"] == pytest.approx(roi, rel=1e-6)


def test_lift_tests_are_noisy_measurements_of_the_truth():
    _, truth = simulate()
    tests = lift_tests(truth)
    assert set(tests) == set(LIFT_TESTS)
    for c, (measured, se) in tests.items():
        assert se == LIFT_TESTS[c] and abs(measured - truth["channels"][c]["roi"]) < 4 * se


def test_optimiser_keeps_the_budget_and_the_guardrails():
    curves = {"a": (0.2, 5000.0, 1.2, 30000.0), "b": (0.5, 20000.0, 1.5, 10000.0)}
    current = {"a": 10000.0, "b": 10000.0}
    plan = optimise(curves, current)
    assert sum(plan.values()) == pytest.approx(20000.0, rel=1e-6)
    assert all(0.5 * current[c] - 1e-6 <= v <= 1.5 * current[c] + 1e-6 for c, v in plan.items())
    assert weekly_revenue(curves, plan) >= weekly_revenue(curves, current) - 1e-6
