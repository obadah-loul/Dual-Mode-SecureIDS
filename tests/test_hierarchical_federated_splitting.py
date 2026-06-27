from __future__ import annotations

import numpy as np

from secureids.federated.splitting import (
    plan_attack_family_aware_iid_client_indices,
    summarize_hierarchical_client_distribution,
)


def _toy_hierarchical_labels():
    y_binary = np.asarray([0, 0, 0, 1, 1, 1, 1, 1], dtype=np.int64)
    y_attack_family = np.asarray([-1, -1, -1, 0, 0, 1, 2, 2], dtype=np.int64)
    attack_family_mask = np.asarray([0, 0, 0, 1, 1, 1, 1, 1], dtype=np.int64)
    return y_binary, y_attack_family, attack_family_mask


def test_attack_family_aware_iid_split_is_deterministic_and_complete():
    y_binary, y_attack_family, attack_family_mask = _toy_hierarchical_labels()

    first = plan_attack_family_aware_iid_client_indices(
        y_binary,
        y_attack_family,
        attack_family_mask,
        num_clients=3,
        seed=42,
    )
    second = plan_attack_family_aware_iid_client_indices(
        y_binary,
        y_attack_family,
        attack_family_mask,
        num_clients=3,
        seed=42,
    )

    assert len(first) == 3
    assert [indices.tolist() for indices in first] == [
        indices.tolist() for indices in second
    ]
    assigned = np.concatenate(first)
    assert sorted(assigned.tolist()) == list(range(y_binary.shape[0]))
    assert len(set(assigned.tolist())) == y_binary.shape[0]
    assert int(max(assigned)) < y_binary.shape[0]


def test_hierarchical_client_distribution_audits_binary_and_attack_counts():
    y_binary, y_attack_family, attack_family_mask = _toy_hierarchical_labels()
    client_indices = plan_attack_family_aware_iid_client_indices(
        y_binary,
        y_attack_family,
        attack_family_mask,
        num_clients=3,
        seed=7,
    )

    rows, warnings = summarize_hierarchical_client_distribution(
        y_binary,
        y_attack_family,
        attack_family_mask,
        client_indices,
    )

    assert len(rows) == 3
    assert sum(row["total_samples"] for row in rows) == y_binary.shape[0]
    assert all("binary_class_counts" in row for row in rows)
    assert all("attack_family_counts" in row for row in rows)
    assert any(
        warning["type"] == "rare_attack_family_starvation"
        for warning in warnings
    )
