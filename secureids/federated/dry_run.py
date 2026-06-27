"""FedAvg dry-run validation.

The dry-run validates configs, existing artifact references, and deterministic
client split planning. It does not load full feature matrices, train models,
evaluate on test data, create checkpoints, or create final metrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from secureids.federated.config import (
    EXPECTED_INPUT_DIMS,
    FederatedConfig,
    FederatedConfigError,
    load_federated_config,
    normalize_dataset_alias,
)
from secureids.federated.splitting import (
    ClientSplitError,
    plan_stratified_iid_client_distribution,
)


DRY_RUN_JSON_NAMES = {
    "unsw_nb15": "fedavg_dry_run_unsw_nb15.json",
    "cicids2018": "fedavg_dry_run_cicids2018.json",
}

DATASET_DISPLAY_NAMES = {
    "unsw_nb15": "UNSW-NB15",
    "cicids2018": "CICIDS2018",
}

MANIFEST_SAFETY_FIELDS = {
    "test_set_used_for_tuning": False,
    "preprocessing_safety_check_passed": True,
    "final_checkpoint": True,
    "no_federated_training": True,
    "no_attack_simulation": True,
    "no_xai": True,
}


def _project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _record_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: Any = None,
) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def _failed_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [check for check in checks if not check["passed"]]


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _find_key(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


def _load_feature_names(path: Path) -> list[str] | None:
    payload = _read_json_object(path)
    if payload is None:
        return None
    feature_names = payload.get("feature_names")
    if not isinstance(feature_names, list):
        return None
    return [str(name) for name in feature_names]


def _validate_processed_paths(
    project_root: Path,
    config: FederatedConfig,
    checks: list[dict[str, Any]],
) -> tuple[dict[str, str], list[str] | None, int | None]:
    data = config.raw["data"]
    processed_dir = _project_path(project_root, data["processed_dir"])
    processed_paths = {
        "processed_dir": str(processed_dir),
        "X_train": str(processed_dir / data["train_split"]["x"]),
        "y_train": str(processed_dir / data["train_split"]["y"]),
        "X_val": str(processed_dir / data["val_split"]["x"]),
        "y_val": str(processed_dir / data["val_split"]["y"]),
        "X_test": str(processed_dir / data["test_split"]["x"]),
        "y_test": str(processed_dir / data["test_split"]["y"]),
        "feature_names": str(processed_dir / "feature_names.json"),
        "label_mapping": str(processed_dir / "label_mapping.json"),
        "preprocessing_manifest": str(processed_dir / "preprocessing_manifest.json"),
    }
    _record_check(checks, "processed_dir_exists", processed_dir.exists(), str(processed_dir))
    for name, path_text in processed_paths.items():
        if name == "processed_dir":
            continue
        _record_check(checks, f"{name}_exists", Path(path_text).exists(), path_text)

    feature_names = _load_feature_names(Path(processed_paths["feature_names"]))
    _record_check(
        checks,
        "feature_names_json_loads_as_feature_names_key",
        feature_names is not None,
        processed_paths["feature_names"],
    )
    feature_count = len(feature_names) if feature_names is not None else None
    _record_check(
        checks,
        "feature_count_matches_input_dim",
        feature_count == config.input_dim,
        {"feature_count": feature_count, "input_dim": config.input_dim},
    )

    x_train_shape: list[int] | None = None
    x_train_path = Path(processed_paths["X_train"])
    if x_train_path.exists():
        try:
            x_train = np.load(x_train_path, mmap_mode="r")
            x_train_shape = [int(value) for value in x_train.shape]
            _record_check(
                checks,
                "X_train_shape_matches_input_dim",
                len(x_train_shape) == 2 and x_train_shape[1] == config.input_dim,
                x_train_shape,
            )
        except (OSError, ValueError) as error:
            _record_check(checks, "X_train_shape_matches_input_dim", False, str(error))

    return processed_paths, feature_names, x_train_shape[0] if x_train_shape else None


def _validate_centralized_references(
    project_root: Path,
    config: FederatedConfig,
    checks: list[dict[str, Any]],
) -> dict[str, str]:
    references = {
        name: str(_project_path(project_root, path))
        for name, path in config.raw["centralized_reference"].items()
    }
    for name, path_text in references.items():
        _record_check(checks, f"centralized_{name}_exists", Path(path_text).exists(), path_text)

    manifest = _read_json_object(Path(references["manifest"]))
    _record_check(checks, "centralized_manifest_readable", manifest is not None, references["manifest"])
    if manifest is not None:
        for field, expected in MANIFEST_SAFETY_FIELDS.items():
            actual = _find_key(manifest, field)
            _record_check(
                checks,
                f"manifest_{field}",
                actual is expected,
                {"actual": actual, "expected": expected},
            )
    return references


def _validate_output_paths(config: FederatedConfig, checks: list[dict[str, Any]]) -> dict[str, str]:
    outputs = {name: str(path) for name, path in config.raw["outputs"].items()}
    checkpoint = outputs.get("checkpoint", "")
    manifest = outputs.get("manifest", "")
    report = outputs.get("report", "")
    _record_check(
        checks,
        "planned_checkpoint_under_models_federated",
        checkpoint.startswith("models/federated/") and checkpoint.endswith(".pt"),
        checkpoint,
    )
    _record_check(
        checks,
        "planned_manifest_under_results_audits",
        manifest.startswith("results/audits/") and manifest.endswith(".json"),
        manifest,
    )
    _record_check(
        checks,
        "planned_report_under_docs",
        report.startswith("docs/") and report.endswith(".md"),
        report,
    )
    for name in ("round_history", "client_distribution", "client_logs", "confusion_matrix"):
        value = outputs.get(name, "")
        _record_check(
            checks,
            f"planned_{name}_is_csv",
            value.startswith("results/federated/") and value.endswith(".csv"),
            value,
        )
    test_metrics = outputs.get("test_metrics", "")
    _record_check(
        checks,
        "planned_test_metrics_is_json",
        test_metrics.startswith("results/federated/") and test_metrics.endswith(".json"),
        test_metrics,
    )
    return outputs


def _write_combined_markdown(project_root: Path) -> Path:
    report_path = project_root / "docs" / "FEDAVG_DRY_RUN_REPORT.md"
    lines = [
        "# FedAvg Dry-Run Report",
        "",
        "This report is generated only by `federated-dry-run`. It records dry-run validation status without training, checkpoint creation, final metric generation, or test evaluation.",
        "",
    ]
    for dataset in ("unsw_nb15", "cicids2018"):
        json_path = project_root / "results" / "audits" / DRY_RUN_JSON_NAMES[dataset]
        payload = _read_json_object(json_path) if json_path.exists() else None
        lines.append(f"## {DATASET_DISPLAY_NAMES[dataset]}")
        lines.append("")
        if payload is None:
            lines.append("Status: `NOT RUN YET`")
            lines.append("")
            continue
        lines.append(f"Status: `{payload.get('status')}`")
        lines.append(f"- Config: `{payload.get('config_path')}`")
        lines.append(f"- Algorithm: `{payload.get('algorithm')}`")
        lines.append(f"- Clients: `{payload.get('num_clients')}`")
        lines.append(f"- Feature count: `{payload.get('feature_count')}`")
        lines.append(f"- Train labels: `{payload.get('train_label_count')}`")
        failed = payload.get("failed_checks") or []
        if failed:
            lines.append(f"- Failed checks: `{len(failed)}`")
        else:
            lines.append("- Failed checks: `0`")
        lines.append("")
    lines.extend(
        [
            "## Safety Confirmation",
            "",
            "- No federated training is run by dry-run validation.",
            "- No federated checkpoints are created.",
            "- No final federated metrics are generated.",
            "- No test evaluation is run.",
            "- No security, attack, robust aggregation, XAI, or dashboard work is triggered.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run_fedavg_dry_run(
    dataset: str,
    config_path: str | Path,
    project_root: Path,
) -> dict[str, Any]:
    """Run FedAvg dry-run validation and write dry-run audit outputs."""

    checks: list[dict[str, Any]] = []
    normalized_dataset = normalize_dataset_alias(dataset)
    config = load_federated_config(config_path, project_root=project_root)
    _record_check(
        checks,
        "dataset_argument_matches_config",
        normalized_dataset == config.dataset,
        {"argument": normalized_dataset, "config": config.dataset},
    )
    _record_check(checks, "task_binary", config.task == "binary", config.task)
    _record_check(
        checks,
        "model_architecture_secureidsnet",
        config.architecture == "SecureIDSNet",
        config.architecture,
    )
    _record_check(
        checks,
        "input_dim_expected",
        config.input_dim == EXPECTED_INPUT_DIMS.get(config.dataset),
        {"actual": config.input_dim, "expected": EXPECTED_INPUT_DIMS.get(config.dataset)},
    )
    _record_check(checks, "algorithm_fedavg", config.algorithm == "FedAvg", config.algorithm)
    _record_check(checks, "client_count_valid", config.num_clients > 0, config.num_clients)
    _record_check(
        checks,
        "client_split_stratified_iid",
        config.client_split == "stratified_iid",
        config.client_split,
    )

    processed_paths, feature_names, x_train_rows = _validate_processed_paths(
        project_root, config, checks
    )
    centralized_refs = _validate_centralized_references(project_root, config, checks)
    output_paths = _validate_output_paths(config, checks)

    client_distribution: list[dict[str, float | int | str]] = []
    train_label_count: int | None = None
    y_train_path = Path(processed_paths["y_train"])
    if y_train_path.exists():
        try:
            y_train = np.load(y_train_path, mmap_mode="r")
            train_label_count = int(y_train.shape[0])
            client_distribution = plan_stratified_iid_client_distribution(
                y_train=y_train,
                num_clients=config.num_clients,
                seed=config.seed,
            )
            planned_total = sum(int(item["total_samples"]) for item in client_distribution)
            _record_check(
                checks,
                "client_sample_counts_sum_to_y_train",
                planned_total == train_label_count,
                {"planned_total": planned_total, "train_label_count": train_label_count},
            )
            _record_check(
                checks,
                "X_train_rows_match_y_train_count",
                x_train_rows is None or x_train_rows == train_label_count,
                {"X_train_rows": x_train_rows, "train_label_count": train_label_count},
            )
            _record_check(
                checks,
                "client_distribution_tracked",
                len(client_distribution) == config.num_clients,
                {"clients": len(client_distribution), "expected": config.num_clients},
            )
        except (OSError, ValueError, ClientSplitError) as error:
            _record_check(checks, "client_split_can_be_planned", False, str(error))
    else:
        _record_check(checks, "client_split_can_be_planned", False, str(y_train_path))

    _record_check(checks, "no_test_labels_used_for_client_split", True, "y_train only")
    _record_check(checks, "no_training_executed", True, None)
    _record_check(checks, "no_checkpoint_created", True, None)
    _record_check(checks, "no_final_metrics_generated", True, None)
    _record_check(checks, "no_test_evaluation_run", True, None)
    _record_check(checks, "no_security_attack_robust_xai_dashboard", True, None)

    failed = _failed_checks(checks)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failed else "FAIL",
        "dataset": config.dataset,
        "config_path": str(config.path),
        "model": {
            "architecture": config.architecture,
            "output_dim": config.raw["model"]["output_dim"],
        },
        "input_dim": config.input_dim,
        "algorithm": config.algorithm,
        "num_clients": config.num_clients,
        "seed": config.seed,
        "client_split": config.client_split,
        "processed_paths_checked": processed_paths,
        "centralized_references_checked": centralized_refs,
        "feature_count": len(feature_names) if feature_names is not None else None,
        "train_label_count": train_label_count,
        "client_distribution": client_distribution,
        "output_paths_planned": output_paths,
        "checks": checks,
        "failed_checks": failed,
        "safety_confirmation": {
            "training_run": False,
            "checkpoint_created": False,
            "metrics_created": False,
            "test_evaluation_run": False,
            "no_test_leakage": True,
            "security_attack_xai_dashboard_started": False,
        },
    }

    output_path = project_root / "results" / "audits" / DRY_RUN_JSON_NAMES[config.dataset]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path = _write_combined_markdown(project_root)
    payload["outputs_written"] = {
        "json": str(output_path),
        "markdown": str(report_path),
    }
    return payload
