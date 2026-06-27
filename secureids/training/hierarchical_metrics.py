"""Non-final hierarchical smoke diagnostic metrics.

These helpers compute small smoke diagnostics from predictions supplied by the
caller. They do not write files and must not be used as final model metrics.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from secureids.training.metrics import compute_binary_metrics


def _to_numpy(values: Any) -> np.ndarray:
    if hasattr(values, "detach"):
        values = values.detach().cpu().numpy()
    return np.asarray(values)


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


# --------------------------------------------------------------------------- #
# Final (non-smoke) multiclass metric primitives for Head 2 evaluation.
# Macro-F1 is computed over the FULL fixed class set (0..num_classes-1), not just
# the classes observed in a batch, so the score is not inflated by missing
# classes. These are NumPy-only and file-free so they are easy to unit test.
# --------------------------------------------------------------------------- #
def multiclass_confusion_matrix(
    y_true: Any,
    y_pred: Any,
    num_classes: int,
) -> np.ndarray:
    """Return the ``num_classes x num_classes`` confusion matrix (rows=true)."""

    yt = _to_numpy(y_true).reshape(-1).astype(np.int64)
    yp = _to_numpy(y_pred).reshape(-1).astype(np.int64)
    if yt.shape[0] != yp.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    cm = np.zeros((int(num_classes), int(num_classes)), dtype=np.int64)
    valid = (yt >= 0) & (yt < int(num_classes)) & (yp >= 0) & (yp < int(num_classes))
    np.add.at(cm, (yt[valid], yp[valid]), 1)
    return cm


def multiclass_classification_report(
    y_true: Any,
    y_pred: Any,
    num_classes: int,
    class_names: list[str] | None = None,
) -> dict[str, Any]:
    """Per-class precision/recall/F1/support plus macro-F1 over all classes."""

    cm = multiclass_confusion_matrix(y_true, y_pred, num_classes)
    names = (
        [str(name) for name in class_names]
        if class_names is not None
        else [f"class_{index}" for index in range(int(num_classes))]
    )
    if len(names) != int(num_classes):
        raise ValueError("class_names length must equal num_classes.")

    per_class: list[dict[str, Any]] = []
    f1_scores: list[float] = []
    total = int(cm.sum())
    correct = int(np.trace(cm))
    for index in range(int(num_classes)):
        tp = int(cm[index, index])
        fp = int(cm[:, index].sum() - tp)
        fn = int(cm[index, :].sum() - tp)
        support = int(cm[index, :].sum())
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2.0 * precision * recall, precision + recall)
        f1_scores.append(f1)
        per_class.append(
            {
                "class_id": index,
                "class_name": names[index],
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
            }
        )

    return {
        "num_classes": int(num_classes),
        "accuracy": _safe_div(correct, total),
        "macro_f1": float(np.mean(f1_scores)) if f1_scores else 0.0,
        "n_samples": total,
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "class_names": names,
    }


def rare_class_macro_f1(
    report: dict[str, Any],
    rare_class_names: list[str],
) -> dict[str, Any]:
    """Mean F1 over the documented rare classes, with per-class detail."""

    by_name = {entry["class_name"]: entry for entry in report.get("per_class", [])}
    entries: list[dict[str, Any]] = []
    f1_scores: list[float] = []
    for name in rare_class_names:
        entry = by_name.get(name)
        if entry is None:
            entries.append({"class_name": name, "present": False, "f1": None, "support": None})
            continue
        f1_scores.append(float(entry["f1"]))
        entries.append(
            {
                "class_name": name,
                "present": True,
                "precision": entry["precision"],
                "recall": entry["recall"],
                "f1": entry["f1"],
                "support": entry["support"],
            }
        )
    return {
        "rare_classes": rare_class_names,
        "rare_class_macro_f1": float(np.mean(f1_scores)) if f1_scores else None,
        "per_rare_class": entries,
    }


def compute_attack_family_smoke_metrics(
    y_true: Any,
    y_pred: Any,
) -> dict[str, Any]:
    """Compute attack-family diagnostics on attack rows only."""

    true = _to_numpy(y_true).reshape(-1).astype(np.int64)
    pred = _to_numpy(y_pred).reshape(-1).astype(np.int64)
    if true.shape[0] != pred.shape[0]:
        raise ValueError("y_true and y_pred must have the same length.")
    if true.shape[0] == 0:
        return {
            "smoke_attack_family_accuracy": None,
            "smoke_attack_family_macro_f1_if_possible": None,
            "attack_rows_evaluated": 0,
            "attack_family_classes_seen_in_smoke": [],
            "attack_family_predicted_classes_seen_in_smoke": [],
        }

    classes = sorted(int(value) for value in np.unique(true))
    f1_scores: list[float] = []
    for cls in classes:
        tp = int(np.sum((true == cls) & (pred == cls)))
        fp = int(np.sum((true != cls) & (pred == cls)))
        fn = int(np.sum((true == cls) & (pred != cls)))
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2.0 * precision * recall, precision + recall)
        f1_scores.append(f1)

    return {
        "smoke_attack_family_accuracy": float(np.mean(true == pred)),
        "smoke_attack_family_macro_f1_if_possible": (
            float(np.mean(f1_scores)) if f1_scores else None
        ),
        "attack_rows_evaluated": int(true.shape[0]),
        "attack_family_classes_seen_in_smoke": classes,
        "attack_family_predicted_classes_seen_in_smoke": sorted(
            int(value) for value in np.unique(pred)
        ),
    }


def compute_hierarchical_smoke_diagnostics(
    y_binary: Any,
    binary_logits: Any,
    y_attack_family: Any,
    attack_logits: Any,
    attack_family_mask: Any,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute binary and attack-family diagnostics for a smoke eval pass."""

    yb = _to_numpy(y_binary).reshape(-1).astype(np.int64)
    binary_scores = _to_numpy(binary_logits).reshape(-1)
    ya = _to_numpy(y_attack_family).reshape(-1).astype(np.int64)
    attack_scores = _to_numpy(attack_logits)
    mask = _to_numpy(attack_family_mask).reshape(-1).astype(np.int64)

    if attack_scores.ndim != 2:
        raise ValueError("attack_logits must be a 2D array.")
    if not (
        yb.shape[0] == binary_scores.shape[0] == ya.shape[0] == mask.shape[0] == attack_scores.shape[0]
    ):
        raise ValueError("all diagnostic arrays must have the same row count.")

    binary = compute_binary_metrics(
        yb,
        binary_scores,
        threshold=threshold,
        from_logits=True,
    )
    binary_prefixed = {
        "smoke_binary_accuracy": binary["accuracy"],
        "smoke_binary_precision": binary["precision"],
        "smoke_binary_recall": binary["recall"],
        "smoke_binary_f1": binary["f1"],
        "smoke_binary_macro_f1": binary["macro_f1"],
        "binary_confusion_counts": binary["confusion_matrix"],
        "threshold": binary["threshold"],
        "n_samples": binary["n_samples"],
    }

    attack_rows = (mask == 1) & (ya >= 0)
    attack_predictions = np.argmax(attack_scores[attack_rows], axis=1)
    attack = compute_attack_family_smoke_metrics(
        ya[attack_rows],
        attack_predictions,
    )

    return {
        "non_final": True,
        "do_not_report_as_final": True,
        "binary": binary_prefixed,
        "attack_family": attack,
    }
