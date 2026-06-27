"""Torch-free tests for hierarchical training and smoke config safety.

These tests validate Task A6 config structure only. They do not run
hierarchical training, final evaluation, checkpointing, or metric generation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from secureids.training.hierarchical_config import (
    HierarchicalTrainingConfigError,
    load_hierarchical_smoke_config,
    load_hierarchical_training_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "config_name,dataset,input_dim,attack_head_dim,checkpoint_name",
    [
        (
            "cicids2018_hierarchical.yaml",
            "cicids2018",
            77,
            14,
            "final_cicids_hierarchical.pt",
        ),
        (
            "unsw_nb15_hierarchical.yaml",
            "unsw_nb15",
            192,
            9,
            "final_unsw_hierarchical.pt",
        ),
    ],
)
def test_full_hierarchical_configs_lock_dataset_dims_and_outputs(
    config_name: str,
    dataset: str,
    input_dim: int,
    attack_head_dim: int,
    checkpoint_name: str,
):
    config = load_hierarchical_training_config(
        REPO_ROOT / "configs" / "training" / config_name,
        project_root=REPO_ROOT,
    )

    assert config.dataset == dataset
    assert config.model_name == "SecureIDSHierarchicalAdvancedNet"
    assert config.input_dim == input_dim
    assert config.attack_head_dim == attack_head_dim
    assert config.outputs["checkpoint"].endswith(checkpoint_name)
    assert config.raw["loss"]["type"] == "masked_multi_task"
    assert config.raw["loss"]["ignore_index"] == -1
    assert config.raw["checkpoint_selection"]["use_validation_only"] is True
    assert config.raw["checkpoint_selection"]["select_by_test_metrics"] is False
    assert config.raw["class_imbalance"]["compute_weights_from"] == "train_only"
    assert config.raw["class_imbalance"]["allow_test_based_weights"] is False
    assert (
        config.raw["class_imbalance"]["attack_family_class_weighting"]
        == "train_split_sqrt_inverse_frequency_mean_normalized_capped"
    )
    assert config.raw["class_imbalance"]["class_weight_max_clip"] == 10.0
    assert config.raw["class_weights"]["binary"] == {
        "enabled": True,
        "source_split": "train",
        "method": "balanced",
        "normalize_mean": True,
        "max_weight": 10.0,
        "use_validation_labels": False,
        "use_test_labels": False,
    }
    assert config.raw["class_weights"]["attack_family"] == {
        "enabled": True,
        "source_split": "train_attack_rows_only",
        "method": "sqrt_inverse_frequency",
        "normalize_mean": True,
        "max_weight": 10.0,
        "use_validation_labels": False,
        "use_test_labels": False,
        "oversampling": False,
    }
    assert config.raw["safety"]["full_training_run_in_a6"] is False
    assert config.raw["safety"]["final_checkpoint_created_in_a6"] is False
    assert config.raw["safety"]["final_metrics_created_in_a6"] is False


@pytest.mark.parametrize(
    "config_name,dataset,input_dim,attack_head_dim",
    [
        ("smoke_cicids2018_hierarchical.yaml", "cicids2018", 77, 14),
        ("smoke_unsw_nb15_hierarchical.yaml", "unsw_nb15", 192, 9),
    ],
)
def test_smoke_hierarchical_configs_are_non_final_and_safe(
    config_name: str,
    dataset: str,
    input_dim: int,
    attack_head_dim: int,
):
    config = load_hierarchical_smoke_config(
        REPO_ROOT / "configs" / "training" / config_name,
        project_root=REPO_ROOT,
    )

    assert config.dataset == dataset
    assert config.input_dim == input_dim
    assert config.attack_head_dim == attack_head_dim
    assert config.smoke["enabled"] is True
    assert config.smoke["non_final"] is True
    assert config.smoke["save_checkpoint"] is False
    assert config.smoke["final_metrics"] is False
    assert config.smoke["max_epochs"] == 1
    assert not str(config.smoke["output_json"]).startswith("results/final")
    assert config.safety["no_full_training"] is True
    assert config.safety["do_not_report_as_final"] is True


def test_full_config_rejects_wrong_dataset_dimension(tmp_path: Path):
    config_path = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["input_dim"] = 190
    invalid_path = tmp_path / "invalid_cicids_hierarchical.yaml"
    invalid_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(HierarchicalTrainingConfigError):
        load_hierarchical_training_config(invalid_path, project_root=REPO_ROOT)


def test_a9_6_head2_loss_weight_config_is_one_factor_experiment():
    config = load_hierarchical_training_config(
        REPO_ROOT
        / "configs"
        / "training"
        / "unsw_nb15_hierarchical_a9_6_head2_loss_weight.yaml",
        project_root=REPO_ROOT,
    )

    assert config.dataset == "unsw_nb15"
    assert config.input_dim == 192
    assert config.attack_head_dim == 9
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.5
    assert config.outputs["checkpoint"] == (
        "models/final/final_unsw_hierarchical_a9_6_head2_loss_weight.pt"
    )
    assert config.outputs["result_dir"] == (
        "results/final/hierarchical/unsw_a9_6_head2_loss_weight"
    )
    assert config.outputs["manifest_json"] == (
        "results/audits/"
        "hierarchical_training_manifest_unsw_nb15_a9_6_head2_loss_weight.json"
    )
    assert config.raw["class_imbalance"]["class_weight_max_clip"] == 10.0
    assert config.raw["class_weights"]["attack_family"]["oversampling"] is False
    assert config.raw["checkpoint_selection"]["use_validation_only"] is True
    assert config.raw["checkpoint_selection"]["select_by_test_metrics"] is False


def test_a9_7_head2_branch_capacity_config_is_one_factor_experiment():
    config = load_hierarchical_training_config(
        REPO_ROOT
        / "configs"
        / "training"
        / "unsw_nb15_hierarchical_a9_7_head2_branch_capacity.yaml",
        project_root=REPO_ROOT,
    )

    assert config.dataset == "unsw_nb15"
    assert config.input_dim == 192
    assert config.attack_head_dim == 9
    # The ONE changed factor vs A9: a non-linear Head 2 (mlp) branch.
    assert config.raw["model"]["attack_head_type"] == "mlp"
    assert config.raw["model"]["attack_head_hidden_dim"] == 128
    assert config.raw["model"]["attack_head_norm"] is True
    assert config.raw["model"]["attack_head_dropout"] == 0.20
    # Everything that must stay at the A9 baseline.
    assert config.raw["model"]["hidden_dims"] == [256, 128, 128]
    assert config.raw["loss"]["binary_loss_weight"] == 1.0
    assert config.raw["loss"]["attack_loss_weight"] == 1.0
    assert config.raw["class_imbalance"]["class_weight_max_clip"] == 10.0
    assert config.raw["class_imbalance"]["compute_weights_from"] == "train_only"
    assert config.raw["class_weights"]["attack_family"]["oversampling"] is False
    assert config.raw["checkpoint_selection"]["use_validation_only"] is True
    assert config.raw["checkpoint_selection"]["select_by_test_metrics"] is False
    assert config.raw["training"]["seed"] == 42
    assert config.raw["training"]["max_epochs"] == 40
    # Separate, namespaced output paths (never A9 / A9.6).
    assert config.outputs["checkpoint"] == (
        "models/final/final_unsw_hierarchical_a9_7_head2_branch_capacity.pt"
    )
    assert config.outputs["result_dir"] == (
        "results/final/hierarchical/unsw_a9_7_head2_branch_capacity"
    )
    assert config.outputs["manifest_json"] == (
        "results/audits/"
        "hierarchical_training_manifest_unsw_nb15_a9_7_head2_branch_capacity.json"
    )
    assert config.outputs["report_md"] == (
        "docs/HIERARCHICAL_TRAINING_REPORT_A9_7_HEAD2_BRANCH_CAPACITY.md"
    )


def test_unsw_a11_enhanced_feature_protocol_config_is_isolated_experiment():
    config = load_hierarchical_training_config(
        REPO_ROOT
        / "configs"
        / "training"
        / "experiments"
        / "unsw_a11_enhanced_feature_protocol_seed42.yaml",
        project_root=REPO_ROOT,
    )

    assert config.dataset == "unsw_nb15"
    assert config.input_dim == 192
    assert config.attack_head_dim == 9
    assert config.hierarchical_data_dir == "data/processed/unsw_a11_enhanced/hierarchical"
    assert config.raw["protocol_name"] == "UNSW A11 Enhanced Feature Protocol"
    assert config.raw["class_imbalance"]["compute_weights_from"] == "train_only"
    assert config.raw["class_imbalance"]["allow_test_based_weights"] is False
    assert config.outputs["checkpoint"] == (
        "models/experiments/unsw_a11_enhanced_feature_protocol_seed42.pt"
    )
    assert config.outputs["result_dir"] == (
        "results/experiments/unsw_a11_enhanced_feature_protocol_seed42/"
    )
    assert config.outputs["report_md"] == (
        "docs/experiments/UNSW_A11_ENHANCED_FEATURE_PROTOCOL_SEED42_REPORT.md"
    )
    assert not any(
        str(path).replace("\\", "/").startswith(("models/final", "results/final"))
        for path in config.outputs.values()
    )


def test_smoke_config_rejects_checkpoint_saving(tmp_path: Path):
    config_path = (
        REPO_ROOT / "configs" / "training" / "smoke_unsw_nb15_hierarchical.yaml"
    )
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["smoke"]["save_checkpoint"] = True
    invalid_path = tmp_path / "invalid_smoke_unsw_hierarchical.yaml"
    invalid_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(HierarchicalTrainingConfigError):
        load_hierarchical_smoke_config(invalid_path, project_root=REPO_ROOT)


def test_smoke_config_rejects_final_output_paths(tmp_path: Path):
    config_path = (
        REPO_ROOT / "configs" / "training" / "smoke_cicids2018_hierarchical.yaml"
    )
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["smoke"]["output_json"] = "results/final/hierarchical/smoke.json"
    invalid_path = tmp_path / "invalid_smoke_cicids_hierarchical.yaml"
    invalid_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(HierarchicalTrainingConfigError):
        load_hierarchical_smoke_config(invalid_path, project_root=REPO_ROOT)
