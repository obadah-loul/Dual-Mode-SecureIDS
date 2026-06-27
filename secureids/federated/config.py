"""Federated learning configuration validation for dry-run planning.

The loader validates the Task 9A FedAvg design configs without importing
PyTorch, creating models, or touching any training artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None


class FederatedConfigError(ValueError):
    """Raised when a federated design config is invalid."""


EXPECTED_INPUT_DIMS = {
    "unsw_nb15": 190,
    "cicids2018": 77,
}

REQUIRED_SECTIONS = (
    "dataset",
    "task",
    "model",
    "centralized_reference",
    "data",
    "federation",
    "training",
    "outputs",
    "scope_flags",
)

DISABLED_FUTURE_SCOPE_FLAGS = (
    "secure_communication_enabled",
    "gradient_integrity_enabled",
    "byzantine_attacks_enabled",
    "robust_aggregation_enabled",
    "xai_enabled",
    "dashboard_demo_enabled",
)


@dataclass(frozen=True)
class FederatedConfig:
    """Validated FedAvg design config."""

    path: Path
    raw: dict[str, Any]

    @property
    def dataset(self) -> str:
        return str(self.raw["dataset"])

    @property
    def task(self) -> str:
        return str(self.raw["task"])

    @property
    def input_dim(self) -> int:
        return int(self.raw["model"]["input_dim"])

    @property
    def architecture(self) -> str:
        return str(self.raw["model"]["architecture"])

    @property
    def algorithm(self) -> str:
        return str(self.raw["federation"]["algorithm"])

    @property
    def num_clients(self) -> int:
        return int(self.raw["federation"]["num_clients"])

    @property
    def seed(self) -> int:
        return int(self.raw["federation"]["seed"])

    @property
    def client_split(self) -> str:
        return str(self.raw["federation"]["client_split"])


def normalize_dataset_alias(dataset: str | None) -> str | None:
    """Normalize CLI dataset aliases to config dataset names."""

    if dataset in {"unsw", "unsw_nb15"}:
        return "unsw_nb15"
    if dataset in {"cicids", "cicids2018"}:
        return "cicids2018"
    return dataset


def _require_mapping(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise FederatedConfigError(f"{context} must be a mapping.")
    return payload


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise FederatedConfigError(f"{context} missing required keys: {missing}")


def _require_bool(payload: dict[str, Any], key: str, expected: bool, context: str) -> None:
    actual = payload.get(key)
    if actual is not expected:
        raise FederatedConfigError(
            f"{context}.{key} must be {expected!r}; found {actual!r}."
        )


def _require_positive_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FederatedConfigError(f"{context} must be a positive integer.")
    return value


def _validate_config(raw: dict[str, Any]) -> None:
    _require_keys(raw, REQUIRED_SECTIONS, "federated config")

    dataset = normalize_dataset_alias(str(raw["dataset"]))
    if dataset not in EXPECTED_INPUT_DIMS:
        raise FederatedConfigError(f"Unsupported dataset: {raw['dataset']!r}.")
    if raw["dataset"] != dataset:
        raise FederatedConfigError(
            "Config dataset must use canonical name "
            f"{dataset!r}, not alias {raw['dataset']!r}."
        )
    if raw["task"] != "binary":
        raise FederatedConfigError("Federated config task must be 'binary'.")

    model = _require_mapping(raw["model"], "model")
    _require_keys(
        model,
        ("architecture", "input_dim", "hidden_dims", "dropout", "output_dim"),
        "model",
    )
    if model["architecture"] != "SecureIDSNet":
        raise FederatedConfigError("Model architecture must be SecureIDSNet.")
    if model["input_dim"] != EXPECTED_INPUT_DIMS[dataset]:
        raise FederatedConfigError(
            f"{dataset} input_dim must be {EXPECTED_INPUT_DIMS[dataset]}."
        )
    if model["output_dim"] != 1:
        raise FederatedConfigError("Binary federated setup requires output_dim=1.")

    centralized_reference = _require_mapping(
        raw["centralized_reference"], "centralized_reference"
    )
    _require_keys(
        centralized_reference,
        ("checkpoint", "metrics", "manifest"),
        "centralized_reference",
    )

    data = _require_mapping(raw["data"], "data")
    _require_keys(
        data,
        (
            "processed_dir",
            "train_split",
            "val_split",
            "test_split",
            "no_test_leakage",
        ),
        "data",
    )
    _require_bool(data, "no_test_leakage", True, "data")
    for split_name in ("train_split", "val_split", "test_split"):
        split = _require_mapping(data[split_name], f"data.{split_name}")
        _require_keys(split, ("x", "y"), f"data.{split_name}")

    federation = _require_mapping(raw["federation"], "federation")
    _require_keys(
        federation,
        (
            "algorithm",
            "num_clients",
            "client_split",
            "seed",
            "rounds",
            "client_fraction",
            "local_epochs",
            "aggregation_weighting",
        ),
        "federation",
    )
    if federation["algorithm"] != "FedAvg":
        raise FederatedConfigError("Only FedAvg is allowed in Task 9B.")
    _require_positive_int(federation["num_clients"], "federation.num_clients")
    _require_positive_int(federation["rounds"], "federation.rounds")
    _require_positive_int(federation["local_epochs"], "federation.local_epochs")
    if federation["client_split"] != "stratified_iid":
        raise FederatedConfigError("Task 9B dry-run supports stratified_iid only.")
    if federation["aggregation_weighting"] != "sample_count":
        raise FederatedConfigError("FedAvg weighting must be sample_count.")

    training = _require_mapping(raw["training"], "training")
    _require_keys(
        training,
        (
            "batch_size",
            "learning_rate",
            "optimizer",
            "weight_decay",
            "use_pos_weight",
            "threshold",
            "early_stopping_metric",
            "final_test_after_best_round_only",
        ),
        "training",
    )
    _require_positive_int(training["batch_size"], "training.batch_size")
    if training["threshold"] != 0.5:
        raise FederatedConfigError("Task 9B must preserve threshold=0.5.")
    _require_bool(
        training,
        "final_test_after_best_round_only",
        True,
        "training",
    )
    if training["early_stopping_metric"] != "val_macro_f1":
        raise FederatedConfigError("Best round selection must use val_macro_f1.")

    outputs = _require_mapping(raw["outputs"], "outputs")
    _require_keys(
        outputs,
        (
            "checkpoint",
            "round_history",
            "client_distribution",
            "client_logs",
            "test_metrics",
            "confusion_matrix",
            "manifest",
            "report",
        ),
        "outputs",
    )

    scope_flags = _require_mapping(raw["scope_flags"], "scope_flags")
    _require_bool(scope_flags, "fedavg_baseline_only", True, "scope_flags")
    for flag in DISABLED_FUTURE_SCOPE_FLAGS:
        _require_bool(scope_flags, flag, False, "scope_flags")


def load_federated_config(
    config_path: str | Path,
    project_root: Path | None = None,
) -> FederatedConfig:
    """Load and validate a federated YAML config."""

    if yaml is None:
        raise FederatedConfigError("PyYAML is required to load federated configs.")

    root = project_root or Path.cwd()
    path = Path(config_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    raw = _require_mapping(loaded, "federated config")
    _validate_config(raw)
    return FederatedConfig(path=path, raw=raw)
