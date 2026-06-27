"""Torch-free config loading for the UNSW A9.9 attack-family specialist router.

A9.9 trains a dedicated attack-only family classifier *behind* the frozen A9
Head 1 binary router. This module validates config shape, output-path safety,
and no-test-tuning flags only. It does NOT train, evaluate, load arrays, save
checkpoints, or write metrics. Importing it is torch-free and side-effect free.

See ``docs/experiments/UNSW_A99_SPECIALIST_ROUTER_DESIGN.md``.
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

DATASET = "unsw_nb15"
TASK = "attack_family_specialist"
MODEL_NAME = "AttackFamilySpecialistNet"
INPUT_DIM = 192
NUM_ATTACK_FAMILIES = 9
A9_ROUTER_CHECKPOINT = "models/final/final_unsw_hierarchical.pt"
A9_IDENTITY = "A9 corrected-protocol hierarchical baseline"

# Attack-family id -> name (UNSW corrected protocol; matches
# data/processed/unsw_nb15/hierarchical/attack_family_label_mapping.json).
ATTACK_FAMILY_NAMES = (
    "Generic",
    "Exploits",
    "Fuzzers",
    "DoS",
    "Reconnaissance",
    "Analysis",
    "Backdoor",
    "Shellcode",
    "Worms",
)
RARE_CLASSES = ("Shellcode", "Worms")
WEAK_CLASSES_MUST_REMAIN_VISIBLE = ("Analysis", "Backdoor", "DoS", "Shellcode", "Worms")

REQUIRED_KEYS = (
    "dataset",
    "task",
    "status",
    "experiment",
    "model_name",
    "seed",
    "input_dim",
    "num_attack_families",
    "hierarchical_data_dir",
    "attack_family_label_mapping_path",
    "frozen_a9_router",
    "protocol",
    "training_data",
    "model",
    "loss",
    "class_imbalance",
    "checkpoint_selection",
    "rare_classes",
    "weak_classes_must_remain_visible",
    "outputs",
    "safety",
)

REQUIRED_OUTPUT_KEYS = (
    "checkpoint",
    "result_dir",
    "training_history_csv",
    "oracle_metrics_json",
    "routed_metrics_json",
    "per_class_attack_metrics_csv",
    "rare_class_metrics_csv",
    "attack_family_confusion_matrix_csv",
    "routing_summary_json",
    "training_config_snapshot_yaml",
    "class_weight_snapshot_json",
    "model_summary_json",
    "report_md",
)

# This build phase is preparation only; the config must be clearly marked not run.
ALLOWED_STATUS = "not_run_yet"


class AttackFamilySpecialistConfigError(ValueError):
    """Raised when an A9.9 specialist config fails validation."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AttackFamilySpecialistConfigError(message)


def is_final_path(path_str: str) -> bool:
    """True if the path targets the protected final model/result trees."""

    normalized = str(path_str).replace("\\", "/").lstrip("./")
    return normalized.startswith("models/final") or normalized.startswith("results/final")


def safe_experiment_relative_path(path_str: str, label: str) -> str:
    """Validate a project-relative, non-final, traversal-free output path.

    Returns the normalized relative path or raises
    ``AttackFamilySpecialistConfigError``. Used for every specialist output so a
    misconfigured path can never write into ``models/final`` or
    ``results/final`` or escape the project root.
    """

    normalized = str(path_str).replace("\\", "/").strip()
    path = Path(normalized)
    _require(bool(normalized), f"{label} must not be empty.")
    _require(not path.is_absolute(), f"{label} must be a relative path.")
    _require(":" not in normalized, f"{label} must not include a drive or URI prefix.")
    _require(".." not in path.parts, f"{label} must not contain parent traversal.")
    _require(not normalized.startswith("/"), f"{label} must be project-relative.")
    _require(not is_final_path(normalized), f"{label} must not write into models/final or results/final.")
    return normalized.rstrip("/")


def is_safe_experiment_output_path(path_str: str) -> bool:
    """Boolean wrapper around :func:`safe_experiment_relative_path`."""

    try:
        safe_experiment_relative_path(path_str, "path")
    except AttackFamilySpecialistConfigError:
        return False
    return True


@dataclass(frozen=True)
class AttackFamilySpecialistConfig:
    path: Path
    dataset: str
    task: str
    status: str
    experiment: str
    model_name: str
    seed: int
    input_dim: int
    num_attack_families: int
    hierarchical_data_dir: str
    attack_family_label_mapping_path: str
    frozen_a9_router: dict[str, Any]
    protocol: str
    training_data: dict[str, Any]
    model: dict[str, Any]
    loss: dict[str, Any]
    class_imbalance: dict[str, Any]
    checkpoint_selection: dict[str, Any]
    rare_classes: list[str]
    weak_classes_must_remain_visible: list[str]
    outputs: dict[str, str]
    safety: dict[str, Any]
    raw: dict[str, Any]
    project_root: Path = field(default=PROJECT_ROOT)

    def resolve(self, path_str: str) -> Path:
        path = Path(path_str)
        return path if path.is_absolute() else self.project_root / path


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:  # pragma: no cover - depends on environment
        raise AttackFamilySpecialistConfigError("PyYAML is required.")
    if not path.exists():
        raise AttackFamilySpecialistConfigError(f"Config not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _require(isinstance(loaded, dict), f"Config root must be a mapping: {path}")
    return loaded


def load_attack_family_specialist_config(
    path: Path | str,
    project_root: Path | None = None,
) -> AttackFamilySpecialistConfig:
    """Load and validate an A9.9 specialist config WITHOUT executing it."""

    config_path = Path(path)
    raw = _load_yaml(config_path)

    missing = [key for key in REQUIRED_KEYS if key not in raw]
    _require(not missing, f"A9.9 specialist config missing keys: {sorted(missing)}")

    _require(str(raw["dataset"]) == DATASET, f"dataset must be {DATASET!r}.")
    _require(str(raw["task"]) == TASK, f"task must be {TASK!r}.")
    _require(
        str(raw["status"]) == ALLOWED_STATUS,
        f"status must be {ALLOWED_STATUS!r} for prep/scaffolding (no training yet).",
    )
    _require(str(raw["model_name"]) == MODEL_NAME, f"model_name must be {MODEL_NAME!r}.")
    _require(int(raw["input_dim"]) == INPUT_DIM, f"input_dim must be {INPUT_DIM}.")
    _require(
        int(raw["num_attack_families"]) == NUM_ATTACK_FAMILIES,
        f"num_attack_families must be {NUM_ATTACK_FAMILIES}.",
    )
    seed = int(raw["seed"])
    _require(seed >= 0, "seed must be >= 0.")

    experiment = str(raw["experiment"])
    _require(
        experiment.startswith("unsw_a99_attack_family_specialist"),
        "experiment must start with 'unsw_a99_attack_family_specialist'.",
    )

    # Frozen A9 router protection.
    router = raw.get("frozen_a9_router", {})
    _require(isinstance(router, dict), "frozen_a9_router must be a mapping.")
    _require(
        str(router.get("checkpoint")).replace("\\", "/") == A9_ROUTER_CHECKPOINT,
        f"frozen_a9_router.checkpoint must be {A9_ROUTER_CHECKPOINT!r}.",
    )
    _require(
        str(router.get("identity")) == A9_IDENTITY,
        f"frozen_a9_router.identity must be {A9_IDENTITY!r}.",
    )
    _require(router.get("trainable") is False, "frozen_a9_router.trainable must be false.")

    # Attack-only training scope.
    training_data = raw.get("training_data", {})
    _require(isinstance(training_data, dict), "training_data must be a mapping.")
    _require(
        training_data.get("attack_rows_only") is True,
        "training_data.attack_rows_only must be true.",
    )
    _require(str(training_data.get("split")) == "train", "training_data.split must be 'train'.")

    # Loss / class weights / selection safety.
    loss = raw.get("loss", {})
    _require(isinstance(loss, dict), "loss must be a mapping.")
    _require(
        str(loss.get("type")) == "cross_entropy_attack_rows_only",
        "loss.type must be 'cross_entropy_attack_rows_only'.",
    )

    imbalance = raw.get("class_imbalance", {})
    _require(isinstance(imbalance, dict), "class_imbalance must be a mapping.")
    _require(
        imbalance.get("compute_weights_from") == "train_only",
        "class weights must be computed from train_only.",
    )
    _require(
        imbalance.get("allow_test_based_weights") is False,
        "test-based class weights must be disabled.",
    )

    selection = raw.get("checkpoint_selection", {})
    _require(isinstance(selection, dict), "checkpoint_selection must be a mapping.")
    _require(
        selection.get("use_validation_only") is True,
        "checkpoint_selection.use_validation_only must be true.",
    )
    _require(
        selection.get("select_by_test_metrics") is False,
        "checkpoint_selection.select_by_test_metrics must be false.",
    )

    # Weak classes must remain visible; never merged/hidden.
    weak = [str(name) for name in raw.get("weak_classes_must_remain_visible", [])]
    for required_name in WEAK_CLASSES_MUST_REMAIN_VISIBLE:
        _require(
            required_name in weak,
            f"weak_classes_must_remain_visible must include {required_name!r}.",
        )

    rare = [str(name) for name in raw.get("rare_classes", [])]
    _require(list(rare) == list(RARE_CLASSES), f"rare_classes must be {list(RARE_CLASSES)}.")

    # Output paths: all isolated, non-final, traversal-free.
    outputs = raw.get("outputs", {})
    _require(isinstance(outputs, dict), "outputs must be a mapping.")
    for key in REQUIRED_OUTPUT_KEYS:
        _require(key in outputs, f"outputs.{key} is required.")
    safe_outputs: dict[str, str] = {}
    for key, value in outputs.items():
        safe_outputs[str(key)] = safe_experiment_relative_path(str(value), f"outputs.{key}")

    checkpoint = safe_outputs["checkpoint"]
    _require(
        checkpoint.startswith("models/experiments/") and checkpoint.endswith(".pt"),
        "outputs.checkpoint must be a models/experiments/*.pt path.",
    )
    _require("a99" in checkpoint, "outputs.checkpoint must be an A9.9-specific name.")
    _require(
        safe_outputs["result_dir"].startswith("results/experiments/"),
        "outputs.result_dir must be under results/experiments/.",
    )
    _require(
        safe_outputs["report_md"].startswith("docs/experiments/"),
        "outputs.report_md must be under docs/experiments/.",
    )

    # Safety flags.
    safety = raw.get("safety", {})
    _require(isinstance(safety, dict), "safety must be a mapping.")
    for flag in (
        "no_test_tuning",
        "attack_rows_only",
        "validation_only_selection",
        "freeze_a9_head1",
        "no_final_overwrite",
    ):
        _require(safety.get(flag) is True, f"safety.{flag} must be true.")
    _require(
        safety.get("training_executed") is False,
        "safety.training_executed must be false in this prep/scaffolding phase.",
    )

    return AttackFamilySpecialistConfig(
        path=config_path,
        dataset=DATASET,
        task=TASK,
        status=str(raw["status"]),
        experiment=experiment,
        model_name=MODEL_NAME,
        seed=seed,
        input_dim=INPUT_DIM,
        num_attack_families=NUM_ATTACK_FAMILIES,
        hierarchical_data_dir=str(raw["hierarchical_data_dir"]),
        attack_family_label_mapping_path=str(raw["attack_family_label_mapping_path"]),
        frozen_a9_router=dict(router),
        protocol=str(raw["protocol"]),
        training_data=dict(training_data),
        model=dict(raw.get("model", {})),
        loss=dict(loss),
        class_imbalance=dict(imbalance),
        checkpoint_selection=dict(selection),
        rare_classes=rare,
        weak_classes_must_remain_visible=weak,
        outputs=safe_outputs,
        safety=dict(safety),
        raw=raw,
        project_root=Path(project_root) if project_root is not None else PROJECT_ROOT,
    )
