"""PyTorch dataset and DataLoader helpers for centralized training.

The pure NumPy/JSON loaders live in :mod:`secureids.training.planning` (which is
torch-free so the dry-run path can run without PyTorch). They are re-exported
here for convenience, alongside the torch-only ``BinaryNumpyDataset`` and
``create_data_loaders``. Importing this module requires torch; the dry-run path
must import :mod:`secureids.training.planning` instead.

Feature matrices may be memory-mapped (``mmap_mode="r"``) so the large
CICIDS2018 train array is never fully materialized in RAM; individual rows are
copied to ``float32`` only when a batch is assembled. Validation/test loaders
never shuffle and no files are written here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from secureids.training.planning import (
    SPLITS,
    get_input_dim_from_processed,
    load_feature_names,
    load_label_mapping,
    load_numpy_split,
)

if TYPE_CHECKING:  # avoid importing config at runtime; only needed for hints
    from secureids.training.config import TrainingConfig

__all__ = [
    "SPLITS",
    "BinaryNumpyDataset",
    "create_data_loaders",
    "get_input_dim_from_processed",
    "load_feature_names",
    "load_label_mapping",
    "load_numpy_split",
]


class BinaryNumpyDataset(Dataset):
    """Wrap preprocessed ``X``/``y`` arrays for ``BCEWithLogitsLoss`` training.

    Each item is ``(x, y)`` where ``x`` is a ``float32`` feature vector and
    ``y`` is a ``float32`` tensor of shape ``[1]``. A batch therefore collates
    to ``y`` of shape ``[batch, 1]``, matching the ``[batch, 1]`` logits emitted
    by :class:`~secureids.models.secureids_net.SecureIDSNet`.

    ``X`` may be a memory-mapped array; rows are copied into owned, contiguous
    ``float32`` arrays on access so the mmap is not held by returned tensors.
    """

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        if X.ndim != 2:
            raise ValueError(f"X must be 2D, got shape {X.shape}.")
        y = np.asarray(y).reshape(-1)
        if X.shape[0] != y.shape[0]:
            raise ValueError(
                f"X rows ({X.shape[0]}) and y rows ({y.shape[0]}) must match."
            )
        self._X = X
        self._y = y

    def __len__(self) -> int:
        return int(self._X.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.from_numpy(np.array(self._X[index], dtype=np.float32, copy=True))
        y = torch.tensor([float(self._y[index])], dtype=torch.float32)
        return x, y


def create_data_loaders(
    config: "TrainingConfig",
    splits: tuple[str, ...] = SPLITS,
    mmap: bool = True,
    num_workers: int = 0,
) -> dict[str, DataLoader]:
    """Build DataLoaders for the requested splits.

    The train loader shuffles and drops a trailing partial batch (so BatchNorm
    never sees a size-1 batch); validation and test loaders never shuffle and
    keep every sample. Building a loader reads arrays via mmap but does not
    iterate over them, so no training is performed here.
    """

    processed = config.resolve(config.processed_dir)
    loaders: dict[str, DataLoader] = {}
    for split in splits:
        X, y = load_numpy_split(processed, split, mmap=mmap)
        dataset = BinaryNumpyDataset(X, y)
        is_train = split == "train"
        loaders[split] = DataLoader(
            dataset,
            batch_size=config.training.batch_size,
            shuffle=is_train,
            drop_last=is_train,
            num_workers=num_workers,
        )
    return loaders
