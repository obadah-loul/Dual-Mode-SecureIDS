from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from secureids.preprocessing.unsw_a11_config import load_unsw_a11_preprocessing_config
from secureids.preprocessing.unsw_a11_preprocessor import (
    UNSWA11PreprocessingError,
    build_a11_split_summary,
    ensure_output_paths_are_clear,
    fit_a11_feature_transformer,
    inspect_partial_output_state,
    resolve_class_name,
    transform_a11_features,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = PROJECT_ROOT / "configs/preprocessing/experiments/unsw_a11_enhanced_feature_protocol.yaml"


def make_config(tmp_path: Path, *, proto_min_frequency: int = 2):
    raw = yaml.safe_load(ACTIVE_CONFIG.read_text(encoding="utf-8"))
    raw = deepcopy(raw)
    raw["feature_protocol"]["categorical_grouping"]["proto"]["min_frequency"] = proto_min_frequency
    config_path = tmp_path / "unsw_a11_test.yaml"
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_unsw_a11_preprocessing_config(config_path, project_root=tmp_path)


def toy_frame(proto_values: list[str], durations: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": list(range(1, len(proto_values) + 1)),
            "dur": durations,
            "sbytes": [10.0 * (index + 1) for index in range(len(proto_values))],
            "proto": proto_values,
            "service": ["http", "dns", "http", "dns"][: len(proto_values)],
            "state": ["FIN", "CON", "FIN", "CON"][: len(proto_values)],
            "attack_cat": ["Normal", "Generic", "DoS", "Normal"][: len(proto_values)],
            "label": [0, 1, 1, 0][: len(proto_values)],
        }
    )


def test_numeric_only_scaling_leaves_one_hot_columns_binary(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    train = toy_frame(["tcp", "tcp", "udp", "ospf"], [1.0, 2.0, 3.0, 4.0])
    transformer = fit_a11_feature_transformer(train, config)

    x_train, summary = transform_a11_features(transformer, train, split_name="train")
    numeric_count = len(transformer.numeric_columns)
    numeric_block = x_train[:, :numeric_count]
    categorical_block = x_train[:, numeric_count:]

    assert np.allclose(numeric_block.mean(axis=0), 0.0, atol=1e-6)
    assert set(np.unique(categorical_block)).issubset({0.0, 1.0})
    assert summary["one_hot_values_are_binary"] is True


def test_proto_grouping_is_train_only_and_unknown_val_maps_to_other(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    train = toy_frame(["tcp", "tcp", "udp", "ospf"], [1.0, 2.0, 3.0, 4.0])
    val = toy_frame(["tcp", "newproto"], [100.0, 200.0])
    transformer = fit_a11_feature_transformer(train, config)

    _x_val, summary = transform_a11_features(transformer, val, split_name="val")
    proto_rule = transformer.grouping_rules["proto"]

    assert proto_rule.kept_values == ("tcp",)
    assert proto_rule.other_bucket == "__other__"
    assert summary["grouping"]["proto"]["unknown_categories_mapped_to_other"] == 1
    assert summary["grouping"]["proto"]["total_values_mapped_to_other"] == 1


def test_no_test_fitting_numeric_scaler_uses_train_only(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    train = toy_frame(["tcp", "tcp", "udp", "ospf"], [1.0, 2.0, 3.0, 4.0])
    test = toy_frame(["tcp", "newproto"], [1000.0, 2000.0])
    transformer = fit_a11_feature_transformer(train, config)

    assert np.allclose(transformer.scaler.mean_, [2.5, 25.0])
    transform_a11_features(transformer, test, split_name="test")
    assert np.allclose(transformer.scaler.mean_, [2.5, 25.0])


def test_feature_order_consistent_across_splits(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    train = toy_frame(["tcp", "tcp", "udp", "ospf"], [1.0, 2.0, 3.0, 4.0])
    val = toy_frame(["tcp", "newproto"], [10.0, 20.0])
    test = toy_frame(["ospf", "tcp"], [30.0, 40.0])
    transformer = fit_a11_feature_transformer(train, config)

    x_train, _ = transform_a11_features(transformer, train, split_name="train")
    x_val, _ = transform_a11_features(transformer, val, split_name="val")
    x_test, _ = transform_a11_features(transformer, test, split_name="test")

    assert x_train.shape[1] == x_val.shape[1] == x_test.shape[1]
    assert x_train.shape[1] == len(transformer.feature_names)


def test_a11_output_path_isolation_and_no_overwrite_default(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    processed_dir = tmp_path / "data/processed/unsw_a11_enhanced"
    processed_dir.mkdir(parents=True)

    with pytest.raises(UNSWA11PreprocessingError, match="partial outputs"):
        ensure_output_paths_are_clear(config)


@pytest.mark.parametrize(
    "id_to_class",
    [
        {0: "Generic", 1: "Exploits"},
        {"0": "Generic", "1": "Exploits"},
        {"0": "Generic", 1: "Exploits"},
    ],
)
def test_resolve_class_name_supports_int_string_and_mixed_keys(id_to_class: dict) -> None:
    assert resolve_class_name(id_to_class, 0) == "Generic"
    assert resolve_class_name(id_to_class, 1) == "Exploits"


def test_resolve_class_name_errors_with_context_for_missing_id() -> None:
    with pytest.raises(UNSWA11PreprocessingError, match="Unable to resolve"):
        resolve_class_name({"0": "Generic"}, 8)


@pytest.mark.parametrize(
    "id_to_class",
    [
        {0: "Generic", 1: "Exploits"},
        {"0": "Generic", "1": "Exploits"},
        {"0": "Generic", 1: "Exploits"},
    ],
)
def test_build_a11_split_summary_resolves_class_names_without_keyerror(id_to_class: dict) -> None:
    labels = {}
    for split in ("train", "val", "test"):
        labels[split] = {
            "y_binary": np.asarray([1, 1, 0], dtype=np.int64),
            "y_attack_family": np.asarray([0, 1, -1], dtype=np.int64),
            "attack_family_mask": np.asarray([1, 1, 0], dtype=np.int64),
        }
    taxonomy_info = {
        "id_to_class": id_to_class,
        "ignore_index": -1,
        "mask_benign": 0,
        "mask_attack": 1,
    }

    summary = build_a11_split_summary(
        np.zeros((3, 2), dtype=np.float32),
        np.zeros((3, 2), dtype=np.float32),
        np.zeros((3, 2), dtype=np.float32),
        labels,
        taxonomy_info,
    )

    assert summary["train"]["attack_family_class_counts_excluding_ignore_named"] == {
        "Generic": 1,
        "Exploits": 1,
    }
    assert summary["train"]["mask_valid"] is True


def test_partial_output_detection_marks_incomplete_state(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    hierarchical_dir = tmp_path / "data/processed/unsw_a11_enhanced/hierarchical"
    hierarchical_dir.mkdir(parents=True)
    (hierarchical_dir / "feature_names.json").write_text('{"feature_names": []}', encoding="utf-8")

    state = inspect_partial_output_state(config)

    assert state["detected"] is True
    assert state["classification"] == "incomplete"
    assert state["safe_to_use_for_training"] is False
    assert state["requires_cleanup_approval"] is True
