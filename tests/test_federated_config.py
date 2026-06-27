from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from secureids.federated.config import (
    FederatedConfigError,
    load_federated_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_unsw_fedavg_config_loads_with_expected_contract():
    config = load_federated_config(
        PROJECT_ROOT / "configs" / "federated" / "unsw_nb15_fedavg.yaml",
        project_root=PROJECT_ROOT,
    )

    assert config.dataset == "unsw_nb15"
    assert config.task == "binary"
    assert config.architecture == "SecureIDSNet"
    assert config.input_dim == 190
    assert config.algorithm == "FedAvg"
    assert config.num_clients == 5
    assert config.client_split == "stratified_iid"
    assert config.raw["training"]["threshold"] == 0.5


def test_cicids_fedavg_config_loads_with_expected_contract():
    config = load_federated_config(
        PROJECT_ROOT / "configs" / "federated" / "cicids2018_fedavg.yaml",
        project_root=PROJECT_ROOT,
    )

    assert config.dataset == "cicids2018"
    assert config.task == "binary"
    assert config.architecture == "SecureIDSNet"
    assert config.input_dim == 77
    assert config.algorithm == "FedAvg"
    assert config.num_clients == 5
    assert config.client_split == "stratified_iid"
    assert config.raw["training"]["threshold"] == 0.5


def test_missing_required_section_fails(tmp_path):
    config = load_federated_config(
        PROJECT_ROOT / "configs" / "federated" / "unsw_nb15_fedavg.yaml",
        project_root=PROJECT_ROOT,
    )
    raw = copy.deepcopy(config.raw)
    del raw["outputs"]
    path = tmp_path / "missing_outputs.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(FederatedConfigError, match="missing required keys"):
        load_federated_config(path, project_root=PROJECT_ROOT)


def test_dataset_input_dim_mismatch_fails(tmp_path):
    config = load_federated_config(
        PROJECT_ROOT / "configs" / "federated" / "cicids2018_fedavg.yaml",
        project_root=PROJECT_ROOT,
    )
    raw = copy.deepcopy(config.raw)
    raw["model"]["input_dim"] = 190
    path = tmp_path / "wrong_input_dim.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(FederatedConfigError, match="input_dim"):
        load_federated_config(path, project_root=PROJECT_ROOT)


def test_future_scope_flags_must_remain_disabled(tmp_path):
    config = load_federated_config(
        PROJECT_ROOT / "configs" / "federated" / "unsw_nb15_fedavg.yaml",
        project_root=PROJECT_ROOT,
    )
    raw = copy.deepcopy(config.raw)
    raw["scope_flags"]["xai_enabled"] = True
    path = tmp_path / "xai_enabled.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(FederatedConfigError, match="xai_enabled"):
        load_federated_config(path, project_root=PROJECT_ROOT)
