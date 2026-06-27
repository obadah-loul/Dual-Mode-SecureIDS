from __future__ import annotations

import numpy as np
import pytest

from secureids.federated.splitting import (
    ClientSplitError,
    plan_stratified_iid_client_distribution,
)


def test_stratified_iid_split_is_deterministic():
    y_train = np.array([0] * 51 + [1] * 29, dtype=np.int64)

    first = plan_stratified_iid_client_distribution(y_train, num_clients=5, seed=42)
    second = plan_stratified_iid_client_distribution(y_train, num_clients=5, seed=42)

    assert first == second


def test_client_distribution_counts_sum_to_train_labels():
    y_train = np.array([0] * 60 + [1] * 40, dtype=np.int64)

    distribution = plan_stratified_iid_client_distribution(
        y_train,
        num_clients=5,
        seed=42,
    )

    assert len(distribution) == 5
    assert sum(client["total_samples"] for client in distribution) == len(y_train)
    assert sum(client["class_0_count"] for client in distribution) == 60
    assert sum(client["class_1_count"] for client in distribution) == 40
    for client in distribution:
        assert client["total_samples"] == 20
        assert client["class_0_count"] == 12
        assert client["class_1_count"] == 8
        assert client["class_0_fraction"] == 0.6
        assert client["class_1_fraction"] == 0.4


def test_split_planning_requires_train_labels_only():
    y_train = np.array([0, 0, 1, 1, 0, 1], dtype=np.int64)

    distribution = plan_stratified_iid_client_distribution(
        y_train,
        num_clients=3,
        seed=42,
    )

    assert sum(client["total_samples"] for client in distribution) == len(y_train)


@pytest.mark.parametrize("num_clients", [0, -1, 1.5, "5"])
def test_invalid_client_count_fails(num_clients):
    y_train = np.array([0, 1, 0, 1], dtype=np.int64)

    with pytest.raises(ClientSplitError, match="num_clients"):
        plan_stratified_iid_client_distribution(
            y_train,
            num_clients=num_clients,
            seed=42,
        )


def test_non_binary_labels_fail():
    y_train = np.array([0, 1, 2], dtype=np.int64)

    with pytest.raises(ClientSplitError, match="binary labels"):
        plan_stratified_iid_client_distribution(
            y_train,
            num_clients=2,
            seed=42,
        )
