"""Centralized baseline artifact validation.

This module validates existing finalized centralized baseline artifacts without
loading training arrays, importing PyTorch, running evaluation, or mutating any
checkpoint/metric/history/confusion/manifest artifacts. The only outputs it
creates are the validation JSON and markdown report for this check.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_DATASETS: tuple[dict[str, Any], ...] = (
    {
        "key": "unsw_nb15",
        "display_name": "UNSW-NB15",
        "dataset": "unsw_nb15",
        "task": "binary",
        "model": "SecureIDSNet",
        "input_dim": 190,
        "artifacts": {
            "checkpoint": "models/final/final_unsw_binary.pt",
            "metrics": "results/final/centralized/unsw_test_metrics.json",
            "history": "results/final/centralized/unsw_training_history.csv",
            "confusion_matrix": "results/final/centralized/unsw_confusion_matrix.csv",
            "manifest": "results/audits/training_manifest_unsw_nb15.json",
        },
    },
    {
        "key": "cicids2018",
        "display_name": "CICIDS2018",
        "dataset": "cicids2018",
        "task": "binary",
        "model": "SecureIDSNet",
        "input_dim": 77,
        "artifacts": {
            "checkpoint": "models/final/final_cicids_binary.pt",
            "metrics": "results/final/centralized/cicids_test_metrics.json",
            "history": "results/final/centralized/cicids_training_history.csv",
            "confusion_matrix": "results/final/centralized/cicids_confusion_matrix.csv",
            "manifest": "results/audits/training_manifest_cicids2018.json",
        },
    },
)

EXPECTED_SAFETY_METADATA: dict[str, bool] = {
    "test_set_used_for_tuning": False,
    "preprocessing_safety_check_passed": True,
    "no_federated_training": True,
    "no_attack_simulation": True,
    "no_xai": True,
    "final_checkpoint": True,
}

VALIDATION_JSON = Path("results/audits/centralized_baseline_validation.json")
VALIDATION_DOC = Path("docs/CENTRALIZED_BASELINE_VALIDATION.md")
TRAINING_REPORT = Path("docs/CENTRALIZED_TRAINING_REPORT.md")


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        return None, str(error)
    except json.JSONDecodeError as error:
        return None, f"Invalid JSON: {error}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object."
    return payload, None


def _find_key(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_key(item, key)
            if found is not None:
                return found
    return None


def _find_any_key(payload: Any, keys: tuple[str, ...]) -> Any:
    for key in keys:
        found = _find_key(payload, key)
        if found is not None:
            return found
    return None


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _model_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        nested = _find_any_key(value, ("name", "class_name", "architecture", "model_name"))
        return _model_name(nested)
    return None


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "actual": actual,
        "expected": expected,
        "passed": actual == expected,
    }


def _check_dataset(project_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    artifacts = {
        name: str(project_root / relative)
        for name, relative in spec["artifacts"].items()
    }
    artifact_checks = [
        {
            "name": f"{name}_exists",
            "path": path,
            "passed": Path(path).exists(),
        }
        for name, path in artifacts.items()
    ]

    manifest_path = Path(artifacts["manifest"])
    manifest, manifest_error = (
        _read_json(manifest_path) if manifest_path.exists() else (None, "Manifest missing.")
    )

    manifest_checks: list[dict[str, Any]] = []
    if manifest is not None:
        actual_model = _model_name(
            _find_any_key(manifest, ("model", "model_name", "architecture"))
        )
        manifest_checks.extend(
            [
                _check_equal("dataset", _find_key(manifest, "dataset"), spec["dataset"]),
                _check_equal("task", _find_key(manifest, "task"), spec["task"]),
                _check_equal("model", actual_model, spec["model"]),
                _check_equal(
                    "input_dim",
                    _coerce_int(_find_any_key(manifest, ("input_dim", "detected_input_dim"))),
                    spec["input_dim"],
                ),
            ]
        )
        for key, expected in EXPECTED_SAFETY_METADATA.items():
            manifest_checks.append(_check_equal(key, _find_key(manifest, key), expected))
    else:
        manifest_checks.append(
            {
                "name": "manifest_readable",
                "actual": manifest_error,
                "expected": "readable JSON object",
                "passed": False,
            }
        )

    passed = all(check["passed"] for check in artifact_checks + manifest_checks)
    return {
        "dataset": spec["dataset"],
        "display_name": spec["display_name"],
        "expected": {
            "task": spec["task"],
            "model": spec["model"],
            "input_dim": spec["input_dim"],
        },
        "artifacts": artifacts,
        "artifact_checks": artifact_checks,
        "manifest_checks": manifest_checks,
        "status": "PASS" if passed else "FAIL",
    }


def _check_training_report(project_root: Path) -> dict[str, Any]:
    report_path = project_root / TRAINING_REPORT
    exists = report_path.exists()
    text = ""
    if exists:
        text = report_path.read_text(encoding="utf-8").lower()
    contains_unsw = "unsw" in text
    contains_cicids = "cicids" in text
    contains_completion_language = "complete" in text or "completed" in text
    passed = exists and contains_unsw and contains_cicids and contains_completion_language
    return {
        "path": str(report_path),
        "exists": exists,
        "contains_unsw": contains_unsw,
        "contains_cicids": contains_cicids,
        "contains_completion_language": contains_completion_language,
        "status": "PASS" if passed else "FAIL",
    }


def _write_validation_doc(project_root: Path, payload: dict[str, Any]) -> Path:
    output_path = project_root / VALIDATION_DOC
    lines = [
        "# Centralized Baseline Validation",
        "",
        f"Status: `{payload['overall_status']}`",
        "",
        "This report validates existing centralized baseline artifacts only. It does not run training, retraining, model evaluation, preprocessing, federated learning, attack simulation, XAI, dashboard work, or Git operations.",
        "",
        "## Dataset Checks",
        "",
    ]
    for result in payload["datasets"]:
        lines.extend(
            [
                f"### {result['display_name']}",
                "",
                f"- Status: `{result['status']}`",
                f"- Expected dataset/task/model/input_dim: `{result['dataset']}` / `{result['expected']['task']}` / `{result['expected']['model']}` / `{result['expected']['input_dim']}`",
                "- Artifact existence checks:",
            ]
        )
        for check in result["artifact_checks"]:
            lines.append(f"  - `{check['name']}`: `{check['passed']}`")
        lines.append("- Manifest checks:")
        for check in result["manifest_checks"]:
            lines.append(
                f"  - `{check['name']}`: `{check['passed']}` "
                f"(actual: `{check['actual']}`, expected: `{check['expected']}`)"
            )
        lines.append("")

    report_check = payload["training_report_check"]
    lines.extend(
        [
            "## Training Report Check",
            "",
            f"- Path: `{report_check['path']}`",
            f"- Exists: `{report_check['exists']}`",
            f"- Contains UNSW: `{report_check['contains_unsw']}`",
            f"- Contains CICIDS: `{report_check['contains_cicids']}`",
            f"- Contains completion language: `{report_check['contains_completion_language']}`",
            f"- Status: `{report_check['status']}`",
            "",
            "## Safety Confirmation",
            "",
            "- No training was run.",
            "- No retraining was run.",
            "- No model evaluation was run.",
            "- No checkpoints, metrics, histories, confusion matrices, or training manifests were modified.",
            "- No datasets, splits, preprocessing outputs, preprocessing artifacts, thresholds, or model architecture were changed.",
            "- No federated learning, security, attack, XAI, dashboard, Git commit, or Git push work was performed.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def run_centralized_baseline_validation(project_root: Path) -> dict[str, Any]:
    """Validate existing centralized baseline artifacts and write validation logs."""

    dataset_results = [
        _check_dataset(project_root=project_root, spec=spec)
        for spec in EXPECTED_DATASETS
    ]
    training_report_check = _check_training_report(project_root)
    overall_passed = all(result["status"] == "PASS" for result in dataset_results)
    overall_passed = overall_passed and training_report_check["status"] == "PASS"

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASS" if overall_passed else "FAIL",
        "datasets": dataset_results,
        "training_report_check": training_report_check,
        "safety_confirmation": {
            "training_run": False,
            "retraining_run": False,
            "evaluation_run": False,
            "checkpoints_modified": False,
            "metrics_modified": False,
            "histories_modified": False,
            "confusion_matrices_modified": False,
            "training_manifests_modified": False,
            "raw_data_modified": False,
            "processed_arrays_modified": False,
            "preprocessing_artifacts_modified": False,
            "model_architecture_modified": False,
            "thresholds_modified": False,
            "federated_security_attack_xai_dashboard_started": False,
            "git_commit_or_push": False,
        },
        "outputs": {
            "json": str(project_root / VALIDATION_JSON),
            "markdown": str(project_root / VALIDATION_DOC),
        },
    }

    json_path = project_root / VALIDATION_JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_validation_doc(project_root=project_root, payload=payload)
    return payload
