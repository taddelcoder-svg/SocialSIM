import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sozialsimulator.config import Distribution
from sozialsimulator.data_sources import DATA_SOURCES, list_data_sources
from sozialsimulator.distributions import sample


def test_every_entry_has_a_valid_distribution_and_citation():
    for entry in DATA_SOURCES:
        assert entry["citation"].strip()
        dist = Distribution.from_dict(entry["distribution"], path=entry["id"])
        values = sample(dist, np.random.default_rng(0), size=1000)
        assert len(values) == 1000


def test_list_data_sources_filters_by_applies_to():
    opinion_entries = list_data_sources("opinion_continuous")
    assert all(e["applies_to"] == "opinion_continuous" for e in opinion_entries)
    assert len(opinion_entries) >= 1

    unknown = list_data_sources("does_not_exist")
    assert unknown == []


def test_list_data_sources_without_filter_returns_all():
    assert list_data_sources() == DATA_SOURCES
