"""Reusable binary classification metric helpers.

These helpers are implemented with NumPy and handle zero division safely. They
compute metrics only from real predictions passed by the caller; nothing here
fabricates placeholder values and nothing writes files. The same helpers are
intended for reuse later by federated, robustness, and XAI evaluation code.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _to_numpy(values: Any) -> np.ndarray:
    """Convert torch tensors or array-likes to a flat NumPy array."""

    if hasattr(values, "detach"):  # torch.Tensor
        values = values.detach().cpu().numpy()
    return np.asarray(values).reshape(-1)


def sigmoid(logits: Any) -> np.ndarray:
    """Numerically stable elementwise sigmoid."""

    x = _to_numpy(logits).astype(np.float64)
    probabilities = np.empty_like(x, dtype=np.float64)

    positive = x >= 0.0
    negative = x < 0.0
    nan_values = np.isnan(x)

    probabilities[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[negative])
    probabilities[negative] = exp_x / (1.0 + exp_x)
    probabilities[nan_values] = np.nan
    return probabilities


def to_probabilities(scores: Any, from_logits: bool = True) -> np.ndarray:
    """Return probabilities, applying a sigmoid when ``scores`` are logits."""

    values = _to_numpy(scores).astype(np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError('Scores must be finite.')
    if not from_logits and np.any((values < 0) | (values > 1)):
        raise ValueError('Probabilities must be in [0, 1].')
    return sigmoid(values) if from_logits else values


def threshold_predictions(probabilities: Any, threshold: float = 0.5) -> np.ndarray:
    """Threshold probabilities into ``{0, 1}`` integer predictions."""

    if isinstance(threshold, bool) or not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('threshold must be finite and in [0, 1].')
    values = to_probabilities(probabilities, from_logits=False)
    return (values >= threshold).astype(np.int64)


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def binary_confusion_matrix(y_true: Any, y_pred: Any) -> dict[str, int]:
    """Return the confusion matrix as ``{"tp", "fp", "fn", "tn"}``."""

    yt = _to_numpy(y_true)
    yp = _to_numpy(y_pred)
    if not np.all(np.isin(yt, [0, 1])) or not np.all(np.isin(yp, [0, 1])):
        raise ValueError('Binary labels must be exactly 0 or 1.')
    if yt.shape[0] != yp.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    return {
        "tp": int(np.sum((yt == 1) & (yp == 1))),
        "fp": int(np.sum((yt == 0) & (yp == 1))),
        "fn": int(np.sum((yt == 1) & (yp == 0))),
        "tn": int(np.sum((yt == 0) & (yp == 0))),
    }


def accuracy(cm: dict[str, int]) -> float:
    total = cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]
    return _safe_div(cm["tp"] + cm["tn"], total)


def precision(cm: dict[str, int]) -> float:
    return _safe_div(cm["tp"], cm["tp"] + cm["fp"])


def recall(cm: dict[str, int]) -> float:
    return _safe_div(cm["tp"], cm["tp"] + cm["fn"])


def f1(cm: dict[str, int]) -> float:
    prec = precision(cm)
    rec = recall(cm)
    return _safe_div(2.0 * prec * rec, prec + rec)


def macro_f1(cm: dict[str, int]) -> float:
    """Unweighted mean of the positive-class and negative-class F1 scores."""

    positive_f1 = f1(cm)
    # Negative-class F1: treat label 0 as the positive class.
    negative_cm = {
        "tp": cm["tn"],
        "fp": cm["fn"],
        "fn": cm["fp"],
        "tn": cm["tp"],
    }
    negative_f1 = f1(negative_cm)
    return 0.5 * (positive_f1 + negative_f1)


def compute_binary_metrics(
    y_true: Any,
    scores: Any,
    threshold: float = 0.5,
    from_logits: bool = True,
) -> dict[str, Any]:
    """Compute the standard binary metric bundle from real predictions.

    Parameters
    ----------
    y_true:
        Ground-truth labels in ``{0, 1}``.
    scores:
        Model outputs. Interpreted as raw logits when ``from_logits`` is True,
        otherwise as probabilities in ``[0, 1]``.
    threshold:
        Decision threshold applied to probabilities.
    """

    probabilities = to_probabilities(scores, from_logits=from_logits)
    y_pred = threshold_predictions(probabilities, threshold=threshold)
    cm = binary_confusion_matrix(y_true, y_pred)
    return {
        "accuracy": accuracy(cm),
        "precision": precision(cm),
        "recall": recall(cm),
        "f1": f1(cm),
        "macro_f1": macro_f1(cm),
        "confusion_matrix": cm,
        "threshold": float(threshold),
        "n_samples": int(cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]),
    }
