"""Safety + behavior tests for the hierarchical trainer (Task A9).

Uses tiny synthetic arrays and a hand-built config so the training loop, masked
weighted loss, validation-only checkpoint selection, and single final test
evaluation can be exercised without the full project metadata. The dry-run path
is checked against the real UNSW config but never trains.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from secureids.training.hierarchical_config import HierarchicalTrainingConfig  # noqa: E402
from secureids.training.hierarchical_trainer import (  # noqa: E402
    _write_extra_result_files,
    _write_report,
    _validate_split_labels,
    fit_hierarchical,
    run_hierarchical_training,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIM = 6
ATTACK_HEAD_DIM = 3
CLASS_NAMES = ["c0", "c1", "c2"]
RARE = ["c2"]


def _write_split(data_dir: Path, split: str, rows: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(rows, INPUT_DIM)).astype(np.float32)
    # First ~half benign, rest attacks cycling through all classes.
    y_binary = np.zeros(rows, dtype=np.int64)
    attack_count = rows // 2
    y_binary[attack_count:] = 1
    mask = y_binary.copy()
    y_attack = np.full(rows, -1, dtype=np.int64)
    y_attack[attack_count:] = np.arange(rows - attack_count) % ATTACK_HEAD_DIM
    np.save(data_dir / f"X_{split}.npy", X)
    np.save(data_dir / f"y_binary_{split}.npy", y_binary)
    np.save(data_dir / f"y_attack_family_{split}.npy", y_attack)
    np.save(data_dir / f"attack_family_mask_{split}.npy", mask.astype(np.int8))


def _tiny_config(tmp_path: Path) -> HierarchicalTrainingConfig:
    data_dir = tmp_path / "hier"
    data_dir.mkdir(parents=True)
    _write_split(data_dir, "train", 60, seed=1)
    _write_split(data_dir, "val", 30, seed=2)
    _write_split(data_dir, "test", 30, seed=3)
    raw = {
        "training": {
            "seed": 0,
            "batch_size": 8,
            "max_epochs": 3,
            "learning_rate": 0.01,
            "weight_decay": 0.0,
            "early_stopping_patience": 5,
        },
        "loss": {"binary_loss_weight": 1.0, "attack_loss_weight": 1.0, "ignore_index": -1},
        "model": {"hidden_dims": [16, 8], "dropout": 0.0, "normalization": "layernorm"},
    }
    return HierarchicalTrainingConfig(
        path=tmp_path / "config.yaml",
        dataset="unsw_nb15",
        task="hierarchical",
        model_name="SecureIDSHierarchicalAdvancedNet",
        hierarchical_data_dir="hier",
        feature_names_path="hier/feature_names.json",
        attack_family_label_mapping_path="hier/attack_family_label_mapping.json",
        preprocessing_manifest_path="hier/manifest.json",
        readiness_json="readiness.json",
        taxonomy_config="tax.yaml",
        input_dim=INPUT_DIM,
        attack_head_dim=ATTACK_HEAD_DIM,
        outputs={},
        raw=raw,
        project_root=tmp_path,
    )


def _weights() -> dict:
    return {
        "binary_pos_weight": 1.0,
        "binary_class_weights": {"0": 1.0, "1": 1.0},
        "attack_class_weights": [1.0, 1.0, 2.0],
        "attack_class_weights_by_name": {"c0": 1.0, "c1": 1.0, "c2": 2.0},
        "id_to_class": {"0": "c0", "1": "c1", "2": "c2"},
        "weight_cap": 10.0,
    }


def _minimal_writer_result() -> dict:
    per_class = [
        {
            "class_id": index,
            "class_name": name,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "support": 1,
        }
        for index, name in enumerate(CLASS_NAMES)
    ]
    return {
        "device": "cpu",
        "best_epoch": 1,
        "epochs_run": 1,
        "best_val_hierarchical_score": 1.0,
        "best_val_bundle": {
            "selection": {
                "val_binary_macro_f1": 1.0,
                "val_attack_family_macro_f1": 1.0,
            },
            "hierarchical_routing": {},
        },
        "class_distribution_train": {"0": 30, "1": 30},
        "param_count": 123,
        "architecture_metadata": {},
        "test_bundle": {
            "binary": {
                "accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "macro_f1": 1.0,
                "attack_false_negatives": 0,
                "confusion_matrix": {"tn": 1, "fp": 0, "fn": 0, "tp": 1},
                "n_samples": 2,
            },
            "attack_family": {
                "accuracy_on_attack_rows": 1.0,
                "macro_f1_on_attack_rows": 1.0,
                "attack_rows_evaluated": 3,
                "per_class": per_class,
                "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "class_names": CLASS_NAMES,
            },
            "rare_class": {
                "rare_class_macro_f1": 1.0,
                "per_rare_class": [
                    {
                        "class_name": "c2",
                        "present": True,
                        "precision": 1.0,
                        "recall": 1.0,
                        "f1": 1.0,
                        "support": 1,
                    }
                ],
            },
            "hierarchical_routing": {
                "benign_total": 1,
                "attack_total": 1,
                "benign_correctly_stopped": 1,
                "benign_correctly_stopped_rate": 1.0,
                "benign_flagged_as_attack": 0,
                "benign_flagged_as_attack_rate": 0.0,
                "attack_detected_and_correctly_attributed": 1,
                "attack_detected_and_correctly_attributed_rate": 1.0,
                "attack_detected_wrong_family": 0,
                "attack_detected_wrong_family_rate": 0.0,
                "attack_missed_as_benign": 0,
                "attack_missed_as_benign_rate": 0.0,
            },
        },
    }


def test_result_writers_honor_config_defined_paths(tmp_path: Path):
    config = replace(
        _tiny_config(tmp_path),
        outputs={
            "result_dir": "fallback_results",
            "manifest_json": "audits/custom_manifest.json",
            "report_md": "docs/custom_report.md",
            "hierarchical_routing_summary_json": "custom/routing.json",
            "class_weight_snapshot_json": "custom/weights.json",
            "model_summary_json": "custom/model.json",
            "training_config_snapshot_yaml": "custom/config.yaml",
        },
    )
    result = _minimal_writer_result()

    paths = _write_extra_result_files(
        config,
        result,
        _weights(),
        tmp_path / "fallback_results",
    )
    report_path = _write_report(
        config,
        result,
        tmp_path / "models" / "custom.pt",
        tmp_path,
    )

    assert Path(paths["hierarchical_routing_summary"]) == tmp_path / "custom" / "routing.json"
    assert Path(paths["class_weight_snapshot"]) == tmp_path / "custom" / "weights.json"
    assert Path(paths["model_summary"]) == tmp_path / "custom" / "model.json"
    assert Path(paths["training_config_snapshot"]) == tmp_path / "custom" / "config.yaml"
    assert report_path == tmp_path / "docs" / "custom_report.md"
    assert not (tmp_path / "docs" / "HIERARCHICAL_TRAINING_REPORT.md").exists()


def test_validate_split_labels_accepts_clean_data(tmp_path: Path):
    data_dir = tmp_path / "hier"
    data_dir.mkdir()
    _write_split(data_dir, "train", 20, seed=5)
    arrays = {
        "X": np.load(data_dir / "X_train.npy"),
        "y_binary": np.load(data_dir / "y_binary_train.npy"),
        "y_attack_family": np.load(data_dir / "y_attack_family_train.npy"),
        "attack_family_mask": np.load(data_dir / "attack_family_mask_train.npy"),
    }
    assert _validate_split_labels(arrays, "train", INPUT_DIM, ATTACK_HEAD_DIM) == []


def test_validate_split_labels_catches_mask_mismatch():
    rows = 10
    arrays = {
        "X": np.zeros((rows, INPUT_DIM), dtype=np.float32),
        "y_binary": np.array([0, 1] * 5, dtype=np.int64),
        # benign rows wrongly carry a non-ignore Head 2 label, and mask disagrees
        "y_attack_family": np.zeros(rows, dtype=np.int64),
        "attack_family_mask": np.ones(rows, dtype=np.int64),
    }
    issues = _validate_split_labels(arrays, "train", INPUT_DIM, ATTACK_HEAD_DIM)
    assert any("disagree" in issue for issue in issues)


def test_validate_split_labels_catches_benign_non_ignore():
    rows = 4
    arrays = {
        "X": np.zeros((rows, INPUT_DIM), dtype=np.float32),
        "y_binary": np.array([0, 0, 1, 1], dtype=np.int64),
        "y_attack_family": np.array([0, -1, 0, 1], dtype=np.int64),  # first benign not -1
        "attack_family_mask": np.array([0, 0, 1, 1], dtype=np.int64),
    }
    issues = _validate_split_labels(arrays, "train", INPUT_DIM, ATTACK_HEAD_DIM)
    assert any("y_attack_family == -1" in issue for issue in issues)


def test_fit_hierarchical_selects_by_validation_and_tests_once(tmp_path: Path):
    config = _tiny_config(tmp_path)
    result = fit_hierarchical(
        config, CLASS_NAMES, RARE, _weights(), device=torch.device("cpu"), verbose=False
    )

    # Trained and produced finite losses.
    assert result["epochs_run"] >= 1
    assert result["best_epoch"] >= 1
    for row in result["history"]:
        assert np.isfinite(row["train_total_loss"])
        assert np.isfinite(row["val_hierarchical_score"])

    # Best score equals the max validation hierarchical score seen (validation-only).
    best_seen = max(row["val_hierarchical_score"] for row in result["history"])
    assert result["best_val_hierarchical_score"] == pytest.approx(best_seen)

    # History carries no test fields (no test leakage into selection).
    assert all(not key.startswith("test") for row in result["history"] for key in row)

    # Test bundle exists and is structured; selection score is the 0.5/0.5 blend.
    test = result["test_bundle"]
    assert "binary" in test and "attack_family" in test and "rare_class" in test
    assert test["selection"]["val_hierarchical_score"] == pytest.approx(
        0.5 * test["binary"]["macro_f1"] + 0.5 * test["attack_family"]["macro_f1_on_attack_rows"]
    )


def test_dry_run_on_real_config_does_not_train():
    outcome = run_hierarchical_training(
        REPO_ROOT / "configs" / "training" / "unsw_nb15_hierarchical.yaml",
        execute=False,
        project_root=REPO_ROOT,
    )
    assert outcome["executed"] is False
    assert "plan" in outcome
    assert outcome["plan"]["dataset"] == "unsw_nb15"
    assert outcome["plan"]["input_dim"] == 192
