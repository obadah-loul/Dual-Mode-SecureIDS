"""Typed loading and validation for centralized training configs.

This module is intentionally free of any heavy dependency (no torch, no numpy):
it only reads and validates YAML config files so that config validation stays
cheap and importable on its own. Path fields are stored as written in the config
and resolved against the project root on demand via :meth:`TrainingConfig.resolve`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - depends on local environment
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SUPPORTED_DATASETS = {"cicids2018", "unsw_nb15"}
SUPPORTED_TASK = "binary"

REQUIRED_TOP_LEVEL_KEYS = (
    "dataset",
    "task",
    "processed_dir",
    "input_dim",
    "feature_names_path",
    "label_mapping_path",
    "preprocessing_manifest_path",
    "output_checkpoint",
    "training",
    "model",
    "evaluation",
    "outputs",
)


class TrainingConfigError(ValueError):
    """Raised when a training config is missing keys or fails validation."""


@dataclass(frozen=True)
class ModelConfig:
    architecture: str
    hidden_dims: list[int]
    dropout: float
    output_dim: int


@dataclass(frozen=True)
class TrainingParams:
    seed: int
    batch_size: int
    max_epochs: int
    learning_rate: float
    optimizer: str
    weight_decay: float
    early_stopping_metric: str
    early_stopping_patience: int
    use_pos_weight: bool


@dataclass(frozen=True)
class EvaluationConfig:
    threshold: float
    final_test_once: bool


@dataclass(frozen=True)
class OutputsConfig:
    history_csv: str
    metrics_json: str
    confusion_matrix_csv: str
    manifest_json: str


@dataclass(frozen=True)
class TrainingConfig:
    """Validated, typed view over a centralized training config file."""

    dataset: str
    task: str
    processed_dir: str
    input_dim: int
    feature_names_path: str
    label_mapping_path: str
    preprocessing_manifest_path: str
    output_checkpoint: str
    training: TrainingParams
    model: ModelConfig
    evaluation: EvaluationConfig
    outputs: OutputsConfig
    project_root: Path = field(default=PROJECT_ROOT)
    raw: dict[str, Any] = field(default_factory=dict)

    def resolve(self, path_str: str) -> Path:
        """Resolve a config path against the project root if it is relative."""

        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TrainingConfigError(message)


def _load_feature_names_for_validation(path: Path) -> list[str]:
    """Load feature names stored as ``{"feature_names": [...]}``.

    A bare top-level list is tolerated for robustness, but the canonical format
    is the object form used by the preprocessing artifacts.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        names = payload.get("feature_names")
        _require(
            isinstance(names, list),
            f"{path} must contain a 'feature_names' list.",
        )
        return list(names)
    if isinstance(payload, list):
        return list(payload)
    raise TrainingConfigError(f"Unsupported feature_names format in {path}.")


def _build_model_config(raw_model: dict[str, Any]) -> ModelConfig:
    _require(isinstance(raw_model, dict), "'model' section must be a mapping.")
    hidden_dims = raw_model.get("hidden_dims", [256, 128, 64])
    _require(
        isinstance(hidden_dims, list) and len(hidden_dims) > 0,
        "model.hidden_dims must be a non-empty list.",
    )
    output_dim = int(raw_model.get("output_dim", 1))
    _require(
        output_dim == 1,
        f"model.output_dim must be 1 for the binary task, got {output_dim}.",
    )
    return ModelConfig(
        architecture=str(raw_model.get("architecture", "SecureIDSNet")),
        hidden_dims=[int(width) for width in hidden_dims],
        dropout=float(raw_model.get("dropout", 0.20)),
        output_dim=output_dim,
    )


def _build_training_params(raw_training: dict[str, Any]) -> TrainingParams:
    _require(isinstance(raw_training, dict), "'training' section must be a mapping.")
    batch_size = int(raw_training.get("batch_size", 1024))
    max_epochs = int(raw_training.get("max_epochs", 20))
    patience = int(raw_training.get("early_stopping_patience", 5))
    _require(batch_size > 0, "training.batch_size must be > 0.")
    _require(max_epochs > 0, "training.max_epochs must be > 0.")
    _require(patience > 0, "training.early_stopping_patience must be > 0.")
    return TrainingParams(
        seed=int(raw_training.get("seed", 42)),
        batch_size=batch_size,
        max_epochs=max_epochs,
        learning_rate=float(raw_training.get("learning_rate", 1e-3)),
        optimizer=str(raw_training.get("optimizer", "adamw")),
        weight_decay=float(raw_training.get("weight_decay", 1e-4)),
        early_stopping_metric=str(
            raw_training.get("early_stopping_metric", "val_macro_f1")
        ),
        early_stopping_patience=patience,
        use_pos_weight=bool(raw_training.get("use_pos_weight", True)),
    )


def _build_evaluation_config(raw_eval: dict[str, Any]) -> EvaluationConfig:
    _require(isinstance(raw_eval, dict), "'evaluation' section must be a mapping.")
    threshold = float(raw_eval.get("threshold", 0.5))
    _require(0.0 < threshold < 1.0, "evaluation.threshold must be in (0.0, 1.0).")
    return EvaluationConfig(
        threshold=threshold,
        final_test_once=bool(raw_eval.get("final_test_once", True)),
    )


def _build_outputs_config(raw_outputs: dict[str, Any]) -> OutputsConfig:
    _require(isinstance(raw_outputs, dict), "'outputs' section must be a mapping.")
    for key in ("history_csv", "metrics_json", "confusion_matrix_csv", "manifest_json"):
        _require(key in raw_outputs, f"outputs.{key} is required.")
    return OutputsConfig(
        history_csv=str(raw_outputs["history_csv"]),
        metrics_json=str(raw_outputs["metrics_json"]),
        confusion_matrix_csv=str(raw_outputs["confusion_matrix_csv"]),
        manifest_json=str(raw_outputs["manifest_json"]),
    )


def load_training_config(
    path: Path | str,
    project_root: Path | None = None,
) -> TrainingConfig:
    """Load and validate a centralized training config.

    This performs validation only. It never loads processed arrays and never
    runs training.

    Raises
    ------
    TrainingConfigError
        If the file is missing required keys or fails any validation rule.
    """

    if yaml is None:  # pragma: no cover - depends on local environment
        raise TrainingConfigError("PyYAML is required to load training configs.")

    config_path = Path(path)
    _require(config_path.exists(), f"Training config not found: {config_path}.")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    _require(isinstance(raw, dict), "Training config root must be a mapping.")

    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in raw]
    _require(not missing, f"Training config is missing keys: {sorted(missing)}.")

    dataset = str(raw["dataset"])
    _require(
        dataset in SUPPORTED_DATASETS,
        f"dataset must be one of {sorted(SUPPORTED_DATASETS)}, got {dataset!r}.",
    )

    task = str(raw["task"])
    _require(
        task == SUPPORTED_TASK,
        f"task must be {SUPPORTED_TASK!r}, got {task!r}.",
    )

    input_dim = int(raw["input_dim"])
    _require(input_dim > 0, f"input_dim must be > 0, got {input_dim}.")

    model = _build_model_config(raw["model"])
    training = _build_training_params(raw["training"])
    evaluation = _build_evaluation_config(raw["evaluation"])
    outputs = _build_outputs_config(raw["outputs"])

    root = Path(project_root) if project_root is not None else PROJECT_ROOT

    feature_names_path = Path(raw["feature_names_path"])
    if not feature_names_path.is_absolute():
        feature_names_path = root / feature_names_path
    if feature_names_path.exists():
        names = _load_feature_names_for_validation(feature_names_path)
        _require(
            len(names) == input_dim,
            (
                f"feature_names length ({len(names)}) does not match input_dim "
                f"({input_dim}) in {feature_names_path}."
            ),
        )

    return TrainingConfig(
        dataset=dataset,
        task=task,
        processed_dir=str(raw["processed_dir"]),
        input_dim=input_dim,
        feature_names_path=str(raw["feature_names_path"]),
        label_mapping_path=str(raw["label_mapping_path"]),
        preprocessing_manifest_path=str(raw["preprocessing_manifest_path"]),
        output_checkpoint=str(raw["output_checkpoint"]),
        training=training,
        model=model,
        evaluation=evaluation,
        outputs=outputs,
        project_root=root,
        raw=raw,
    )


# --------------------------------------------------------------------------- #
# Smoke (tiny, non-final) training config. Torch-free so it can be validated and
# unit-tested without PyTorch installed. Execution lives in
# secureids.training.smoke (which requires torch).
# --------------------------------------------------------------------------- #
SMOKE_REQUIRED_TOP_LEVEL_KEYS = (
    "dataset",
    "base_config",
    "processed_dir",
    "input_dim",
    "smoke",
)


class SmokeConfigError(ValueError):
    """Raised when a smoke config is missing keys or fails validation."""


@dataclass(frozen=True)
class SmokeConfig:
    """Validated, typed view over a tiny non-final smoke-training config."""

    dataset: str
    base_config: str
    processed_dir: str
    input_dim: int
    max_train_samples: int
    max_val_samples: int
    max_test_samples: int
    batch_size: int
    max_epochs: int
    max_batches_per_epoch: int
    evaluation_batches: int
    save_checkpoint: bool
    output_json: str
    report_md: str
    enabled: bool = True
    non_final: bool = True
    project_root: Path = field(default=PROJECT_ROOT)
    raw: dict[str, Any] = field(default_factory=dict)

    def resolve(self, path_str: str) -> Path:
        """Resolve a config path against the project root if it is relative."""

        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


def _is_final_results_path(path_str: str) -> bool:
    """True if a path points under results/final (forbidden for smoke outputs)."""

    normalized = str(path_str).replace("\\", "/").lstrip("./")
    return normalized.startswith("results/final")


def load_smoke_config(
    path: Path | str,
    project_root: Path | None = None,
) -> SmokeConfig:
    """Load and validate a smoke-training config.

    Validation only; this never loads arrays, imports torch, or runs training.
    A smoke config must explicitly declare ``smoke.enabled: true`` and
    ``smoke.non_final: true``, default ``save_checkpoint`` to ``false``, and must
    not write outputs under ``results/final``.

    Raises
    ------
    SmokeConfigError
        On missing keys or any failed validation rule.
    """

    if yaml is None:  # pragma: no cover - depends on local environment
        raise SmokeConfigError("PyYAML is required to load smoke configs.")

    config_path = Path(path)
    if not config_path.exists():
        raise SmokeConfigError(f"Smoke config not found: {config_path}.")

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise SmokeConfigError("Smoke config root must be a mapping.")

    missing = [key for key in SMOKE_REQUIRED_TOP_LEVEL_KEYS if key not in raw]
    if missing:
        raise SmokeConfigError(f"Smoke config is missing keys: {sorted(missing)}.")

    dataset = str(raw["dataset"])
    if dataset not in SUPPORTED_DATASETS:
        raise SmokeConfigError(
            f"dataset must be one of {sorted(SUPPORTED_DATASETS)}, got {dataset!r}."
        )

    input_dim = int(raw["input_dim"])
    if input_dim <= 0:
        raise SmokeConfigError(f"input_dim must be > 0, got {input_dim}.")

    smoke = raw["smoke"]
    if not isinstance(smoke, dict):
        raise SmokeConfigError("'smoke' section must be a mapping.")
    if smoke.get("enabled") is not True:
        raise SmokeConfigError("smoke.enabled must be true for a smoke config.")
    if smoke.get("non_final") is not True:
        raise SmokeConfigError("smoke.non_final must be true for a smoke config.")

    # Default false; only an explicit true opts into a marked, non-final
    # checkpoint under models/checkpoints/smoke (never under models/final).
    save_checkpoint = bool(smoke.get("save_checkpoint", False))

    output_json = str(
        smoke.get("output_json", "results/audits/centralized_smoke_check.json")
    )
    report_md = str(smoke.get("report_md", "docs/CENTRALIZED_TRAINING_SMOKE_CHECK.md"))
    for label, candidate in (("output_json", output_json), ("report_md", report_md)):
        if _is_final_results_path(candidate):
            raise SmokeConfigError(
                f"smoke.{label} must not point under results/final (got {candidate!r})."
            )

    root = Path(project_root) if project_root is not None else PROJECT_ROOT

    return SmokeConfig(
        dataset=dataset,
        base_config=str(raw["base_config"]),
        processed_dir=str(raw["processed_dir"]),
        input_dim=input_dim,
        max_train_samples=int(smoke.get("max_train_samples", 4096)),
        max_val_samples=int(smoke.get("max_val_samples", 2048)),
        max_test_samples=int(smoke.get("max_test_samples", 2048)),
        batch_size=int(smoke.get("batch_size", 512)),
        max_epochs=int(smoke.get("max_epochs", 1)),
        max_batches_per_epoch=int(smoke.get("max_batches_per_epoch", 4)),
        evaluation_batches=int(smoke.get("evaluation_batches", 2)),
        save_checkpoint=save_checkpoint,
        output_json=output_json,
        report_md=report_md,
        enabled=True,
        non_final=True,
        project_root=root,
        raw=raw,
    )
