"""Torch-free config loading for hierarchical training plans.

Task A6 is design/config/smoke-preparation only. This module validates config
shape and safety flags; it does not train, evaluate, save checkpoints, or write
metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - local environment dependent
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_DATASETS = {
    "cicids2018": {"input_dim": 77, "attack_head_dim": 14},
    # A8.8: UNSW hierarchical input_dim is 192 after the split-protocol correction
    # (train on the canonical 175,341-row partition). Legacy pre-correction was 190.
    "unsw_nb15": {"input_dim": 192, "attack_head_dim": 9},
}
MODEL_NAME = "SecureIDSHierarchicalAdvancedNet"
FULL_TASK = "hierarchical"
SMOKE_TASK = "hierarchical_smoke"
CICIDS_EXPERIMENT_PREFIX = "cicids_hierarchical_exp"
UNSW_A11_EXPERIMENT = "unsw_a11_enhanced_feature_protocol_seed42"
A9_8_MULTI_SEED_SEEDS = ("42", "123", "999")
A9_8_MULTI_SEED_VARIANTS = {
    "a9_linear": {
        "checkpoint_template": "models/final/multiseed/unsw_a9_linear_seed{seed}.pt",
        "result_dir_template": "results/final/hierarchical/multiseed/unsw_a9_linear_seed{seed}",
        "manifest_template": (
            "results/audits/multiseed/"
            "hierarchical_training_manifest_unsw_a9_linear_seed{seed}.json"
        ),
        "report_template": "docs/multiseed/HIERARCHICAL_TRAINING_REPORT_UNSW_A9_LINEAR_SEED{seed}.md",
    },
    "a9_7_branch": {
        "checkpoint_template": "models/final/multiseed/unsw_a9_7_branch_seed{seed}.pt",
        "result_dir_template": "results/final/hierarchical/multiseed/unsw_a9_7_branch_seed{seed}",
        "manifest_template": (
            "results/audits/multiseed/"
            "hierarchical_training_manifest_unsw_a9_7_branch_seed{seed}.json"
        ),
        "report_template": "docs/multiseed/HIERARCHICAL_TRAINING_REPORT_UNSW_A9_7_BRANCH_SEED{seed}.md",
    },
}

FULL_REQUIRED_KEYS = (
    "dataset",
    "task",
    "model_name",
    "hierarchical_data_dir",
    "feature_names_path",
    "attack_family_label_mapping_path",
    "preprocessing_manifest_path",
    "readiness_json",
    "taxonomy_config",
    "input_dim",
    "attack_head_dim",
    "model",
    "loss",
    "class_imbalance",
    "training",
    "checkpoint_selection",
    "metrics",
    "outputs",
    "safety",
)
SMOKE_REQUIRED_KEYS = (
    "dataset",
    "task",
    "base_config",
    "model_name",
    "hierarchical_data_dir",
    "input_dim",
    "attack_head_dim",
    "smoke",
    "safety",
)


class HierarchicalTrainingConfigError(ValueError):
    """Raised when a hierarchical training config fails validation."""


@dataclass(frozen=True)
class HierarchicalTrainingConfig:
    path: Path
    dataset: str
    task: str
    model_name: str
    hierarchical_data_dir: str
    feature_names_path: str
    attack_family_label_mapping_path: str
    preprocessing_manifest_path: str
    readiness_json: str
    taxonomy_config: str
    input_dim: int
    attack_head_dim: int
    outputs: dict[str, str]
    raw: dict[str, Any]
    project_root: Path = field(default=PROJECT_ROOT)

    def resolve(self, path_str: str) -> Path:
        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


@dataclass(frozen=True)
class HierarchicalSmokeConfig:
    path: Path
    dataset: str
    task: str
    base_config: str
    model_name: str
    hierarchical_data_dir: str
    input_dim: int
    attack_head_dim: int
    smoke: dict[str, Any]
    safety: dict[str, Any]
    raw: dict[str, Any]
    project_root: Path = field(default=PROJECT_ROOT)

    def resolve(self, path_str: str) -> Path:
        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HierarchicalTrainingConfigError(message)


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:  # pragma: no cover - depends on environment
        raise HierarchicalTrainingConfigError("PyYAML is required.")
    if not path.exists():
        raise HierarchicalTrainingConfigError(f"Config not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _require(isinstance(loaded, dict), f"Config root must be a mapping: {path}")
    return loaded


def _validate_dataset_dims(raw: dict[str, Any]) -> tuple[str, int, int]:
    dataset = str(raw.get("dataset"))
    _require(
        dataset in SUPPORTED_DATASETS,
        f"dataset must be one of {sorted(SUPPORTED_DATASETS)}, got {dataset!r}",
    )
    input_dim = int(raw.get("input_dim"))
    attack_head_dim = int(raw.get("attack_head_dim"))
    expected = SUPPORTED_DATASETS[dataset]
    _require(
        input_dim == expected["input_dim"],
        f"{dataset} input_dim must be {expected['input_dim']}, got {input_dim}",
    )
    _require(
        attack_head_dim == expected["attack_head_dim"],
        (
            f"{dataset} attack_head_dim must be "
            f"{expected['attack_head_dim']}, got {attack_head_dim}"
        ),
    )
    return dataset, input_dim, attack_head_dim


def _validate_common_model(raw: dict[str, Any]) -> None:
    _require(
        str(raw.get("model_name")) == MODEL_NAME,
        f"model_name must be {MODEL_NAME!r}.",
    )
    model = raw.get("model", {})
    if isinstance(model, dict):
        _require(
            str(model.get("architecture", MODEL_NAME)) == MODEL_NAME,
            f"model.architecture must be {MODEL_NAME!r}.",
        )


def _is_final_path(path_str: str) -> bool:
    normalized = str(path_str).replace("\\", "/").lstrip("./")
    return normalized.startswith("results/final") or normalized.startswith("models/final")


def _safe_relative_path(path_str: str, label: str) -> str:
    normalized = str(path_str).replace("\\", "/").strip()
    path = Path(normalized)
    _require(normalized, f"{label} must not be empty.")
    _require(not path.is_absolute(), f"{label} must be a relative path.")
    _require(":" not in normalized, f"{label} must not include a drive or URI prefix.")
    _require(".." not in path.parts, f"{label} must not contain parent traversal.")
    _require(not normalized.startswith("/"), f"{label} must be project-relative.")
    return normalized.rstrip("/")


def _regular_hierarchical_checkpoint_allowed(checkpoint: str) -> bool:
    checkpoint_name = Path(checkpoint).name
    return (
        checkpoint.startswith("models/final/final_")
        and checkpoint_name.endswith(".pt")
        and "_hierarchical" in checkpoint_name
    )


def _is_cicids_hierarchical_experiment_config(raw: dict[str, Any], checkpoint: str) -> bool:
    experiment = str(raw.get("experiment", ""))
    return (
        str(raw.get("dataset")) == "cicids2018"
        and (
            experiment.startswith(CICIDS_EXPERIMENT_PREFIX)
            or checkpoint.startswith(f"models/experiments/{CICIDS_EXPERIMENT_PREFIX}")
        )
    )


def _is_unsw_a11_experiment_config(raw: dict[str, Any], checkpoint: str) -> bool:
    experiment = str(raw.get("experiment", ""))
    return (
        str(raw.get("dataset")) == "unsw_nb15"
        and experiment == UNSW_A11_EXPERIMENT
        and checkpoint == f"models/experiments/{UNSW_A11_EXPERIMENT}.pt"
    )


def _validate_unsw_a11_experiment_outputs(
    raw: dict[str, Any],
    outputs: dict[str, Any],
) -> None:
    _require(str(raw.get("experiment")) == UNSW_A11_EXPERIMENT, "unexpected UNSW A11 experiment name.")
    _require(str(raw.get("dataset")) == "unsw_nb15", "UNSW A11 requires unsw_nb15.")
    _require(str(raw.get("task")) == FULL_TASK, "UNSW A11 requires hierarchical task.")
    _require(int(raw.get("input_dim")) == 192, "UNSW A11 requires input_dim 192.")
    _require(int(raw.get("attack_head_dim")) == 9, "UNSW A11 requires attack_head_dim 9.")
    _require(
        str(raw.get("hierarchical_data_dir")).replace("\\", "/")
        == "data/processed/unsw_a11_enhanced/hierarchical",
        "UNSW A11 must use A11 processed hierarchical data.",
    )
    _require(
        str(raw.get("protocol_name")) == "UNSW A11 Enhanced Feature Protocol",
        "UNSW A11 protocol_name must be explicit.",
    )

    result_dir = f"results/experiments/{UNSW_A11_EXPERIMENT}"
    required_exact_outputs = {
        "checkpoint": f"models/experiments/{UNSW_A11_EXPERIMENT}.pt",
        "result_dir": result_dir,
        "training_history_csv": f"{result_dir}/training_history.csv",
        "test_metrics_json": f"{result_dir}/test_metrics.json",
        "binary_confusion_matrix_csv": f"{result_dir}/binary_confusion_matrix.csv",
        "attack_family_confusion_matrix_csv": f"{result_dir}/attack_family_confusion_matrix.csv",
        "per_class_attack_metrics_csv": f"{result_dir}/per_class_attack_metrics.csv",
        "rare_class_metrics_csv": f"{result_dir}/rare_class_metrics.csv",
        "manifest_json": f"{result_dir}/manifest.json",
        "report_md": "docs/experiments/UNSW_A11_ENHANCED_FEATURE_PROTOCOL_SEED42_REPORT.md",
    }
    for key, expected in required_exact_outputs.items():
        _require(key in outputs, f"outputs.{key} is required for UNSW A11.")
        actual = _safe_relative_path(str(outputs[key]), f"outputs.{key}")
        _require(actual == expected, f"unexpected UNSW A11 output for {key}: {actual}")


def _validate_cicids_hierarchical_experiment_outputs(
    raw: dict[str, Any],
    outputs: dict[str, Any],
) -> None:
    experiment = str(raw.get("experiment", ""))
    _require(
        experiment.startswith(CICIDS_EXPERIMENT_PREFIX),
        f"CICIDS experiment name must start with {CICIDS_EXPERIMENT_PREFIX!r}.",
    )
    _require(str(raw.get("dataset")) == "cicids2018", "CICIDS experiments require cicids2018.")
    _require(str(raw.get("task")) == FULL_TASK, "CICIDS experiments require hierarchical task.")
    _require(int(raw.get("input_dim")) == 77, "CICIDS experiments require input_dim 77.")
    _require(int(raw.get("attack_head_dim")) == 14, "CICIDS experiments require attack_head_dim 14.")

    result_dir = f"results/experiments/{experiment}"
    required_exact_outputs = {
        "checkpoint": f"models/experiments/{experiment}.pt",
        "result_dir": result_dir,
        "training_history_csv": f"{result_dir}/training_history.csv",
        "test_metrics_json": f"{result_dir}/test_metrics.json",
        "binary_confusion_matrix_csv": f"{result_dir}/binary_confusion_matrix.csv",
        "attack_family_confusion_matrix_csv": f"{result_dir}/attack_family_confusion_matrix.csv",
        "per_class_attack_metrics_csv": f"{result_dir}/per_class_attack_metrics.csv",
        "rare_class_metrics_csv": f"{result_dir}/rare_class_metrics.csv",
        "hierarchical_routing_summary_json": f"{result_dir}/hierarchical_routing_summary.json",
        "training_config_snapshot_yaml": f"{result_dir}/training_config_snapshot.yaml",
        "class_weight_snapshot_json": f"{result_dir}/class_weight_snapshot.json",
        "model_summary_json": f"{result_dir}/model_summary.json",
        "manifest_json": f"results/audits/hierarchical_training_manifest_{experiment}.json",
        "report_md": f"docs/experiments/{experiment.upper()}_REPORT.md",
    }
    for key, expected in required_exact_outputs.items():
        _require(key in outputs, f"outputs.{key} is required for CICIDS experiments.")
        actual = _safe_relative_path(str(outputs[key]), f"outputs.{key}")
        _require(actual == expected, f"unexpected CICIDS experiment output for {key}: {actual}")


def _a9_8_multiseed_variant_seed_from_checkpoint(checkpoint: str) -> tuple[str, str] | None:
    for variant, templates in A9_8_MULTI_SEED_VARIANTS.items():
        for seed in A9_8_MULTI_SEED_SEEDS:
            if checkpoint == templates["checkpoint_template"].format(seed=seed):
                return variant, seed
    return None


def _is_a9_8_multiseed_config(raw: dict[str, Any], checkpoint: str) -> bool:
    experiment = str(raw.get("experiment", ""))
    status = str(raw.get("status", ""))
    return (
        "a9_8_multiseed" in experiment
        or "a9_8_multiseed" in status
        or checkpoint.startswith("models/final/multiseed/")
    )


def _validate_a9_8_multiseed_outputs(raw: dict[str, Any], outputs: dict[str, Any]) -> None:
    checkpoint = _safe_relative_path(str(outputs["checkpoint"]), "outputs.checkpoint")
    variant_seed = _a9_8_multiseed_variant_seed_from_checkpoint(checkpoint)
    _require(variant_seed is not None, f"unexpected checkpoint path: {checkpoint}")
    variant, seed = variant_seed
    expected_experiment = f"a9_8_multiseed_{variant}_seed{seed}"
    _require(
        str(raw.get("experiment")) == expected_experiment,
        f"unexpected A9.8 multiseed experiment name: {raw.get('experiment')!r}",
    )
    _require(
        str(raw.get("status")) == "task_a9_8_multiseed_prep_not_run",
        f"unexpected A9.8 multiseed status: {raw.get('status')!r}",
    )

    templates = A9_8_MULTI_SEED_VARIANTS[variant]
    result_dir = templates["result_dir_template"].format(seed=seed)
    expected_outputs = {
        "checkpoint": checkpoint,
        "result_dir": result_dir,
        "training_history_csv": f"{result_dir}/training_history.csv",
        "test_metrics_json": f"{result_dir}/test_metrics.json",
        "binary_confusion_matrix_csv": f"{result_dir}/binary_confusion_matrix.csv",
        "attack_family_confusion_matrix_csv": f"{result_dir}/attack_family_confusion_matrix.csv",
        "per_class_attack_metrics_csv": f"{result_dir}/per_class_attack_metrics.csv",
        "rare_class_metrics_csv": f"{result_dir}/rare_class_metrics.csv",
        "hierarchical_routing_summary_json": f"{result_dir}/hierarchical_routing_summary.json",
        "training_config_snapshot_yaml": f"{result_dir}/training_config_snapshot.yaml",
        "class_weight_snapshot_json": f"{result_dir}/class_weight_snapshot.json",
        "model_summary_json": f"{result_dir}/model_summary.json",
        "manifest_json": templates["manifest_template"].format(seed=seed),
        "report_md": templates["report_template"].format(seed=seed),
    }
    for key, expected in expected_outputs.items():
        _require(key in outputs, f"outputs.{key} is required for A9.8 multiseed configs.")
        actual = _safe_relative_path(str(outputs[key]), f"outputs.{key}")
        _require(actual == expected, f"unexpected output path for {key}: {actual}")


def load_hierarchical_training_config(
    path: Path | str,
    project_root: Path | None = None,
) -> HierarchicalTrainingConfig:
    """Load a future full hierarchical training config without executing it."""

    config_path = Path(path)
    raw = _load_yaml(config_path)
    missing = [key for key in FULL_REQUIRED_KEYS if key not in raw]
    _require(not missing, f"Hierarchical config missing keys: {sorted(missing)}")
    _require(str(raw["task"]) == FULL_TASK, f"task must be {FULL_TASK!r}.")
    _validate_common_model(raw)
    dataset, input_dim, attack_head_dim = _validate_dataset_dims(raw)

    outputs = raw.get("outputs", {})
    _require(isinstance(outputs, dict), "outputs must be a mapping.")
    for key in (
        "checkpoint",
        "result_dir",
        "training_history_csv",
        "test_metrics_json",
        "binary_confusion_matrix_csv",
        "attack_family_confusion_matrix_csv",
        "per_class_attack_metrics_csv",
        "rare_class_metrics_csv",
        "manifest_json",
        "report_md",
    ):
        _require(key in outputs, f"outputs.{key} is required.")

    loss = raw.get("loss", {})
    _require(loss.get("type") == "masked_multi_task", "loss.type must be masked_multi_task.")
    _require(float(loss.get("binary_loss_weight")) > 0.0, "binary loss weight must be > 0.")
    _require(float(loss.get("attack_loss_weight")) > 0.0, "attack loss weight must be > 0.")
    _require(int(loss.get("ignore_index")) == -1, "loss.ignore_index must be -1.")

    imbalance = raw.get("class_imbalance", {})
    _require(
        imbalance.get("compute_weights_from") == "train_only",
        "class weights must be computed from train_only.",
    )
    _require(
        imbalance.get("allow_test_based_weights") is False,
        "test-based class weights must be disabled.",
    )

    checkpoint = _safe_relative_path(str(outputs["checkpoint"]), "outputs.checkpoint")
    if _is_a9_8_multiseed_config(raw, checkpoint):
        _validate_a9_8_multiseed_outputs(raw, outputs)
    elif _is_cicids_hierarchical_experiment_config(raw, checkpoint):
        _validate_cicids_hierarchical_experiment_outputs(raw, outputs)
    elif _is_unsw_a11_experiment_config(raw, checkpoint):
        _validate_unsw_a11_experiment_outputs(raw, outputs)
    else:
        _require(
            _regular_hierarchical_checkpoint_allowed(checkpoint),
            f"unexpected checkpoint path: {checkpoint}",
        )

    return HierarchicalTrainingConfig(
        path=config_path,
        dataset=dataset,
        task=str(raw["task"]),
        model_name=str(raw["model_name"]),
        hierarchical_data_dir=str(raw["hierarchical_data_dir"]),
        feature_names_path=str(raw["feature_names_path"]),
        attack_family_label_mapping_path=str(raw["attack_family_label_mapping_path"]),
        preprocessing_manifest_path=str(raw["preprocessing_manifest_path"]),
        readiness_json=str(raw["readiness_json"]),
        taxonomy_config=str(raw["taxonomy_config"]),
        input_dim=input_dim,
        attack_head_dim=attack_head_dim,
        outputs={str(key): str(value) for key, value in outputs.items()},
        raw=raw,
        project_root=Path(project_root) if project_root is not None else PROJECT_ROOT,
    )


def load_hierarchical_smoke_config(
    path: Path | str,
    project_root: Path | None = None,
) -> HierarchicalSmokeConfig:
    """Load a non-final hierarchical smoke config without executing it."""

    config_path = Path(path)
    raw = _load_yaml(config_path)
    missing = [key for key in SMOKE_REQUIRED_KEYS if key not in raw]
    _require(not missing, f"Hierarchical smoke config missing keys: {sorted(missing)}")
    _require(str(raw["task"]) == SMOKE_TASK, f"task must be {SMOKE_TASK!r}.")
    _require(str(raw.get("model_name")) == MODEL_NAME, f"model_name must be {MODEL_NAME!r}.")
    dataset, input_dim, attack_head_dim = _validate_dataset_dims(raw)

    smoke = raw.get("smoke", {})
    safety = raw.get("safety", {})
    _require(isinstance(smoke, dict), "smoke must be a mapping.")
    _require(isinstance(safety, dict), "safety must be a mapping.")
    _require(smoke.get("enabled") is True, "smoke.enabled must be true.")
    _require(smoke.get("non_final") is True, "smoke.non_final must be true.")
    _require(smoke.get("save_checkpoint") is False, "smoke.save_checkpoint must be false.")
    _require(smoke.get("final_metrics") is False, "smoke.final_metrics must be false.")
    _require(int(smoke.get("max_epochs")) == 1, "smoke.max_epochs must be 1.")
    for key in ("train_samples", "val_samples", "test_samples", "max_train_batches", "max_eval_batches"):
        _require(int(smoke.get(key)) > 0, f"smoke.{key} must be > 0.")
    for key in ("output_json", "report_md"):
        _require(key in smoke, f"smoke.{key} is required.")
        _require(not _is_final_path(str(smoke[key])), f"smoke.{key} must not be final path.")
    for key in (
        "no_final_checkpoint",
        "no_final_metrics",
        "no_results_final_outputs",
        "no_full_training",
        "do_not_report_as_final",
    ):
        _require(safety.get(key) is True, f"safety.{key} must be true.")

    return HierarchicalSmokeConfig(
        path=config_path,
        dataset=dataset,
        task=str(raw["task"]),
        base_config=str(raw["base_config"]),
        model_name=str(raw["model_name"]),
        hierarchical_data_dir=str(raw["hierarchical_data_dir"]),
        input_dim=input_dim,
        attack_head_dim=attack_head_dim,
        smoke=dict(smoke),
        safety=dict(safety),
        raw=raw,
        project_root=Path(project_root) if project_root is not None else PROJECT_ROOT,
    )
