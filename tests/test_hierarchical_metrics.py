"""Tests for final (non-smoke) hierarchical metric primitives and evaluation.

Pure-function tests on tiny synthetic arrays. No model training, no file writes.
"""

from __future__ import annotations

import numpy as np
import pytest

from secureids.training.hierarchical_metrics import (
    multiclass_classification_report,
    multiclass_confusion_matrix,
    rare_class_macro_f1,
)
from secureids.training.hierarchical_evaluation import (
    compute_routing_metrics,
    evaluate_hierarchical,
)

CLASS_NAMES = ["Generic", "Exploits", "Shellcode", "Worms"]
RARE = ["Shellcode", "Worms"]


def test_confusion_matrix_shape_and_counts():
    y_true = [0, 0, 1, 2, 3, 3]
    y_pred = [0, 1, 1, 2, 3, 0]
    cm = multiclass_confusion_matrix(y_true, y_pred, num_classes=4)
    assert cm.shape == (4, 4)
    assert cm[0, 0] == 1 and cm[0, 1] == 1
    assert cm[1, 1] == 1
    assert cm[2, 2] == 1
    assert cm[3, 3] == 1 and cm[3, 0] == 1
    assert int(cm.sum()) == 6


def test_classification_report_perfect():
    y = [0, 1, 2, 3, 0, 1]
    report = multiclass_classification_report(y, y, num_classes=4, class_names=CLASS_NAMES)
    assert report["accuracy"] == 1.0
    assert report["macro_f1"] == 1.0
    assert report["num_classes"] == 4
    supports = {entry["class_name"]: entry["support"] for entry in report["per_class"]}
    assert supports == {"Generic": 2, "Exploits": 2, "Shellcode": 1, "Worms": 1}


def test_macro_f1_counts_all_fixed_classes_even_when_absent():
    # Only classes 0 and 1 appear; classes 2,3 have zero support -> F1 0 each,
    # so macro-F1 over the FULL fixed set is (1 + 1 + 0 + 0)/4 = 0.5, not 1.0.
    y = [0, 0, 1, 1]
    report = multiclass_classification_report(y, y, num_classes=4, class_names=CLASS_NAMES)
    assert report["accuracy"] == 1.0
    assert report["macro_f1"] == pytest.approx(0.5)


def test_classification_report_rejects_bad_class_names():
    with pytest.raises(ValueError):
        multiclass_classification_report([0, 1], [0, 1], num_classes=4, class_names=["a", "b"])


def test_rare_class_macro_f1_selects_rare_only():
    y_true = [0, 0, 1, 2, 3]
    y_pred = [0, 0, 1, 2, 0]  # Worms (3) misclassified as Generic
    report = multiclass_classification_report(y_true, y_pred, num_classes=4, class_names=CLASS_NAMES)
    rare = rare_class_macro_f1(report, RARE)
    by_name = {entry["class_name"]: entry for entry in rare["per_rare_class"]}
    assert by_name["Shellcode"]["f1"] == pytest.approx(1.0)  # class 2 perfect
    assert by_name["Worms"]["f1"] == pytest.approx(0.0)      # class 3 missed
    assert rare["rare_class_macro_f1"] == pytest.approx(0.5)


def test_routing_metrics_counts():
    # rows: 2 benign, 3 attacks (families 0,1,2)
    y_binary = np.array([0, 0, 1, 1, 1])
    binary_pred = np.array([0, 1, 1, 1, 0])  # 1 benign flagged, 1 attack missed
    y_attack = np.array([-1, -1, 0, 1, 2])
    attack_pred = np.array([0, 0, 0, 0, 2])  # detected attacks: rows 2,3 -> 2 correct? row2 fam0 correct, row3 fam1 pred0 wrong
    routing = compute_routing_metrics(y_binary, binary_pred, y_attack, attack_pred)
    assert routing["benign_total"] == 2
    assert routing["attack_total"] == 3
    assert routing["benign_correctly_stopped"] == 1
    assert routing["benign_flagged_as_attack"] == 1
    assert routing["attack_missed_as_benign"] == 1          # row4 (fam2) predicted benign
    assert routing["attack_detected_and_correctly_attributed"] == 1  # row2 fam0 correct
    assert routing["attack_detected_wrong_family"] == 1     # row3 detected, fam wrong


def test_evaluate_hierarchical_bundle_structure():
    rng = np.random.default_rng(0)
    n = 40
    num_classes = 4
    y_binary = (rng.random(n) > 0.5).astype(np.int64)
    mask = y_binary.copy()
    y_attack = np.where(mask == 1, rng.integers(0, num_classes, size=n), -1).astype(np.int64)
    binary_logits = rng.normal(size=n).astype(np.float32)
    attack_logits = rng.normal(size=(n, num_classes)).astype(np.float32)
    collected = {
        "binary_logits": binary_logits,
        "attack_logits": attack_logits,
        "y_binary": y_binary,
        "y_attack_family": y_attack,
        "attack_family_mask": mask,
    }
    bundle = evaluate_hierarchical(collected, CLASS_NAMES, RARE, threshold=0.5)
    assert set(bundle) == {"binary", "attack_family", "rare_class", "hierarchical_routing", "selection"}
    assert bundle["selection"]["val_hierarchical_score"] == pytest.approx(
        0.5 * bundle["binary"]["macro_f1"] + 0.5 * bundle["attack_family"]["macro_f1_on_attack_rows"]
    )
    # attack-family metrics computed on attack rows only
    assert bundle["attack_family"]["attack_rows_evaluated"] == int(mask.sum())
    assert len(bundle["attack_family"]["per_class"]) == num_classes
