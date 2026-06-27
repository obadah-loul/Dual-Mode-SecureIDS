from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pytest

from secureids.cli import build_parser
from secureids.federated.config import FederatedConfig
from secureids.federated.training import (
    CICIDS_DATASET,
    FederatedTrainingError,
    FullNumpyDataset,
    IndexedNumpyDataset,
    build_manifest_payload,
    build_safety_notes,
    ensure_fedavg_training_enabled,
    ensure_unsw_training_enabled,
    existing_guarded_outputs,
)


torch = pytest.importorskip("torch")


def _minimal_config(tmp_path: Path, dataset: str = "unsw_nb15") -> FederatedConfig:
    is_cicids = dataset == "cicids2018"
    dataset_token = "cicids" if is_cicids else "unsw"
    input_dim = 77 if is_cicids else 190
    outputs = {
        "checkpoint": f"models/federated/fedavg_{dataset_token}_binary.pt",
        "round_history": f"results/federated/{dataset_token}/fedavg_round_history.csv",
        "client_distribution": f"results/federated/{dataset_token}/fedavg_client_distribution.csv",
        "client_logs": f"results/federated/{dataset_token}/fedavg_client_logs.csv",
        "test_metrics": f"results/federated/{dataset_token}/fedavg_test_metrics.json",
        "confusion_matrix": f"results/federated/{dataset_token}/fedavg_confusion_matrix.csv",
        "manifest": (
            "results/audits/fedavg_manifest_cicids2018.json"
            if is_cicids
            else "results/audits/fedavg_manifest_unsw_nb15.json"
        ),
        "report": "docs/FEDERATED_LEARNING_REPORT.md",
    }
    return FederatedConfig(
        path=tmp_path / f"{dataset}_fedavg.yaml",
        raw={
            "dataset": dataset,
            "task": "binary",
            "model": {"architecture": "SecureIDSNet", "input_dim": input_dim},
            "federation": {
                "algorithm": "FedAvg",
                "num_clients": 5,
                "seed": 42,
                "client_split": "stratified_iid",
                "client_fraction": 1.0,
                "local_epochs": 1,
                "rounds": 20,
            },
            "training": {"threshold": 0.5},
            "outputs": outputs,
            "centralized_reference": {
                "checkpoint": (
                    "models/final/final_cicids_binary.pt"
                    if is_cicids
                    else "models/final/final_unsw_binary.pt"
                ),
                "metrics": (
                    "results/final/centralized/cicids_test_metrics.json"
                    if is_cicids
                    else "results/final/centralized/unsw_test_metrics.json"
                ),
                "manifest": (
                    "results/audits/training_manifest_cicids2018.json"
                    if is_cicids
                    else "results/audits/training_manifest_unsw_nb15.json"
                ),
            },
        },
    )


def test_cicids_federated_training_is_now_enabled_by_generic_gate():
    assert ensure_fedavg_training_enabled("cicids") == CICIDS_DATASET
    assert ensure_fedavg_training_enabled("cicids2018") == CICIDS_DATASET


def test_unsw_only_legacy_gate_still_refuses_cicids():
    with pytest.raises(FederatedTrainingError, match="Only UNSW-NB15"):
        ensure_unsw_training_enabled("cicids")


def test_unsw_dataset_alias_is_allowed():
    assert ensure_unsw_training_enabled("unsw") == "unsw_nb15"
    assert ensure_unsw_training_enabled("unsw_nb15") == "unsw_nb15"


def test_existing_unsw_output_guard_detects_guarded_output(tmp_path):
    config = _minimal_config(tmp_path)
    guarded_checkpoint = tmp_path / "models" / "federated" / "fedavg_unsw_binary.pt"
    guarded_checkpoint.parent.mkdir(parents=True)
    guarded_checkpoint.write_bytes(b"existing")

    existing = existing_guarded_outputs(config, project_root=tmp_path)

    assert guarded_checkpoint in existing


def test_existing_cicids_output_guard_detects_guarded_output(tmp_path):
    config = _minimal_config(tmp_path, dataset="cicids2018")
    guarded_checkpoint = tmp_path / "models" / "federated" / "fedavg_cicids_binary.pt"
    guarded_checkpoint.parent.mkdir(parents=True)
    guarded_checkpoint.write_bytes(b"existing")

    existing = existing_guarded_outputs(config, project_root=tmp_path)

    assert guarded_checkpoint in existing


def test_safety_notes_include_required_scope_fields():
    notes = build_safety_notes()

    assert notes["no_fake_metrics"] is True
    assert notes["final_test_after_best_validation_round_only"] is True
    assert notes["no_cicids_fedavg_training"] is True
    assert notes["no_security_or_attack_simulation"] is True
    assert notes["no_robust_aggregation"] is True
    assert notes["no_xai"] is True
    assert notes["no_dashboard_model_demo"] is True

    cicids_notes = build_safety_notes("cicids2018")
    assert cicids_notes["no_unsw_fedavg_rerun"] is True
    assert cicids_notes["no_security_or_attack_simulation"] is True


def test_manifest_payload_contains_required_safety_fields(tmp_path):
    config = _minimal_config(tmp_path)
    output_paths = {
        "checkpoint": tmp_path / "models" / "federated" / "fedavg_unsw_binary.pt",
        "round_history": tmp_path / "results" / "federated" / "unsw" / "fedavg_round_history.csv",
        "client_distribution": tmp_path / "results" / "federated" / "unsw" / "fedavg_client_distribution.csv",
        "client_logs": tmp_path / "results" / "federated" / "unsw" / "fedavg_client_logs.csv",
        "test_metrics": tmp_path / "results" / "federated" / "unsw" / "fedavg_test_metrics.json",
        "confusion_matrix": tmp_path / "results" / "federated" / "unsw" / "fedavg_confusion_matrix.csv",
        "manifest": tmp_path / "results" / "audits" / "fedavg_manifest_unsw_nb15.json",
    }
    validation = {
        "paths": {
            "X_train": tmp_path / "X_train.npy",
            "y_train": tmp_path / "y_train.npy",
            "X_val": tmp_path / "X_val.npy",
            "y_val": tmp_path / "y_val.npy",
            "X_test": tmp_path / "X_test.npy",
            "y_test": tmp_path / "y_test.npy",
            "feature_names": tmp_path / "feature_names.json",
            "label_mapping": tmp_path / "label_mapping.json",
            "preprocessing_manifest": tmp_path / "preprocessing_manifest.json",
        },
        "references": config.raw["centralized_reference"],
    }

    payload = build_manifest_payload(
        config=config,
        config_path=config.path,
        validation=validation,
        client_distribution=[],
        device_name="cpu",
        cuda_available=False,
        best_round=3,
        output_paths=output_paths,
        created_at_utc="2026-06-24T00:00:00+00:00",
    )

    assert payload["dataset"] == "unsw_nb15"
    assert payload["algorithm"] == "FedAvg"
    assert payload["device"] == "cpu"
    assert payload["cuda_available"] is False
    assert payload["final_checkpoint"] is True
    assert payload["test_set_used_for_tuning"] is False
    assert payload["final_test_after_best_validation_round_only"] is True
    assert payload["no_cicids_fedavg_training"] is True
    assert payload["no_security_or_attack_simulation"] is True
    assert payload["no_robust_aggregation"] is True
    assert payload["no_xai"] is True
    assert payload["no_dashboard_model_demo"] is True


def test_cicids_manifest_payload_contains_required_safety_fields(tmp_path):
    config = _minimal_config(tmp_path, dataset="cicids2018")
    output_paths = {
        "checkpoint": tmp_path / "models" / "federated" / "fedavg_cicids_binary.pt",
        "round_history": tmp_path / "results" / "federated" / "cicids" / "fedavg_round_history.csv",
        "client_distribution": tmp_path / "results" / "federated" / "cicids" / "fedavg_client_distribution.csv",
        "client_logs": tmp_path / "results" / "federated" / "cicids" / "fedavg_client_logs.csv",
        "test_metrics": tmp_path / "results" / "federated" / "cicids" / "fedavg_test_metrics.json",
        "confusion_matrix": tmp_path / "results" / "federated" / "cicids" / "fedavg_confusion_matrix.csv",
        "manifest": tmp_path / "results" / "audits" / "fedavg_manifest_cicids2018.json",
    }
    validation = {
        "paths": {
            "X_train": tmp_path / "X_train.npy",
            "y_train": tmp_path / "y_train.npy",
            "X_val": tmp_path / "X_val.npy",
            "y_val": tmp_path / "y_val.npy",
            "X_test": tmp_path / "X_test.npy",
            "y_test": tmp_path / "y_test.npy",
            "feature_names": tmp_path / "feature_names.json",
            "label_mapping": tmp_path / "label_mapping.json",
            "preprocessing_manifest": tmp_path / "preprocessing_manifest.json",
        },
        "references": config.raw["centralized_reference"],
    }

    payload = build_manifest_payload(
        config=config,
        config_path=config.path,
        validation=validation,
        client_distribution=[],
        device_name="cpu",
        cuda_available=False,
        best_round=3,
        output_paths=output_paths,
        created_at_utc="2026-06-24T00:00:00+00:00",
    )

    assert payload["dataset"] == "cicids2018"
    assert payload["input_dim"] == 77
    assert payload["no_unsw_fedavg_rerun"] is True
    assert payload["no_security_or_attack_simulation"] is True
    assert payload["no_robust_aggregation"] is True
    assert payload["no_xai"] is True


def test_federated_train_command_parser_exists():
    parser = build_parser()

    args = parser.parse_args(
        [
            "federated-train",
            "--dataset",
            "unsw",
            "--config",
            "configs/federated/unsw_nb15_fedavg.yaml",
            "--execute",
        ]
    )

    assert args.command == "federated-train"
    assert args.dataset == "unsw"
    assert args.execute is True


def test_cicids_federated_train_command_parser_exists():
    parser = build_parser()

    args = parser.parse_args(
        [
            "federated-train",
            "--dataset",
            "cicids",
            "--config",
            "configs/federated/cicids2018_fedavg.yaml",
            "--execute",
        ]
    )

    assert args.command == "federated-train"
    assert args.dataset == "cicids"
    assert args.execute is True


def test_dataset_getitem_handles_non_writable_numpy_rows_without_warning():
    features = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ],
        dtype=np.float32,
    )
    labels = np.array([0, 1], dtype=np.int64)
    features.setflags(write=False)

    indexed = IndexedNumpyDataset(features, labels, np.array([1], dtype=np.int64))
    full = FullNumpyDataset(features, labels)

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        indexed_features, indexed_label = indexed[0]
        full_features, full_label = full[0]

    assert torch.equal(indexed_features, torch.tensor([4.0, 5.0, 6.0]))
    assert indexed_label.item() == 1.0
    assert torch.equal(full_features, torch.tensor([1.0, 2.0, 3.0]))
    assert full_label.item() == 0.0
