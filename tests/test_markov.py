"""Markov attribution on small journeys where the right answer is known."""
from __future__ import annotations

import pytest

from attribution.markov import attribute, conversion_probability, removal_effects, transitions


def test_conversion_probability_matches_the_journeys():
    paths = [(["A"], True), (["A"], False), (["A"], True), (["A"], False)]
    states, m = transitions(paths)
    assert conversion_probability(states, m) == pytest.approx(0.5)


def test_a_channel_on_every_converting_path_has_removal_effect_one():
    paths = [(["A", "B"], True), (["B"], True), (["C"], False)]
    assert removal_effects(paths)["B"] == pytest.approx(1.0)


def test_symmetric_channels_get_equal_credit_and_credit_sums_to_the_total():
    paths = [(["A", "B"], True), (["B", "A"], True), (["A"], False), (["B"], False)]
    credit = attribute(paths, 100.0)
    assert credit["A"] == pytest.approx(credit["B"])
    assert sum(credit.values()) == pytest.approx(100.0)


def test_a_channel_that_never_leads_to_conversion_gets_no_credit():
    paths = [(["A"], True), (["A", "X"], False), (["X"], False)]
    assert attribute(paths, 10.0)["X"] == pytest.approx(0.0, abs=1e-9)
