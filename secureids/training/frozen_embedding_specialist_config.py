"""Torch-free config validation for the A9.10 frozen-embedding specialist."""

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
TASK = "frozen_embedding_specialist"
MODEL_NAME = "FrozenEmbeddingSpecialistHead"
INPUT_DIM = 192
EMBEDDING_DIM = 128
NUM_ATTACK_FAMILIES = 9
A9_CHECKPOINT = "models/final/final_unsw_hierarchical.pt"
A9_IDENTITY = "A9 corrected-protocol hierarchical baseline"
ALLOWED_STATUS = "not_run_yet"
ALLOWED_HEAD_TYPES = ("linear", "shallow_mlp")
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
    "embedding_dim",
    "num_attack_families",
    "hierarchical_data_dir",
    "attack_family_label_mapping_path",
    "frozen_a9",
    "protocol",
    "training_data",
    "embedding",
    "model",
    "loss",
    "class_imbalance",
    "training",
    "checkpoint_selection",
    "evaluation",
    "baselines",
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
    "manifest_json",
    "report_md",
)


class FrozenEmbeddingSpecialistConfigError(ValueError):
    """Raised when an A9.10 config is unsafe or malformed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FrozenEmbeddingSpecialistConfigError(message)


def is_final_path(path_str: str) -> bool:
    normalized = str(path_str).replace("\\", "/").lstrip("./")
    return normalized.startswith("models/final") or normalized.startswith("results/final")


def safe_experiment_relative_path(path_str: str, label: str) -> str:
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
    try:
        safe_experiment_relative_path(path_str, "path")
    except FrozenEmbeddingSpecialistConfigError:
        return False
    return True


@dataclass(frozen=True)
class FrozenEmbeddingSpecialistConfig:
    path: Path
    dataset: str
    task: str
    status: str
    experiment: str
    model_name: str
    seed: int
    input_dim: int
    embedding_dim: int
    num_attack_families: int
    hierarchical_data_dir: str
    attack_family_label_mapping_path: str
    frozen_a9: dict[str, Any]
    protocol: str
    training_data: dict[str, Any]
    embedding: dict[str, Any]
    model: dict[str, Any]
    loss: dict[str, Any]
    class_imbalance: dict[str, Any]
    training: dict[str, Any]
    checkpoint_selection: dict[str, Any]
    evaluation: dict[str, Any]
    baselines: dict[str, Any]
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
    if yaml is None:  # pragma: no cover
        raise FrozenEmbeddingSpecialistConfigError("PyYAML is required.")
    if not path.exists():
        raise FrozenEmbeddingSpecialistConfigError(f"Config not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _require(isinstance(loaded, dict), f"Config root must be a mapping: {path}")
    return loaded


def load_frozen_embedding_specialist_config(
    path: Path | str,
    project_root: Path | None = None,
) -> FrozenEmbeddingSpecialistConfig:
    """Load and validate an A9.10 config without training or writing files."""

    config_path = Path(path)
    raw = _load_yaml(config_path)
    missing = [key for key in REQUIRED_KEYS if key not in raw]
    _require(not missing, f"A9.10 config missing keys: {sorted(missing)}")

    _require(str(raw["dataset"]) == DATASET, f"dataset must be {DATASET!r}.")
    _require(str(raw["task"]) == TASK, f"task must be {TASK!r}.")
    _require(str(raw["status"]) == ALLOWED_STATUS, f"status must be {ALLOWED_STATUS!r}.")
    _require(str(raw["model_name"]) == MODEL_NAME, f"model_name must be {MODEL_NAME!r}.")
    _require(int(raw["input_dim"]) == INPUT_DIM, f"input_dim must be {INPUT_DIM}.")
    _require(int(raw["embedding_dim"]) == EMBEDDING_DIM, f"embedding_dim must be {EMBEDDING_DIM}.")
    _require(
        int(raw["num_attack_families"]) == NUM_ATTACK_FAMILIES,
        f"num_attack_families must be {NUM_ATTACK_FAMILIES}.",
    )
    seed = int(raw["seed"])
    _require(seed >= 0, "seed must be >= 0.")

    experiment = str(raw["experiment"])
    _require(
        experiment.startswith("unsw_a10_frozen_embedding_specialist"),
        "experiment must start with 'unsw_a10_frozen_embedding_specialist'.",
    )

    frozen_a9 = raw.get("frozen_a9", {})
    _require(isinstance(frozen_a9, dict), "frozen_a9 must be a mapping.")
    _require(
        str(frozen_a9.get("checkpoint")).replace("\\", "/") == A9_CHECKPOINT,
        f"frozen_a9.checkpoint must be {A9_CHECKPOINT!r}.",
    )
    _require(str(frozen_a9.get("identity")) == A9_IDENTITY, f"frozen_a9.identity must be {A9_IDENTITY!r}.")
    _require(frozen_a9.get("trainable") is False, "frozen_a9.trainable must be false.")
    _require(frozen_a9.get("freeze_encoder") is True, "frozen_a9.freeze_encoder must be true.")
    _require(frozen_a9.get("freeze_binary_router") is True, "frozen_a9.freeze_binary_router must be true.")

    training_data = raw.get("training_data", {})
    _require(isinstance(training_data, dict), "training_data must be a mapping.")
    _require(training_data.get("attack_rows_only") is True, "training_data.attack_rows_only must be true.")
    _require(str(training_data.get("train_split")) == "train", "training_data.train_split must be 'train'.")

    embedding = raw.get("embedding", {})
    _require(isinstance(embedding, dict), "embedding must be a mapping.")
    _require(
        str(embedding.get("source")) == "a9_forward_embedding",
        "embedding.source must be 'a9_forward_embedding'.",
    )
    _require(int(embedding.get("dim")) == EMBEDDING_DIM, f"embedding.dim must be {EMBEDDING_DIM}.")
    _require(embedding.get("fixed_features") is True, "embedding.fixed_features must be true.")

    model = raw.get("model", {})
    _require(isinstance(model, dict), "model must be a mapping.")
    head_type = str(model.get("head_type", "")).lower()
    _require(head_type in ALLOWED_HEAD_TYPES, f"model.head_type must be one of {ALLOWED_HEAD_TYPES}.")
    dropout = float(model.get("dropout"))
    _require(0.0 <= dropout < 1.0, "model.dropout must be in [0.0, 1.0).")

    loss = raw.get("loss", {})
    _require(isinstance(loss, dict), "loss must be a mapping.")
    _require(
        str(loss.get("type")) == "cross_entropy_attack_rows_only",
        "loss.type must be 'cross_entropy_attack_rows_only'.",
    )
    label_smoothing = float(loss.get("label_smoothing", 0.0))
    _require(0.0 <= label_smoothing < 0.5, "loss.label_smoothing must be in [0.0, 0.5).")

    imbalance = raw.get("class_imbalance", {})
    _require(isinstance(imbalance, dict), "class_imbalance must be a mapping.")
    _require(imbalance.get("compute_weights_from") == "train_only", "class weights must come from train_only.")
    _require(imbalance.get("allow_test_based_weights") is False, "test-based class weights must be disabled.")
    temperature = float(imbalance.get("temperature", 0.5))
    _require(0.0 <= temperature <= 1.0, "class_imbalance.temperature must be in [0.0, 1.0].")

    training = raw.get("training", {})
    _require(isinstance(training, dict), "training must be a mapping.")
    _require(float(training.get("weight_decay", 0.0)) > 0.0, "training.weight_decay must be > 0.")
    _require(int(training.get("early_stopping_patience", 0)) > 0, "training.early_stopping_patience must be > 0.")

    selection = raw.get("checkpoint_selection", {})
    _require(isinstance(selection, dict), "checkpoint_selection must be a mapping.")
    _require(selection.get("use_validation_only") is True, "checkpoint_selection.use_validation_only must be true.")
    _require(selection.get("select_by_test_metrics") is False, "checkpoint_selection.select_by_test_metrics must be false.")
    _require(
        str(selection.get("monitor")) in {"val_attack_family_macro_f1", "val_generalization_score"},
        "checkpoint_selection.monitor must be validation-only.",
    )

    evaluation = raw.get("evaluation", {})
    _require(isinstance(evaluation, dict), "evaluation must be a mapping.")
    _require(evaluation.get("separate_oracle_and_routed") is True, "oracle/routed metrics must be separated.")
    _require(evaluation.get("do_not_report_oracle_as_routed") is True, "oracle must not be reported as routed.")

    baselines = raw.get("baselines", {})
    _require(isinstance(baselines, dict), "baselines must be a mapping.")
    _require(float(baselines.get("a9_attack_family_macro_f1")) == 0.500429, "A9 attack baseline mismatch.")
    _require(float(baselines.get("a9_rare_class_macro_f1")) == 0.385669, "A9 rare baseline mismatch.")

    weak = [str(name) for name in raw.get("weak_classes_must_remain_visible", [])]
    for required_name in WEAK_CLASSES_MUST_REMAIN_VISIBLE:
        _require(required_name in weak, f"weak_classes_must_remain_visible must include {required_name!r}.")
    rare = [str(name) for name in raw.get("rare_classes", [])]
    _require(rare == list(RARE_CLASSES), f"rare_classes must be {list(RARE_CLASSES)}.")

    outputs = raw.get("outputs", {})
    _require(isinstance(outputs, dict), "outputs must be a mapping.")
    for key in REQUIRED_OUTPUT_KEYS:
        _require(key in outputs, f"outputs.{key} is required.")
    safe_outputs = {
        str(key): safe_experiment_relative_path(str(value), f"outputs.{key}")
        for key, value in outputs.items()
    }
    checkpoint = safe_outputs["checkpoint"]
    _require(
        checkpoint.startswith("models/experiments/") and checkpoint.endswith(".pt"),
        "outputs.checkpoint must be a models/experiments/*.pt path.",
    )
    _require("a10" in checkpoint, "outputs.checkpoint must be an A9.10-specific name.")
    _require(safe_outputs["result_dir"].startswith("results/experiments/"), "outputs.result_dir must be under results/experiments/.")
    _require(safe_outputs["report_md"].startswith("docs/experiments/"), "outputs.report_md must be under docs/experiments/.")

    safety = raw.get("safety", {})
    _require(isinstance(safety, dict), "safety must be a mapping.")
    for flag in (
        "no_test_tuning",
        "attack_rows_only",
        "validation_only_selection",
        "freeze_a9_encoder",
        "freeze_a9_binary_router",
        "no_final_overwrite",
        "do_not_report_oracle_as_routed",
        "do_not_replace_a9_without_approval",
    ):
        _require(safety.get(flag) is True, f"safety.{flag} must be true.")
    for flag in ("training_executed", "allow_overwrite", "checkpoint_created"):
        _require(safety.get(flag) is False, f"safety.{flag} must be false.")

    return FrozenEmbeddingSpecialistConfig(
        path=config_path,
        dataset=DATASET,
        task=TASK,
        status=str(raw["status"]),
        experiment=experiment,
        model_name=MODEL_NAME,
        seed=seed,
        input_dim=INPUT_DIM,
        embedding_dim=EMBEDDING_DIM,
        num_attack_families=NUM_ATTACK_FAMILIES,
        hierarchical_data_dir=str(raw["hierarchical_data_dir"]),
        attack_family_label_mapping_path=str(raw["attack_family_label_mapping_path"]),
        frozen_a9=dict(frozen_a9),
        protocol=str(raw["protocol"]),
        training_data=dict(training_data),
        embedding=dict(embedding),
        model=dict(model),
        loss=dict(loss),
        class_imbalance=dict(imbalance),
        training=dict(training),
        checkpoint_selection=dict(selection),
        evaluation=dict(evaluation),
        baselines=dict(baselines),
        rare_classes=rare,
        weak_classes_must_remain_visible=weak,
        outputs=safe_outputs,
        safety=dict(safety),
        raw=raw,
        project_root=Path(project_root) if project_root is not None else PROJECT_ROOT,
    )
