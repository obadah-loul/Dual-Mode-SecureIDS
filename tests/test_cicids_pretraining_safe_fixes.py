"""Lightweight tests for the CICIDS pre-training safe fixes (H1, H2, M1).

Synthetic/in-memory only: no training, no full datasets, no checkpoints. These
verify the CICIDS report-path fix (H1), dataset-aware report/metrics/manifest
wording (H2), and the float32-safe finite check (M1). UNSW behavior must remain
correct.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from secureids.training.hierarchical_config import (  # noqa: E402
    load_hierarchical_training_config,
)

torch = pytest.importorskip("torch")

from secureids.training.hierarchical_config import HierarchicalTrainingConfig  # noqa: E402
from secureids.training.hierarchical_trainer import (  # noqa: E402
    _build_manifest,
    _build_test_metrics_payload,
    _dataset_report_metadata,
    _validate_split_labels,
    _write_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CICIDS_CONFIG = REPO_ROOT / "configs" / "training" / "cicids2018_hierarchical.yaml"
UNSW_CONFIG = REPO_ROOT / "configs" / "training" / "unsw_nb15_hierarchical.yaml"
UNSW_REPORT = "docs/HIERARCHICAL_TRAINING_REPORT.md"
CICIDS_REPORT = "docs/CICIDS_HIERARCHICAL_TRAINING_REPORT.md"

UNSW_TOKENS = ("UNSW", "A8.8", "175,341", "82,332")


# --------------------------------------------------------------------------- #
# H1: report-path collision
# --------------------------------------------------------------------------- #
def test_cicids_config_uses_cicids_specific_report_path():
    config = load_hierarchical_training_config(CICIDS_CONFIG, project_root=REPO_ROOT)
    assert config.outputs["report_md"] == CICIDS_REPORT


def test_cicids_config_does_not_write_to_shared_unsw_report():
    config = load_hierarchical_training_config(CICIDS_CONFIG, project_root=REPO_ROOT)
    assert config.outputs["report_md"] != UNSW_REPORT
    assert UNSW_REPORT not in set(config.outputs.values())


def test_unsw_report_path_is_unchanged_and_not_overwritten_by_cicids():
    unsw = load_hierarchical_training_config(UNSW_CONFIG, project_root=REPO_ROOT)
    cicids = load_hierarchical_training_config(CICIDS_CONFIG, project_root=REPO_ROOT)
    assert unsw.outputs["report_md"] == UNSW_REPORT
    assert cicids.outputs["report_md"] != unsw.outputs["report_md"]


# --------------------------------------------------------------------------- #
# H2: dataset-aware metadata
# --------------------------------------------------------------------------- #
def _config(dataset: str, tmp_path: Path) -> HierarchicalTrainingConfig:
    is_cicids = dataset == "cicids2018"
    return HierarchicalTrainingConfig(
        path=tmp_path / "config.yaml",
        dataset=dataset,
        task="hierarchical",
        model_name="SecureIDSHierarchicalAdvancedNet",
        hierarchical_data_dir="hier",
        feature_names_path="hier/feature_names.json",
        attack_family_label_mapping_path="hier/mapping.json",
        preprocessing_manifest_path="hier/manifest.json",
        readiness_json="readiness.json",
        taxonomy_config="tax.yaml",
        input_dim=77 if is_cicids else 192,
        attack_head_dim=14 if is_cicids else 9,
        outputs={
            "report_md": "report.md",
            "result_dir": "result_dir",
            "manifest_json": "manifest.json",
        },
        raw={"training": {"seed": 42, "batch_size": 4096, "max_epochs": 30}},
        project_root=tmp_path,
    )


def _result(dataset: str) -> dict:
    rare_names = ["Web-XSS", "SQL-Injection"] if dataset == "cicids2018" else ["Shellcode", "Worms"]
    per_class = [
        {"class_id": 0, "class_name": "c0", "precision": 1.0, "recall": 1.0, "f1": 1.0, "support": 10}
    ]
    per_rare = [
        {"class_name": name, "present": True, "precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 5}
        for name in rare_names
    ]
    return {
        "device": "cpu",
        "best_epoch": 3,
        "epochs_run": 5,
        "best_val_hierarchical_score": 0.9,
        "class_distribution_train": {"0": 100, "1": 50},
        "param_count": 123456,
        "threshold": 0.5,
        "best_val_bundle": {
            "selection": {"val_binary_macro_f1": 0.9, "val_attack_family_macro_f1": 0.8}
        },
        "test_bundle": {
            "binary": {
                "accuracy": 0.95, "precision": 0.95, "recall": 0.95, "f1": 0.95,
                "macro_f1": 0.94, "attack_false_negatives": 1,
                "confusion_matrix": {"tn": 50, "fp": 2, "fn": 1, "tp": 47}, "n_samples": 100,
            },
            "attack_family": {
                "accuracy_on_attack_rows": 0.9, "macro_f1_on_attack_rows": 0.8,
                "attack_rows_evaluated": 48, "per_class": per_class,
                "confusion_matrix": [[10]], "class_names": ["c0"],
            },
            "rare_class": {
                "rare_class_macro_f1": 0.5, "rare_classes": rare_names, "per_rare_class": per_rare,
            },
            "hierarchical_routing": {
                "benign_total": 52, "attack_total": 48,
                "benign_correctly_stopped": 50, "benign_correctly_stopped_rate": 0.96,
                "attack_detected_and_correctly_attributed": 40,
                "attack_detected_and_correctly_attributed_rate": 0.83,
                "attack_detected_wrong_family": 7, "attack_detected_wrong_family_rate": 0.15,
                "attack_missed_as_benign": 1, "attack_missed_as_benign_rate": 0.02,
            },
        },
    }


def _preflight() -> dict:
    return {
        "feature_count": 77, "attack_family_class_count": 14,
        "cuda_available": False, "gpu_name": None,
        "split_shapes": {"train": [100, 77], "val": [50, 77], "test": [50, 77]},
    }


def _weights() -> dict:
    return {"binary_pos_weight": 2.5, "attack_class_weights": [1.0], "weight_cap": 10.0}


def test_metadata_is_dataset_aware(tmp_path):
    cicids = _dataset_report_metadata(_config("cicids2018", tmp_path))
    unsw = _dataset_report_metadata(_config("unsw_nb15", tmp_path))

    assert "CICIDS2018" in cicids["report_title"]
    assert not any(token in cicids["protocol"] for token in UNSW_TOKENS)
    assert not any(token in cicids["report_status"] for token in UNSW_TOKENS)

    assert "UNSW-NB15" in unsw["report_title"]
    assert "UNSW" in unsw["protocol"] and "A8.8" in unsw["protocol"]


def test_cicids_test_metrics_payload_has_no_unsw_wording(tmp_path):
    config = _config("cicids2018", tmp_path)
    payload = _build_test_metrics_payload(config, _result("cicids2018"), tmp_path / "ckpt.pt")
    assert payload["dataset"] == "cicids2018"
    assert "CICIDS2018" in payload["protocol"]
    assert not any(token in payload["protocol"] for token in UNSW_TOKENS)
    # No UNSW-centric safety keys leak into the CICIDS payload.
    assert "cicids_hierarchical_training_run" not in payload["safety_notes"]
    assert "old_unsw_pre_correction_baselines_used_as_final" not in payload["safety_notes"]
    assert payload["safety_notes"]["single_dataset_hierarchical_run"] is True


def test_unsw_test_metrics_payload_keeps_unsw_wording(tmp_path):
    config = _config("unsw_nb15", tmp_path)
    payload = _build_test_metrics_payload(config, _result("unsw_nb15"), tmp_path / "ckpt.pt")
    assert payload["dataset"] == "unsw_nb15"
    assert "UNSW" in payload["protocol"] and "A8.8" in payload["protocol"]
    assert payload["safety_notes"]["cicids_hierarchical_training_run"] is False


def test_cicids_manifest_has_no_unsw_wording(tmp_path):
    config = _config("cicids2018", tmp_path)
    manifest = _build_manifest(
        config, "config.yaml", _result("cicids2018"), _weights(), _preflight(),
        tmp_path / "ckpt.pt", {"report_md": "report.md"},
    )
    assert manifest["dataset"] == "cicids2018"
    assert not any(token in manifest["protocol"] for token in UNSW_TOKENS)
    assert "cicids_hierarchical_training_run" not in manifest["safety"]


def test_unsw_manifest_keeps_unsw_wording(tmp_path):
    config = _config("unsw_nb15", tmp_path)
    manifest = _build_manifest(
        config, "config.yaml", _result("unsw_nb15"), _weights(), _preflight(),
        tmp_path / "ckpt.pt", {"report_md": "report.md"},
    )
    assert "A8.8" in manifest["protocol"] and "UNSW" in manifest["protocol"]


def test_cicids_report_text_has_no_unsw_wording(tmp_path):
    config = _config("cicids2018", tmp_path)
    report_path = _write_report(config, _result("cicids2018"), tmp_path / "ckpt.pt", tmp_path)
    text = report_path.read_text(encoding="utf-8")
    assert "CICIDS2018" in text
    for token in UNSW_TOKENS:
        assert token not in text, f"CICIDS report unexpectedly contains UNSW token {token!r}"
    # Rare-class header is dataset-aware.
    assert "Web-XSS" in text and "SQL-Injection" in text


def test_unsw_report_text_keeps_unsw_wording(tmp_path):
    config = _config("unsw_nb15", tmp_path)
    report_path = _write_report(config, _result("unsw_nb15"), tmp_path / "ckpt.pt", tmp_path)
    text = report_path.read_text(encoding="utf-8")
    assert "UNSW-NB15" in text and "A8.8" in text
    assert "Shellcode" in text and "Worms" in text


# --------------------------------------------------------------------------- #
# M1: float32-safe finite check
# --------------------------------------------------------------------------- #
def _clean_arrays(dtype=np.float32) -> dict:
    X = np.ones((6, 4), dtype=dtype)
    y_binary = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
    mask = y_binary.copy()
    y_attack = np.array([-1, -1, -1, 0, 1, 2], dtype=np.int64)
    return {"X": X, "y_binary": y_binary, "y_attack_family": y_attack, "attack_family_mask": mask}


def test_finite_check_passes_clean_float32():
    issues = _validate_split_labels(_clean_arrays(np.float32), "train", 4, 3)
    assert issues == []


def test_finite_check_flags_nan_in_float32():
    arrays = _clean_arrays(np.float32)
    arrays["X"][0, 0] = np.nan
    issues = _validate_split_labels(arrays, "train", 4, 3)
    assert any("non-finite" in issue for issue in issues)


def test_finite_check_flags_inf_in_float32():
    arrays = _clean_arrays(np.float32)
    arrays["X"][1, 2] = np.inf
    issues = _validate_split_labels(arrays, "train", 4, 3)
    assert any("non-finite" in issue for issue in issues)


def test_finite_check_handles_integer_features_without_error():
    # Integer feature arrays are inherently finite and must not raise or upcast.
    issues = _validate_split_labels(_clean_arrays(np.int64), "train", 4, 3)
    assert all("non-finite" not in issue for issue in issues)
