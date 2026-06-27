"""Focused tests for Task A8 hierarchical full-training readiness.

The synthetic project data is tiny and local to pytest tmp directories. These
tests run readiness checks only; they do not train, backpropagate, save
checkpoints, or create final metrics.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from secureids.training.hierarchical_readiness import (
    run_hierarchical_training_readiness,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_split(root: Path, split: str, input_dim: int, attack_head_dim: int) -> None:
    rng = np.random.default_rng(200 + len(split))
    benign_rows = 12
    attack_rows = attack_head_dim * 2
    rows = benign_rows + attack_rows
    X = rng.normal(size=(rows, input_dim)).astype(np.float32)
    y_binary = np.array([0] * benign_rows + [1] * attack_rows, dtype=np.int64)
    y_attack = np.full(rows, -1, dtype=np.int64)
    mask = np.zeros(rows, dtype=np.int64)
    y_attack[benign_rows:] = np.arange(attack_rows, dtype=np.int64) % attack_head_dim
    mask[benign_rows:] = 1

    np.save(root / f"X_{split}.npy", X)
    np.save(root / f"y_binary_{split}.npy", y_binary)
    np.save(root / f"y_attack_family_{split}.npy", y_attack)
    np.save(root / f"attack_family_mask_{split}.npy", mask)


def _create_binary_checkpoints(root: Path) -> None:
    for rel_path in (
        "models/final/final_cicids_binary.pt",
        "models/final/final_unsw_binary.pt",
        "models/federated/fedavg_cicids_binary.pt",
        "models/federated/fedavg_unsw_binary.pt",
    ):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")


def _create_binary_results(root: Path) -> None:
    for rel_path in (
        "results/final/centralized/cicids_training_history.csv",
        "results/final/centralized/cicids_test_metrics.json",
        "results/final/centralized/cicids_confusion_matrix.csv",
        "results/audits/training_manifest_cicids2018.json",
        "results/final/centralized/unsw_training_history.csv",
        "results/final/centralized/unsw_test_metrics.json",
        "results/final/centralized/unsw_confusion_matrix.csv",
        "results/audits/training_manifest_unsw_nb15.json",
    ):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")


def _create_smoke_jsons(root: Path) -> None:
    for dataset in ("cicids2018", "unsw_nb15"):
        _write_json(
            root / "results" / "audits" / f"hierarchical_smoke_training_{dataset}.json",
            {
                "dataset": dataset,
                "status": "PASS",
                "smoke_only": True,
                "non_final": True,
                "do_not_report_as_final": True,
                "checkpoint_created": False,
                "final_metrics_created": False,
                "full_training_run": False,
            },
        )


def _create_tiny_unsw_project(tmp_path: Path) -> None:
    input_dim = 192  # A8.8: matches corrected UNSW hierarchical feature dim
    attack_head_dim = 9
    data_dir = tmp_path / "data" / "processed" / "unsw_nb15" / "hierarchical"
    data_dir.mkdir(parents=True)
    for split in ("train", "val", "test"):
        _write_split(data_dir, split, input_dim=input_dim, attack_head_dim=attack_head_dim)

    class_to_id = {
        "Generic": 0,
        "Exploits": 1,
        "Fuzzers": 2,
        "DoS": 3,
        "Reconnaissance": 4,
        "Analysis": 5,
        "Backdoor": 6,
        "Shellcode": 7,
        "Worms": 8,
    }
    id_to_class = {str(value): key for key, value in class_to_id.items()}
    _write_json(data_dir / "feature_names.json", {"feature_names": [f"f{i}" for i in range(input_dim)]})
    _write_json(data_dir / "binary_label_mapping.json", {"class_to_id": {"Benign / Normal": 0, "Attack": 1}})
    _write_json(
        data_dir / "attack_family_label_mapping.json",
        {
            "dataset": "unsw_nb15",
            "head": "Head 2",
            "ignore_index": -1,
            "class_to_id": class_to_id,
            "id_to_class": id_to_class,
            "common_superclass_is_training_target": False,
            "rare_raw_labels": ["Shellcode", "Worms"],
        },
    )
    _write_json(
        data_dir / "common_attack_superclass_mapping.json",
        {"common_superclass_is_training_target": False},
    )
    _write_json(data_dir / "split_summary.json", {"status": "PASS"})
    _write_json(
        data_dir / "hierarchical_preprocessing_manifest.json",
        {
            "status": "PASS",
            "dataset": "unsw_nb15",
            "task": "hierarchical_preprocessing",
            "feature_dim": input_dim,
            "no_test_set_tuning": True,
            "no_scaler_encoder_refit_on_test": True,
            "fake_shared_multiclass_label_list_created": False,
        },
    )
    _write_json(
        tmp_path
        / "results"
        / "audits"
        / "hierarchical_preprocessing_readiness_unsw_nb15.json",
        {
            "status": "PASS",
            "ready_for_hierarchical_model_implementation": True,
        },
    )
    _write_yaml(tmp_path / "configs" / "taxonomy" / "unsw_nb15_attack_taxonomy.yaml", {"dataset": "unsw_nb15"})

    config = {
        "dataset": "unsw_nb15",
        "task": "hierarchical",
        "model_name": "SecureIDSHierarchicalAdvancedNet",
        "hierarchical_data_dir": "data/processed/unsw_nb15/hierarchical",
        "feature_names_path": "data/processed/unsw_nb15/hierarchical/feature_names.json",
        "attack_family_label_mapping_path": "data/processed/unsw_nb15/hierarchical/attack_family_label_mapping.json",
        "preprocessing_manifest_path": "data/processed/unsw_nb15/hierarchical/hierarchical_preprocessing_manifest.json",
        "readiness_json": "results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json",
        "taxonomy_config": "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        "input_dim": input_dim,
        "attack_head_dim": attack_head_dim,
        "model": {
            "architecture": "SecureIDSHierarchicalAdvancedNet",
            "hidden_dims": [16, 8],
            "dropout": 0.0,
            "normalization": "layernorm",
            "binary_output_dim": 1,
            "attack_output_dim": attack_head_dim,
        },
        "loss": {
            "type": "masked_multi_task",
            "binary_loss_weight": 1.0,
            "attack_loss_weight": 1.0,
            "ignore_index": -1,
        },
        "class_imbalance": {
            "binary_class_weighting": "train_split_pos_weight",
            "attack_family_class_weighting": "train_split_inverse_frequency",
            "class_weight_max_clip": 20.0,
            "class_weight_min_clip": 0.1,
            "compute_weights_from": "train_only",
            "allow_test_based_weights": False,
            "oversampling_enabled": False,
        },
        "training": {
            "seed": 7,
            "batch_size": 8,
            "max_epochs": 1,
            "learning_rate": 0.001,
            "optimizer": "adamw",
            "weight_decay": 0.0,
            "early_stopping_metric": "val_hierarchical_score",
            "early_stopping_patience": 1,
        },
        "checkpoint_selection": {
            "monitor": "val_hierarchical_score",
            "formula": "0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1",
            "use_validation_only": True,
            "select_by_test_metrics": False,
            "final_test_once_after_best_validation": True,
        },
        "metrics": {
            "binary": ["macro_f1", "confusion_matrix"],
            "attack_family": [
                "attack_family_macro_f1_on_attack_rows",
                "per_class_precision_recall_f1_support",
                "rare_class_macro_f1",
                "weak_hard_class_report",
                "attack_family_confusion_matrix",
                "validation_vs_test_gap_report",
            ],
            "hierarchical_end_to_end": [],
        },
        "rare_classes": ["Shellcode", "Worms"],
        "weak_hard_classes": [],
        "outputs": {
            "checkpoint": "models/final/final_unsw_hierarchical.pt",
            "result_dir": "results/final/hierarchical/unsw",
            "training_history_csv": "results/final/hierarchical/unsw/training_history.csv",
            "test_metrics_json": "results/final/hierarchical/unsw/test_metrics.json",
            "binary_confusion_matrix_csv": "results/final/hierarchical/unsw/binary_confusion_matrix.csv",
            "attack_family_confusion_matrix_csv": "results/final/hierarchical/unsw/attack_family_confusion_matrix.csv",
            "per_class_attack_metrics_csv": "results/final/hierarchical/unsw/per_class_attack_metrics.csv",
            "rare_class_metrics_csv": "results/final/hierarchical/unsw/rare_class_metrics.csv",
            "manifest_json": "results/audits/hierarchical_training_manifest_unsw_nb15.json",
            "report_md": "docs/HIERARCHICAL_TRAINING_REPORT.md",
        },
        "safety": {
            "a6_design_only": True,
            "full_training_run_in_a6": False,
            "final_checkpoint_created_in_a6": False,
            "final_metrics_created_in_a6": False,
            "no_test_set_tuning": True,
            "no_scaler_encoder_refit_on_test": True,
            "overwrite_binary_artifacts": False,
            "overwrite_hierarchical_preprocessing_artifacts": False,
            "hierarchical_fedavg_started": False,
            "security_attack_xai_dashboard_started": False,
        },
    }
    _write_yaml(tmp_path / "configs" / "training" / "unsw_nb15_hierarchical.yaml", config)
    _create_binary_checkpoints(tmp_path)
    _create_binary_results(tmp_path)
    _create_smoke_jsons(tmp_path)


def test_readiness_runner_writes_a8_outputs_without_final_artifacts(tmp_path: Path, monkeypatch):
    _create_tiny_unsw_project(tmp_path)
    monkeypatch.setattr(
        "secureids.training.hierarchical_readiness.torch.cuda.is_available",
        lambda: False,
    )

    outcome = run_hierarchical_training_readiness(
        dataset="unsw",
        project_root=tmp_path,
    )

    output_json = (
        tmp_path
        / "results"
        / "audits"
        / "hierarchical_full_training_readiness_unsw_nb15.json"
    )
    report = tmp_path / "docs" / "HIERARCHICAL_FULL_TRAINING_READINESS_REPORT.md"
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert outcome["status"] == "PASS"
    assert payload["dataset"] == "unsw_nb15"
    assert payload["status"] == "PASS"
    assert payload["ready_for_full_hierarchical_training"] is True
    assert payload["blocking_issues"] == []
    assert payload["dataloader_check"]["splits"]["train"]["one_batch_loaded"] is True
    assert payload["dataloader_check"]["splits"]["train"]["required_keys_present"] == [
        "X",
        "attack_family_mask",
        "y_attack_family",
        "y_binary",
    ]
    assert payload["model_forward_check"]["status"] == "PASS"
    assert payload["loss_check"]["status"] == "PASS"
    assert payload["class_weight_preview"]["computed_from_split"] == "train"
    assert payload["class_weight_preview"]["test_labels_used"] is False
    assert payload["no_fake_results_check"]["no_test_based_class_weights"] is True
    assert payload["output_safety_check"]["all_binary_result_files_exist"] is True
    assert payload["a8_safety"]["full_training_run"] is False
    assert output_json.exists()
    assert report.exists()
    assert not (tmp_path / "models" / "final" / "final_unsw_hierarchical.pt").exists()
    assert not (tmp_path / "results" / "final" / "hierarchical" / "unsw").exists()


def test_readiness_blocks_existing_final_checkpoint(tmp_path: Path, monkeypatch):
    _create_tiny_unsw_project(tmp_path)
    final_checkpoint = tmp_path / "models" / "final" / "final_unsw_hierarchical.pt"
    final_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    final_checkpoint.write_bytes(b"do not overwrite")
    monkeypatch.setattr(
        "secureids.training.hierarchical_readiness.torch.cuda.is_available",
        lambda: False,
    )

    outcome = run_hierarchical_training_readiness(
        dataset="unsw",
        project_root=tmp_path,
    )

    payload = json.loads(
        (
            tmp_path
            / "results"
            / "audits"
            / "hierarchical_full_training_readiness_unsw_nb15.json"
        ).read_text(encoding="utf-8")
    )
    assert outcome["status"] == "BLOCKED"
    assert payload["ready_for_full_hierarchical_training"] is False
    assert any("Planned checkpoint already exists" in issue for issue in payload["blocking_issues"])
