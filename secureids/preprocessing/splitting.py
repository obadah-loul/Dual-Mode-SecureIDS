"""Split policy helpers for preprocessing."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.model_selection import train_test_split


def describe_split_policy(split_config: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized split-policy summary without splitting data."""

    return dict(split_config)


SPLIT_TRAIN = 0
SPLIT_VAL = 1
SPLIT_TEST = 2
SPLIT_NAMES = {
    SPLIT_TRAIN: "train",
    SPLIT_VAL: "val",
    SPLIT_TEST: "test",
}


def make_class_split_codes(
    label_counts: dict[int, int],
    train_size: float,
    val_size: float,
    random_seed: int,
) -> dict[int, np.ndarray]:
    """Create exact per-class randomized split codes for streaming assignment."""

    split_codes: dict[int, np.ndarray] = {}
    for label, count in sorted(label_counts.items()):
        train_count = int(round(count * train_size))
        val_count = int(round(count * val_size))
        test_count = count - train_count - val_count
        if test_count < 0:
            val_count = max(0, val_count + test_count)
            test_count = 0

        codes = np.empty(count, dtype=np.uint8)
        codes[:train_count] = SPLIT_TRAIN
        codes[train_count:train_count + val_count] = SPLIT_VAL
        codes[train_count + val_count:] = SPLIT_TEST

        rng = np.random.default_rng(random_seed + int(label))
        rng.shuffle(codes)
        split_codes[int(label)] = codes
    return split_codes


def split_train_validation(
    features,
    labels,
    val_size: float,
    random_seed: int,
):
    """Split official training data into train and validation subsets."""

    return train_test_split(
        features,
        labels,
        test_size=val_size,
        random_state=random_seed,
        stratify=labels,
    )
