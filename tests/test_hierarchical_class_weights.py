"""Focused tests for Task A8.5 hierarchical class-weight strategy locking."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

from secureids.training.hierarchical_class_weights import (
    EXPECTED_ATTACK_STRATEGY,
    EXPECTED_BINARY_STRATEGY,
    compute_attack_family_weights,
    compute_balanced_binary_weights,
    run_hierarchical_class_weight_lock,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_binary_weights_are_balanced_mean_normalized_and_capped():
    preview = compute_balanced_binary_weights({"0": 90, "1": 10}, max_weight=10.0)

    assert preview["final_weights"]["1"] > preview["final_weights"]["0"]
    assert max(preview["final_weights"].values()) <= 10.0
    assert preview["normalization"]["applied"] is True
    assert preview["normalization"]["mean_after_normalization_before_cap"] == 1.0


def test_attack_weights_use_sqrt_normalization_and_cap():
    preview = compute_attack_family_weights(
        {"0": 1000, "1": 100, "2": 1},
        ["common", "medium", "rare"],
        max_weight=2.0,
    )

    assert preview["final_weights"]["rare"] == 2.0
    assert preview["final_weights"]["rare"] > preview["final_weights"]["medium"]
    assert preview["final_weights"]["medium"] > preview["final_weights"]["common"]
    assert preview["raw_inverse_frequency_weight_preview_for_comparison"]["rare"] > 300
    assert preview["max_final_attack_weight"] <= 2.0
    assert preview["normalization"]["applied"] is True
    assert preview["all_final_weights_finite"] is True
    assert preview["all_final_weights_positive"] is True


def test_repo_hierarchical_configs_lock_a85_strategy():
    for name in ("cicids2018_hierarchical.yaml", "unsw_nb15_hierarchical.yaml"):
        payload = yaml.safe_load(
            (REPO_ROOT / "configs" / "training" / name).read_text(encoding="utf-8")
        )
        assert payload["class_weights"]["binary"] == EXPECTED_BINARY_STRATEGY
        assert payload["class_weights"]["attack_family"] == EXPECTED_ATTACK_STRATEGY
        assert payload["class_imbalance"]["allow_test_based_weights"] is False
        assert payload["class_imbalance"]["oversampling_enabled"] is False
        assert payload["class_imbalance"]["class_weight_max_clip"] == 10.0


def _create_tiny_unsw_project(root: Path) -> None:
    data_dir = root / "data" / "processed" / "unsw_nb15" / "hierarchical"
    data_dir.mkdir(parents=True)
    y_binary = np.array([0] * 12 + [1] * 18, dtype=np.int64)
    attack_mask = np.array([0] * 12 + [1] * 18, dtype=np.int8)
    y_attack = np.full(y_binary.shape[0], -1, dtype=np.int64)
    y_attack[attack_mask == 1] = np.arange(18, dtype=np.int64) % 9
    np.save(data_dir / "y_binary_train.npy", y_binary)
    np.save(data_dir / "attack_family_mask_train.npy", attack_mask)
    np.save(data_dir / "y_attack_family_train.npy", y_attack)

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
    _write_json(
        data_dir / "attack_family_label_mapping.json",
        {
            "class_to_id": class_to_id,
            "id_to_class": {str(value): key for key, value in class_to_id.items()},
        },
    )
    _write_yaml(root / "configs" / "taxonomy" / "unsw_nb15_attack_taxonomy.yaml", {})

    config = {
        "dataset": "unsw_nb15",
        "task": "hierarchical",
        "model_name": "SecureIDSHierarchicalAdvancedNet",
        "hierarchical_data_dir": "data/processed/unsw_nb15/hierarchical",
        "feature_names_path": "data/processed/unsw_nb15/hierarchical/feature_names.json",
        "attack_family_label_mapping_path": (
            "data/processed/unsw_nb15/hierarchical/attack_family_label_mapping.json"
        ),
        "preprocessing_manifest_path": (
            "data/processed/unsw_nb15/hierarchical/hierarchical_preprocessing_manifest.json"
        ),
        "readiness_json": "results/audits/hierarchical_preprocessing_readiness_unsw_nb15.json",
        "taxonomy_config": "configs/taxonomy/unsw_nb15_attack_taxonomy.yaml",
        "input_dim": 192,
        "attack_head_dim": 9,
        "model": {"architecture": "SecureIDSHierarchicalAdvancedNet"},
        "loss": {
            "type": "masked_multi_task",
            "binary_loss_weight": 1.0,
            "attack_loss_weight": 1.0,
            "ignore_index": -1,
        },
        "class_imbalance": {
            "compute_weights_from": "train_only",
            "allow_test_based_weights": False,
            "oversampling_enabled": False,
        },
        "class_weights": {
            "binary": EXPECTED_BINARY_STRATEGY,
            "attack_family": EXPECTED_ATTACK_STRATEGY,
        },
        "training": {"batch_size": 8, "max_epochs": 1},
        "checkpoint_selection": {
            "monitor": "val_hierarchical_score",
            "formula": "0.5 * val_binary_macro_f1 + 0.5 * val_attack_family_macro_f1",
            "use_validation_only": True,
            "select_by_test_metrics": False,
            "final_test_once_after_best_validation": True,
        },
        "metrics": {"binary": [], "attack_family": [], "hierarchical_end_to_end": []},
        "rare_classes": ["Shellcode", "Worms"],
        "outputs": {
            "checkpoint": "models/final/final_unsw_hierarchical.pt",
            "result_dir": "results/final/hierarchical/unsw",
            "training_history_csv": "results/final/hierarchical/unsw/training_history.csv",
            "test_metrics_json": "results/final/hierarchical/unsw/test_metrics.json",
            "binary_confusion_matrix_csv": (
                "results/final/hierarchical/unsw/binary_confusion_matrix.csv"
            ),
            "attack_family_confusion_matrix_csv": (
                "results/final/hierarchical/unsw/attack_family_confusion_matrix.csv"
            ),
            "per_class_attack_metrics_csv": (
                "results/final/hierarchical/unsw/per_class_attack_metrics.csv"
            ),
            "rare_class_metrics_csv": "results/final/hierarchical/unsw/rare_class_metrics.csv",
            "manifest_json": "results/audits/hierarchical_training_manifest_unsw_nb15.json",
            "report_md": "docs/HIERARCHICAL_TRAINING_REPORT.md",
        },
        "safety": {},
    }
    _write_yaml(root / "configs" / "training" / "unsw_nb15_hierarchical.yaml", config)

    for rel_path in (
        "models/final/final_cicids_binary.pt",
        "models/final/final_unsw_binary.pt",
        "models/federated/fedavg_cicids_binary.pt",
        "models/federated/fedavg_unsw_binary.pt",
        "results/final/centralized/cicids_test_metrics.json",
        "results/final/centralized/unsw_test_metrics.json",
    ):
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")


def test_a85_runner_reads_train_labels_only(tmp_path: Path):
    _create_tiny_unsw_project(tmp_path)

    outcome = run_hierarchical_class_weight_lock("unsw", project_root=tmp_path)
    audit_path = (
        tmp_path
        / "results"
        / "audits"
        / "hierarchical_class_weight_strategy_unsw_nb15.json"
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    assert outcome["status"] == "PASS"
    assert audit["strategy_locked"] is True
    assert audit["validation_labels_used"] is False
    assert audit["test_labels_used"] is False
    assert audit["oversampling_enabled"] is False
    assert audit["train_only_read_diagnostics"]["validation_files_read"] == []
    assert audit["train_only_read_diagnostics"]["test_files_read"] == []
    assert audit["max_final_attack_weight"] <= 10.0
    assert not (tmp_path / "models" / "final" / "final_unsw_hierarchical.pt").exists()
