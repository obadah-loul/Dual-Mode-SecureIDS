from __future__ import annotations

import pytest

from secureids.federated.robust_aggregation import (
    AggregationValidationError,
    aggregate_fedavg,
    aggregate_krum,
    aggregate_median,
    aggregate_trimmed_mean,
)


torch = pytest.importorskip("torch")


def test_fedavg_correctness_with_sample_weights():
    updates = [
        {"w": torch.tensor([1.0, 3.0]), "b": torch.tensor([1.0])},
        {"w": torch.tensor([5.0, 7.0]), "b": torch.tensor([3.0])},
    ]

    aggregated = aggregate_fedavg(updates, weights=[1, 3])

    assert torch.allclose(aggregated["w"], torch.tensor([4.0, 6.0]))
    assert torch.allclose(aggregated["b"], torch.tensor([2.5]))


def test_trimmed_mean_removes_coordinate_outliers():
    updates = [
        torch.tensor([1.0, 10.0]),
        torch.tensor([2.0, 20.0]),
        torch.tensor([3.0, 30.0]),
        torch.tensor([100.0, 400.0]),
    ]

    aggregated = aggregate_trimmed_mean(updates, trim_ratio=0.25)

    assert torch.allclose(aggregated, torch.tensor([2.5, 25.0]))


def test_median_correctness():
    updates = [
        {"w": torch.tensor([1.0, 9.0])},
        {"w": torch.tensor([2.0, 8.0])},
        {"w": torch.tensor([100.0, 7.0])},
    ]

    aggregated = aggregate_median(updates)

    assert torch.allclose(aggregated["w"], torch.tensor([2.0, 8.0]))


def test_invalid_shape_rejected():
    with pytest.raises(AggregationValidationError, match="shape"):
        aggregate_fedavg([torch.tensor([1.0]), torch.tensor([[1.0]])])


def test_invalid_weights_rejected():
    with pytest.raises(AggregationValidationError, match="weights"):
        aggregate_fedavg([torch.tensor([1.0]), torch.tensor([2.0])], weights=[1, 0])


def test_krum_selects_honest_update_in_toy_case():
    updates = [
        torch.tensor([1.0, 1.0]),
        torch.tensor([1.1, 1.0]),
        torch.tensor([0.9, 1.0]),
        torch.tensor([1.0, 1.1]),
        torch.tensor([50.0, 50.0]),
    ]

    selected = aggregate_krum(updates, num_malicious=1)

    assert torch.linalg.vector_norm(selected - torch.tensor([1.0, 1.0])) < 0.2
