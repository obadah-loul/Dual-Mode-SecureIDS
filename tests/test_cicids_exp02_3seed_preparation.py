"""Lightweight CICIDS EXP02 3-seed preparation checks.

These tests validate YAML/config structure and CLI gating only. They do not run
training, preprocessing, evaluation, checkpoint creation, metric generation, or
full CICIDS array loading.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secureids.cli import _validate_train_hierarchical_cli_gate
from secureids.training.hierarchical_config import load_hierarchical_training_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_GROUP = "cicids_hierarchical_exp02_attack_loss_weight"
SEEDS = (42, 123, 999)
BASELINE_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
EXP01_CONFIG = (
    REPO_ROOT
    / "configs"
    / "training"
    / "experiments"
    / "cicids_hierarchical_exp01_head2_mlp_capacity.yaml"
)
EXP01_FAILURE_JSON = (
    REPO_ROOT / "results" / "audits" / "cicids_hierarchical_exp01_failure_analysis.json"
)


def _config_path(seed: int) -> Path:
    return (
        REPO_ROOT
        / "configs"
        / "training"
        / "experiments"
        / f"{EXP_GROUP}_seed{seed}.yaml"
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_exp02_seed_config_locks_contract_and_one_factor(seed: int) -> None:
    config = load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT)

    assert config.dataset == "cicids2018"
    assert config.task == "hierarchical"
    assert config.input_dim == 77
    assert config.attack_head_dim == 14
    assert config.raw["experiment"] == f"{EXP_GROUP}_seed{seed}"
    assert config.raw["experiment_group"] == EXP_GROUP
    assert config.raw["training"]["seed"] == seed
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.5
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


@pytest.mark.parametrize("seed", SEEDS)
def test_exp02_seed_outputs_are_isolated(seed: int) -> None:
    config = load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT)
    experiment = f"{EXP_GROUP}_seed{seed}"

    assert config.outputs["checkpoint"] == f"models/experiments/{experiment}.pt"
    assert config.outputs["result_dir"] == f"results/experiments/{experiment}"
    assert config.outputs["report_md"] == (
        f"docs/experiments/CICIDS_HIERARCHICAL_EXP02_ATTACK_LOSS_WEIGHT_SEED{seed}_REPORT.md"
    )
    assert config.outputs["manifest_json"] == (
        f"results/audits/hierarchical_training_manifest_{experiment}.json"
    )
    assert not config.outputs["checkpoint"].startswith("models/final/")
    assert not config.outputs["result_dir"].startswith("results/final/")
    assert config.outputs["checkpoint"] != "models/final/final_cicids_hierarchical.pt"
    assert config.outputs["result_dir"] != "results/final/hierarchical/cicids"
    # Completed experiments may already have checkpoints. Config loading must preserve them.
    assert config.outputs["checkpoint"].endswith(f"{experiment}.pt")


def test_exp02_seed_manifest_paths_are_unique() -> None:
    manifests = {
        load_hierarchical_training_config(_config_path(seed), project_root=REPO_ROOT).outputs[
            "manifest_json"
        ]
        for seed in SEEDS
    }

    assert len(manifests) == len(SEEDS)


def test_exp02_preserves_baseline_and_exp01_evidence() -> None:
    baseline = load_hierarchical_training_config(BASELINE_CONFIG, project_root=REPO_ROOT)
    exp01 = load_hierarchical_training_config(EXP01_CONFIG, project_root=REPO_ROOT)
    failure = json.loads(EXP01_FAILURE_JSON.read_text(encoding="utf-8"))

    assert baseline.outputs["checkpoint"] == "models/final/final_cicids_hierarchical.pt"
    assert (REPO_ROOT / baseline.outputs["checkpoint"]).exists()
    assert exp01.raw["model"]["attack_head_type"] == "mlp"
    assert failure["experiment_id"] == "cicids_hierarchical_exp01_head2_mlp_capacity"
    assert failure["next_step"] == "exp02_planning"


@pytest.mark.parametrize("seed", SEEDS)
def test_exp02_cli_gate_accepts_scoped_seed_configs(seed: int) -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="cicids",
        config_path=Path("configs/training/experiments") / f"{EXP_GROUP}_seed{seed}.yaml",
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )

    assert label == "CICIDS2018"


def test_exp02_cli_gate_rejects_unscoped_experiment_path() -> None:
    with pytest.raises(ValueError, match="approved"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="cicids",
            config_path=Path("configs/training/cicids_hierarchical_exp02_attack_loss_weight_seed42.yaml"),
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=14,
            config_task="hierarchical",
        )
