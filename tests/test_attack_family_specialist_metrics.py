"""Oracle vs routed metric-separation tests (torch-free)."""

from __future__ import annotations

import pytest

from secureids.training.attack_family_specialist_evaluation import (
    ORACLE_VIEW,
    ROUTED_VIEW,
    assemble_specialist_report,
    compute_oracle_attack_family_metrics,
    compute_routed_attack_family_metrics,
)


def test_oracle_macro_f1_over_full_class_set_keeps_weak_classes_visible():
    # Only 4 of 9 families appear; the other 5 (incl. Analysis, Backdoor) score 0.
    y_true = [0, 1, 2, 3]
    y_pred = [0, 1, 2, 3]
    m = compute_oracle_attack_family_metrics(y_true, y_pred)
    assert m["view"] == ORACLE_VIEW and m["is_oracle"] is True
    assert m["is_routed_deployment_metric"] is False
    assert m["attack_family_accuracy"] == pytest.approx(1.0)
    # macro-F1 averaged over all 9 classes (4 perfect, 5 zero) = 4/9.
    assert m["attack_family_macro_f1"] == pytest.approx(4 / 9)
    names = [p["class_name"] for p in m["per_class"]]
    for weak in ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms"):
        assert weak in names


def test_routed_accounts_for_missed_as_benign_and_is_bounded_by_oracle():
    y_true = [0, 1, 2, 3]
    router = [1, 1, 1, 0]  # frozen A9 Head 1 missed the last attack as benign
    specialist = [0, 1, 2, 3]
    routed = compute_routed_attack_family_metrics(y_true, router, specialist)
    assert routed["view"] == ROUTED_VIEW and routed["is_routed_deployment_metric"] is True
    assert routed["attack_missed_as_benign"] == 1
    assert routed["attack_detected_and_correctly_attributed"] == 3
    assert routed["attack_detected_and_correctly_attributed_rate"] == pytest.approx(3 / 4)

    oracle = compute_oracle_attack_family_metrics(y_true, specialist)
    # Routed correctly-attributed count cannot exceed oracle correct count.
    oracle_correct = sum(1 for t, p in zip(y_true, specialist) if t == p)
    assert routed["attack_detected_and_correctly_attributed"] <= oracle_correct
    # And routed macro-F1 is <= oracle macro-F1 when Head 1 misses an attack.
    assert routed["routed_attack_family_macro_f1"] <= oracle["attack_family_macro_f1"]


def test_assemble_requires_correct_view_labels():
    y_true = [0, 1, 2, 3]
    oracle = compute_oracle_attack_family_metrics(y_true, [0, 1, 2, 3])
    routed = compute_routed_attack_family_metrics(y_true, [1, 1, 1, 1], [0, 1, 2, 3])
    a9_binary = {"binary_macro_f1": 0.894488, "source": "frozen_a9_head1"}

    bundle = assemble_specialist_report(a9_binary, oracle, routed)
    assert bundle["do_not_report_oracle_as_routed"] is True
    assert "specialist_oracle_attack_family" in bundle
    assert "routed_end_to_end" in bundle
    assert "a9_binary_head1" in bundle

    # Swapping the two views must raise (prevents reporting oracle as routed).
    with pytest.raises(ValueError):
        assemble_specialist_report(a9_binary, routed, oracle)
