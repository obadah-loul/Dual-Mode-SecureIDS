"""PyTorch dataset helpers for hierarchical smoke training.

The A7 smoke runner uses these helpers to read hierarchical processed arrays
with NumPy mmap, select tiny deterministic in-memory samples, and feed real
feature/label/mask rows into PyTorch. Nothing here writes files, saves sampled
datasets, or performs full training.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

SPLITS: tuple[str, ...] = ("train", "val", "test")
CHUNK_SIZE = 262_144


class HierarchicalNumpyDataset(Dataset):
    """Wrap hierarchical ``X``/Head1/Head2/mask arrays for PyTorch batches."""

    def __init__(
        self,
        X: np.ndarray,
        y_binary: np.ndarray,
        y_attack_family: np.ndarray,
        attack_family_mask: np.ndarray,
        indices: np.ndarray,
    ) -> None:
        if X.ndim != 2:
            raise ValueError(f"X must be 2D, got shape {X.shape}.")
        self._X = X
        self._y_binary = np.asarray(y_binary).reshape(-1)
        self._y_attack_family = np.asarray(y_attack_family).reshape(-1)
        self._attack_family_mask = np.asarray(attack_family_mask).reshape(-1)
        self._indices = np.asarray(indices, dtype=np.int64).reshape(-1)

        row_count = int(X.shape[0])
        for name, array in (
            ("y_binary", self._y_binary),
            ("y_attack_family", self._y_attack_family),
            ("attack_family_mask", self._attack_family_mask),
        ):
            if int(array.shape[0]) != row_count:
                raise ValueError(
                    f"{name} rows ({array.shape[0]}) must match X rows ({row_count})."
                )
        if self._indices.size == 0:
            raise ValueError("indices must not be empty.")
        if int(self._indices.min()) < 0 or int(self._indices.max()) >= row_count:
            raise ValueError("indices contain rows outside the array bounds.")

    def __len__(self) -> int:
        return int(self._indices.shape[0])

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        row = int(self._indices[item])
        x = torch.from_numpy(np.array(self._X[row], dtype=np.float32, copy=True))
        y_binary = torch.tensor(float(self._y_binary[row]), dtype=torch.float32)
        y_attack = torch.tensor(int(self._y_attack_family[row]), dtype=torch.long)
        attack_mask = torch.tensor(int(self._attack_family_mask[row]), dtype=torch.long)
        return x, y_binary, y_attack, attack_mask


def load_hierarchical_split(
    data_dir: Path | str,
    split: str,
    mmap: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load one hierarchical split, using mmap by default for all arrays."""

    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}.")
    root = Path(data_dir)
    mode = "r" if mmap else None
    paths = {
        "X": root / f"X_{split}.npy",
        "y_binary": root / f"y_binary_{split}.npy",
        "y_attack_family": root / f"y_attack_family_{split}.npy",
        "attack_family_mask": root / f"attack_family_mask_{split}.npy",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing hierarchical split files: {missing}")
    return (
        np.load(paths["X"], mmap_mode=mode),
        np.load(paths["y_binary"], mmap_mode=mode),
        np.load(paths["y_attack_family"], mmap_mode=mode),
        np.load(paths["attack_family_mask"], mmap_mode=mode),
    )


def _first_slice_has_required_classes(
    y_binary: np.ndarray,
    attack_family_mask: np.ndarray,
    limit: int,
) -> bool:
    y_first = np.asarray(y_binary[:limit]).reshape(-1)
    mask_first = np.asarray(attack_family_mask[:limit]).reshape(-1)
    return bool(np.any(y_first == 0) and np.any(y_first == 1) and np.any(mask_first == 1))


def _append_until(
    target: list[int],
    local_indices: np.ndarray,
    start: int,
    desired: int,
) -> None:
    if len(target) >= desired:
        return
    needed = desired - len(target)
    target.extend((local_indices[:needed] + start).astype(np.int64).tolist())


def select_hierarchical_smoke_indices(
    y_binary: np.ndarray,
    attack_family_mask: np.ndarray,
    max_samples: int,
    seed: int = 42,
) -> np.ndarray:
    """Select tiny deterministic indices, balancing only if first-N is weak.

    First-N is accepted when it already contains benign rows, attack rows, and
    attack-family mask rows. If not, the labels are scanned in chunks and a
    deterministic benign/attack mini-sample is built in memory.
    """

    y = np.asarray(y_binary).reshape(-1)
    mask = np.asarray(attack_family_mask).reshape(-1)
    if y.shape[0] != mask.shape[0]:
        raise ValueError("y_binary and attack_family_mask lengths must match.")
    total_rows = int(y.shape[0])
    limit = min(int(max_samples), total_rows)
    if limit <= 0:
        raise ValueError("max_samples must select at least one row.")

    rng = np.random.default_rng(int(seed))
    if total_rows <= limit:
        return rng.permutation(np.arange(total_rows, dtype=np.int64))

    first_indices = np.arange(limit, dtype=np.int64)
    if _first_slice_has_required_classes(y, mask, limit):
        return rng.permutation(first_indices)

    desired_attack = max(1, limit // 2)
    desired_benign = limit - desired_attack
    attack_indices: list[int] = []
    benign_indices: list[int] = []

    for start in range(0, total_rows, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, total_rows)
        y_chunk = np.asarray(y[start:end]).reshape(-1)
        mask_chunk = np.asarray(mask[start:end]).reshape(-1)
        _append_until(
            attack_indices,
            np.flatnonzero((y_chunk == 1) & (mask_chunk == 1)),
            start,
            desired_attack,
        )
        _append_until(
            benign_indices,
            np.flatnonzero((y_chunk == 0) & (mask_chunk == 0)),
            start,
            desired_benign,
        )
        if len(attack_indices) >= desired_attack and len(benign_indices) >= desired_benign:
            break

    selected = attack_indices + benign_indices
    selected_set = set(selected)
    if len(selected) < limit:
        for start in range(0, total_rows, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, total_rows)
            for row in range(start, end):
                if row not in selected_set:
                    selected.append(row)
                    selected_set.add(row)
                    if len(selected) >= limit:
                        break
            if len(selected) >= limit:
                break

    if not selected:
        raise ValueError("Could not select smoke indices.")
    return rng.permutation(np.asarray(selected[:limit], dtype=np.int64))


def summarize_hierarchical_indices(
    y_binary: np.ndarray,
    y_attack_family: np.ndarray,
    attack_family_mask: np.ndarray,
    indices: np.ndarray,
) -> dict[str, Any]:
    """Return small label/mask counts for a smoke subset."""

    idx = np.asarray(indices, dtype=np.int64)
    yb = np.asarray(y_binary[idx]).reshape(-1).astype(np.int64)
    ya = np.asarray(y_attack_family[idx]).reshape(-1).astype(np.int64)
    mask = np.asarray(attack_family_mask[idx]).reshape(-1).astype(np.int64)
    attack_rows = mask == 1
    class_ids = sorted(int(value) for value in np.unique(ya[attack_rows]) if int(value) >= 0)
    return {
        "selected_rows": int(idx.shape[0]),
        "binary_class_counts": {
            "0": int(np.sum(yb == 0)),
            "1": int(np.sum(yb == 1)),
        },
        "attack_rows": int(np.sum(attack_rows)),
        "benign_or_normal_rows": int(np.sum(mask == 0)),
        "attack_family_classes_seen": class_ids,
        "min_index": int(idx.min()),
        "max_index": int(idx.max()),
    }


def build_hierarchical_smoke_dataset(
    data_dir: Path | str,
    split: str,
    max_samples: int,
    seed: int = 42,
) -> tuple[HierarchicalNumpyDataset, dict[str, Any]]:
    """Build a tiny in-memory-indexed dataset and summary for one split."""

    X, y_binary, y_attack_family, attack_family_mask = load_hierarchical_split(
        data_dir,
        split,
        mmap=True,
    )
    indices = select_hierarchical_smoke_indices(
        y_binary,
        attack_family_mask,
        max_samples=max_samples,
        seed=seed,
    )
    dataset = HierarchicalNumpyDataset(
        X,
        y_binary,
        y_attack_family,
        attack_family_mask,
        indices,
    )
    summary = summarize_hierarchical_indices(
        y_binary,
        y_attack_family,
        attack_family_mask,
        indices,
    )
    summary["X_shape"] = [int(X.shape[0]), int(X.shape[1])]
    summary["split"] = split
    return dataset, summary
