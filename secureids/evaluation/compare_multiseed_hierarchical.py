"""Aggregate completed UNSW A9.8 multi-seed hierarchical results.

This script is intentionally dormant during A9.8-prep. Run it manually only
after all six configured seed trainings have completed.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


METRICS = (
    "binary_macro_f1",
    "binary_f1",
    "attack_family_macro_f1",
    "attack_family_accuracy",
    "rare_class_macro_f1",
    "attack_false_negatives",
    "benign_false_positives",
)
PER_CLASS_NAMES = (
    "Analysis",
    "Backdoor",
    "DoS",
    "Shellcode",
    "Worms",
    "Exploits",
    "Generic",
    "Reconnaissance",
    "Fuzzers",
)
HARD_CLASS_NAMES = ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _read_per_class_f1(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["class_name"]: float(row["f1"]) for row in csv.DictReader(handle)}


def _extract_seed_metrics(result_dir: Path) -> dict[str, Any]:
    metrics_path = result_dir / "test_metrics.json"
    per_class_path = result_dir / "per_class_attack_metrics.csv"
    missing = [str(path) for path in (metrics_path, per_class_path) if not path.exists()]
    if missing:
        return {"missing_files": missing}

    payload = _load_json(metrics_path)["test_metrics"]
    binary = payload["binary"]
    attack = payload["attack_family"]
    rare = payload["rare_class"]
    per_class_f1 = _read_per_class_f1(per_class_path)

    extracted = {
        "binary_macro_f1": float(binary["macro_f1"]),
        "binary_f1": float(binary["f1"]),
        "attack_family_macro_f1": float(attack["macro_f1_on_attack_rows"]),
        "attack_family_accuracy": float(attack["accuracy_on_attack_rows"]),
        "rare_class_macro_f1": float(rare["rare_class_macro_f1"]),
        "attack_false_negatives": int(binary["attack_false_negatives"]),
        "benign_false_positives": int(binary["confusion_matrix"]["fp"]),
        "missing_files": [],
    }
    for class_name in PER_CLASS_NAMES:
        extracted[f"per_class_f1_{class_name}"] = float(per_class_f1.get(class_name, 0.0))
    return extracted


def _summarize(values: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    seed_values = [
        {"seed": item["seed"], "value": item["metrics"][metric]}
        for item in values
        if not item["metrics"].get("missing_files")
    ]
    numeric = [entry["value"] for entry in seed_values]
    if not numeric:
        return {"mean": None, "std": None, "seed_values": seed_values}
    return {
        "mean": statistics.mean(numeric),
        "std": statistics.stdev(numeric) if len(numeric) > 1 else 0.0,
        "seed_values": seed_values,
    }


def _format_float(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def _write_outputs(summary: dict[str, Any], out_json: Path, out_csv: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["metric", "model_key", "mean", "std", "seed_values", "branch_minus_linear_delta"],
        )
        writer.writeheader()
        for metric, model_map in summary["metric_summary"].items():
            delta = summary["branch_minus_linear_delta"].get(metric)
            for model_key, stats in model_map.items():
                writer.writerow(
                    {
                        "metric": metric,
                        "model_key": model_key,
                        "mean": stats["mean"],
                        "std": stats["std"],
                        "seed_values": json.dumps(stats["seed_values"]),
                        "branch_minus_linear_delta": delta if model_key == "a9_7_branch" else "",
                    }
                )

    lines = [
        "# UNSW A9 vs A9.7 Multi-Seed Report",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Promotion Decision",
        "",
        f"- Promote A9.7 branch: `{summary['promotion_decision']['promote_a9_7_branch']}`",
        f"- Reason: {summary['promotion_decision']['reason']}",
        "",
        "## Headline Metrics",
        "",
        "| Metric | A9 linear mean | A9 linear std | A9.7 branch mean | A9.7 branch std | Branch minus linear |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric in METRICS:
        linear = summary["metric_summary"][metric]["a9_linear"]
        branch = summary["metric_summary"][metric]["a9_7_branch"]
        delta = summary["branch_minus_linear_delta"][metric]
        lines.append(
            "| "
            + " | ".join(
                [
                    metric,
                    _format_float(linear["mean"]),
                    _format_float(linear["std"]),
                    _format_float(branch["mean"]),
                    _format_float(branch["std"]),
                    _format_float(delta),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Missing Files",
            "",
            "```json",
            json.dumps(summary["missing_files"], indent=2),
            "```",
            "",
            "Generated by `secureids/evaluation/compare_multiseed_hierarchical.py`.",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _promotion_decision(metric_summary: dict[str, Any], missing_files: dict[str, Any]) -> dict[str, Any]:
    if any(missing_files.values()):
        return {
            "promote_a9_7_branch": False,
            "reason": "Missing seed result files; complete all six runs before deciding.",
        }

    delta = {
        metric: (
            metric_summary[metric]["a9_7_branch"]["mean"] - metric_summary[metric]["a9_linear"]["mean"]
        )
        for metric in metric_summary
        if metric_summary[metric]["a9_7_branch"]["mean"] is not None
        and metric_summary[metric]["a9_linear"]["mean"] is not None
    }

    attack_gain = delta["attack_family_macro_f1"] >= 0.015
    rare_safe = delta["rare_class_macro_f1"] >= -0.010
    binary_macro_safe = metric_summary["binary_macro_f1"]["a9_7_branch"]["mean"] >= 0.884
    binary_f1_safe = metric_summary["binary_f1"]["a9_7_branch"]["mean"] >= 0.905
    branch_fn_values = [
        entry["value"]
        for entry in metric_summary["attack_false_negatives"]["a9_7_branch"]["seed_values"]
    ]
    attack_fn_safe = all(value <= 2450 for value in branch_fn_values)
    branch_rare_values = [
        entry["value"]
        for entry in metric_summary["rare_class_macro_f1"]["a9_7_branch"]["seed_values"]
    ]
    no_rare_collapse = all(value >= 0.300 for value in branch_rare_values)
    hard_class_signal = any(
        delta.get(f"per_class_f1_{name}", 0.0) >= 0.005 for name in HARD_CLASS_NAMES
    )

    checks = {
        "attack_family_macro_f1_gain_at_least_0_015": attack_gain,
        "rare_class_macro_f1_not_worse_than_minus_0_010": rare_safe,
        "binary_macro_f1_mean_at_least_0_884": binary_macro_safe,
        "binary_f1_mean_at_least_0_905": binary_f1_safe,
        "all_branch_attack_false_negatives_at_or_below_2450": attack_fn_safe,
        "no_branch_seed_severe_rare_collapse": no_rare_collapse,
        "improvement_not_only_easy_classes": hard_class_signal,
        "no_missing_files": True,
    }
    promote = all(checks.values())
    reason = "All promotion criteria passed." if promote else "One or more promotion criteria failed."
    return {
        "promote_a9_7_branch": promote,
        "reason": reason,
        "checks": checks,
    }


def build_summary(config_path: Path, project_root: Path) -> dict[str, Any]:
    prep = _load_json(config_path)
    collected: dict[str, list[dict[str, Any]]] = {}
    missing_files: dict[str, Any] = {}

    for model in prep["models_compared"]:
        model_key = model["key"]
        collected[model_key] = []
        missing_files[model_key] = {}
        for run in model["seed_runs"]:
            result_dir = project_root / run["result_dir"]
            metrics = _extract_seed_metrics(result_dir)
            collected[model_key].append({"seed": run["seed"], "metrics": metrics})
            if metrics.get("missing_files"):
                missing_files[model_key][str(run["seed"])] = metrics["missing_files"]

    all_metrics = list(METRICS) + [f"per_class_f1_{name}" for name in PER_CLASS_NAMES]
    metric_summary = {
        metric: {
            model_key: _summarize(values, metric)
            for model_key, values in collected.items()
        }
        for metric in all_metrics
    }
    delta = {}
    for metric, model_map in metric_summary.items():
        linear = model_map["a9_linear"]["mean"]
        branch = model_map["a9_7_branch"]["mean"]
        delta[metric] = None if linear is None or branch is None else branch - linear

    status = "complete" if not any(missing_files.values()) else "incomplete_missing_files"
    summary = {
        "status": status,
        "task": "A9.8 multi-seed A9 linear vs A9.7 branch-capacity aggregation",
        "config": str(config_path),
        "metric_summary": metric_summary,
        "branch_minus_linear_delta": delta,
        "missing_files": missing_files,
        "promotion_decision": _promotion_decision(metric_summary, missing_files),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("results/audits/unsw_a9_8_multiseed_prep.json"),
        help="A9.8 prep audit JSON containing seed result paths.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    config_path = args.config if args.config.is_absolute() else project_root / args.config
    summary = build_summary(config_path, project_root)
    _write_outputs(
        summary,
        project_root / "results/audits/unsw_a9_vs_a9_7_multiseed_summary.json",
        project_root / "results/audits/unsw_a9_vs_a9_7_multiseed_summary.csv",
        project_root / "docs/UNSW_A9_VS_A9_7_MULTI_SEED_REPORT.md",
    )
    print(f"A9.8 multiseed aggregation status: {summary['status']}")
    print(f"Promote A9.7 branch: {summary['promotion_decision']['promote_a9_7_branch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
