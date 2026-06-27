"""Deterministic client split planning for federated dry-runs.

Only label arrays are used here. No validation labels, test labels, raw data, or
feature matrices are required for client split planning.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class ClientSplitError(ValueError):
    """Raised when client split planning is invalid."""


def _validate_labels(labels: Any) -> np.ndarray:
    y = np.asarray(labels).reshape(-1)
    if y.size == 0:
        raise ClientSplitError("y_train labels must not be empty.")
    unique = set(np.unique(y).astype(int).tolist())
    if not unique.issubset({0, 1}):
        raise ClientSplitError(f"Expected binary labels in {{0, 1}}, found {unique}.")
    return y.astype(np.int64, copy=False)


def plan_stratified_iid_client_distribution(
    y_train: Any,
    num_clients: int,
    seed: int,
) -> list[dict[str, float | int | str]]:
    """Plan a deterministic stratified IID client distribution summary.

    The function intentionally returns distribution summaries only, not indices,
    so dry-runs cannot be mistaken for a materialized training split artifact.
    """

    if (
        isinstance(num_clients, bool)
        or not isinstance(num_clients, int)
        or num_clients <= 0
    ):
        raise ClientSplitError("num_clients must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ClientSplitError("seed must be an integer.")

    client_indices = plan_stratified_iid_client_indices(
        y_train=y_train,
        num_clients=num_clients,
        seed=seed,
    )
    y = _validate_labels(y_train)

    summaries: list[dict[str, float | int | str]] = []
    for client_id, indices in enumerate(client_indices):
        labels = y[indices]
        class_0_count = int(np.sum(labels == 0))
        class_1_count = int(np.sum(labels == 1))
        total_samples = class_0_count + class_1_count
        summaries.append(
            {
                "client_id": f"client_{client_id:02d}",
                "total_samples": total_samples,
                "class_0_count": class_0_count,
                "class_1_count": class_1_count,
                "class_0_fraction": (
                    float(class_0_count) / float(total_samples)
                    if total_samples
                    else 0.0
                ),
                "class_1_fraction": (
                    float(class_1_count) / float(total_samples)
                    if total_samples
                    else 0.0
                ),
            }
        )
    return summaries


def plan_stratified_iid_client_indices(
    y_train: Any,
    num_clients: int,
    seed: int,
) -> list[np.ndarray]:
    """Return deterministic stratified IID train indices for real training.

    This helper still uses only ``y_train``. It never consumes validation/test
    labels or raw data.
    """

    if (
        isinstance(num_clients, bool)
        or not isinstance(num_clients, int)
        or num_clients <= 0
    ):
        raise ClientSplitError("num_clients must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ClientSplitError("seed must be an integer.")

    y = _validate_labels(y_train)
    if num_clients > y.shape[0]:
        raise ClientSplitError("num_clients cannot exceed the number of labels.")

    rng = np.random.default_rng(int(seed))
    client_parts = [[] for _ in range(num_clients)]
    for label in (0, 1):
        indices = np.flatnonzero(y == label)
        rng.shuffle(indices)
        partitions = np.array_split(indices, num_clients)
        for client_id, partition in enumerate(partitions):
            client_parts[client_id].append(partition)

    client_indices = []
    for parts in client_parts:
        combined = np.concatenate(parts).astype(np.int64, copy=False)
        rng.shuffle(combined)
        client_indices.append(combined)
    return client_indices


def _validate_hierarchical_labels(
    y_binary: Any,
    y_attack_family: Any,
    attack_family_mask: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    yb = np.asarray(y_binary).reshape(-1).astype(np.int64, copy=False)
    ya = np.asarray(y_attack_family).reshape(-1).astype(np.int64, copy=False)
    mask = np.asarray(attack_family_mask).reshape(-1).astype(np.int64, copy=False)
    if yb.size == 0:
        raise ClientSplitError("hierarchical train labels must not be empty.")
    if not (yb.shape[0] == ya.shape[0] == mask.shape[0]):
        raise ClientSplitError("hierarchical label/mask lengths must match.")
    if not set(np.unique(yb).astype(int).tolist()).issubset({0, 1}):
        raise ClientSplitError("Expected binary labels in {0, 1}.")
    if not set(np.unique(mask).astype(int).tolist()).issubset({0, 1}):
        raise ClientSplitError("Expected attack_family_mask values in {0, 1}.")
    if not np.array_equal(yb, mask):
        raise ClientSplitError("y_binary and attack_family_mask must agree.")
    if not np.all(ya[mask == 0] == -1):
        raise ClientSplitError("Benign/mask-0 rows must have attack family -1.")
    if np.any(ya[mask == 1] < 0):
        raise ClientSplitError("Attack rows must have non-negative attack family ids.")
    return yb, ya, mask


def plan_attack_family_aware_iid_client_indices(
    y_binary: Any,
    y_attack_family: Any,
    attack_family_mask: Any,
    num_clients: int,
    seed: int,
) -> list[np.ndarray]:
    """Split train rows by benign bucket and each attack-family bucket.

    This avoids binary-only IID splitting, which can hide rare attack-family
    starvation. Only train labels are accepted by contract; validation/test
    labels are not inputs to this helper.
    """

    if (
        isinstance(num_clients, bool)
        or not isinstance(num_clients, int)
        or num_clients <= 0
    ):
        raise ClientSplitError("num_clients must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ClientSplitError("seed must be an integer.")

    yb, ya, mask = _validate_hierarchical_labels(
        y_binary,
        y_attack_family,
        attack_family_mask,
    )
    if num_clients > yb.shape[0]:
        raise ClientSplitError("num_clients cannot exceed the number of train rows.")

    rng = np.random.default_rng(int(seed))
    client_parts = [[] for _ in range(num_clients)]

    buckets: list[np.ndarray] = [np.flatnonzero((yb == 0) & (mask == 0))]
    for class_id in sorted(int(value) for value in np.unique(ya[mask == 1])):
        buckets.append(np.flatnonzero((mask == 1) & (ya == class_id)))

    for bucket in buckets:
        shuffled = np.asarray(bucket, dtype=np.int64).copy()
        rng.shuffle(shuffled)
        partitions = np.array_split(shuffled, num_clients)
        for client_id, partition in enumerate(partitions):
            if partition.size:
                client_parts[client_id].append(partition)

    client_indices: list[np.ndarray] = []
    for parts in client_parts:
        if parts:
            combined = np.concatenate(parts).astype(np.int64, copy=False)
        else:
            combined = np.asarray([], dtype=np.int64)
        rng.shuffle(combined)
        client_indices.append(combined)
    return client_indices


def summarize_hierarchical_client_distribution(
    y_binary: Any,
    y_attack_family: Any,
    attack_family_mask: Any,
    client_indices: list[np.ndarray],
    min_attack_family_support_per_client: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return client distribution rows and rare-family starvation warnings."""

    yb, ya, mask = _validate_hierarchical_labels(
        y_binary,
        y_attack_family,
        attack_family_mask,
    )
    row_count = int(yb.shape[0])
    seen: list[int] = []
    attack_class_ids = sorted(int(value) for value in np.unique(ya[mask == 1]))
    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for client_id, indices in enumerate(client_indices):
        idx = np.asarray(indices, dtype=np.int64).reshape(-1)
        if idx.size and (int(idx.min()) < 0 or int(idx.max()) >= row_count):
            raise ClientSplitError("client indices contain out-of-range rows.")
        seen.extend(int(value) for value in idx.tolist())
        client_binary = yb[idx]
        client_attack = ya[idx]
        client_mask = mask[idx]
        attack_counts = {
            str(class_id): int(np.sum((client_mask == 1) & (client_attack == class_id)))
            for class_id in attack_class_ids
        }
        row = {
            "client_id": f"client_{client_id:02d}",
            "total_samples": int(idx.size),
            "binary_class_counts": {
                "0": int(np.sum(client_binary == 0)),
                "1": int(np.sum(client_binary == 1)),
            },
            "attack_family_counts": attack_counts,
            "attack_rows": int(np.sum(client_mask == 1)),
            "benign_rows": int(np.sum(client_mask == 0)),
        }
        rows.append(row)
        for class_id, count in attack_counts.items():
            if 0 < count < int(min_attack_family_support_per_client):
                warnings.append(
                    {
                        "type": "low_attack_family_support",
                        "client_id": row["client_id"],
                        "attack_family_id": class_id,
                        "support": count,
                        "minimum": int(min_attack_family_support_per_client),
                    }
                )

    unique_seen = sorted(seen)
    if unique_seen != list(range(row_count)):
        raise ClientSplitError("client split must assign every train row exactly once.")
    for class_id in attack_class_ids:
        global_support = int(np.sum((mask == 1) & (ya == class_id)))
        client_supports = [
            int(row["attack_family_counts"][str(class_id)]) for row in rows
        ]
        zero_clients = [
            row["client_id"]
            for row in rows
            if int(row["attack_family_counts"][str(class_id)]) == 0
        ]
        if zero_clients:
            warnings.append(
                {
                    "type": "rare_attack_family_starvation",
                    "attack_family_id": str(class_id),
                    "global_support": global_support,
                    "clients_missing_family": zero_clients,
                    "min_client_support": min(client_supports) if client_supports else 0,
                }
            )
    return rows, warnings
