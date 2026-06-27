"""Lightweight CICIDS EXP03 screening preparation checks.

These tests validate YAML/config structure and CLI gating only. They do not run
training, preprocessing, evaluation, checkpoint creation, metric generation, or
full CICIDS array loading.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from secureids.cli import _validate_train_hierarchical_cli_gate
from secureids.training.hierarchical_config import load_hierarchical_training_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_GROUP = "cicids_hierarchical_exp03_attack_loss_weight_conservative_sweep"
EXP_PREFIX = "cicids_hierarchical_exp03_attack_loss_weight"
BASELINE_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
BASELINE_CHECKPOINT = REPO_ROOT / "models" / "final" / "final_cicids_hierarchical.pt"
EXP01_CONFIG = (
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp01_head2_mlp_capacity.yaml"
)
EXP02_CONFIGS = (
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp02_attack_loss_weight_seed42.yaml",
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp02_attack_loss_weight_seed123.yaml",
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp02_attack_loss_weight_seed999.yaml",
)
SCREENING_CASES = (
    ("125", 1.25),
    ("135", 1.35),
)


def _config_path(label: str) -> Path:
    return (
        REPO_ROOT
        / "configs"
        / "training"
        / "experiments"
        / f"{EXP_PREFIX}_{label}_seed42.yaml"
    )


@pytest.mark.parametrize("label,weight", SCREENING_CASES)
def test_exp03_screening_config_locks_contract_and_one_factor(
    label: str,
    weight: float,
) -> None:
    config = load_hierarchical_training_config(_config_path(label), project_root=REPO_ROOT)

    assert config.dataset == "cicids2018"
    assert config.task == "hierarchical"
    assert config.input_dim == 77
    assert config.attack_head_dim == 14
    assert config.raw["experiment"] == f"{EXP_PREFIX}_{label}_seed42"
    assert config.raw["experiment_group"] == EXP_GROUP
    assert config.raw["training"]["seed"] == 42
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == weight
    assert config.raw["model"].get("attack_head_type", "linear") == "linear"
    assert "attack_head_hidden_dim" not in config.raw["model"]
    assert config.raw["checkpoint_selection"]["use_validation_only"] is True
    assert config.raw["checkpoint_selection"]["select_by_test_metrics"] is False
    assert config.raw["checkpoint_selection"]["final_test_once_after_best_validation"] is True
    assert config.raw["class_imbalance"]["compute_weights_from"] == "train_only"
    assert config.raw["class_imbalance"]["allow_test_based_weights"] is False
    assert config.raw["class_weights"]["binary"]["use_validation_labels"] is False
    assert config.raw["class_weights"]["binary"]["use_test_labels"] is False
    assert config.raw["class_weights"]["attack_family"]["use_validation_labels"] is False
    assert config.raw["class_weights"]["attack_family"]["use_test_labels"] is False
    assert config.raw["class_weights"]["attack_family"]["oversampling"] is False


@pytest.mark.parametrize("label,weight", SCREENING_CASES)
def test_exp03_screening_outputs_are_isolated(label: str, weight: float) -> None:
    config = load_hierarchical_training_config(_config_path(label), project_root=REPO_ROOT)
    experiment = f"{EXP_PREFIX}_{label}_seed42"

    assert config.outputs["checkpoint"] == f"models/experiments/{experiment}.pt"
    assert config.outputs["result_dir"] == f"results/experiments/{experiment}"
    assert config.outputs["report_md"] == (
        f"docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_{label}_SEED42_REPORT.md"
    )
    assert config.outputs["manifest_json"] == (
        f"results/audits/hierarchical_training_manifest_{experiment}.json"
    )
    assert config.outputs["checkpoint"].startswith("models/experiments/")
    assert config.outputs["result_dir"].startswith("results/experiments/")
    assert config.outputs["report_md"].startswith("docs/experiments/")
    assert config.outputs["manifest_json"].startswith("results/audits/")
    assert config.outputs["checkpoint"] != "models/final/final_cicids_hierarchical.pt"
    assert config.outputs["result_dir"] != "results/final/hierarchical/cicids"
    assert not (REPO_ROOT / config.outputs["checkpoint"]).exists()


def test_exp03_manifest_paths_are_unique() -> None:
    manifests = {
        load_hierarchical_training_config(_config_path(label), project_root=REPO_ROOT).outputs[
            "manifest_json"
        ]
        for label, _ in SCREENING_CASES
    }

    assert len(manifests) == len(SCREENING_CASES)


def test_exp03_preserves_baseline_exp01_and_exp02_references() -> None:
    baseline = load_hierarchical_training_config(BASELINE_CONFIG, project_root=REPO_ROOT)
    exp01 = load_hierarchical_training_config(EXP01_CONFIG, project_root=REPO_ROOT)
    exp02_configs = [
        load_hierarchical_training_config(path, project_root=REPO_ROOT) for path in EXP02_CONFIGS
    ]

    assert baseline.outputs["checkpoint"] == "models/final/final_cicids_hierarchical.pt"
    assert BASELINE_CHECKPOINT.exists()
    assert exp01.raw["model"]["attack_head_type"] == "mlp"
    assert exp01.raw["loss"]["attack_loss_weight"] == 1.0
    assert [cfg.raw["loss"]["attack_loss_weight"] for cfg in exp02_configs] == [1.5, 1.5, 1.5]
    assert [cfg.raw["training"]["seed"] for cfg in exp02_configs] == [42, 123, 999]


@pytest.mark.parametrize("label,weight", SCREENING_CASES)
def test_exp03_cli_gate_accepts_scoped_screening_configs(label: str, weight: float) -> None:
    label_result = _validate_train_hierarchical_cli_gate(
        dataset_selection="cicids",
        config_path=Path("configs/training/experiments") / f"{EXP_PREFIX}_{label}_seed42.yaml",
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )

    assert label_result == "CICIDS2018"


def test_exp03_cli_gate_rejects_unscoped_experiment_path() -> None:
    with pytest.raises(ValueError, match="approved"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="cicids",
            config_path=Path("configs/training/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.yaml"),
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=14,
            config_task="hierarchical",
        )
