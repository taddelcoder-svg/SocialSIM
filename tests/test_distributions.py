import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import Distribution
from sozialsimulator.distributions import sample


def test_histogram_respects_bin_ranges():
    dist = Distribution.from_dict(
        {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": 0.0, "max": 1.0, "weight": 0.5},
                    {"min": 10.0, "max": 11.0, "weight": 0.5},
                ]
            },
        },
        path="test",
    )
    values = sample(dist, np.random.default_rng(1), size=1000)
    in_first_bin = (values >= 0.0) & (values <= 1.0)
    in_second_bin = (values >= 10.0) & (values <= 11.0)
    assert (in_first_bin | in_second_bin).all()


def test_histogram_matches_weights_approximately():
    dist = Distribution.from_dict(
        {
            "kind": "histogram",
            "params": {
                "bins": [
                    {"min": 0.0, "max": 1.0, "weight": 0.9},
                    {"min": 100.0, "max": 101.0, "weight": 0.1},
                ]
            },
        },
        path="test",
    )
    values = sample(dist, np.random.default_rng(2), size=20000)
    share_first_bin = (values < 50).mean()
    assert abs(share_first_bin - 0.9) < 0.02


def test_histogram_is_reproducible_with_same_seed():
    dist = Distribution.from_dict(
        {"kind": "histogram", "params": {"bins": [{"min": 0, "max": 1, "weight": 1.0}]}},
        path="test",
    )
    a = sample(dist, np.random.default_rng(5), size=50)
    b = sample(dist, np.random.default_rng(5), size=50)
    assert (a == b).all()
