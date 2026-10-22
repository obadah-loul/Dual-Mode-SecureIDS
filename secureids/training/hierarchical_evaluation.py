"""Final hierarchical evaluation for SecureIDS-HierarchicalAdvancedNet.

This module evaluates a trained hierarchical model over a DataLoader and returns
a full metric bundle: Head 1 (binary) metrics, Head 2 (attack-family) metrics on
attack rows only over the full fixed class set, rare-class metrics, and
end-to-end routed metrics. It is used both per-epoch on validation (for
checkpoint selection) and once on the test split after the best validation
checkpoint is selected. It never writes files.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from secureids.training.metrics import compute_binary_metrics, sigmoid
from secureids.training.hierarchical_metrics import (
    multiclass_classification_report,
    rare_class_macro_f1,
)


@torch.no_grad()
def collect_hierarchical_outputs(
    model: torch.nn.Module,
    loader: Any,
    device: torch.device,
) -> dict[str, np.ndarray]:
    """Run the model over ``loader`` and gather CPU arrays for scoring."""

    model.eval()
    binary_logits: list[torch.Tensor] = []
    attack_logits: list[torch.Tensor] = []
    y_binary: list[torch.Tensor] = []
    y_attack: list[torch.Tensor] = []
    masks: list[torch.Tensor] = []

    for features, yb, ya, mask in loader:
        features = features.to(device)
        outputs = model(features)
        binary_logits.append(outputs["binary_logit"].detach().cpu())
        attack_logits.append(outputs["attack_logits"].detach().cpu())
        y_binary.append(yb.detach().cpu())
        y_attack.append(ya.detach().cpu())
        masks.append(mask.detach().cpu())

    return {
        "binary_logits": torch.cat(binary_logits).numpy().reshape(-1),
        "attack_logits": torch.cat(attack_logits).numpy(),
        "y_binary": torch.cat(y_binary).numpy().reshape(-1).astype(np.int64),
        "y_attack_family": torch.cat(y_attack).numpy().reshape(-1).astype(np.int64),
        "attack_family_mask": torch.cat(masks).numpy().reshape(-1).astype(np.int64),
    }


def compute_routing_metrics(
    y_binary: np.ndarray,
    binary_pred: np.ndarray,
    y_attack_family: np.ndarray,
    attack_pred: np.ndarray,
) -> dict[str, Any]:
    """End-to-end routed outcomes for the hierarchical decision.

    Routing uses the binary head to gate Head 2: an attack is only attributed to
    a family if the binary head fires. Categories:

    - benign_correctly_stopped: true benign predicted benign
    - attack_detected_and_correctly_attributed: true attack, predicted attack,
      and Head 2 argmax equals the true family
    - attack_detected_wrong_family: true attack, predicted attack, wrong family
    - attack_missed_as_benign: true attack predicted benign
    """

    true_benign = y_binary == 0
    true_attack = y_binary == 1
    pred_attack = binary_pred == 1

    benign_total = int(true_benign.sum())
    attack_total = int(true_attack.sum())

    benign_stopped = int(np.sum(true_benign & (binary_pred == 0)))
    benign_flagged = int(np.sum(true_benign & pred_attack))

    detected = true_attack & pred_attack
    missed = int(np.sum(true_attack & (binary_pred == 0)))
    correct_family = int(np.sum(detected & (attack_pred == y_attack_family)))
    wrong_family = int(np.sum(detected)) - correct_family

    def _rate(numerator: int, denominator: int) -> float:
        return float(numerator) / float(denominator) if denominator else 0.0

    return {
        "benign_total": benign_total,
        "attack_total": attack_total,
        "benign_correctly_stopped": benign_stopped,
        "benign_correctly_stopped_rate": _rate(benign_stopped, benign_total),
        "benign_flagged_as_attack": benign_flagged,
        "benign_flagged_as_attack_rate": _rate(benign_flagged, benign_total),
        "attack_detected_and_correctly_attributed": correct_family,
        "attack_detected_and_correctly_attributed_rate": _rate(correct_family, attack_total),
        "attack_detected_wrong_family": wrong_family,
        "attack_detected_wrong_family_rate": _rate(wrong_family, attack_total),
        "attack_missed_as_benign": missed,
        "attack_missed_as_benign_rate": _rate(missed, attack_total),
    }


def evaluate_hierarchical(
    collected: dict[str, np.ndarray],
    class_names: list[str],
    rare_class_names: list[str],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute the full hierarchical metric bundle from collected outputs."""

    binary_logits = collected["binary_logits"]
    attack_logits = collected["attack_logits"]
    y_binary = collected["y_binary"]
    y_attack_family = collected["y_attack_family"]
    mask = collected["attack_family_mask"]
    if attack_logits.ndim != 2 or attack_logits.shape[1] != len(class_names):
        raise ValueError('Family logits must match the fixed taxonomy.')
    rows = attack_logits.shape[0]
    if any(np.asarray(a).shape != (rows,) for a in (binary_logits, y_binary, y_attack_family, mask)):
        raise ValueError('Hierarchical outputs, labels, and masks must align.')
    if not np.isfinite(attack_logits).all() or not np.isfinite(binary_logits).all():
        raise ValueError('Hierarchical logits must be finite.')
    if not np.isin(y_binary, [0, 1]).all() or not np.array_equal(mask, y_binary):
        raise ValueError('Family mask must identify exactly the binary attack rows.')
    if np.any(y_attack_family[mask == 0] != -1):
        raise ValueError('Benign family labels must use ignore_index=-1.')
    if not np.isin(y_attack_family[mask == 1], np.arange(len(class_names))).all():
        raise ValueError('Attack labels must belong to the fixed family taxonomy.')
    num_classes = int(attack_logits.shape[1])

    # --- Head 1: binary ---
    binary = compute_binary_metrics(y_binary, binary_logits, threshold=threshold, from_logits=True)
    binary_cm = binary["confusion_matrix"]
    binary_block = {
        "accuracy": binary["accuracy"],
        "precision": binary["precision"],
        "recall": binary["recall"],
        "f1": binary["f1"],
        "macro_f1": binary["macro_f1"],
        "confusion_matrix": binary_cm,
        "attack_false_negatives": int(binary_cm["fn"]),
        "n_samples": binary["n_samples"],
        "threshold": float(threshold),
    }

    # --- Head 2: attack-family on attack rows only ---
    attack_rows = (mask == 1) & (y_attack_family >= 0)
    attack_true = y_attack_family[attack_rows]
    attack_pred_rows = (
        np.argmax(attack_logits[attack_rows], axis=1)
        if int(attack_rows.sum()) > 0
        else np.array([], dtype=np.int64)
    )
    attack_report = multiclass_classification_report(
        attack_true, attack_pred_rows, num_classes, class_names=class_names
    )
    rare = rare_class_macro_f1(attack_report, rare_class_names)

    # --- End-to-end routing (all rows) ---
    binary_pred_all = (sigmoid(binary_logits) >= threshold).astype(np.int64)
    attack_pred_all = np.argmax(attack_logits, axis=1).astype(np.int64)
    routing = compute_routing_metrics(
        y_binary, binary_pred_all, y_attack_family, attack_pred_all
    )

    return {
        "binary": binary_block,
        "attack_family": {
            "accuracy_on_attack_rows": attack_report["accuracy"],
            "macro_f1_on_attack_rows": attack_report["macro_f1"],
            "attack_rows_evaluated": attack_report["n_samples"],
            "per_class": attack_report["per_class"],
            "confusion_matrix": attack_report["confusion_matrix"],
            "class_names": attack_report["class_names"],
        },
        "rare_class": rare,
        "hierarchical_routing": routing,
        "selection": {
            "val_binary_macro_f1": binary_block["macro_f1"],
            "val_attack_family_macro_f1": attack_report["macro_f1"],
            "val_hierarchical_score": 0.5 * binary_block["macro_f1"]
            + 0.5 * attack_report["macro_f1"],
        },
    }


def evaluate_hierarchical_model(
    model: torch.nn.Module,
    loader: Any,
    device: torch.device,
    class_names: list[str],
    rare_class_names: list[str],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Convenience wrapper: collect outputs then compute the full bundle."""

    collected = collect_hierarchical_outputs(model, loader, device)
    return evaluate_hierarchical(collected, class_names, rare_class_names, threshold=threshold)
