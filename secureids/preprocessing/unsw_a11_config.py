"""Config validation for the UNSW A11 Enhanced Feature Protocol.

This module is intentionally torch-free and side-effect free. Loading a config
must never run preprocessing, create arrays, create checkpoints, or touch final
artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - environment dependent
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET = "unsw_nb15"
TASK = "preprocessing"
STATUS = "not_run_yet"
PROTOCOL_NAME = "UNSW A11 Enhanced Feature Protocol"
EXPERIMENT = "unsw_a11_enhanced_feature_protocol"
A11_PROCESSED_PREFIX = "data/processed/unsw_a11_enhanced"
A11_PREPROCESSOR_PREFIX = "models/experiments/preprocessors/unsw_a11_enhanced"
A11_AUDIT_DIR = "results/audits"
A9_CHECKPOINT = "models/final/final_unsw_hierarchical.pt"

REQUIRED_KEYS = (
    "dataset",
    "task",
    "status",
    "protocol_name",
    "experiment",
    "source_protocol",
    "canonical_split",
    "target_columns",
    "drop_columns",
    "categorical_columns",
    "taxonomy_config_path",
    "feature_protocol",
    "planned_outputs",
    "baseline_reference",
    "safety",
)

REQUIRED_PLANNED_OUTPUT_KEYS = (
    "processed_data_dir",
    "hierarchical_data_dir",
    "binary_data_dir",
    "preprocessor_dir",
    "preprocessor_artifact",
    "preprocessing_audit",
    "feature_inventory_csv",
    "category_inventory_csv",
    "separability_diagnostics_csv",
    "preprocessing_manifest_json",
    "feature_names_json",
    "attack_family_label_mapping_json",
)


class UNSWA11ConfigError(ValueError):
    """Raised when an A11 preprocessing config is unsafe or malformed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise UNSWA11ConfigError(message)


def normalized_relative_path(path_str: str, label: str) -> str:
    """Validate and normalize a project-relative path."""

    normalized = str(path_str).replace("\\", "/").strip()
    path = Path(normalized)
    _require(bool(normalized), f"{label} must not be empty.")
    _require(not path.is_absolute(), f"{label} must be project-relative.")
    _require(":" not in normalized, f"{label} must not include a drive or URI prefix.")
    _require(not normalized.startswith("/"), f"{label} must be project-relative.")
    _require(".." not in path.parts, f"{label} must not contain parent traversal.")
    return normalized.rstrip("/")


def is_final_path(path_str: str) -> bool:
    normalized = str(path_str).replace("\\", "/").lstrip("./")
    return normalized.startswith("models/final") or normalized.startswith("results/final")


def safe_a11_path(path_str: str, label: str) -> str:
    normalized = normalized_relative_path(path_str, label)
    _require(not is_final_path(normalized), f"{label} must not target models/final or results/final.")
    return normalized


def _require_prefix(path_str: str, prefix: str, label: str) -> None:
    normalized = path_str.rstrip("/")
    prefix = prefix.rstrip("/")
    _require(
        normalized == prefix or normalized.startswith(prefix + "/"),
        f"{label} must stay under {prefix!r}, got {path_str!r}.",
    )


@dataclass(frozen=True)
class UNSWA11PreprocessingConfig:
    path: Path
    dataset: str
    task: str
    status: str
    protocol_name: str
    experiment: str
    canonical_split: dict[str, Any]
    target_columns: dict[str, str]
    drop_columns: list[str]
    categorical_columns: list[str]
    taxonomy_config_path: str
    feature_protocol: dict[str, Any]
    planned_outputs: dict[str, str]
    baseline_reference: dict[str, Any]
    safety: dict[str, Any]
    raw: dict[str, Any]
    project_root: Path = field(default=PROJECT_ROOT)

    def resolve(self, path_str: str | Path) -> Path:
        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:  # pragma: no cover - depends on local environment
        raise UNSWA11ConfigError("PyYAML is required to load A11 configs.")
    if not path.exists():
        raise UNSWA11ConfigError(f"A11 config not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _require(isinstance(loaded, dict), f"A11 config root must be a mapping: {path}")
    return loaded


def load_unsw_a11_preprocessing_config(
    path: str | Path,
    project_root: Path | None = None,
) -> UNSWA11PreprocessingConfig:
    """Load and validate the dry A11 preprocessing config."""

    config_path = Path(path)
    raw = _load_yaml(config_path)
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    _require(not missing, f"A11 config missing keys: {sorted(missing)}")

    _require(str(raw["dataset"]) == DATASET, f"dataset must be {DATASET!r}.")
    _require(str(raw["task"]) == TASK, f"task must be {TASK!r}.")
    _require(str(raw["status"]) == STATUS, f"status must remain {STATUS!r}.")
    _require(
        str(raw["protocol_name"]) == PROTOCOL_NAME,
        f"protocol_name must be {PROTOCOL_NAME!r}.",
    )
    _require(str(raw["experiment"]) == EXPERIMENT, f"experiment must be {EXPERIMENT!r}.")

    canonical_split = raw["canonical_split"]
    _require(isinstance(canonical_split, dict), "canonical_split must be a mapping.")
    train_source = canonical_split.get("train_source", {})
    test_source = canonical_split.get("test_source", {})
    validation = canonical_split.get("validation", {})
    expected_rows = canonical_split.get("expected_split_rows", {})
    _require(
        str(train_source.get("local_file")).replace("\\", "/")
        == "data/raw/unsw_nb15/UNSW_NB15_testing-set.csv",
        "canonical train source must be the corrected 175341-row local testing-set CSV.",
    )
    _require(int(train_source.get("expected_rows")) == 175341, "canonical train rows must be 175341.")
    _require(
        str(test_source.get("local_file")).replace("\\", "/")
        == "data/raw/unsw_nb15/UNSW_NB15_training-set.csv",
        "canonical test source must be the corrected 82332-row local training-set CSV.",
    )
    _require(int(test_source.get("expected_rows")) == 82332, "canonical test rows must be 82332.")
    _require(
        str(validation.get("derived_from")) == "canonical_train_source_only",
        "validation must be derived only from the canonical train source.",
    )
    _require(int(expected_rows.get("train")) == 149039, "expected train split rows must be 149039.")
    _require(int(expected_rows.get("val")) == 26302, "expected val split rows must be 26302.")
    _require(int(expected_rows.get("test")) == 82332, "expected test split rows must be 82332.")

    target_columns = raw["target_columns"]
    _require(isinstance(target_columns, dict), "target_columns must be a mapping.")
    _require(target_columns.get("binary_label") == "label", "binary_label must be label.")
    _require(target_columns.get("attack_family_label") == "attack_cat", "attack_family_label must be attack_cat.")

    drop_columns = [str(column) for column in raw["drop_columns"]]
    categorical_columns = [str(column) for column in raw["categorical_columns"]]
    _require(drop_columns == ["id", "label", "attack_cat"], "drop_columns must remove id, label, and attack_cat.")
    _require(categorical_columns == ["proto", "service", "state"], "categorical_columns must be proto/service/state.")

    feature_protocol = raw["feature_protocol"]
    _require(isinstance(feature_protocol, dict), "feature_protocol must be a mapping.")
    for flag in (
        "train_only_fitting",
        "no_test_fitting",
        "no_test_label_feature_selection",
        "no_test_tuning",
        "numeric_only_scaling",
        "one_hot_columns_not_scaled",
    ):
        _require(feature_protocol.get(flag) is True, f"feature_protocol.{flag} must be true.")
    _require(
        feature_protocol.get("median_imputation", {}).get("fit_on") == "train_only",
        "median imputation must fit on train_only.",
    )
    scaling = feature_protocol.get("numeric_scaling", {})
    _require(scaling.get("fit_on") == "train_only", "numeric scaling must fit on train_only.")
    _require(scaling.get("applies_to") == "numeric_columns_only", "scaling must apply to numeric columns only.")
    encoding = feature_protocol.get("categorical_encoding", {})
    _require(encoding.get("fit_on") == "train_only", "categorical encoding must fit on train_only.")
    _require(encoding.get("scale_encoded_columns") is False, "one-hot encoded columns must not be scaled.")
    grouping = feature_protocol.get("categorical_grouping", {})
    _require(grouping.get("enabled") is True, "categorical grouping must be enabled.")
    _require(grouping.get("fit_on") == "train_only", "categorical grouping must fit on train_only.")
    proto = grouping.get("proto", {})
    _require(proto.get("enabled") is True, "proto grouping must be enabled.")
    _require(proto.get("method") in {"min_frequency_other_bucket", "top_k_other_bucket"}, "unsupported proto grouping method.")
    if proto.get("method") == "min_frequency_other_bucket":
        _require(int(proto.get("min_frequency", 0)) > 1, "proto.min_frequency must be > 1.")
    if proto.get("method") == "top_k_other_bucket":
        _require(int(proto.get("top_k", 0)) > 0, "proto.top_k must be > 0.")
    _require(str(proto.get("other_bucket_name", "")), "proto.other_bucket_name is required.")

    planned_outputs_raw = raw["planned_outputs"]
    _require(isinstance(planned_outputs_raw, dict), "planned_outputs must be a mapping.")
    missing_outputs = [key for key in REQUIRED_PLANNED_OUTPUT_KEYS if key not in planned_outputs_raw]
    _require(not missing_outputs, f"A11 planned_outputs missing keys: {sorted(missing_outputs)}")

    planned_outputs: dict[str, str] = {}
    for key, value in planned_outputs_raw.items():
        planned_outputs[str(key)] = safe_a11_path(str(value), f"planned_outputs.{key}")

    for key in ("processed_data_dir", "hierarchical_data_dir", "binary_data_dir", "preprocessing_manifest_json", "feature_names_json", "attack_family_label_mapping_json"):
        _require_prefix(planned_outputs[key], A11_PROCESSED_PREFIX, f"planned_outputs.{key}")
    for key in ("preprocessor_dir", "preprocessor_artifact"):
        _require_prefix(planned_outputs[key], A11_PREPROCESSOR_PREFIX, f"planned_outputs.{key}")
    for key in ("preprocessing_audit", "feature_inventory_csv", "category_inventory_csv", "separability_diagnostics_csv"):
        _require_prefix(planned_outputs[key], A11_AUDIT_DIR, f"planned_outputs.{key}")
        _require(
            Path(planned_outputs[key]).name.startswith("unsw_a11"),
            f"planned_outputs.{key} must use an unsw_a11 audit filename.",
        )
    _require(planned_outputs["preprocessor_artifact"].endswith(".joblib"), "preprocessor_artifact must be a .joblib path.")

    baseline = raw["baseline_reference"]
    _require(isinstance(baseline, dict), "baseline_reference must be a mapping.")
    _require(
        str(baseline.get("checkpoint")).replace("\\", "/") == A9_CHECKPOINT,
        "baseline_reference.checkpoint must point to the frozen A9 checkpoint.",
    )
    _require(float(baseline.get("binary_macro_f1")) == 0.894488, "A9 binary baseline mismatch.")
    _require(float(baseline.get("attack_family_macro_f1")) == 0.500429, "A9 attack-family baseline mismatch.")
    _require(float(baseline.get("rare_class_macro_f1")) == 0.385669, "A9 rare baseline mismatch.")

    safety = raw["safety"]
    _require(isinstance(safety, dict), "safety must be a mapping.")
    for flag in (
        "no_overwrite_by_default",
    ):
        _require(safety.get(flag) is True, f"safety.{flag} must be true.")
    for flag in (
        "preprocessing_run",
        "training_run",
        "evaluation_run",
        "allow_overwrite",
        "overwrite_a9_artifacts",
        "overwrite_final_models",
        "overwrite_final_results",
        "refit_scaler_on_test",
        "test_label_feature_selection",
        "test_tuning",
        "taxonomy_change",
        "hide_weak_classes",
        "fake_metrics",
        "git_action",
        "v1_modified",
    ):
        _require(safety.get(flag) is False, f"safety.{flag} must be false.")

    return UNSWA11PreprocessingConfig(
        path=config_path,
        dataset=DATASET,
        task=TASK,
        status=STATUS,
        protocol_name=PROTOCOL_NAME,
        experiment=EXPERIMENT,
        canonical_split=dict(canonical_split),
        target_columns={str(key): str(value) for key, value in target_columns.items()},
        drop_columns=drop_columns,
        categorical_columns=categorical_columns,
        taxonomy_config_path=safe_a11_path(str(raw["taxonomy_config_path"]), "taxonomy_config_path"),
        feature_protocol=dict(feature_protocol),
        planned_outputs=planned_outputs,
        baseline_reference=dict(baseline),
        safety=dict(safety),
        raw=raw,
        project_root=Path(project_root) if project_root is not None else PROJECT_ROOT,
    )
