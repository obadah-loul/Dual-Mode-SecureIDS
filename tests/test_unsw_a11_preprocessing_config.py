from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from secureids.preprocessing.unsw_a11_config import (
    UNSWA11ConfigError,
    load_unsw_a11_preprocessing_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = PROJECT_ROOT / "configs/preprocessing/experiments/unsw_a11_enhanced_feature_protocol.yaml"


def load_active_raw() -> dict:
    return yaml.safe_load(ACTIVE_CONFIG.read_text(encoding="utf-8"))


def write_yaml(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_active_unsw_a11_preprocessing_config_validates() -> None:
    config = load_unsw_a11_preprocessing_config(ACTIVE_CONFIG, project_root=PROJECT_ROOT)

    assert config.dataset == "unsw_nb15"
    assert config.status == "not_run_yet"
    assert config.protocol_name == "UNSW A11 Enhanced Feature Protocol"
    assert config.planned_outputs["processed_data_dir"] == "data/processed/unsw_a11_enhanced"
    assert config.planned_outputs["preprocessor_artifact"].startswith(
        "models/experiments/preprocessors/unsw_a11_enhanced/"
    )
    assert config.feature_protocol["numeric_only_scaling"] is True
    assert config.feature_protocol["one_hot_columns_not_scaled"] is True


def test_unsw_a11_config_rejects_final_output_paths(tmp_path: Path) -> None:
    raw = deepcopy(load_active_raw())
    raw["planned_outputs"]["preprocessing_audit"] = "results/final/bad_a11_audit.json"
    bad_config = write_yaml(tmp_path / "bad_final_path.yaml", raw)

    with pytest.raises(UNSWA11ConfigError, match="models/final or results/final"):
        load_unsw_a11_preprocessing_config(bad_config, project_root=tmp_path)


def test_unsw_a11_config_rejects_non_a11_processed_path(tmp_path: Path) -> None:
    raw = deepcopy(load_active_raw())
    raw["planned_outputs"]["processed_data_dir"] = "data/processed/unsw_nb15/hierarchical"
    bad_config = write_yaml(tmp_path / "bad_processed_path.yaml", raw)

    with pytest.raises(UNSWA11ConfigError, match="processed_data_dir"):
        load_unsw_a11_preprocessing_config(bad_config, project_root=tmp_path)


def test_unsw_a11_config_requires_not_run_yet_status(tmp_path: Path) -> None:
    raw = deepcopy(load_active_raw())
    raw["status"] = "executed"
    bad_config = write_yaml(tmp_path / "bad_status.yaml", raw)

    with pytest.raises(UNSWA11ConfigError, match="status must remain"):
        load_unsw_a11_preprocessing_config(bad_config, project_root=tmp_path)


def test_unsw_a11_config_rejects_test_fitting_flags(tmp_path: Path) -> None:
    raw = deepcopy(load_active_raw())
    raw["feature_protocol"]["no_test_fitting"] = False
    bad_config = write_yaml(tmp_path / "bad_test_fitting.yaml", raw)

    with pytest.raises(UNSWA11ConfigError, match="no_test_fitting"):
        load_unsw_a11_preprocessing_config(bad_config, project_root=tmp_path)
