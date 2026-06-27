"""Lightweight tests for the centralized training components.

These tests use tiny synthetic arrays/configs only. They do not train a model,
create checkpoints, or write metrics. No test runner is invoked here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml

from secureids.cli import main as cli_main
from secureids.models.secureids_net import SecureIDSNet
from secureids.training.config import TrainingConfigError, load_training_config
from secureids.training.datasets import BinaryNumpyDataset, load_feature_names
from secureids.training.metrics import compute_binary_metrics


def _write_feature_names(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"feature_names": [f"f{i}" for i in range(count)]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_config(path: Path, input_dim: int, feature_names_path: Path) -> None:
    config = {
        "dataset": "cicids2018",
        "task": "binary",
        "processed_dir": "data/processed/cicids2018/binary",
        "input_dim": input_dim,
        "feature_names_path": str(feature_names_path),
        "label_mapping_path": "data/processed/cicids2018/binary/label_mapping.json",
        "preprocessing_manifest_path": (
            "data/processed/cicids2018/binary/preprocessing_manifest.json"
        ),
        "output_checkpoint": "models/final/final_cicids_binary.pt",
        "training": {
            "seed": 42,
            "batch_size": 4096,
            "max_epochs": 20,
            "learning_rate": 0.001,
            "optimizer": "adamw",
            "weight_decay": 0.0001,
            "early_stopping_metric": "val_macro_f1",
            "early_stopping_patience": 4,
            "use_pos_weight": True,
        },
        "model": {
            "architecture": "SecureIDSNet",
            "hidden_dims": [256, 128, 64],
            "dropout": 0.20,
            "output_dim": 1,
        },
        "evaluation": {"threshold": 0.5, "final_test_once": True},
        "outputs": {
            "history_csv": "results/final/centralized/cicids_training_history.csv",
            "metrics_json": "results/final/centralized/cicids_test_metrics.json",
            "confusion_matrix_csv": (
                "results/final/centralized/cicids_confusion_matrix.csv"
            ),
            "manifest_json": "results/audits/training_manifest_cicids2018.json",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def test_secureids_net_output_shape_is_batch_by_one():
    model = SecureIDSNet(input_dim=8)
    batch = torch.randn(4, 8)
    logits = model(batch)
    assert logits.shape == (4, 1)


def test_secureids_net_rejects_non_binary_output_dim():
    with pytest.raises(ValueError):
        SecureIDSNet(input_dim=8, output_dim=2)


def test_config_validation_rejects_mismatched_input_dim(tmp_path):
    feature_names_path = tmp_path / "feature_names.json"
    _write_feature_names(feature_names_path, count=8)
    config_path = tmp_path / "cicids2018_binary.yaml"
    _write_config(config_path, input_dim=5, feature_names_path=feature_names_path)

    with pytest.raises(TrainingConfigError):
        load_training_config(config_path, project_root=tmp_path)


def test_config_validation_accepts_matching_input_dim(tmp_path):
    feature_names_path = tmp_path / "feature_names.json"
    _write_feature_names(feature_names_path, count=8)
    config_path = tmp_path / "cicids2018_binary.yaml"
    _write_config(config_path, input_dim=8, feature_names_path=feature_names_path)

    config = load_training_config(config_path, project_root=tmp_path)
    assert config.input_dim == 8
    assert config.model.output_dim == 1


def test_feature_names_loader_handles_object_form(tmp_path):
    path = tmp_path / "feature_names.json"
    _write_feature_names(path, count=3)
    names = load_feature_names(path)
    assert names == ["f0", "f1", "f2"]


def test_binary_numpy_dataset_returns_float32(tmp_path):
    X = np.random.rand(6, 4).astype(np.float64)
    y = np.array([0, 1, 0, 1, 0, 1], dtype=np.int64)
    dataset = BinaryNumpyDataset(X, y)

    assert len(dataset) == 6
    x_item, y_item = dataset[0]
    assert x_item.dtype == torch.float32
    assert y_item.dtype == torch.float32
    assert tuple(y_item.shape) == (1,)


def test_metrics_perfect_predictions():
    y_true = [0, 1, 0, 1]
    logits = [-10.0, 10.0, -10.0, 10.0]
    metrics = compute_binary_metrics(y_true, logits, threshold=0.5, from_logits=True)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["macro_f1"] == 1.0


def test_metrics_handle_zero_division_safely():
    # All-negative labels with all-negative predictions: no positives at all.
    y_true = [0, 0, 0]
    logits = [-5.0, -5.0, -5.0]
    metrics = compute_binary_metrics(y_true, logits, threshold=0.5, from_logits=True)
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0
    assert metrics["accuracy"] == 1.0
    assert not np.isnan(metrics["macro_f1"])


def test_cli_train_centralized_requires_explicit_mode():
    code = cli_main(["train-centralized", "--config", "dummy.yaml"])
    assert code == 1


def test_cli_train_centralized_execute_missing_config_fails():
    # Full execution is enabled for UNSW-NB15 and CICIDS2018, but a missing or
    # invalid config must fail cleanly (and before importing torch) instead of
    # starting training.
    code = cli_main(
        ["train-centralized", "--dataset", "cicids", "--config", "dummy.yaml", "--execute"]
    )
    assert code == 1
