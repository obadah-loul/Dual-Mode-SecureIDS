"""Safe one-sample live inference helpers for the SecureIDS dashboard."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from secureids.artifacts import read_artifact_path, sha256_file
from secureids.training.checkpoints import load_checkpoint

from secureids.models.secureids_hierarchical_advanced_net import (
    SecureIDSHierarchicalAdvancedNet,
)
from secureids.xai.local_attribution import (
    extract_hierarchical_outputs,
    gradient_x_input_attribution,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE_A_MATRIX_PATH = (
    PROJECT_ROOT
    / "results"
    / "experiments"
    / "federated_security"
    / "phase_a_signflip25_attack_defense_matrix.csv"
)


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    display_name: str
    checkpoint_path: Path
    data_dir: Path
    input_dim: int
    attack_head_dim: int
    default_sample_index: int
    expected_true_binary: str
    expected_true_family: str
    hidden_dims: tuple[int, int, int] = (256, 128, 128)
    dropout: float = 0.20
    normalization: str = "layernorm"
    attack_head_type: str = "linear"
    binary_threshold: float = 0.5


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    dataset_name: str
    sample_index: int
    traffic_family: str
    routed_model_label: str


DATASET_SPECS: dict[str, DatasetSpec] = {
    "CICIDS2018": DatasetSpec(
        key="cicids2018",
        display_name="CICIDS2018",
        checkpoint_path=PROJECT_ROOT
        / "models"
        / "experiments"
        / "federated_security"
        / "cicids_hierarchical_clean_fedavg.pt",
        data_dir=PROJECT_ROOT / "data" / "processed" / "cicids2018" / "hierarchical",
        input_dim=77,
        attack_head_dim=14,
        default_sample_index=7921,
        expected_true_binary="Attack",
        expected_true_family="Bot",
    ),
    "UNSW-NB15": DatasetSpec(
        key="unsw_nb15",
        display_name="UNSW-NB15",
        checkpoint_path=PROJECT_ROOT
        / "models"
        / "experiments"
        / "federated_security"
        / "unsw_hierarchical_clean_fedavg.pt",
        data_dir=PROJECT_ROOT / "data" / "processed" / "unsw_nb15" / "hierarchical",
        input_dim=192,
        attack_head_dim=9,
        default_sample_index=2030,
        expected_true_binary="Attack",
        expected_true_family="Exploits",
    ),
}

DATASET_CHOICES: tuple[str, ...] = ("CICIDS2018", "UNSW-NB15")

SCENARIO_SPECS: dict[str, ScenarioSpec] = {
    "CICIDS2018 Bot attack traffic sample": ScenarioSpec(
        name="CICIDS2018 Bot attack traffic sample",
        dataset_name="CICIDS2018",
        sample_index=7921,
        traffic_family="Bot",
        routed_model_label="CICIDS2018 Hierarchical Federated IDS",
    ),
    "CICIDS2018 DDoS attack traffic sample": ScenarioSpec(
        name="CICIDS2018 DDoS attack traffic sample",
        dataset_name="CICIDS2018",
        sample_index=365528,
        traffic_family="DDoS-HOIC",
        routed_model_label="CICIDS2018 Hierarchical Federated IDS",
    ),
    "CICIDS2018 DoS attack traffic sample": ScenarioSpec(
        name="CICIDS2018 DoS attack traffic sample",
        dataset_name="CICIDS2018",
        sample_index=842601,
        traffic_family="DoS-GoldenEye",
        routed_model_label="CICIDS2018 Hierarchical Federated IDS",
    ),
    "CICIDS2018 Brute Force attack traffic sample": ScenarioSpec(
        name="CICIDS2018 Brute Force attack traffic sample",
        dataset_name="CICIDS2018",
        sample_index=1399769,
        traffic_family="SSH-Bruteforce",
        routed_model_label="CICIDS2018 Hierarchical Federated IDS",
    ),
    "UNSW-NB15 Exploits attack traffic sample": ScenarioSpec(
        name="UNSW-NB15 Exploits attack traffic sample",
        dataset_name="UNSW-NB15",
        sample_index=2030,
        traffic_family="Exploits",
        routed_model_label="UNSW-NB15 Hierarchical Federated IDS",
    ),
    "UNSW-NB15 Generic attack traffic sample": ScenarioSpec(
        name="UNSW-NB15 Generic attack traffic sample",
        dataset_name="UNSW-NB15",
        sample_index=11982,
        traffic_family="Generic",
        routed_model_label="UNSW-NB15 Hierarchical Federated IDS",
    ),
    "UNSW-NB15 Reconnaissance attack traffic sample": ScenarioSpec(
        name="UNSW-NB15 Reconnaissance attack traffic sample",
        dataset_name="UNSW-NB15",
        sample_index=901,
        traffic_family="Reconnaissance",
        routed_model_label="UNSW-NB15 Hierarchical Federated IDS",
    ),
}

SCENARIO_CHOICES: tuple[str, ...] = tuple(SCENARIO_SPECS.keys())


def _relative(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _id_to_label(mapping: dict[str, Any], class_id: int | None) -> str | None:
    if class_id is None:
        return None
    labels = mapping.get("id_to_class", mapping)
    return str(labels.get(str(int(class_id)), str(int(class_id))))


def _binary_prediction_label(probability: float, threshold: float) -> str:
    return "Attack" if float(probability) >= float(threshold) else "Benign"


def _hash_sample_row(row: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(row.astype(np.float32, copy=False))
    return hashlib.sha256(contiguous.tobytes()).hexdigest().upper()


def _hash_prediction_record(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def short_hash(value: str | None) -> str:
    """Return a compact SHA-256 display string for dashboards."""

    if not value:
        return "Not available"
    text = str(value)
    if len(text) <= 16:
        return text
    return f"{text[:8]}...{text[-4:]}"


def get_dataset_spec(dataset_name: str) -> DatasetSpec:
    try:
        return DATASET_SPECS[dataset_name]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported dataset {dataset_name!r}; expected one of {DATASET_CHOICES}."
        ) from exc


def get_scenario_choices() -> tuple[str, ...]:
    return SCENARIO_CHOICES


def get_scenario_spec(scenario_name: str) -> ScenarioSpec:
    try:
        return SCENARIO_SPECS[scenario_name]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported scenario {scenario_name!r}; expected one of {SCENARIO_CHOICES}."
        ) from exc


def _load_model(dataset_name: str) -> SecureIDSHierarchicalAdvancedNet:
    spec = get_dataset_spec(dataset_name)
    if not spec.checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {_relative(spec.checkpoint_path)}")

    model = SecureIDSHierarchicalAdvancedNet(
        input_dim=spec.input_dim,
        attack_head_dim=spec.attack_head_dim,
        hidden_dims=spec.hidden_dims,
        dropout=spec.dropout,
        normalization=spec.normalization,
        attack_head_type=spec.attack_head_type,
    )
    checkpoint = load_checkpoint(spec.checkpoint_path, map_location="cpu")
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise KeyError("Checkpoint must be a dict containing model_state_dict.")
    if checkpoint.get('dataset') != spec.key:
        raise ValueError('Checkpoint dataset does not match the selected schema.')
    model.load_state_dict(checkpoint["model_state_dict"])
    model.cpu()
    model.eval()
    return model


def _load_metadata(dataset_name: str) -> dict[str, Any]:
    spec = get_dataset_spec(dataset_name)
    feature_payload = _load_json(spec.data_dir / "feature_names.json")
    feature_names = feature_payload.get('feature_names') if isinstance(feature_payload, dict) else feature_payload
    if not isinstance(feature_names, list):
        raise ValueError("feature_names.json must contain a feature_names list.")
    attack_mapping = _load_json(spec.data_dir / "attack_family_label_mapping.json")
    binary_mapping = _load_json(spec.data_dir / "binary_label_mapping.json")
    if len(feature_names) != spec.input_dim or len(set(feature_names)) != len(feature_names):
        raise ValueError('Feature names must uniquely match the model input dimension.')
    if set(attack_mapping.get('id_to_class', {})) != {str(i) for i in range(spec.attack_head_dim)}:
        raise ValueError('Family label mapping does not match the model taxonomy.')
    return {
        "feature_names": [str(name) for name in feature_names],
        "attack_mapping": attack_mapping,
        "binary_mapping": binary_mapping,
    }


def _load_memmap(path: Path) -> np.ndarray:
    path = read_artifact_path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {_relative(path)}")
    return np.load(path, mmap_mode="r", allow_pickle=False)


def get_dataset_shape(dataset_name: str) -> dict[str, int]:
    spec = get_dataset_spec(dataset_name)
    x_test, _ = _load_sample_layout(spec)
    rows, cols = x_test.shape
    return {"rows": int(rows), "features": int(cols)}


def _load_sample_layout(spec: DatasetSpec) -> tuple[np.ndarray, dict[str, Any] | None]:
    """A compact bundle keeps original test indices without padding fake rows."""
    path = spec.data_dir / 'demo_samples.json'
    if not path.exists():
        return _load_memmap(spec.data_dir / 'X_test.npy'), None
    manifest = _load_json(path)
    if manifest.get('format_version') != 1 or manifest.get('dataset') != spec.key:
        raise ValueError('Compact demo metadata has an incompatible dataset or version.')
    indices = manifest.get('source_indices', [])
    source_rows = manifest.get('source_test_rows')
    if not isinstance(source_rows, int) or isinstance(source_rows, bool) or source_rows <= 0:
        raise ValueError('Compact demo must identify the original test-set size.')
    if not indices or any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < source_rows for i in indices) or len(set(indices)) != len(indices):
        raise ValueError('Compact demo source indices must be unique valid integers.')
    X = _load_memmap(spec.data_dir / 'X_demo.npy')
    if X.ndim != 2 or X.shape != (len(indices), spec.input_dim):
        raise ValueError('Compact sample shape does not match its manifest and model.')
    return X, manifest


def _load_optional_label_array(path: Path) -> np.ndarray | None:
    path = read_artifact_path(path)
    if not path.exists():
        return None
    return np.load(path, mmap_mode="r", allow_pickle=False)


def run_live_inference(
    dataset_name: str,
    sample_index: int | None = None,
    *,
    top_k: int = 8,
) -> dict[str, Any]:
    """Run one-row CPU inference and Gradient x Input attribution."""

    spec = get_dataset_spec(dataset_name)
    metadata = _load_metadata(dataset_name)
    feature_names: list[str] = metadata["feature_names"]
    model = _load_model(dataset_name)

    x_test, demo_manifest = _load_sample_layout(spec)
    num_rows, num_features = x_test.shape
    if int(num_features) != spec.input_dim:
        raise ValueError(
            f"X_test feature count {num_features} does not match model input_dim {spec.input_dim}."
        )
    if len(feature_names) != int(num_features):
        raise ValueError(
            f"Feature name count {len(feature_names)} does not match X_test width {num_features}."
        )

    if sample_index is not None and (isinstance(sample_index, bool) or not isinstance(sample_index, (int, np.integer))):
        raise ValueError('sample_index must be an integer.')
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError('top_k must be a positive integer.')
    index = spec.default_sample_index if sample_index is None else int(sample_index)
    storage_index = index
    if demo_manifest is not None:
        try:
            storage_index = demo_manifest['source_indices'].index(index)
        except ValueError as error:
            raise IndexError('This original test index is not included in the compact demo.') from error
    elif index < 0 or index >= int(num_rows):
        raise IndexError(f"sample_index must be between 0 and {int(num_rows) - 1}.")

    row = np.array(x_test[storage_index], dtype=np.float32, copy=True)
    if not np.all(np.isfinite(row)):
        raise ValueError('Inference input contains nonfinite values.')
    input_tensor = torch.from_numpy(row).unsqueeze(0).to(dtype=torch.float32)

    with torch.no_grad():
        outputs = model(input_tensor)
        binary_logit, attack_logits = extract_hierarchical_outputs(outputs)
        if not torch.isfinite(binary_logit).all() or (attack_logits is not None and not torch.isfinite(attack_logits).all()):
            raise ValueError('Model produced nonfinite outputs.')
        binary_probability = float(torch.sigmoid(binary_logit.reshape(-1)[0]).item())
        binary_prediction = _binary_prediction_label(
            binary_probability,
            spec.binary_threshold,
        )

        predicted_family_id = None
        predicted_family_probability = None
        if binary_prediction == 'Attack' and attack_logits is not None and attack_logits.ndim == 2:
            if tuple(attack_logits.shape) != (1, spec.attack_head_dim):
                raise ValueError('Family logits do not match the configured taxonomy.')
            family_probs = torch.softmax(attack_logits, dim=1)
            predicted_family_id = int(torch.argmax(family_probs, dim=1).item())
            predicted_family_probability = float(family_probs[0, predicted_family_id].item())

    attack_mapping: dict[str, Any] = metadata["attack_mapping"]
    binary_mapping: dict[str, Any] = metadata["binary_mapping"]
    predicted_family = _id_to_label(attack_mapping, predicted_family_id)

    suffix = 'demo' if demo_manifest is not None else 'test'
    y_binary = _load_optional_label_array(spec.data_dir / f'y_binary_{suffix}.npy')
    y_family = _load_optional_label_array(spec.data_dir / f'y_attack_family_{suffix}.npy')
    family_mask = _load_optional_label_array(spec.data_dir / f'attack_family_mask_{suffix}.npy')
    if demo_manifest is not None and any(a is None for a in (y_binary, y_family, family_mask)):
        raise ValueError('Compact demo requires its genuine labels and family masks.')
    for label_array in (y_binary, y_family, family_mask):
        if label_array is not None and (label_array.ndim != 1 or len(label_array) != num_rows):
            raise ValueError('Test label arrays must align with the feature rows.')

    true_binary_id = int(y_binary[storage_index]) if y_binary is not None else None
    true_binary = _id_to_label(binary_mapping, true_binary_id)
    family_label_available = family_mask is None or int(family_mask[storage_index]) == 1
    true_family_id = (
        int(y_family[storage_index])
        if y_family is not None and family_label_available
        else None
    )
    true_family = _id_to_label(attack_mapping, true_family_id)

    binary_correct = (
        None
        if true_binary_id is None
        else (1 if binary_prediction == "Attack" else 0) == int(true_binary_id)
    )
    family_correct = (
        None
        if true_family_id is None or predicted_family_id is None
        else int(predicted_family_id) == int(true_family_id)
    )
    if true_family_id is not None and binary_prediction == 'Benign':
        family_correct = False

    attribution = gradient_x_input_attribution(
        model,
        input_tensor,
        feature_names,
        top_k=top_k,
        binary_threshold=spec.binary_threshold,
        include_family=(binary_prediction == "Attack"),
        family_index=predicted_family_id,
    )

    sample_hash = _hash_sample_row(row)
    prediction_record = {
        "dataset": spec.display_name,
        "sample_index": index,
        "binary_prediction": binary_prediction,
        "binary_probability": round(binary_probability, 12),
        "attack_family_prediction": predicted_family,
        "attack_family_probability": (
            None
            if predicted_family_probability is None
            else round(predicted_family_probability, 12)
        ),
        "sample_hash": sample_hash,
        "model_checkpoint": _relative(spec.checkpoint_path),
        "model_checkpoint_sha256": sha256_file(spec.checkpoint_path),
        "feature_schema_sha256": sha256_file(spec.data_dir / 'feature_names.json'),
        "family_mapping_sha256": sha256_file(spec.data_dir / 'attack_family_label_mapping.json'),
        "xai_method": attribution["method"],
    }
    prediction_hash = _hash_prediction_record(prediction_record)

    return {
        "dataset": spec.display_name,
        "dataset_key": spec.key,
        "sample_index": index,
        "test_set_rows": int(num_rows),
        "sample_storage": 'compact_demo' if demo_manifest is not None else 'full_test_split',
        "source_test_rows": demo_manifest['source_test_rows'] if demo_manifest is not None else int(num_rows),
        "feature_count": int(num_features),
        "model_checkpoint": _relative(spec.checkpoint_path),
        "data_dir": _relative(spec.data_dir),
        "binary_prediction": binary_prediction,
        "binary_probability": binary_probability,
        "binary_threshold": spec.binary_threshold,
        "attack_family_prediction": predicted_family,
        "attack_family_probability": predicted_family_probability,
        "true_binary": true_binary,
        "true_binary_id": true_binary_id,
        "true_attack_family": true_family,
        "true_attack_family_id": true_family_id,
        "binary_correct": binary_correct,
        "attack_family_correct": family_correct,
        "expected_demo_true_binary": spec.expected_true_binary,
        "expected_demo_true_family": spec.expected_true_family,
        "sample_row_sha256": sample_hash,
        "prediction_record_sha256": prediction_hash,
        "prediction_record": prediction_record,
        "integrity_status": 'Fingerprints computed; no independent reference',
        "attribution": attribution,
    }


def load_phase_a_matrix_rows() -> list[dict[str, str]]:
    """Read the final Phase A matrix as supporting evidence only."""

    if not PHASE_A_MATRIX_PATH.exists():
        return []
    with PHASE_A_MATRIX_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


__all__ = [
    "DATASET_CHOICES",
    "DatasetSpec",
    "SCENARIO_CHOICES",
    "ScenarioSpec",
    "get_dataset_shape",
    "get_dataset_spec",
    "get_scenario_choices",
    "get_scenario_spec",
    "load_phase_a_matrix_rows",
    "run_live_inference",
    "short_hash",
]
