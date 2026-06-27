"""Dry-run validation for future hierarchical federated/security configs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None


class HierarchicalFederatedPlanError(ValueError):
    """Raised when a future hierarchical federated config is unsafe."""


DATASET_ALIASES = {
    "cicids": "cicids2018",
    "cicids2018": "cicids2018",
    "cicids-2018": "cicids2018",
    "unsw": "unsw_nb15",
    "unsw_nb15": "unsw_nb15",
    "unsw-nb15": "unsw_nb15",
}

FINAL_REFERENCES = {
    "cicids2018": {
        "checkpoint": "models/final/final_cicids_hierarchical.pt",
        "sha256": "2C154253162CF18CD25D78F2AB77127CE51C26488D1F9BCABC93BAF591CD74C0",
        "input_dim": 77,
        "attack_head_dim": 14,
    },
    "unsw_nb15": {
        "checkpoint": "models/final/final_unsw_hierarchical.pt",
        "sha256": "5FE688BF43C68A7DE63E106E0AD46F608BBAE3D78DCED6E90ABBE2C6F956CBEA",
        "input_dim": 192,
        "attack_head_dim": 9,
    },
}

ALLOWED_AGGREGATIONS = {"fedavg", "trimmed_mean", "median", "krum"}
ALLOWED_ATTACK_TYPES = {"none", "sign_flip", "gaussian", "scaling"}
ALLOWED_CLIENT_SPLITS = {"stratified_iid", "attack_family_aware_iid"}
FORBIDDEN_PATH_PREFIXES = ("models/final/", "results/final/")


@dataclass(frozen=True)
class HierarchicalFederatedPlan:
    """Validated future federated/security experiment plan."""

    path: Path
    raw: dict[str, Any]
    checked_paths: dict[str, str]

    @property
    def dataset(self) -> str:
        return str(self.raw["dataset"])

    @property
    def aggregation_strategy(self) -> str:
        return str(self.raw["aggregation"]["strategy"])

    @property
    def attack_type(self) -> str:
        return str(self.raw["attack"]["type"])

    @property
    def num_clients(self) -> int:
        return int(self.raw["federation"]["num_clients"])


def normalize_dataset_alias(dataset: str | None) -> str | None:
    if dataset is None:
        return None
    return DATASET_ALIASES.get(str(dataset), str(dataset))


def _require_mapping(payload: Any, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HierarchicalFederatedPlanError(f"{context} must be a mapping.")
    return payload


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise HierarchicalFederatedPlanError(f"{context} missing required keys: {missing}")


def _require_bool(payload: dict[str, Any], key: str, expected: bool, context: str) -> None:
    actual = payload.get(key)
    if actual is not expected:
        raise HierarchicalFederatedPlanError(
            f"{context}.{key} must be {expected!r}; found {actual!r}."
        )


def _require_positive_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HierarchicalFederatedPlanError(f"{context} must be a positive integer.")
    return int(value)


def _require_number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HierarchicalFederatedPlanError(f"{context} must be numeric.")
    return float(value)


def _project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def _normalized_slash_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def _reject_final_path(value: str | Path, context: str) -> None:
    text = _normalized_slash_path(value)
    if text.startswith(FORBIDDEN_PATH_PREFIXES):
        raise HierarchicalFederatedPlanError(
            f"{context} must not write under models/final or results/final: {value}"
        )


def _require_prefix(value: str | Path, prefix: str, context: str) -> None:
    text = _normalized_slash_path(value)
    if not text.startswith(prefix):
        raise HierarchicalFederatedPlanError(
            f"{context} must start with {prefix!r}; found {value!r}."
        )


def _validate_reference(dataset: str, reference: dict[str, Any]) -> None:
    expected = FINAL_REFERENCES[dataset]
    if "a11" in str(reference.get("checkpoint", "")).lower():
        raise HierarchicalFederatedPlanError("A11 must not be used as a final reference.")
    if reference.get("checkpoint") != expected["checkpoint"]:
        raise HierarchicalFederatedPlanError(
            f"{dataset} centralized reference checkpoint must be "
            f"{expected['checkpoint']!r}."
        )
    if reference.get("sha256") != expected["sha256"]:
        raise HierarchicalFederatedPlanError(
            f"{dataset} centralized reference sha256 is not the accepted final hash."
        )
    if reference.get("use") != "reference_only":
        raise HierarchicalFederatedPlanError(
            "centralized_reference.use must be 'reference_only'."
        )
    if reference.get("warm_start_from_centralized") is not False:
        raise HierarchicalFederatedPlanError(
            "centralized_reference.warm_start_from_centralized must be false."
        )


def _validate_reference_metrics(reference: dict[str, Any]) -> None:
    metrics = _require_mapping(reference.get("metrics"), "centralized_reference.metrics")
    for key in (
        "binary_macro_f1",
        "attack_family_macro_f1",
        "rare_class_macro_f1",
    ):
        value = _require_number(metrics.get(key), f"centralized_reference.metrics.{key}")
        if value < 0.0 or value > 1.0:
            raise HierarchicalFederatedPlanError(
                f"centralized_reference.metrics.{key} must be in [0, 1]."
            )


def _validate_training(training: dict[str, Any]) -> None:
    _require_keys(
        training,
        ("seed", "batch_size", "learning_rate", "optimizer", "weight_decay", "threshold"),
        "training",
    )
    _require_positive_int(training["seed"], "training.seed")
    _require_positive_int(training["batch_size"], "training.batch_size")
    learning_rate = _require_number(training["learning_rate"], "training.learning_rate")
    if learning_rate <= 0.0:
        raise HierarchicalFederatedPlanError("training.learning_rate must be > 0.")
    weight_decay = _require_number(training["weight_decay"], "training.weight_decay")
    if weight_decay < 0.0:
        raise HierarchicalFederatedPlanError("training.weight_decay must be >= 0.")
    if str(training["optimizer"]).lower() != "adamw":
        raise HierarchicalFederatedPlanError("training.optimizer must be 'adamw'.")
    threshold = _require_number(training["threshold"], "training.threshold")
    if threshold <= 0.0 or threshold >= 1.0:
        raise HierarchicalFederatedPlanError("training.threshold must satisfy 0 < threshold < 1.")


def _validate_loss(loss: dict[str, Any]) -> None:
    _require_keys(
        loss,
        ("binary_loss_weight", "attack_loss_weight", "ignore_index"),
        "loss",
    )
    for key in ("binary_loss_weight", "attack_loss_weight"):
        value = _require_number(loss[key], f"loss.{key}")
        if value <= 0.0:
            raise HierarchicalFederatedPlanError(f"loss.{key} must be > 0.")
    if int(loss["ignore_index"]) != -1:
        raise HierarchicalFederatedPlanError("loss.ignore_index must be -1.")


def _is_clean_fedavg_config(raw: dict[str, Any]) -> bool:
    aggregation = raw.get("aggregation")
    attack = raw.get("attack")
    return (
        isinstance(aggregation, dict)
        and isinstance(attack, dict)
        and aggregation.get("strategy") == "fedavg"
        and attack.get("enabled") is False
        and attack.get("type") == "none"
    )


def _validate_outputs(outputs: dict[str, Any]) -> None:
    _require_keys(
        outputs,
        (
            "checkpoint",
            "result_dir",
            "round_history",
            "client_distribution",
            "test_metrics",
            "audit_json",
            "report_md",
        ),
        "outputs",
    )
    for key, value in outputs.items():
        if isinstance(value, str):
            _reject_final_path(value, f"outputs.{key}")
    _require_prefix(outputs["checkpoint"], "models/experiments/", "outputs.checkpoint")
    _require_prefix(outputs["result_dir"], "results/experiments/", "outputs.result_dir")
    for key in ("round_history", "client_distribution", "test_metrics"):
        _require_prefix(outputs[key], "results/experiments/", f"outputs.{key}")
    _require_prefix(outputs["audit_json"], "results/audits/", "outputs.audit_json")
    _require_prefix(outputs["report_md"], "docs/experiments/", "outputs.report_md")


def _validate_config(raw: dict[str, Any], project_root: Path) -> dict[str, str]:
    _require_keys(
        raw,
        (
            "status",
            "dataset",
            "task",
            "protocol_label",
            "model",
            "hierarchical_data",
            "centralized_reference",
            "federation",
            "aggregation",
            "attack",
            "integrity",
            "outputs",
            "safety",
        ),
        "hierarchical federated config",
    )
    if raw["status"] != "not_run_yet":
        raise HierarchicalFederatedPlanError("status must be 'not_run_yet'.")
    dataset = normalize_dataset_alias(str(raw["dataset"]))
    if dataset not in FINAL_REFERENCES:
        raise HierarchicalFederatedPlanError(f"Unsupported dataset: {raw['dataset']!r}.")
    if raw["dataset"] != dataset:
        raise HierarchicalFederatedPlanError(
            f"Config dataset must be canonical {dataset!r}, not alias {raw['dataset']!r}."
        )
    if raw["task"] != "hierarchical_federated":
        raise HierarchicalFederatedPlanError("task must be 'hierarchical_federated'.")

    expected = FINAL_REFERENCES[dataset]
    model = _require_mapping(raw["model"], "model")
    _require_keys(model, ("architecture", "input_dim", "attack_head_dim"), "model")
    if model["architecture"] != "SecureIDSHierarchicalAdvancedNet":
        raise HierarchicalFederatedPlanError(
            "model.architecture must be SecureIDSHierarchicalAdvancedNet."
        )
    if int(model["input_dim"]) != expected["input_dim"]:
        raise HierarchicalFederatedPlanError(
            f"{dataset} input_dim must be {expected['input_dim']}."
        )
    if int(model["attack_head_dim"]) != expected["attack_head_dim"]:
        raise HierarchicalFederatedPlanError(
            f"{dataset} attack_head_dim must be {expected['attack_head_dim']}."
        )

    hierarchical_data = _require_mapping(raw["hierarchical_data"], "hierarchical_data")
    _require_keys(
        hierarchical_data,
        (
            "processed_dir",
            "feature_names",
            "attack_family_label_mapping",
            "preprocessing_manifest",
        ),
        "hierarchical_data",
    )
    checked_paths = {
        name: str(_project_path(project_root, value))
        for name, value in hierarchical_data.items()
        if isinstance(value, str)
    }

    reference = _require_mapping(raw["centralized_reference"], "centralized_reference")
    _require_keys(
        reference,
        ("checkpoint", "sha256", "status", "use", "warm_start_from_centralized"),
        "centralized_reference",
    )
    _validate_reference(dataset, reference)

    federation = _require_mapping(raw["federation"], "federation")
    _require_keys(
        federation,
        (
            "num_clients",
            "client_split",
            "non_iid_planned",
            "seed",
            "rounds",
            "client_fraction",
            "local_epochs",
            "execute_gate_required",
        ),
        "federation",
    )
    _require_positive_int(federation["num_clients"], "federation.num_clients")
    _require_positive_int(federation["rounds"], "federation.rounds")
    _require_positive_int(federation["local_epochs"], "federation.local_epochs")
    if federation["client_split"] not in ALLOWED_CLIENT_SPLITS:
        raise HierarchicalFederatedPlanError(
            "federation.client_split must be one of "
            f"{sorted(ALLOWED_CLIENT_SPLITS)}."
        )
    _require_bool(federation, "non_iid_planned", True, "federation")
    _require_bool(federation, "execute_gate_required", True, "federation")
    client_fraction = _require_number(federation["client_fraction"], "federation.client_fraction")
    if client_fraction <= 0.0 or client_fraction > 1.0:
        raise HierarchicalFederatedPlanError(
            "federation.client_fraction must satisfy 0 < fraction <= 1."
        )

    aggregation = _require_mapping(raw["aggregation"], "aggregation")
    _require_keys(aggregation, ("strategy",), "aggregation")
    if aggregation["strategy"] not in ALLOWED_AGGREGATIONS:
        raise HierarchicalFederatedPlanError(
            f"Unsupported aggregation strategy: {aggregation['strategy']!r}."
        )
    if aggregation["strategy"] == "trimmed_mean":
        trim_ratio = _require_number(aggregation.get("trim_ratio"), "aggregation.trim_ratio")
        if trim_ratio < 0.0 or trim_ratio >= 0.5:
            raise HierarchicalFederatedPlanError(
                "aggregation.trim_ratio must satisfy 0 <= ratio < 0.5."
            )

    attack = _require_mapping(raw["attack"], "attack")
    _require_keys(attack, ("enabled", "type", "malicious_fraction", "seed"), "attack")
    if attack["type"] not in ALLOWED_ATTACK_TYPES:
        raise HierarchicalFederatedPlanError(f"Unsupported attack type: {attack['type']!r}.")
    attack_fraction = _require_number(
        attack["malicious_fraction"], "attack.malicious_fraction"
    )
    if attack_fraction < 0.0 or attack_fraction > 1.0:
        raise HierarchicalFederatedPlanError(
            "attack.malicious_fraction must satisfy 0 <= fraction <= 1."
        )
    if attack["enabled"] is False and attack["type"] != "none":
        raise HierarchicalFederatedPlanError("Disabled attacks must use type 'none'.")
    if attack["enabled"] is True and attack["type"] == "none":
        raise HierarchicalFederatedPlanError("Enabled attacks require a non-none type.")

    integrity = _require_mapping(raw["integrity"], "integrity")
    _require_bool(integrity, "sha256_update_hashing", True, "integrity")
    _require_bool(integrity, "verify_before_aggregation", True, "integrity")
    if integrity.get("secure_aggregation") not in (False, "future_optional"):
        raise HierarchicalFederatedPlanError(
            "integrity.secure_aggregation must be false or future_optional."
        )

    outputs = _require_mapping(raw["outputs"], "outputs")
    _validate_outputs(outputs)

    safety = _require_mapping(raw["safety"], "safety")
    for key in (
        "dry_run_writes_outputs",
        "training_allowed_in_scaffold",
        "evaluation_allowed_in_scaffold",
        "models_final_write_allowed",
        "results_final_write_allowed",
        "a11_used_as_final",
    ):
        _require_bool(safety, key, False, "safety")
    for key in ("no_final_path_writes", "a11_excluded_as_final", "no_test_tuning"):
        _require_bool(safety, key, True, "safety")

    if _is_clean_fedavg_config(raw):
        if raw.get("initialization") != "from_scratch":
            raise HierarchicalFederatedPlanError(
                "Clean hierarchical FedAvg requires initialization: from_scratch."
            )
        if federation["client_split"] != "attack_family_aware_iid":
            raise HierarchicalFederatedPlanError(
                "Clean hierarchical FedAvg requires attack_family_aware_iid splitting."
            )
        _validate_reference_metrics(reference)
        _validate_training(_require_mapping(raw.get("training"), "training"))
        _validate_loss(_require_mapping(raw.get("loss"), "loss"))

    return checked_paths


def load_hierarchical_federated_plan(
    config_path: str | Path,
    project_root: Path | None = None,
) -> HierarchicalFederatedPlan:
    """Load and validate a future hierarchical FL/security config."""

    if yaml is None:
        raise HierarchicalFederatedPlanError("PyYAML is required to load configs.")
    root = project_root or Path.cwd()
    path = Path(config_path)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    raw = _require_mapping(loaded, "hierarchical federated config")
    checked_paths = _validate_config(raw, root)
    return HierarchicalFederatedPlan(path=path, raw=raw, checked_paths=checked_paths)


def run_hierarchical_federated_plan_dry_run(
    config_path: str | Path,
    project_root: Path,
) -> dict[str, Any]:
    """Validate a future hierarchical federated config without writing files."""

    plan = load_hierarchical_federated_plan(config_path, project_root=project_root)
    path_checks = [
        {
            "name": name,
            "path": path,
            "exists": Path(path).exists(),
        }
        for name, path in plan.checked_paths.items()
    ]
    return {
        "status": "PASS",
        "config_path": str(plan.path),
        "dataset": plan.dataset,
        "protocol_label": plan.raw["protocol_label"],
        "protocol_identity": plan.raw.get("protocol_identity", plan.raw["protocol_label"]),
        "initialization": plan.raw.get("initialization"),
        "aggregation_strategy": plan.aggregation_strategy,
        "attack_type": plan.attack_type,
        "num_clients": plan.num_clients,
        "path_checks": path_checks,
        "writes_outputs": False,
        "training_run": False,
        "evaluation_run": False,
        "checkpoint_created": False,
        "metrics_created": False,
    }
