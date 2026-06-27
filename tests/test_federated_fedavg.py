from __future__ import annotations

import pytest

from secureids.federated.fedavg import aggregate_state_dicts_weighted


torch = pytest.importorskip("torch")


def test_weighted_fedavg_aggregates_tiny_state_dicts_by_sample_count():
    first = {
        "linear.weight": torch.tensor([[1.0, 3.0]]),
        "linear.bias": torch.tensor([1.0]),
    }
    second = {
        "linear.weight": torch.tensor([[5.0, 7.0]]),
        "linear.bias": torch.tensor([3.0]),
    }

    aggregated = aggregate_state_dicts_weighted([first, second], [1, 3])

    assert torch.allclose(aggregated["linear.weight"], torch.tensor([[4.0, 6.0]]))
    assert torch.allclose(aggregated["linear.bias"], torch.tensor([2.5]))


def test_weighted_fedavg_refuses_mismatched_sample_counts():
    state = {"weight": torch.tensor([1.0])}

    with pytest.raises(ValueError, match="same length"):
        aggregate_state_dicts_weighted([state], [1, 2])


def test_weighted_fedavg_preserves_non_floating_buffers_from_first_client():
    first = {"counter": torch.tensor(2, dtype=torch.int64)}
    second = {"counter": torch.tensor(9, dtype=torch.int64)}

    aggregated = aggregate_state_dicts_weighted([first, second], [1, 3])

    assert aggregated["counter"].item() == 2
