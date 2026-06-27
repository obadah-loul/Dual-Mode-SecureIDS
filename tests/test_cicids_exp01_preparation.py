"""Lightweight CICIDS EXP01 preparation checks.

These tests validate config structure and CLI gating only. They do not run
training, preprocessing, long evaluation, checkpoint creation, or metric
generation, and they do not load full CICIDS arrays.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from secureids.cli import _validate_train_hierarchical_cli_gate
from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfigError,
    load_hierarchical_training_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_ID = "cicids_hierarchical_exp01_head2_mlp_capacity"
EXP_CONFIG = REPO_ROOT / "configs" / "training" / "experiments" / f"{EXP_ID}.yaml"
BASELINE_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"


def test_exp01_config_exists_and_locks_cicids_contract() -> None:
    config = load_hierarchical_training_config(EXP_CONFIG, project_root=REPO_ROOT)

    assert config.dataset == "cicids2018"
    assert config.task == "hierarchical"
    assert config.input_dim == 77
    assert config.attack_head_dim == 14
    assert config.raw["experiment"] == EXP_ID
    assert config.raw["baseline_checkpoint"] == "models/final/final_cicids_hierarchical.pt"
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


def test_exp01_outputs_are_isolated_from_baseline() -> None:
    config = load_hierarchical_training_config(EXP_CONFIG, project_root=REPO_ROOT)
    baseline = load_hierarchical_training_config(BASELINE_CONFIG, project_root=REPO_ROOT)

    assert baseline.outputs["checkpoint"] == "models/final/final_cicids_hierarchical.pt"
    assert config.outputs["checkpoint"] == f"models/experiments/{EXP_ID}.pt"
    assert config.outputs["result_dir"] == f"results/experiments/{EXP_ID}"
    assert config.outputs["report_md"] == (
        "docs/experiments/CICIDS_HIERARCHICAL_EXP01_HEAD2_MLP_CAPACITY_REPORT.md"
    )
    assert config.outputs["checkpoint"] != baseline.outputs["checkpoint"]
    assert config.outputs["result_dir"] != baseline.outputs["result_dir"]
    assert config.outputs["report_md"] != baseline.outputs["report_md"]
    assert not config.outputs["checkpoint"].startswith("models/final/")
    assert not config.outputs["result_dir"].startswith("results/final/")


def test_exp01_selected_variable_is_head2_mlp_capacity_only() -> None:
    config = load_hierarchical_training_config(EXP_CONFIG, project_root=REPO_ROOT)
    baseline = load_hierarchical_training_config(BASELINE_CONFIG, project_root=REPO_ROOT)

    assert baseline.raw["model"].get("attack_head_type", "linear") == "linear"
    assert config.raw["model"]["attack_head_type"] == "mlp"
    assert config.raw["model"]["attack_head_hidden_dim"] == 128
    assert config.raw["model"]["attack_head_norm"] is True
    assert config.raw["model"]["attack_head_dropout"] == 0.20
    assert config.raw["model"]["hidden_dims"] == baseline.raw["model"]["hidden_dims"]
    assert config.raw["model"]["dropout"] == baseline.raw["model"]["dropout"]
    assert config.raw["model"]["normalization"] == baseline.raw["model"]["normalization"]
    assert config.raw["loss"]["binary_loss_weight"] == baseline.raw["loss"]["binary_loss_weight"]
    assert config.raw["loss"]["attack_loss_weight"] == baseline.raw["loss"]["attack_loss_weight"]
    assert config.raw["training"] == baseline.raw["training"]


def test_exp01_cli_gate_accepts_scoped_config_and_rejects_cross_pair() -> None:
    label = _validate_train_hierarchical_cli_gate(
        dataset_selection="cicids",
        config_path=Path("configs/training/experiments") / f"{EXP_ID}.yaml",
        config_dataset="cicids2018",
        config_input_dim=77,
        config_attack_head_dim=14,
        config_task="hierarchical",
    )
    assert label == "CICIDS2018"

    with pytest.raises(ValueError, match="does not match"):
        _validate_train_hierarchical_cli_gate(
            dataset_selection="unsw",
            config_path=Path("configs/training/experiments") / f"{EXP_ID}.yaml",
            config_dataset="cicids2018",
            config_input_dim=77,
            config_attack_head_dim=14,
            config_task="hierarchical",
        )


def test_exp01_loader_rejects_baseline_overwrite_paths(tmp_path: Path) -> None:
    data = yaml.safe_load(EXP_CONFIG.read_text(encoding="utf-8"))
    data["outputs"]["checkpoint"] = "models/final/final_cicids_hierarchical.pt"
    invalid_path = tmp_path / "cicids_hierarchical_exp01_bad.yaml"
    invalid_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(HierarchicalTrainingConfigError, match="unexpected CICIDS experiment output"):
        load_hierarchical_training_config(invalid_path, project_root=REPO_ROOT)
