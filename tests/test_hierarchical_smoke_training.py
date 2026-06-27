"""Focused tests for A7 hierarchical smoke training.

The synthetic test data is tiny and local to pytest tmp directories. These
tests do not run full training, do not use GPU, and do not create checkpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from secureids.training.hierarchical_config import HierarchicalTrainingConfigError
from secureids.training.hierarchical_datasets import (
    build_hierarchical_smoke_dataset,
    select_hierarchical_smoke_indices,
)
from secureids.training.hierarchical_smoke import run_hierarchical_smoke


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_split(root: Path, split: str, rows: int, input_dim: int) -> None:
    rng = np.random.default_rng(123 + rows)
    X = rng.normal(size=(rows, input_dim)).astype(np.float32)
    # Put benign rows first so the sampler must balance instead of blindly
    # accepting first-N when the leading slice is all benign.
    y_binary = np.array([0] * (rows // 2) + [1] * (rows - rows // 2), dtype=np.int64)
    y_attack = np.full(rows, -1, dtype=np.int64)
    attack_mask = np.zeros(rows, dtype=np.int64)
    attack_rows = np.flatnonzero(y_binary == 1)
    y_attack[attack_rows] = np.arange(attack_rows.shape[0]) % 9
    attack_mask[attack_rows] = 1

    np.save(root / f"X_{split}.npy", X)
    np.save(root / f"y_binary_{split}.npy", y_binary)
    np.save(root / f"y_attack_family_{split}.npy", y_attack)
    np.save(root / f"attack_family_mask_{split}.npy", attack_mask)


def _create_tiny_unsw_project(tmp_path: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data" / "processed" / "unsw_nb15" / "hierarchical"
    data_dir.mkdir(parents=True)
    input_dim = 192  # A8.8: matches corrected UNSW hierarchical feature dim
    attack_head_dim = 9
    for split, rows in (("train", 24), ("val", 16), ("test", 16)):
        _write_split(data_dir, split, rows=rows, input_dim=input_dim)

    _write_json(
        data_dir / "feature_names.json",
        {"feature_names": [f"f{i}" for i in range(input_dim)]},
    )
    _write_json(
        data_dir / "binary_label_mapping.json",
        {"class_to_id": {"Benign / Normal": 0, "Attack": 1}},
    )
    _write_json(
        data_dir / "attack_family_label_mapping.json",
        {
            "dataset": "unsw_nb15",
            "ignore_index": -1,
            "class_to_id": {f"cls_{i}": i for i in range(attack_head_dim)},
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
    taxonomy = tmp_path / "configs" / "taxonomy" / "unsw_nb15_attack_taxonomy.yaml"
    _write_yaml(taxonomy, {"dataset": "unsw_nb15"})

    full_config = {
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
        "input_dim": input_dim,
        "attack_head_dim": attack_head_dim,
        "model": {
            "architecture": "SecureIDSHierarchicalAdvancedNet",
            "hidden_dims": [16, 8],
            "dropout": 0.0,
            "normalization": "layernorm",
        },
        "loss": {
            "type": "masked_multi_task",
            "binary_loss_weight": 1.0,
            "attack_loss_weight": 1.0,
            "ignore_index": -1,
        },
        "class_imbalance": {
            "compute_weights_from": "train_only",
            "allow_test_based_weights": False,
        },
        "training": {
            "seed": 7,
            "batch_size": 4,
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
        "metrics": {"binary": [], "attack_family": [], "hierarchical_end_to_end": []},
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
    full_config_path = tmp_path / "configs" / "training" / "unsw_nb15_hierarchical.yaml"
    _write_yaml(full_config_path, full_config)

    smoke_config = {
        "dataset": "unsw_nb15",
        "task": "hierarchical_smoke",
        "base_config": "configs/training/unsw_nb15_hierarchical.yaml",
        "model_name": "SecureIDSHierarchicalAdvancedNet",
        "hierarchical_data_dir": "data/processed/unsw_nb15/hierarchical",
        "input_dim": input_dim,
        "attack_head_dim": attack_head_dim,
        "smoke": {
            "enabled": True,
            "non_final": True,
            "train_samples": 8,
            "val_samples": 6,
            "test_samples": 6,
            "batch_size": 4,
            "max_epochs": 1,
            "max_train_batches": 2,
            "max_eval_batches": 1,
            "save_checkpoint": False,
            "final_metrics": False,
            "output_json": "results/audits/hierarchical_smoke_training_unsw_nb15.json",
            "report_md": "docs/HIERARCHICAL_SMOKE_TRAINING_CHECK.md",
        },
        "safety": {
            "no_final_checkpoint": True,
            "no_final_metrics": True,
            "no_results_final_outputs": True,
            "no_test_set_tuning": True,
            "no_full_training": True,
            "do_not_report_as_final": True,
            "no_hierarchical_fedavg": True,
            "no_security_attack_xai_dashboard": True,
        },
    }
    smoke_config_path = (
        tmp_path / "configs" / "training" / "smoke_unsw_nb15_hierarchical.yaml"
    )
    _write_yaml(smoke_config_path, smoke_config)
    return smoke_config_path, data_dir


def test_smoke_sampler_balances_when_first_n_has_no_attacks():
    y_binary = np.array([0] * 10 + [1] * 10, dtype=np.int64)
    mask = np.array([0] * 10 + [1] * 10, dtype=np.int64)

    indices = select_hierarchical_smoke_indices(y_binary, mask, max_samples=8, seed=5)
    selected_y = y_binary[indices]
    selected_mask = mask[indices]

    assert len(indices) == 8
    assert np.any(selected_y == 0)
    assert np.any(selected_y == 1)
    assert np.any(selected_mask == 1)


def test_hierarchical_smoke_dataset_builds_from_tiny_arrays(tmp_path: Path):
    _, data_dir = _create_tiny_unsw_project(tmp_path)
    dataset, summary = build_hierarchical_smoke_dataset(
        data_dir,
        split="train",
        max_samples=8,
        seed=7,
    )

    x, y_binary, y_attack, attack_mask = dataset[0]
    assert len(dataset) == 8
    assert tuple(x.shape) == (192,)
    assert y_binary.ndim == 0
    assert y_attack.ndim == 0
    assert attack_mask.ndim == 0
    assert summary["selected_rows"] == 8
    assert summary["attack_rows"] > 0


def test_hierarchical_smoke_runner_writes_non_final_schema(tmp_path: Path, monkeypatch):
    smoke_config_path, _ = _create_tiny_unsw_project(tmp_path)
    monkeypatch.setattr(
        "secureids.training.hierarchical_smoke.resolve_device",
        lambda: torch.device("cpu"),
    )

    outcome = run_hierarchical_smoke(
        smoke_config_path,
        project_root=tmp_path,
        expected_dataset="unsw_nb15",
    )

    assert outcome["status"] == "PASS"
    output_json = tmp_path / "results" / "audits" / "hierarchical_smoke_training_unsw_nb15.json"
    report = tmp_path / "docs" / "HIERARCHICAL_SMOKE_TRAINING_CHECK.md"
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert payload["smoke_only"] is True
    assert payload["non_final"] is True
    assert payload["do_not_report_as_final"] is True
    assert payload["checkpoint_created"] is False
    assert payload["final_metrics_created"] is False
    assert payload["full_training_run"] is False
    assert payload["final_checkpoint"] is False
    assert payload["final_results"] is False
    assert payload["training"]["batches_run"] <= 2
    assert payload["training"]["optimizer_step_updated_parameters"] is True
    assert payload["smoke_diagnostics_non_final"]["val"]["non_final"] is True
    assert output_json.exists()
    assert report.exists()
    assert not (tmp_path / "models" / "final" / "final_unsw_hierarchical.pt").exists()


def test_hierarchical_smoke_rejects_checkpoint_saving(tmp_path: Path):
    smoke_config_path, _ = _create_tiny_unsw_project(tmp_path)
    data = yaml.safe_load(smoke_config_path.read_text(encoding="utf-8"))
    data["smoke"]["save_checkpoint"] = True
    smoke_config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(HierarchicalTrainingConfigError):
        run_hierarchical_smoke(
            smoke_config_path,
            project_root=tmp_path,
            expected_dataset="unsw_nb15",
        )
