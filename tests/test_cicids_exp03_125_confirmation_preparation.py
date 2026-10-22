"""Lightweight CICIDS EXP03 1.25 confirmation preparation checks.

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
EXP_GROUP = "cicids_hierarchical_exp03_attack_loss_weight_125_confirmation"
EXP_PREFIX = "cicids_hierarchical_exp03_attack_loss_weight_125"
BASELINE_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
BASELINE_CHECKPOINT = REPO_ROOT / "models" / "final" / "final_cicids_hierarchical.pt"
SEED42_CONFIG = (
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp03_attack_loss_weight_125_seed42.yaml"
)
SEED42_CHECKPOINT = (
    REPO_ROOT
    / "models"
    / "experiments"
    / "cicids_hierarchical_exp03_attack_loss_weight_125_seed42.pt"
)
SEED42_REPORT = (
    REPO_ROOT
    / "docs"
    / "experiments"
    / "CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED42_REPORT.md"
)
SEED42_MANIFEST = (
    REPO_ROOT
    / "results"
    / "audits"
    / "hierarchical_training_manifest_cicids_hierarchical_exp03_attack_loss_weight_125_seed42.json"
)
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
CONFIRMATION_SEEDS = (123, 999)


def _config_path(seed: int) -> Path:
    return (
        REPO_ROOT
        / "configs"
        / "training"
        / "experiments"
        / f"{EXP_PREFIX}_seed{seed}.yaml"
    )


@pytest.mark.parametrize("seed", CONFIRMATION_SEEDS)
def test_exp03_125_confirmation_config_locks_contract_and_one_factor(seed: int) -> None:
    config = load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT)

    assert config.dataset == "cicids2018"
    assert config.task == "hierarchical"
    assert config.input_dim == 77
    assert config.attack_head_dim == 14
    assert config.raw["experiment"] == f"{EXP_PREFIX}_seed{seed}"
    assert config.raw["experiment_group"] == EXP_GROUP
    assert config.raw["training"]["seed"] == seed
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.25
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


@pytest.mark.parametrize("seed", CONFIRMATION_SEEDS)
def test_exp03_125_confirmation_outputs_are_isolated(seed: int) -> None:
    config = load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT)
    experiment = f"{EXP_PREFIX}_seed{seed}"

    assert config.outputs["checkpoint"] == f"models/experiments/{experiment}.pt"
    assert config.outputs["result_dir"] == f"results/experiments/{experiment}"
    assert config.outputs["report_md"] == (
        f"docs/experiments/CICIDS_HIERARCHICAL_EXP03_ATTACK_LOSS_WEIGHT_125_SEED{seed}_REPORT.md"
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
    # Completed experiments may already have checkpoints. Config loading must preserve them.
    assert config.outputs["checkpoint"].endswith(f"{experiment}.pt")


def test_exp03_125_confirmation_manifest_paths_are_unique() -> None:
    manifests = {
        load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT).outputs[
            "manifest_json"
        ]
        for seed in CONFIRMATION_SEEDS
    }

    assert len(manifests) == len(CONFIRMATION_SEEDS)


def test_exp03_125_confirmation_preserves_existing_artifacts() -> None:
    baseline = load_hierarchical_training_config(BASELINE_CONFIG, project_root=REPO_ROOT)
    seed42 = load_hierarchical_training_config(SEED42_CONFIG, project_root=REPO_ROOT)
    exp01 = load_hierarchical_training_config(EXP01_CONFIG, project_root=REPO_ROOT)
    exp02_configs = [
        load_hierarchical_training_config(path, project_root=REPO_ROOT) for path in EXP02_CONFIGS
    ]

    assert baseline.outputs["checkpoint"] == "models/final/final_cicids_hierarchical.pt"
    assert BASELINE_CHECKPOINT.exists()
    assert seed42.raw["training"]["seed"] == 42
    assert seed42.raw["loss"]["attack_loss_weight"] == 1.25
    assert seed42.outputs["checkpoint"] == (
        "models/experiments/cicids_hierarchical_exp03_attack_loss_weight_125_seed42.pt"
    )
    assert SEED42_CHECKPOINT.exists()
    assert SEED42_REPORT.exists()
    assert SEED42_MANIFEST.exists()
    assert exp01.raw["model"]["attack_head_type"] == "mlp"
    assert [cfg.raw["loss"]["attack_loss_weight"] for cfg in exp02_configs] == [1.5, 1.5, 1.5]
    assert [cfg.raw["training"]["seed"] for cfg in exp02_configs] == [42, 123, 999]


@pytest.mark.parametrize("seed", CONFIRMATION_SEEDS)
def test_exp03_125_confirmation_cli_gate_accepts_scoped_configs(seed: int) -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="cicids",
        config_path=Path("configs/training/experiments") / f"{EXP_PREFIX}_seed{seed}.yaml",
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )

    assert label == "CICIDS2018"


def test_exp03_125_confirmation_cli_gate_rejects_unscoped_experiment_path() -> None:
    with pytest.raises(ValueError, match="approved"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="cicids",
            config_path=Path("configs/training/cicids_hierarchical_exp03_attack_loss_weight_125_seed123.yaml"),
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=14,
            config_task="hierarchical",
        )
