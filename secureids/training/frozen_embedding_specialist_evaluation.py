"""Metric helpers for A9.10 frozen-embedding specialist reporting."""

from __future__ import annotations

from typing import Any

from secureids.training.attack_family_specialist_evaluation import (
    ORACLE_VIEW,
    ROUTED_VIEW,
    assemble_specialist_report,
    compute_oracle_attack_family_metrics,
    compute_routed_attack_family_metrics,
)


A9_BASELINE = {
    "binary_macro_f1": 0.894488,
    "attack_family_macro_f1": 0.500429,
    "rare_class_macro_f1": 0.385669,
}


def compare_oracle_to_a9(oracle_metrics: dict[str, Any]) -> dict[str, Any]:
    """Return honest A9 comparison deltas for oracle attack-family metrics."""

    attack_f1 = float(oracle_metrics["attack_family_macro_f1"])
    rare_raw = oracle_metrics["rare_class"].get("rare_class_macro_f1")
    rare_f1 = None if rare_raw is None else float(rare_raw)
    return {
        "baseline": dict(A9_BASELINE),
        "oracle_attack_family_macro_f1": attack_f1,
        "oracle_attack_family_delta_vs_a9": attack_f1 - A9_BASELINE["attack_family_macro_f1"],
        "rare_class_macro_f1": rare_f1,
        "rare_class_delta_vs_a9": (
            None if rare_f1 is None else rare_f1 - A9_BASELINE["rare_class_macro_f1"]
        ),
        "passes_seed42_oracle_target": attack_f1 >= 0.515429,
        "rare_class_did_not_drop": (
            False if rare_f1 is None else rare_f1 >= A9_BASELINE["rare_class_macro_f1"]
        ),
        "no_single_seed_promotion": True,
    }


def assemble_a10_report_bundle(
    a9_binary_head1_metrics: dict[str, Any],
    oracle_metrics: dict[str, Any],
    routed_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Bundle A9.10 metric views with explicit oracle/routed separation."""

    if oracle_metrics.get("view") != ORACLE_VIEW:
        raise ValueError("oracle_metrics must use the oracle view.")
    if routed_metrics.get("view") != ROUTED_VIEW:
        raise ValueError("routed_metrics must use the routed view.")
    bundle = assemble_specialist_report(a9_binary_head1_metrics, oracle_metrics, routed_metrics)
    bundle["a10_direction"] = "frozen_a9_embedding_regularized_attack_family_head"
    bundle["a9_baseline_comparison"] = compare_oracle_to_a9(oracle_metrics)
    return bundle
